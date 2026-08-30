"""FMCSA national carrier-license producer (US-373).

Rides the existing ``SLALicenseEvent`` classify→geocode→H3 path as one
national carrier flow: three data.transportation.gov Socrata resources
(Company Census ``az4n-8mr2``, Motus AuthHist ``yu5v-wbh6``, OOS orders
``p2mt-9ige``) as a DatasetSpec-shaped national family beside
``NATIONAL_FEEDS`` — never in the city REGISTRY (see ``fmcsa_specs.py``).

AuthHist and OOS rows carry no address: they join back to the census by
DOT number for the geocode address. Census ``status_code='I'`` includes
dormant shells, not only closures — exits come from AuthHist/OOS events,
never from status I. Rows geocode at street precision with a 3-digit
county-FIPS context; a row that resolves into a registered metro takes that
``city_id``, everything else streams as ``national`` — the stock the metro
slices come from.
"""

from __future__ import annotations

import argparse
import logging
from typing import Any

from src.config import settings
from src.spatial.geography_crosswalk import GeographyCrosswalk

from src.producers.fmcsa_specs import (
    FMCSA_AUTHHIST_SPEC,
    FMCSA_CENSUS_SPEC,
    FMCSA_OOS_SPEC,
)

logger = logging.getLogger(__name__)

NATIONAL_CITY_ID = "national"
_FMCSA_SPECS = {
    "fmcsa_census": FMCSA_CENSUS_SPEC,
    "fmcsa_authhist": FMCSA_AUTHHIST_SPEC,
    "fmcsa_oos": FMCSA_OOS_SPEC,
}
_JOINBACK_KEY = {"fmcsa_authhist": "usdot_number", "fmcsa_oos": "dot_number"}


