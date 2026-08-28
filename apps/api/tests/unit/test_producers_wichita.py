"""Contract tests for Wichita, KS (ArcGIS MABCD building permits)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.wichita import (
    WICHITA_DIVISION_BBOXES,
    WICHITA_DIVISIONS,
    WICHITA_METRO_BBOX,
    WICHITA_SUBMARKETS,
    is_in_wichita_metro,
)
from src.spatial.city_registry import CityId, FeedType

# Recommended DatasetSpec.field_map for US-157. Every entry spells a
# column the shared producer fallback chains cannot reach (mixed-case City of
# Wichita -> MABCD schema); latitude/longitude need no entry because
# ArcGISClient lifts point geometry onto those exact keys before parsing.
# OBJECTID stays out of the job-id chain: it is an edit counter, not a business
# key (Columbus precedent).
WICHITA_FIELD_MAP = {
    "job_id": ["PermitNumber"],
    "issuance_date": ["ApplicationDate"],
    "cost": ["DeclaredValuation"],
    "job_type": ["WorkType", "OccupancyType"],
    "status": ["PermitStatus"],
    "address_street": ["InwardAddress"],
    "zipcode": ["PostalCode"],
    "borough": ["Jurisdiction", "City"],
}


def test_wichita_geometry_is_self_consistent():
    assert is_in_wichita_metro(37.6872, -97.3301)
    # Live row coordinates captured 2026-08-25 (RFS2026-11032, Wichita 67211).
    assert is_in_wichita_metro(37.6645881671311, -97.32921214562072)
    assert not is_in_wichita_metro(35.1495, -90.0490)  # Memphis, TN
    assert not is_in_wichita_metro(None, None)
    for name, bbox in WICHITA_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= WICHITA_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= WICHITA_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= WICHITA_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= WICHITA_METRO_BBOX["max_lng"], name
    claimed = [name for division in WICHITA_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(WICHITA_SUBMARKETS)
    assert {meta.city_id for meta in WICHITA_SUBMARKETS.values()} == {"wichita"}
    assert {meta.borough for meta in WICHITA_SUBMARKETS.values()} == set(WICHITA_DIVISIONS)


def test_wichita_registers_arcgis_permits_and_snap_sla():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.WICHITA
    assert normalize_city("wichita") is city
    assert normalize_city("wichita_ks") is city
    assert normalize_city("ict") is city
    assert REGISTRY[city].job_suffix == "wichita"
    assert REGISTRY[city].state == "KS"
    # US-364 adds the SNAP SLA slice (national FNS feed, State='KS').
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS, FeedType.SLA}

    permits = REGISTRY[city].datasets[FeedType.PERMITS]
    assert permits.platform == "arcgis"
    # Layer index 1 is the permits SDE; layer 0 is Code Enforcement Violations.
    assert permits.endpoint.endswith("/MISC/MABCD/FeatureServer/1")
    assert permits.watermark_col == "ApplicationDate"
    assert permits.id_keys == ["PermitNumber", "OBJECTID"]
    assert permits.interval_seconds == 300.0
    assert permits.producer_key == "permits"
    assert "PermitNumber" in permits.id_keys
    assert permits.expected_cadence_days == 7
    assert permits.oid_field == "OBJECTID"
    assert permits.max_record_count == 2000
    assert permits.field_map == WICHITA_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.COMPLAINTS_311)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)


def _flatten_feature(attributes: dict, geometry: dict, extra_date_fields: tuple[str, ...] = ()) -> dict:
    """Run a raw ArcGIS feature through the production flattener so parser tests
    see exactly what DOBPermitsProducer.parse_socrata_row sees after paginate."""
    from src.producers.arcgis_client import ArcGISClient

    date_fields = {"ApplicationDate", "LastModifiedDate", *extra_date_fields}
    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry}, date_fields=date_fields
    )


PERMITS_ROW = {
    # Live newest-by-ApplicationDate row (OBJECTID 93885) via REST on 2026-08-25,
    # flattened exactly as ArcGISClient._flatten_feature delivers it: attributes
    # dict, point geometry lifted to latitude/longitude, epoch-ms date fields
    # re-encoded to ISO 8601 UTC strings.
    "OBJECTID": 93885,
    "Permit_Id": 490940.0,
    "PermitNumber": "RFS2026-11032",
    "ApplicationDate": 1787617743000,
    "LastModifiedDate": 1787617743000,
    "PermitStatus": "Received",
    "WorkType": "ROOFING",
    "DeclaredValuation": 0.0,
    "OccupancyType": "BUSINESS",
    "City": "WICHITA",
    "PostalCode": "67211",
}
PERMITS_GEOMETRY = {"x": -97.32921214562072, "y": 37.6645881671311}


class TestWichitaPermitParsing:
    """Parse pins against the shared DOBPermitsProducer.

    ``resolve_field_map`` is patched with the exact map recommended for the
    registration because the registry entry itself lands with the spine; the
    registration test above asserts the spec carries this same literal, so the
    two cannot drift once US-157 is wired."""

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=WICHITA_FIELD_MAP,
            ),
        ):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            yield DOBPermitsProducer()

    def _row(self):
        return _flatten_feature(PERMITS_ROW, PERMITS_GEOMETRY)

    def test_live_newest_row_parses(self, producer):
        event = producer.parse_socrata_row(self._row(), city_id="wichita")
        assert event is not None
        assert event.city_id == "wichita"

    def test_job_id_comes_from_permit_number(self, producer):
        event = producer.parse_socrata_row(self._row(), city_id="wichita")
        assert event.job_id == "RFS2026-11032"

    def test_application_date_becomes_issuance_date(self, producer):
        event = producer.parse_socrata_row(self._row(), city_id="wichita")
        assert event.issuance_date is not None
        assert str(event.issuance_date).startswith("2026-08-25")

    def test_status_zip_and_cost_map(self, producer):
        event = producer.parse_socrata_row(self._row(), city_id="wichita")
        assert event.status == "Received"
        assert event.zipcode == "67211"
        assert event.estimated_cost == 0.0

    def test_borough_resolves_to_core_division(self, producer):
        # The coordinate falls inside the WICHITA_CORE division; the source
        # neighborhood (City="WICHITA") is a fallback that the coordinate
        # resolution supersedes.
        event = producer.parse_socrata_row(self._row(), city_id="wichita")
        assert event.borough == "WICHITA_CORE"

    def test_lat_lng_resolve_from_geometry_lift(self, producer):
        event = producer.parse_socrata_row(self._row(), city_id="wichita")
        assert event.latitude == pytest.approx(37.6645881671311)
        assert event.longitude == pytest.approx(-97.32921214562072)

    def test_job_type_from_work_type(self, producer):
        from src.schemas.models import JobType

        event = producer.parse_socrata_row(self._row(), city_id="wichita")
        # "ROOFING" matches no classifier keyword -> the OT fallback.
        assert event.job_type is JobType.OT

    def test_missing_permit_number_drops_the_row(self, producer):
        attrs = {k: v for k, v in PERMITS_ROW.items() if k != "PermitNumber"}
        row = _flatten_feature(attrs, PERMITS_GEOMETRY)
        assert producer.parse_socrata_row(row, city_id="wichita") is None
