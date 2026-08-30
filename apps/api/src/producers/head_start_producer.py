"""Head Start service-location producer: the daily anchor feed (US-376).

Emits ``AnchorInstitutionEvent`` with ``category="head_start"`` from the
national Head Start service-location CSV (verified live 2026-08-30:
``s3foa.s3.us-east-1.amazonaws.com/HS_Service_Locations.csv``, daily refresh,
pre-geocoded points, ``funded_slots`` capacity, Open/Closed ``status``).

Openings are dated by detection (first sight or a Closed→Open transition);
closings surface from the status column flipping or a site leaving the
snapshot. State persists under ``head_start_state_dir`` so every daily poll
does not re-emit the ~19k-site stock.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from src.config import settings
from src.producers.anchor_events_spec import AnchorInstitutionEvent
from src.producers.base_producer import BaseKafkaProducer
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)

HEAD_START_AVSC = Path(__file__).parent.parent / "schemas" / "avro" / "anchor_institution_event.avsc"
HEAD_START_STATE_FILENAME = "sites.json"


def _norm(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def site_key(row: dict[str, Any]) -> str:
    """Stable per-site key: grant number + service location name."""
    return f"{_norm(row.get('grant_number'))}|{_norm(row.get('service_location_name'))}"


class HeadStartProducer:
    """Streams the daily Head Start snapshot as anchor-institution events."""

    def __init__(self, bootstrap_servers: str | None = None, client: Any = None,
                 indexer: Any = None, crosswalk: Any = None, producer: Any = None,
                 state_dir: str | Path | None = None):
        # Uniform producer surface for the scheduler platform dispatch.
        self.socrata = None
        self.client = client  # injectable for tests; default: plain HTTP GET
        self.indexer = indexer or H3SpatialIndexer()
        self.crosswalk = crosswalk
        self.producer = producer or BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=HEAD_START_AVSC,
            dlq_topic=settings.topic_dlq,
        )
        self.state_dir = Path(state_dir) if state_dir else Path(settings.head_start_state_dir)
        self.state_path = self.state_dir / HEAD_START_STATE_FILENAME
        self._seen: dict[str, str] | None = None

    # -- state ---------------------------------------------------------- #

    def _load_state(self) -> dict[str, str]:
        if self._seen is None:
            if self.state_path.exists():
                try:
                    self._seen = {str(k): str(v) for k, v in json.loads(self.state_path.read_text()).items()}
                except (OSError, ValueError):
                    self._seen = {}
            else:
                self._seen = {}
        return self._seen

    def _save_state(self) -> None:
        if self._seen is None:
            return
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self._seen, sort_keys=True))

    # -- fetch + parse --------------------------------------------------- #

    def fetch(self, url: str | None = None) -> bytes:
        if self.client is not None:
            return self.client.fetch(url)
        with httpx.Client(timeout=300.0, follow_redirects=True) as http:
            response = http.get(url or settings.head_start_locations_url)
            response.raise_for_status()
            return response.content

    def parse_rows(self, payload: bytes) -> list[dict[str, Any]]:
        text = payload.decode("utf-8-sig", errors="replace")
        rows = []
        for row in csv.DictReader(io.StringIO(text)):
            rows.append({
                "grant_number": _norm(row.get("grant_Number") or row.get("grant_number")),
                "program_type": _norm(row.get("program_type")),
                "service_location_name": _norm(row.get("service_location_name")),
                "address": " ".join(p for p in (
                    _norm(row.get("address_line_one")), _norm(row.get("address_line_two"))) if p) or None,
                "city": _norm(row.get("city")),
                "state": _norm(row.get("state")),
                "zipcode": _norm(row.get("zip")),
                "latitude": _norm(row.get("latitude")),
                "longitude": _norm(row.get("longitude")),
                "county": _norm(row.get("county")),
                "funded_slots": _norm(row.get("funded_slots")),
                "status": _norm(row.get("status")),
            })
        return rows

    # -- event build ------------------------------------------------------ #

    def _city_for(self, lat: float, lng: float) -> str | None:
        if self.crosswalk is None:
            return None
        return self.crosswalk.city_for_point(lat, lng)

    def build_event(self, row: dict[str, Any], event_type: str,
                    detected_at: datetime) -> AnchorInstitutionEvent | None:
        """One sited Head Start service location; unsited rows return None (DLQ)."""
        try:
            lat, lng = float(row["latitude"]), float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            return None
        capacity = int(row["funded_slots"]) if row.get("funded_slots", "").isdigit() else None
        city_id = self._city_for(lat, lng) or "national"
        return AnchorInstitutionEvent(
            city_id=city_id,
            institution_id=site_key(row),
            source="head_start",
            category="head_start",
            event_type=event_type,
            name=row.get("service_location_name") or None,
            address=row.get("address"),
            zipcode=row.get("zipcode") or None,
            capacity=capacity,
            status=row.get("status") or None,
            latitude=lat,
            longitude=lng,
            event_date=detected_at,
            **self.indexer.get_multi_res_hierarchy(lat, lng),
        )

    # -- run -------------------------------------------------------------- #

    def process_snapshot(self, rows: list[dict[str, Any]],
                         detected_at: datetime | None = None) -> dict[str, int]:
        """Diff one daily snapshot against persisted state; emit transitions."""
        seen = self._load_state()
        now = detected_at or datetime.now(UTC)
        counts = {"events": 0, "opened": 0, "closed": 0, "unsited": 0, "stock": 0, "vanished": 0}
        current: dict[str, str] = {}
        for row in rows:
            key = site_key(row)
            if not key.replace("|", ""):
                continue
            status = (row.get("status") or "Open").upper()
            current[key] = status
            previous = seen.get(key)
            if previous == status:
                counts["stock"] += 1
                continue
            event_type = "closed" if (previous == "OPEN" and status == "CLOSED") else "opened"
            event = self.build_event(row, event_type, now)
            if event is None:
                counts["unsited"] += 1
                continue
            self.producer.produce(
                topic=settings.topic_anchor_institutions,
                key=f"{event.city_id}:{event.institution_id}",
                payload=event,
            )
            counts["events"] += 1
            counts[event_type] += 1
        # A site that vanished from the snapshot was a closing, but its
        # geometry went with it: count it, never guess a coordinate.
        for key, previous in seen.items():
            if key not in current and previous == "OPEN":
                counts["vanished"] += 1
        seen.update(current)
        self._save_state()
        return counts

    def run_stream(self, limit: int | None = None, **_) -> int:
        rows = self.parse_rows(self.fetch())
        if limit is not None:
            rows = rows[:limit]
        counts = self.process_snapshot(rows)
        self.producer.flush()
        return counts["events"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Head Start service-location Kafka producer")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    HeadStartProducer().run_stream(limit=args.limit)
