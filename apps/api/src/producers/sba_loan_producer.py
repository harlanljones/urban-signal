"""SBA 7(a)/504 loan snapshot producer (US-378).

Reads the cumulative FOIA CSV per program (504 + 7a), geocodes the borrower
address (street-first with zip+city fallback), resolves ``city_id`` via
``GeographyCrosswalk.city_for_point``, and emits ``SbaLoanEvent`` records to
``raw.sba.loans``.

There is no per-row watermark — the file as-of date is the watermark. The
scheduler runs once per quarter on the ``/*_Present_*`` file per program.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.sba_client import SbaLoanClient
from src.schemas.models import SbaLoanEvent
from src.spatial.geography_crosswalk import GeographyCrosswalk
from src.spatial.h3_indexer import H3SpatialIndexer
from src.producers.sba_events_spec import (
    SBA_PROGRAMS,
    SBA_FIXED_ASSET,
    naics_sector_of,
    normalize_location_id,
    normalize_program,
    normalize_status,
)

logger = logging.getLogger(__name__)

_STATUS_COLS = ("status", "loanstatus", "loan_status", "chargeoffstatus", "pifstatus")
_NAME_COLS = ("borrowername", "borrname", "name", "businessname", "business_name")
_STREET_COLS = ("borrstreet", "borrowerstreet", "borrower_street", "street", "address", "projectstreet")
_CITY_COLS = ("borrcity", "borrowercity", "borrower_city", "city", "projectcity")
_STATE_COLS = ("borrstate", "borrowerstate", "borrower_state", "state", "projectstate")
_ZIP_COLS = ("borrzip", "borrowerzip", "borrower_zip", "zip", "zipcode", "projectzip")
_DATE_COLS = ("approvaldate", "approval_date", "dateapproved", "date")
_GROSS_COLS = ("grossapproval", "gross_approval", "grossamount", "gross_amount")
_SBA_COLS = ("sbaguaranteedapproval", "sba_guaranteed_approval", "guaranteedamount")
_COUNTY_COLS = ("projectcounty", "project_county", "county", "borrowercounty")


def _first_of(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        val = row.get(k)
        if val is not None and str(val).strip():
            return val
    return None


def _float_val(value: Any, default: float | None = None) -> float | None:
    if value is None or str(value).strip() in ("", "N/A", "."):
        return default
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _date_val(value: Any) -> str | None:
    """Return an ISO date string for a column value that may be a datetime or string."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    if not text or text in ("N/A", "."):
        return None
    from datetime import datetime as _dt
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return _dt.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text[:10] if len(text) >= 10 else None


def _row_key(row: dict[str, Any]) -> str:
    """Composite dedup key from location_id and program."""
    lid = normalize_location_id(row.get("locationid") or row.get("location_id"))
    prog = normalize_program(row.get("program") or row.get("programtype") or "")
    return f"{lid}:{prog}" if lid and prog else f"no_key:{hash(frozenset(row.items()))}"


