"""NCES anchor-institution producer: national school churn (US-375).

Joins the CCD school directory against the EDGE geocode file per school year
and emits ``AnchorInstitutionEvent`` for every status change CCD publishes
explicitly — no diffing. Rows with status ``Open`` never become events; they
are the active-school inventory snapshot (returned for density features
instead). ``RECON_STATUS=Yes`` and ``Changed Boundary/Agency`` rows are
boundary churn, not real openings, and are dropped entirely.

A directory row the EDGE file cannot site goes to the DLQ rather than to a
guessed coordinate. A sited school outside every registered metro is simply
out of scope for a city product and is skipped with a count — most of the
102k national rows are.

Honest tier note: CCD is an annual publication with an ~8–12-month lag, so
these are slow-burn context signals, not flash events; the Head Start daily
feed (US-376) covers the fresh end of the anchor family.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from src.config import settings
from src.producers.anchor_events_spec import (
    ANCHOR_TOPIC,
    CCD_CHARTER_YES,
    CCD_RECON_YES,
    CCD_STATUS_BOUNDARY,
    CCD_STATUS_EVENT_TYPE,
    CCD_STATUS_OPEN,
    AnchorInstitutionEvent,
)
from src.producers.base_producer import BaseKafkaProducer
from src.producers.nces_ccd_client import NcesCcdClient
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)

ANCHOR_AVSC = Path(__file__).parent.parent / "schemas" / "avro" / "anchor_institution_event.avsc"
DEFAULT_SCHOOL_YEAR = "2023-24"
DLQ_UNMATCHED_GEOCODE = "school absent from the EDGE geocode file — no defensible coordinate"
DLQ_BAD_GEOCODE = "EDGE geocode lat/lng not parseable"


def _parse_effective_date(value: Any = None) -> datetime | None:
    """CCD EFFECTIVE_DATE is MM/DD/YYYY in every observed row (verified live)."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%m/%d/%Y").replace(tzinfo=UTC)
    except ValueError:
        return None


def _float(value: Any = None) -> float | None:
    try:
        if value not in (None, ""):
            return float(str(value).strip())
        return None
    except (TypeError, ValueError):
        return None


