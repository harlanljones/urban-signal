"""NCES CCD school directory + EDGE school geocodes client (US-375).

Both sources are **annual zips whose URLs change per school year** (CCD
embeds a release-date suffix; EDGE numbers the year), so the year→URL
manifests below carry only years verified live from this host (2026-08-30,
byte sizes pinned in the recovered stream log). A year absent from the
manifest raises rather than guessing a URL.

Two parse paths, one transport:

* CCD nonfiscal school directory — a comma-CSV member (the archive also
  carries a SAS member that must be ignored) with quoted fields somewhere in
  the 102k rows, parsed with ``csv.DictReader`` and the repo's header
  normalization.
* EDGE school geocodes — a **pipe-delimited member with no header row**
  (parsing it as CSV silently eats the first school as the header — caught
  live). Fields resolve positionally per ``EDGE_LAYOUT``; only the consumed
  columns are named so an unverifiable guess can never leak into an event.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Generator
from typing import Any

import httpx

from src.producers.csv_client import _decode_csv_bytes, _normalize_header

CCD_SCHOOL_YEAR_URLS = {
    "2023-24": "https://nces.ed.gov/ccd/data/zip/ccd_sch_029_2324_w_1a_073124.zip",
}
EDGE_SCHOOL_YEAR_URLS = {
    "2022-23": "https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_2223.zip",
    "2023-24": "https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_2324.zip",
    "2024-25": "https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_2425.zip",
}

# Verified live 2026-08-30 against the 2023-24 member (pipe-delimited,
# headerless): NCESSCH|LEAID|NAME|…|address|city|state|zip|…|LAT|LON|…|year.
EDGE_LAYOUT = {
    "ncessch": 0,
    "school_name": 2,
    "address": 4,
    "city": 5,
    "state": 6,
    "zip": 7,
    "latitude": 12,
    "longitude": 13,
    "school_year": 22,
}

CCD_MEMBER_SUFFIX = ".csv"


def _member_for(payload: zipfile.ZipFile, suffix: str) -> str:
    members = [n for n in payload.namelist() if n.lower().endswith(suffix)]
    if not members:
        raise ValueError(f"no {suffix!r} member in the archive")
    return members[0]


class NcesCcdClient:
    """Downloads and streams the CCD directory and EDGE geocode files."""

    def __init__(self, timeout_seconds: float = 300.0):
        self.timeout = timeout_seconds

    def _fetch(self, url: str) -> bytes:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content

    @staticmethod
    def _zip(fetched: bytes | None) -> zipfile.ZipFile:
        if fetched is None:
            raise ValueError("no payload fetched")
        return zipfile.ZipFile(io.BytesIO(fetched))

    def school_rows(self, school_year: str = "2023-24", *, fetched: bytes | None = None) -> Generator[list[dict[str, Any]], None, None]:
        """Yield batches of normalized CCD directory rows for one school year."""
        try:
            url = CCD_SCHOOL_YEAR_URLS[school_year]
        except KeyError:
            raise ValueError(
                f"no verified CCD URL for school year {school_year!r}; "
                f"verified years: {sorted(CCD_SCHOOL_YEAR_URLS)}"
            ) from None
        archive = self._zip(fetched if fetched is not None else self._fetch(url))
        text = _decode_csv_bytes(archive.read(_member_for(archive, CCD_MEMBER_SUFFIX)))
        reader = csv.DictReader(io.StringIO(text))
        batch: list[dict[str, Any]] = []
        for row in reader:
            batch.append({_normalize_header(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
            if len(batch) >= 1000:
                yield batch
                batch = []
        if batch:
            yield batch

    def geocode_rows(self, school_year: str = "2023-24", *, fetched: bytes | None = None) -> Generator[list[dict[str, Any]], None, None]:
        """Yield batches of EDGE geocode rows (positional parse, headerless)."""
        try:
            url = EDGE_SCHOOL_YEAR_URLS[school_year]
        except KeyError:
            raise ValueError(
                f"no verified EDGE URL for school year {school_year!r}; "
                f"verified years: {sorted(EDGE_SCHOOL_YEAR_URLS)}"
            ) from None
        archive = self._zip(fetched if fetched is not None else self._fetch(url))
        # The TXT member is pipe-delimited with no header; the archive also
        # carries SAS/XLSX/shapefile members that must never be parsed.
        text = archive.read(_member_for(archive, ".txt")).decode("utf-8", errors="replace")
        batch: list[dict[str, Any]] = []
        for line in io.StringIO(text):
            line = line.rstrip("\r\n")
            if not line:
                continue
            fields = line.split("|")
            row = {name: fields[index].strip() for name, index in EDGE_LAYOUT.items() if index < len(fields)}
            batch.append(row)
            if len(batch) >= 1000:
                yield batch
                batch = []
        if batch:
            yield batch