def _norm(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


class CarrierLicenseProducer:
    """Streams the FMCSA carrier registry as classified license events."""

    def __init__(self, bootstrap_servers: str | None = None, client: Any = None,
                 crosswalk: GeographyCrossflow | None = None, sla: Any = None,
                 geocoder: Any = None, indexer: Any = None):
        self.sla = sla  # SLALicensesProducer, injected per test / wired by spine
        self.client = client
        # Uniform producer surface for the scheduler's platform dispatch.
        self.socrata = None
        self.crosswalk = crosswalk or GeographyCrosswalk()
        self.geocoder = geocoder
        self.indexer = indexer
        self._census_addresses: dict[str, dict[str, str]] = {}

    # ------------------------------------------------------------------ #
    # Join-back                                                          #
    # ------------------------------------------------------------------ #

    def load_census_addresses(self, batches: Iterable[list[dict[str, Any]]]) -> int:
        """Index census address fields by DOT number for AuthHist/OOS join-back."""
        count = 0
        for batch in batches:
            for row in batch:
                dot = _norm(row.get("dot_number"))
                if not dot:
                    continue
                self._census_addresses[dot] = {
                    "phy_street": _norm(row.get("phy_street")),
                    "phy_city": _norm(row.get("phy_city")),
                    "phy_state": _norm(row.get("phy_state")),
                    "phy_zip": _norm(row.get("phy_zip")),
                    "legal_name": _norm(row.get("legal_name")),
                }
                count += 1
        return count

    def _joinback(self, spec_key: str, row: dict[str, Any]) -> dict[str, Any]:
        key = _JOINBACK_KEY.get(spec_key)
        if not key:
            return row
        dot = _norm(row.get(key))
        address = self._census_addresses.get(dot)
        if address:
            merged = dict(row)
            for field, value in address.items():
                merged.setdefault(field, value)
            return merged
        return row

    # ------------------------------------------------------------------ #
    # Parse + geocode + place                                            #
    # ------------------------------------------------------------------ #

    def _parse_row(self, spec_key: str, row: dict[str, Any]):
        """Parse one row through the unmodified SLA path with the FMCSA map."""
        from unittest.mock import patch

        from src.producers import field_maps
        from src.producers.field_maps_fmcsa import _SPEC_FIELD_MAPS
        from src.producers.sla_licenses_producer import SLALicensesProducer

        sla = self.sla or SLALicensesProducer()
        self.sla = sla
        # The FMCSA specs are national, not registered city datasets, so the
        # registry-driven field-map resolver cannot see them; the parse path
        # itself is unmodified — the map injection is the only seam.
        with patch.object(field_maps, "resolve_field_map", return_value=_SPEC_FIELD_MAPS[spec_key]):
            return sla.parse_socrata_row(row, city_id=spec_key)

    def _geocode_event(self, event, row: dict[str, Any]):
        """Street geocode with state context; never guesses a coordinate."""
        if event is None or (event.latitude is not None and event.longitude is not None):
            return event
        if self.geocoder is None:
            return event
        query = ", ".join(
            part for part in (
                _norm(row.get("phy_street")) or _norm(row.get("address")),
                " ".join(p for p in (_norm(row.get("phy_city")), _norm(row.get("phy_state"))) if p),
            ) if part
        )
        if len(query) < 6:
            return event
        try:
            point = self.geocoder.geocode(query)
        except Exception:  # noqa: BLE001 — geocoding must never kill parsing
            return event
        if point is None:
            return event
        event.latitude, event.longitude = point.lat, point.lon
        return event

    def _place(self, event):
        """Registered metro id for the point, else the national catch-all."""
        if event is None:
            return event
        if event.latitude is None or event.longitude is None:
            event.city_id = NATIONAL_CITY_ID
            return event
        metro = self.crosswalk.city_for_point(event.latitude, event.longitude)
        event.city_id = metro or NATIONAL_CITY_ID
        return event

    # ------------------------------------------------------------------ #
    # Spec runs                                                          #
    # ------------------------------------------------------------------ #

    def _client(self):
        if self.client is None:
            from src.producers.socrata_client import SocrataClient

            self.client = SocrataClient()
        return self.client

    def run_spec(self, spec_key: str, limit: int | None = None,
                 batches: Iterable[list[dict[str, Any]]] | None = None) -> dict[str, int]:
        """One FMCSA resource: pull, join-back, parse, place; return counters."""
        spec = _FMCSA_SPECS[spec_key]
        counts = {"rows": 0, "events": 0, "in_metro": 0, "national": 0, "unparsed": 0}
        stream = batches if batches is not None else self._client().paginate(
            spec["endpoint"], batch_size=1000, max_records=limit,
        )
        for batch in stream:
            if spec_key == "fmcsa_census":
                self.load_census_addresses([batch])
            for raw in batch:
                counts["rows"] += 1
                row = self._joinback(spec_key, raw)
                event = self._parse_row(spec_key, row)
                if event is None:
                    counts["unparsed"] += 1
                    continue
                event = self._place(self._geocode_event(event, row))
                counts["in_metro" if event.city_id != NATIONAL_CITY_ID else "national"] += 1
                counts["events"] += 1
                producer = getattr(self.sla, "producer", None)
                if producer is not None:
                    producer.produce(
                        topic=spec["topic"],
                        key=f"{event.city_id}:{event.license_id}",
                        payload=event,
                    )
        if getattr(self.sla, "producer", None) is not None:
            self.sla.producer.flush()
        return counts

    def run_stream(self, spec: str | None = None, limit: int | None = None, **_) -> int:
        """Scheduler entrypoint: one spec or the whole carrier family."""
        keys = [spec] if spec else list(_FMCSA_SPECS)
        total = 0
        for key in keys:
            total += self.run_spec(key, limit=limit)["events"]
        return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FMCSA carrier license Kafka producer")
    parser.add_argument("--spec", default=None, choices=sorted(_FMCSA_SPECS))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    CarrierLicenseProducer().run_stream(spec=args.spec, limit=args.limit)
