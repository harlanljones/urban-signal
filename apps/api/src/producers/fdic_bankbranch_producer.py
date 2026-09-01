"""FDIC BankFind branch snapshot-diff producer (US-379)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.fdic_bankfind_client import FdicBankFindClient
from src.schemas.models import BankBranchEvent
from src.spatial.h3_indexer import H3SpatialIndexer

FDIC_AVSC = Path(__file__).parent.parent / "schemas" / "avro" / "bank_branch_event.avsc"


def _text(value: Any) -> str | None:
    return str(value).strip() if value not in (None, "") else None


def _date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "")) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


class FdicBankBranchProducer:
    """Emit transitions from the national SERVTYPE=11 branch snapshot."""

    def __init__(self, bootstrap_servers: str | None = None, client: Any = None,
                 indexer: Any = None, state_dir: str | Path | None = None):
        self.client = client or FdicBankFindClient()
        self.fdic = self.client
        self.socrata = None
        self.indexer = indexer or H3SpatialIndexer()
        self.producer = BaseKafkaProducer(bootstrap_servers=bootstrap_servers,
            schema_file_path=FDIC_AVSC, dlq_topic=settings.topic_dlq)
        self.state_path = Path(state_dir or settings.fdic_bankfind_state_dir) / "branches.json"
        self._seen: dict[str, dict[str, Any]] | None = None

    def _load_state(self) -> dict[str, dict[str, Any]]:
        if self._seen is None:
            try:
                self._seen = json.loads(self.state_path.read_text())
            except (OSError, ValueError):
                self._seen = {}
        return self._seen

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._seen, sort_keys=True))
        tmp.replace(self.state_path)

    @staticmethod
    def _id(row: dict[str, Any]) -> str:
        return _text(FdicBankFindClient.field(row, "UNINUM") or
                     FdicBankFindClient.field(row, "UNINUMBR")) or ""

    def build_event(self, row: dict[str, Any], event_type: str,
                    detected_at: datetime | None = None) -> BankBranchEvent | None:
        try:
            lat = float(FdicBankFindClient.field(row, "LATITUDE"))
            lng = float(FdicBankFindClient.field(row, "LONGITUDE"))
        except (TypeError, ValueError):
            return None
        branch_id = self._id(row)
        if not branch_id:
            return None
        established = _date(FdicBankFindClient.field(row, "ESTYMD"))
        stamp = established if event_type == "opened" and established else (detected_at or datetime.now(UTC))
        return BankBranchEvent(
            branch_id=branch_id, event_type=event_type,
            institution_cert=_text(FdicBankFindClient.field(row, "CERT")),
            institution_name=_text(FdicBankFindClient.field(row, "NAME")),
            address=_text(FdicBankFindClient.field(row, "ADDRESS")),
            city=_text(FdicBankFindClient.field(row, "CITY")),
            state=_text(FdicBankFindClient.field(row, "STNAME")),
            zipcode=_text(FdicBankFindClient.field(row, "ZIP")),
            county=_text(FdicBankFindClient.field(row, "COUNTY")),
            latitude=lat, longitude=lng, established_date=established,
            event_date=stamp, date_is_detection=event_type == "closed" or established is None,
            **self._deposits(row), **self.indexer.get_multi_res_hierarchy(lat, lng),
        )

    def _deposits(self, row: dict[str, Any]) -> dict[str, Any]:
        sod = getattr(self, "_sod", {}).get(self._id(row), {})
        year = FdicBankFindClient.field(sod, "YEAR")
        try:
            year = int(year) if year not in (None, "") else None
        except (TypeError, ValueError):
            year = None
        return {"deposits_year": year,
                "deposits_thousands": _number(FdicBankFindClient.field(sod, "DEPSUMBR"))}

    def run_stream(self, limit: int | None = None, **_: Any) -> int:
        seen = self._load_state()
        self._sod = {}
        for batch in self.client.paginate("sod"):
            for row in batch:
                key = self._id(row)
                year = _number(FdicBankFindClient.field(row, "YEAR")) or -1
                if key and (key not in self._sod or year > (self._sod[key].get("YEAR") or -1)):
                    self._sod[key] = row
        current: dict[str, dict[str, Any]] = {}
        emitted = 0
        now = datetime.now(UTC)
        for batch in self.client.paginate("locations"):
            for row in batch:
                if str(FdicBankFindClient.field(row, "SERVTYPE", "")).strip() != "11":
                    continue
                key = self._id(row)
                if not key:
                    continue
                current[key] = {"fingerprint": json.dumps(row, sort_keys=True, default=str), "row": row}
                if key in seen:
                    continue
                event = self.build_event(row, "opened", now)
                if event:
                    self.producer.produce(settings.topic_bank_branches, key, event)
                    emitted += 1
                if limit is not None and emitted >= limit:
                    break
            if limit is not None and emitted >= limit:
                break
        if limit is None:
            for key, prior in seen.items():
                if key not in current:
                    event = self.build_event(prior["row"], "closed", now)
                    if event:
                        self.producer.produce(settings.topic_bank_branches, key, event)
                        emitted += 1
            seen.clear()
            seen.update(current)
            self._save_state()
        self.producer.flush()
        return emitted