class NcesAnchorProducer:
    """Emits school open/close/reopen events plus the active-school inventory."""

    def __init__(self, client: Any = None, indexer: Any = None, crosswalk: Any = None,
                 producer: Any = None, bootstrap_servers: str | None = None):
        # Uniform producer surface for the scheduler platform dispatch.
        self.socrata = None
        self.client = client or NcesCcdClient()
        self.indexer = indexer or H3SpatialIndexer()
        self.crosswalk = crosswalk
        self.producer = producer or BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=ANCHOR_AVSC,
            dlq_topic=settings.topic_dlq,
        )

    def build_event(self, row: dict[str, Any], geocode: dict[str, Any],
                    city_id: str) -> AnchorInstitutionEvent | None:
        """Build the event for one filtered CCD row joined to its EDGE geocode."""
        lat = _float(geocode.get("latitude"))
        lng = _float(geocode.get("longitude"))
        if lat is None or lng is None:
            return None
        status = str(row.get("updated_status_text") or "").strip()
        event_type = CCD_STATUS_EVENT_TYPE.get(status)
        if event_type is None:
            return None
        address = " ".join(
            part for part in (str(row.get("mstreet1") or "").strip(),
                              str(row.get("mstreet2") or "").strip(),
                              str(row.get("mstreet3") or "").strip()) if part
        ) or None
        charter = str(row.get("charter_text") or "").strip() == CCD_CHARTER_YES
        effective = _parse_effective_date(row.get("effective_date"))
        if effective is None:
            return None
        return AnchorInstitutionEvent(
            city_id=city_id,
            institution_id=str(row.get("ncessch") or "").strip(),
            source="nces_ccd",
            category="charter" if charter else "school",
            event_type=event_type,
            name=str(row.get("sch_name") or "").strip() or None,
            address=address,
            zipcode=str(row.get("lzip") or "").strip() or None,
            status=status,
            school_year=str(geocode.get("school_year") or "").strip() or None,
            latitude=lat,
            longitude=lng,
            event_date=effective,
            **self.indexer.get_multi_res_hierarchy(lat, lng),
        )

    def load_geocodes(self, school_year: str, *, fetched: bytes | None = None) -> dict[str, dict[str, Any]]:
        """Index the EDGE geocode file by NCESSCH (the join key, both sources)."""
        geocodes: dict[str, dict[str, Any]] = {}
        for batch in self.client.geocode_rows(school_year, fetched=fetched):
            for row in batch:
                ncessch = str(row.get("ncessch") or "").strip()
                if not ncessch:
                    continue
                geocodes[ncessch] = row
        logger.info("Loaded %d EDGE geocodes for %s", len(geocodes), school_year)
        return geocodes

    def _city_for(self, lat: float, lng: float) -> str | None:
        if self.crosswalk is None:
            return None
        return self.crosswalk.city_for_point(lat, lng)

    def process_year(self, school_year: str = DEFAULT_SCHOOL_YEAR, limit: int | None = None,
                     *, school_batches: Iterable[list[dict[str, Any]]] | None = None,
                     geocode_fetched: bytes | None = None) -> dict[str, int]:
        """One CCD year: emit churn events, DLQ unsited rows, return counters."""
        geocodes = self.load_geocodes(school_year, fetched=geocode_fetched)
        counts = {
            "events": 0,
            "inventory": 0,
            "dlq_unmatched": 0,
            "out_of_scope": 0,
            "filtered_status": 0,
            "filtered_recon": 0,
        }
        seen = 0
        for batch in (school_batches if school_batches is not None else self.client.school_rows(school_year)):
            for row in batch:
                seen += 1
                self._process_row(row, geocodes, counts, school_year)
                if limit is not None and seen >= limit:
                    return counts
        return counts

    def _process_row(self, row: dict[str, Any], geocodes: dict[str, dict[str, Any]],
                     counts: dict[str, int], school_year: str) -> None:
        ncessch = str(row.get("ncessch") or "").strip()
        if not ncessch:
            return
        status = str(row.get("updated_status_text") or "").strip()
        if str(row.get("recon_status") or "").strip() == CCD_RECON_YES:
            counts["filtered_recon"] += 1
            return
        if status == CCD_STATUS_BOUNDARY:
            counts["filtered_recon"] += 1
            return
        if status == CCD_STATUS_OPEN:
            # Active inventory, not an event (build_inventory consumes it).
            counts["inventory"] += 1
            return
        if status not in CCD_STATUS_EVENT_TYPE:
            counts["filtered_status"] += 1
            return
        geocode = geocodes.get(ncessch)
        if geocode is None:
            counts["dlq_unmatched"] += 1
            return
        lat = _float(geocode.get("latitude"))
        lng = _float(geocode.get("longitude"))
        if lat is None or lng is None:
            counts["dlq_unmatched"] += 1
            return
        city_id = self._city_for(lat, lng)
        if city_id is None:
            counts["out_of_scope"] += 1
            return
        event = self.build_event(row, geocode, city_id)
        if event is None:
            counts["filtered_status"] += 1
            return
        self.producer.produce(
            topic=settings.topic_anchor_institutions,
            key=f"{event.city_id}:{event.institution_id}",
            payload=event,
        )
        counts["events"] += 1

    def build_inventory(self, school_year: str = DEFAULT_SCHOOL_YEAR, limit: int | None = None,
                        *, school_batches: Iterable[list[dict[str, Any]]] | None = None,
                        geocode_fetched: bytes | None = None) -> list[dict[str, Any]]:
        """Active schools (status Open, RECON != Yes, EDGE-sited) for density features.

        A snapshot, not events: one row per active school per school year,
        consumed as the denominator for anchor-density features. Returned
        rather than produced because its consumer is the feature builder, not
        the event stream.
        """
        geocodes = self.load_geocodes(school_year, fetched=geocode_fetched)
        inventory: list[dict[str, Any]] = []
        seen = 0
        for batch in (school_batches if school_batches is not None else self.client.school_rows(school_year)):
            for row in batch:
                seen += 1
                if str(row.get("recon_status") or "").strip() == CCD_RECON_YES:
                    continue
                if str(row.get("updated_status_text") or "").strip() != CCD_STATUS_OPEN:
                    continue
                ncessch = str(row.get("ncessch") or "").strip()
                geocode = geocodes.get(ncessch)
                if geocode is None:
                    continue
                lat = _float(geocode.get("latitude"))
                lng = _float(geocode.get("longitude"))
                if lat is None or lng is None:
                    continue
                inventory.append({
                    "city_id": self._city_for(lat, lng),
                    "ncessch": ncessch,
                    "name": str(row.get("sch_name") or "").strip() or None,
                    "charter": str(row.get("charter_text") or "").strip() == CCD_CHARTER_YES,
                    "latitude": lat,
                    "longitude": lng,
                    "school_year": school_year,
                })
                if limit is not None and seen >= limit:
                    return inventory
        return inventory

    def run_stream(self, school_year: str = DEFAULT_SCHOOL_YEAR, limit: int | None = None, **_) -> int:
        """Scheduler entrypoint: emit the year's churn events, return the count."""
        return self.process_year(school_year, limit=limit)["events"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NCES anchor institution Kafka producer")
    parser.add_argument("--school-year", default=DEFAULT_SCHOOL_YEAR)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    NcesAnchorProducer().run_stream(school_year=args.school_year, limit=args.limit)
