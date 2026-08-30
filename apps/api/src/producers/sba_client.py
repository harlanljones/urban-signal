'''SBA 7(a)/504 FOIA loan-file client (US-378).

The quarterly wrinkle: the download URL changes every quarter because the
as-of date is embedded in the filename (``FOIA_504_FY2010_Present_asof_
260630.csv``), and SBA does not expose a stable alias. So the client runs a
tiny link-resolution step against the dataset page (``data.sba.gov/dataset/
7a-504-foia``), extracts every ``FOIA_*.csv`` href, and parses each filename
into ``(program, segment, as-of date)``. The ``*_Present_*`` file per program
is the cumulative snapshot; the decade-segmented files are one-time backfill.

Files are large (59 MB - 318 MB) and the portal serves range requests, so
production passes should consume ``loan_rows(...)`` once per quarter with
``ingestion_mode=full`` and upsert on ``(LocationID, Program)`` — the same
HMDA-shaped contract the sweep describes. The as-of date parsed from the
filename is the watermark; the ``AsOfDate`` column in-file corroborates it
per row (both verified 2026-06-30 live).

Header normalization reuses the CSVClient convention (``_normalize_header``):
``AsOfDate`` -> ``asofdate``, ``LocationID`` -> ``locationid``, etc.
'''
from __future__ import annotations

import csv
import io
import re
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
import httpx
from src.producers.csv_client import _normalize_header
from src.producers.sba_events_spec import SBA_DATASET_PAGE
FOIA_CSV_HREF = re.compile('href="(?P<url>[^"]*/FOIA_(?P<program>504|7a)_(?P<segment>FY\\d{4}_(?:Present|FY\\d{4}))_asof_(?P<asof>\\d{6})\\.csv)\\"', re.IGNORECASE)
SBA_ASOF_LENGTH = 6


@dataclass
class SbaFileRef:
    """One FOIA CSV file reference resolved from the dataset page."""
    program: str  # "504" | "7a"
    segment: str  # "fy2010_present" | "fy2010_fy2014" etc.
    url: str
    as_of_date: datetime

    @property
    def is_primary(self) -> bool:
        """Cumulative ``FY..._Present`` file is the primary."""
        return "present" in self.segment


def parse_asof(token: Any = None) -> datetime:
    """``260630`` -> 2026-06-30 (UTC). The filename embeds the as-of date."""
    raw = str(token).strip()
    if not raw or len(raw) != SBA_ASOF_LENGTH or not raw.isdigit():
        raise ValueError(f"not a YYMMDD as-of token: {token!r}")
    return datetime(2000 + int(raw[:2]), int(raw[2:4]), int(raw[4:6]), tzinfo=UTC)


def resolve_files(page_html: str | None = None, dataset_page_url: str | None = None) -> dict[str, list[SbaFileRef]]:
    """Extract and classify every FOIA CSV href from the dataset page HTML.

    Returns ``{"504": [refs...], "7a": [refs...]}`` sorted primary-first.
    Raises ``ValueError`` when the page yields nothing — a redesigned page
    must fail loudly rather than silently ingest a stale quarter.
    """
    found: dict[str, list[SbaFileRef]] = {}
    for match in FOIA_CSV_HREF.finditer(page_html or ""):
        program = match.group("program").lower()
        url = match.group("url")
        if url.startswith("/"):
            base = (dataset_page_url or "").rstrip("/")
            url = f"{base}{url}"
        ref = SbaFileRef(
            program=program,
            segment=match.group("segment").lower(),
            url=url,
            as_of_date=parse_asof(match.group("asof")),
        )
        found.setdefault(program, []).append(ref)
    if not found:
        raise ValueError(
            f"no FOIA CSV links resolved from {dataset_page_url} — the dataset "
            "page layout changed; re-verify the source"
        )
    for refs in found.values():
        refs.sort(key=lambda r: (not r.is_primary, r.segment))
    return found


class _ByteStream(io.RawIOBase):
    '''Adapt an ``httpx`` byte iterator to a blocking file-like for csv.

    Keeps a 59-318 MB FOIA file out of memory: bytes arrive in network chunks
    and ``csv`` pulls them through ``TextIOWrapper`` incrementally — quoted
    embedded newlines still parse correctly because ``csv`` owns the framing.
    '''
    
    def __init__(self, chunks):
        self._chunks = chunks
        self._buffer = b''

    
    def readable(self):
        return True

    
    def read(self, size=-1):
        while size < 0 or len(self._buffer) < size:
            try:
                self._buffer += next(self._chunks)
            except StopIteration:
                break
        if not self._buffer:
            return b''
        if size < 0:
            out, self._buffer = self._buffer, b''
        else:
            out, self._buffer = self._buffer[:size], self._buffer[size:]
        return out




class SbaLoanClient:
    """Link resolution + download + parse for the SBA 7(a)/504 FOIA CSVs."""

    def __init__(self, http_client=None):
        if http_client is not None:
            self.http = http_client
        else:
            self.http = httpx.Client(timeout=300, follow_redirects=True)
        self._resolved = None

    def resolve(self, dataset_page_url=None, force=False):
        """Fetch the dataset page and resolve the current file manifest."""
        if not force and self._resolved:
            return self._resolved
        response = self.http.get(dataset_page_url or SBA_DATASET_PAGE)
        response.raise_for_status()
        self._resolved = resolve_files(response.text, dataset_page_url or SBA_DATASET_PAGE)
        return self._resolved

    def primary_file(self, program: str, dataset_page_url: str | None = None) -> SbaFileRef:
        """The cumulative ``FY..._Present`` file for ``"504"`` or ``"7a"``."""
        program_key = program.strip().lower()
        refs = self.resolve(dataset_page_url).get(program_key, [])
        for ref in refs:
            if ref.is_primary:
                return ref
        raise ValueError(
            f"no cumulative (FY..._Present) FOIA file for program {program_key!r} "
            f"in resolved manifest; known: {[r.segment for r in refs]}"
        )

    def loan_rows(
        self,
        program: str,
        url: str | None = None,
        batch_size: int = 1000,
        max_records: int | None = None,
    ) -> Generator[list[dict[str, Any]], None, None]:
        """Stream batches of normalized rows from a program's FOIA CSV.

        Defaults to the resolved cumulative file; pass ``url`` explicitly for
        backfill segments. Rows keep every source column under the normalized
        header (``locationid``, ``grossapproval``, ``borrstreet``, ...). The
        body streams — these files run 59-318 MB quarterly.
        """
        if url is None:
            url = self.primary_file(program).url
        with self.http.stream("GET", url) as response:
            response.raise_for_status()
            stream = _ByteStream(response.iter_bytes())
            text = io.TextIOWrapper(stream, encoding="utf-8-sig", errors="replace")
            try:
                reader = csv.DictReader(text)
                if reader.fieldnames:
                    reader.fieldnames = [_normalize_header(name) for name in reader.fieldnames]
                total = 0
                batch: list[dict[str, Any]] = []
                for row in reader:
                    batch.append(row)
                    total += 1
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                    if max_records is not None and total >= max_records:
                        break
                if batch:
                    yield batch
            finally:
                text.detach()