class SbaLoanProducer:
    """Read SBA 7(a)/504 cumulative FOIA CSV and emit typed loan events."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        client: Any = None,
        crosswalk: GeographyCrosswalk | None = None,
        indexer: Any = None,
        geocoder: Any = None,
    ):
        self.client = client or SbaLoanClient()
        # Compatibility for the scheduler's uniform producer surface.
        self.socrata = None
        self.crosswalk = crosswalk or GeographyCrosswalk()
        self.indexer = indexer or H3SpatialIndexer()
        self.geocoder = geocoder  # may be None; _geocode falls back to zip centroid
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=Path(__file__).parent.parent / "schemas" / "avro" / "sba_loan_event.avsc",
            dlq_topic=settings.topic_dlq,
        )

    def _geocode(self, row: dict[str, Any]) -> tuple[float | None, float | None]:
        """Geocode street-first, fall back to zip+city centroid."""
        street = _first_of(row, _STREET_COLS)
        city = _first_of(row, _CITY_COLS)
        state = _first_of(row, _STATE_COLS)
        zipcode = _first_of(row, _ZIP_COLS)

        if street and self.geocoder is not None:
            parts = [street]
            if city:
                parts.append(city)
            if state:
                parts.append(state)
            if zipcode:
                parts.append(zipcode)
            query = ", ".join(parts)
            try:
                result = self.geocoder.geocode(query)
                if result and hasattr(result, "latitude") and result.latitude is not None:
                    return result.latitude, result.longitude
            except Exception:
                logger.debug("Geocode failed for street query %r, falling back to zip", query, exc_info=True)

        # Fallback: zip centroid
        if zipcode:
            point = self.crosswalk.zip_point(zipcode)
            if point:
                return point.latitude, point.longitude

        return None, None

    def build_event(self, row: dict[str, Any], as_of_date: Any = None) -> SbaLoanEvent | None:
        """Convert one CSV row to an ``SbaLoanEvent``."""
        location_id = normalize_location_id(row.get("locationid") or row.get("location_id"))
        if not location_id:
            return None

        program = normalize_program(row.get("program") or row.get("programtype") or "")
        if not program:
            return None

        lat, lng = self._geocode(row)

        city_id = "national"
        if lat is not None and lng is not None:
            resolved = self.crosswalk.city_for_point(lat, lng)
            if resolved is not None:
                city_id = resolved

        h3 = {}
        if lat is not None and lng is not None:
            try:
                h3 = self.indexer.get_multi_res_hierarchy(lat, lng)
            except Exception:
                pass

        return SbaLoanEvent(
            city_id=city_id,
            program=program,
            location_id=location_id,
            approval_date=_date_val(_first_of(row, _DATE_COLS)),
            gross_approval=_float_val(_first_of(row, _GROSS_COLS)),
            sba_guaranteed_approval=_float_val(_first_of(row, _SBA_COLS)),
            naics_sector=naics_sector_of(row),
            fixed_asset=SBA_FIXED_ASSET.get(program, False),
            status=normalize_status(_first_of(row, _STATUS_COLS)),
            borrower_name=_first_of(row, _NAME_COLS),
            borrower_street=_first_of(row, _STREET_COLS),
            borrower_city=_first_of(row, _CITY_COLS),
            borrower_state=_first_of(row, _STATE_COLS),
            borrower_zip=_first_of(row, _ZIP_COLS),
            project_county=_first_of(row, _COUNTY_COLS),
            latitude=lat,
            longitude=lng,
            as_of_date=as_of_date if hasattr(as_of_date, "isoformat") else None,
            **h3,
        )

    def run_stream(self, limit: int | None = None, **kwargs: Any) -> int:
        """Fetch every program's cumulative FOIA file and emit events.

        Returns the count of events emitted.
        """
        emitted = 0
        for program in SBA_PROGRAMS:
            try:
                primary = self.client.primary_file(program)
            except (ValueError, KeyError) as exc:
                logger.warning("No primary file for program %s: %s", program, exc)
                continue
            as_of_date = primary.as_of_date
            for batch in self.client.loan_rows(program, max_records=limit):
                for row in batch:
                    event = self.build_event(row, as_of_date=as_of_date)
                    if event is None:
                        self.producer.route_to_dlq(
                            settings.topic_sba_loans,
                            _row_key(row),
                            row,
                            "build_event returned None (missing location_id or program)",
                        )
                        continue
                    self.producer.produce(
                        settings.topic_sba_loans,
                        f"{event.city_id}:{event.location_id}:{event.program}",
                        event,
                    )
                    emitted += 1
                    if limit is not None and emitted >= limit:
                        break
                if limit is not None and emitted >= limit:
                    break
            if limit is not None and emitted >= limit:
                break
        self.producer.flush()
        logger.info("SBA loan producer emitted %d events", emitted)
        return emitted
