"""NPPES weekly incremental diff producer (US-374).

The NPPES weekly V.2 zip is deliberately handled as a leaf feed.  The full
monthly file is a reconciliation input and is not downloaded by this module.
Rows are keyed by ``(NPI, normalized practice address)`` so an address change
becomes a close at the old location and an opening at the new one.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections import defaultdict
from collections.abc import Callable, Iterable, MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.schemas.models import SLALicenseEvent
from src.spatial.geocoder import normalize_address
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)

_NPPES_PREFIX = "Provider "
_TAXONOMY_FIELDS = tuple(
    f"Healthcare Provider Taxonomy Code_{index}" for index in range(1, 16)
)


def _value(row: MutableMapping[str, Any], *names: str) -> str:
    """Read an NPPES column while tolerating CSV header case drift."""
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def classify_taxonomy(row: MutableMapping[str, Any]) -> str | None:
    """Return the primary NUCC taxonomy, excluding DME/supplier 33xx codes."""
    codes = [_value(row, field) for field in _TAXONOMY_FIELDS]
    switches = [
        _value(row, f"Healthcare Provider Primary Taxonomy Switch_{index}").upper()
        for index in range(1, 16)
    ]
    for index, code in enumerate(codes):
        if code and switches[index] == "Y" and not code.startswith("33"):
            return code
    for code in codes:
        if code and not code.startswith("33"):
            return code
    return None


def practice_address(row: MutableMapping[str, Any]) -> str:
    """Build the canonical practice address, never the mailing address."""
    line1 = _value(row, "Provider Business Practice Location Address First Line")
    line2 = _value(row, "Provider Business Practice Location Address Second Line")
    city = _value(row, "Provider Business Practice Location Address City Name")
    state = _value(row, "Provider Business Practice Location Address State Name")
    postal = _value(row, "Provider Business Practice Location Address Postal Code")
    return normalize_address(" ".join(part for part in (line1, line2, city, state, postal) if part))


def _is_po_box(address: str) -> bool:
    return any(token in address.split() for token in ("PO", "P.O", "BOX"))


@dataclass(frozen=True)
class NppesRecord:
    npi: str
    address: str
    taxonomy: str
    name: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    enumeration_date: datetime | None
    deactivation_date: datetime | None

    @property
    def pair_key(self) -> tuple[str, str]:
        return self.npi, self.address

    @property
    def license_id(self) -> str:
        return f"{self.npi}:{self.address}"


class InMemoryNppesStateStore:
    """Small state-store adapter for local runs and tests.

    Deployments can provide any mapping-like object with the same string-keyed
    contract; values are ``NppesRecord`` instances.
    """

    def __init__(self, records: Iterable[NppesRecord] = ()):
        self.records: dict[tuple[str, str], NppesRecord] = {record.pair_key: record for record in records}

    def values(self) -> Iterable[NppesRecord]:
        return self.records.values()

    def replace(self, records: Iterable[NppesRecord]) -> None:
        self.records = {record.pair_key: record for record in records}


class NppesDiffProducer:
    """Produce metro-filtered NPPES weekly changes as ``SLALicenseEvent``."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        producer: BaseKafkaProducer | None = None,
        spatial_indexer: H3SpatialIndexer | None = None,
        zip_centroids: dict[str, tuple[float, float]] | None = None,
    ):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "sla_license_event.avsc"
        self.producer = producer or BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=schema_path,
            dlq_topic=settings.topic_dlq,
        )
        self.spatial_indexer = spatial_indexer or H3SpatialIndexer()
        self.zip_centroids = zip_centroids or {}
        self._geocode_cache: dict[str, tuple[float, float] | None] = {}

    @staticmethod
    def parse_row(row: MutableMapping[str, Any]) -> NppesRecord | None:
        npi = _value(row, "NPI")
        address = practice_address(row)
        taxonomy = classify_taxonomy(row)
        if not npi or not address or not taxonomy:
            return None
        return NppesRecord(
            npi=npi,
            address=address,
            taxonomy=taxonomy,
            name=(
                _value(row, "Provider Organization Name (Legal Business Name)")
                or " ".join(
                    part
                    for part in (
                        _value(row, "Provider First Name"),
                        _value(row, "Provider Middle Name"),
                        _value(row, "Provider Last Name (Legal Name)"),
                    )
                    if part
                )
                or None
            ),
            city=_value(row, "Provider Business Practice Location Address City Name") or None,
            state=_value(row, "Provider Business Practice Location Address State Name") or None,
            postal_code=_value(row, "Provider Business Practice Location Address Postal Code") or None,
            enumeration_date=_parse_date(_value(row, "Provider Enumeration Date")),
            deactivation_date=_parse_date(_value(row, "NPI Deactivation Date")),
        )

    @staticmethod
    def read_weekly_zip(payload: bytes | bytearray | io.BufferedIOBase) -> list[dict[str, str]]:
        """Read the first CSV member from a weekly NPPES zip."""
        raw = payload.read() if hasattr(payload, "read") else bytes(payload)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = [name for name in archive.namelist() if not name.endswith("/") and name.lower().endswith(".csv")]
            if not members:
                raise ValueError("NPPES weekly archive contains no CSV member")
            with archive.open(members[0], "r") as stream:
                return list(csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")))

    def _geo(self, address: str, geocoder: Callable[[str], Any] | Any) -> tuple[float, float] | None:
        if address in self._geocode_cache:
            return self._geocode_cache[address]
        try:
            answer = geocoder(address) if callable(geocoder) else geocoder.geocode(address)
            if answer is None:
                point = None
            elif isinstance(answer, tuple):
                point = (float(answer[0]), float(answer[1]))
            else:
                longitude = getattr(answer, "lon", None)
                if longitude is None:
                    longitude = answer.longitude
                point = (float(answer.lat), float(longitude))
        except (AttributeError, TypeError, ValueError, IndexError):
            point = None
        self._geocode_cache[address] = point
        return point

    @staticmethod
    def _in_bbox(point: tuple[float, float], bbox: dict[str, float]) -> bool:
        lat, lon = point
        return bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lng"] <= lon <= bbox["max_lng"]

    def _event(
        self,
        record: NppesRecord,
        *,
        city_id: str,
        point: tuple[float, float],
        closing: bool = False,
    ) -> SLALicenseEvent:
        lat, lon = point
        h3 = self.spatial_indexer.get_multi_res_hierarchy(lat, lon)
        return SLALicenseEvent(
            city_id=city_id,
            license_id=record.license_id,
            license_type=record.taxonomy,
            premises_name=record.name,
            dba=record.name,
            address=record.address,
            latitude=lat,
            longitude=lon,
            effective_date=None if closing else record.enumeration_date,
            expiration_date=record.deactivation_date if closing else None,
            license_status="INACTIVE" if closing else "ACTIVE",
            **h3,
        )

    def _closing_events(
        self,
        record: NppesRecord,
        previous_records: Iterable[NppesRecord],
        *,
        geocoder: Callable[[str], Any] | Any,
        metro_bboxes: dict[str, dict[str, float]] | None,
        fallback_city_id: str,
    ) -> list[SLALicenseEvent]:
        events: list[SLALicenseEvent] = []
        for old_record in previous_records:
            if old_record.pair_key == record.pair_key:
                continue
            old_point = self._geo(old_record.address, geocoder)
            if old_point is None:
                continue
            city_id = fallback_city_id
            if metro_bboxes:
                city_id = next(
                    (city for city, bbox in metro_bboxes.items() if self._in_bbox(old_point, bbox)),
                    "",
                )
            if city_id:
                events.append(self._event(old_record, city_id=city_id, point=old_point, closing=True))
        return events

    def diff_rows(
        self,
        rows: Iterable[MutableMapping[str, Any]],
        state: InMemoryNppesStateStore,
        *,
        geocoder: Callable[[str], Any] | Any,
        zip_centroids: dict[str, tuple[float, float]] | None = None,
        metro_bboxes: dict[str, dict[str, float]] | None = None,
    ) -> list[SLALicenseEvent]:
        """Diff rows, geocode only metro-filtered additions, and update state."""
        incoming_by_key = {
            record.pair_key: record
            for row in rows
            if (record := self.parse_row(row)) is not None
        }
        incoming = list(incoming_by_key.values())
        zip_centroids = self.zip_centroids if zip_centroids is None else zip_centroids
        previous = {record.pair_key: record for record in state.values()}
        by_npi: dict[str, list[NppesRecord]] = defaultdict(list)
        for record in previous.values():
            by_npi[record.npi].append(record)
        current = dict(previous)
        events: list[SLALicenseEvent] = []

        for record in incoming:
            old = previous.get(record.pair_key)
            changed = old is None or old != record
            current[record.pair_key] = record
            if not changed:
                continue
            previous_records = by_npi.get(record.npi, [])
            candidates = zip_centroids.get(record.postal_code or "") if zip_centroids else None
            city_id = "national"
            if metro_bboxes and candidates:
                city_id = next(
                    (city for city, bbox in metro_bboxes.items() if self._in_bbox(candidates, bbox)),
                    "",
                )
                if not city_id:
                    events.extend(
                        self._closing_events(
                            record,
                            previous_records,
                            geocoder=geocoder,
                            metro_bboxes=metro_bboxes,
                            fallback_city_id="",
                        )
                    )
                    continue
            if _is_po_box(record.address):
                self.producer.route_to_dlq(settings.topic_sla, record.license_id, record, "NPPES practice address is a PO Box")
                continue
            # A ZIP centroid that passes the metro bbox is a safe, deterministic
            # fallback for this coarse churn signal. Without one, geocode the
            # metro-filtered delta and validate the returned point below.
            point = candidates or self._geo(record.address, geocoder)
            if point is None:
                self.producer.route_to_dlq(settings.topic_sla, record.license_id, record, "NPPES address geocode below confidence floor")
                continue
            if metro_bboxes and not candidates:
                city_id = next(
                    (city for city, bbox in metro_bboxes.items() if self._in_bbox(point, bbox)),
                    "",
                )
                if not city_id:
                    events.extend(
                        self._closing_events(
                            record,
                            previous_records,
                            geocoder=geocoder,
                            metro_bboxes=metro_bboxes,
                            fallback_city_id="",
                        )
                    )
                    continue
            events.extend(
                self._closing_events(
                    record,
                    previous_records,
                    geocoder=geocoder,
                    metro_bboxes=metro_bboxes,
                    fallback_city_id=city_id,
                )
            )
            events.append(self._event(record, city_id=city_id, point=point))
            by_npi[record.npi] = [record]
        state.replace(current.values())
        return events

    def process_weekly_zip(self, payload: bytes | bytearray | io.BufferedIOBase, state: InMemoryNppesStateStore, **kwargs: Any) -> list[SLALicenseEvent]:
        return self.diff_rows(self.read_weekly_zip(payload), state, **kwargs)

    def emit(self, events: Iterable[SLALicenseEvent]) -> int:
        count = 0
        for event in events:
            self.producer.produce(settings.topic_sla, event.license_id, event)
            count += 1
        self.producer.flush()
        return count
