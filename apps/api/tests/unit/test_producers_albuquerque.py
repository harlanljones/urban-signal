"""Unit tests for the Albuquerque leaf (US-205): spatial module + CSV field
maps + address composition.

These tests run with NO spine registration (no CityId.ALBUQUERQUE, no
ALIASES entry, no DatasetSpec in REGISTRY). They exercise the leaf directly:

* spatial containment / submarket invariants (pure module imports),
* the per-city field map via the shared ``first_mapped`` mechanism,
* dual original + CSVClient-normalized header spellings,
* ``compose_permit_address`` (SiteNumber+Street+Type+Directional + zip),
* CSVClient watermark exclude / Expired NOT IN (no csv_client.py edits),
* the ADR-0004 geocoding caveats,
* the producer path by monkeypatching ``resolve_field_map`` and
  ``geocode_row_if_declared``.

Partial city: PERMITS CSV only. Do not register AGIS City_Building_Permits,
311 CRM, the frozen business-registration dump, or deeds.
"""

from unittest.mock import patch

import pytest

from src.producers.csv_client import CSVClient, _normalize_header, _row_matches
from src.producers.dob_permits_producer import _parse_datetime
from src.producers.field_maps import first_mapped
from src.producers.field_maps_albuquerque import FIELD_MAP, GEOCODE_CONTEXT
from src.spatial.cities.albuquerque import (
    ALBUQUERQUE_CITY_ID,
    ALBUQUERQUE_DIVISION_BBOXES,
    ALBUQUERQUE_DIVISIONS,
    ALBUQUERQUE_FEED_SPECS,
    ALBUQUERQUE_METRO_BBOX,
    ALBUQUERQUE_PERMITS_ENDPOINT,
    ALBUQUERQUE_PERMITS_FIELD_MAP,
    ALBUQUERQUE_PERMITS_WHERE,
    ALBUQUERQUE_SUBMARKETS,
    compose_permit_address,
    get_albuquerque_dataset,
    is_in_albuquerque_metro,
)
from src.spatial.city_registry import CityId, FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# Live-probe fixtures captured 2026-08-27 from
# data.cabq.gov/.../BuildingPermitsCABQ-en-us.csv.
# Original catalog headers (pre-CSVClient) AND normalized (post-_normalize_header).
_PERMITS_ORIGINAL = {
    "ApplicationPermitNumber": "BPR-2026-00781",
    "SiteNumber": "1017",
    "SiteStreet": "22ND",
    "SiteStreetType": "ST",
    "SiteStreetDirectional": "NW",
    "SiteZip": "87104",
    "PlanCheckValuation": "10000",
    "TypeofWork": "Residential",
    "NumberOfUnits": "0",
    "IssueDate": "20260826",
    "Status": "Issued",
    "Lot": "12",
    "Block": "5",
    "Description": "Interior remodel",
}

_PERMITS_NORMALIZED = {_normalize_header(k): v for k, v in _PERMITS_ORIGINAL.items()}

# Downtown Albuquerque WGS84 (geocoder stub).
_GEOCODED = (35.0844, -106.6504)


# ---------------------------------------------------------------------------
# Spatial invariants (no registry needed)
# ---------------------------------------------------------------------------


class TestAlbuquerqueSpatial:
    def test_metro_contains_center(self):
        assert is_in_albuquerque_metro(35.0844, -106.6504) is True  # Downtown
        assert is_in_albuquerque_metro(35.0808, -106.6056) is True  # Nob Hill
        assert is_in_albuquerque_metro(35.1680, -106.7620) is True  # Volcano Cliffs

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_albuquerque_metro(None, None) is False
        assert is_in_albuquerque_metro(35.0844, -106.6504) is True
        assert is_in_albuquerque_metro(35.6870, -105.9378) is False  # Santa Fe
        assert is_in_albuquerque_metro(31.7619, -106.4850) is False  # El Paso
        assert is_in_albuquerque_metro(39.7392, -104.9903) is False  # Denver

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in ALBUQUERQUE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ALBUQUERQUE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ALBUQUERQUE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ALBUQUERQUE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ALBUQUERQUE_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in ALBUQUERQUE_SUBMARKETS.items():
            bbox = ALBUQUERQUE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in ALBUQUERQUE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ALBUQUERQUE_SUBMARKETS)

    def test_submarkets_carry_albuquerque_city_id(self):
        assert {m.city_id for m in ALBUQUERQUE_SUBMARKETS.values()} == {"albuquerque"}

    def test_divisions_carry_albuquerque_city_id(self):
        assert {d.city_id for d in ALBUQUERQUE_DIVISIONS.values()} == {"albuquerque"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in ALBUQUERQUE_DIVISIONS.items():
            bbox = ALBUQUERQUE_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_six_divisions(self):
        assert 4 <= len(ALBUQUERQUE_DIVISION_BBOXES) <= 8
        assert set(ALBUQUERQUE_DIVISION_BBOXES) == set(ALBUQUERQUE_DIVISIONS)


class TestNoSpineRegistration:
    def test_city_id_enum_has_albuquerque(self):
        assert CityId.ALBUQUERQUE.value == "albuquerque"

    def test_city_id_constant_is_the_leaf_string(self):
        assert ALBUQUERQUE_CITY_ID == "albuquerque"


# ---------------------------------------------------------------------------
# Feed spec (leaf-local get_dataset mirror)
# ---------------------------------------------------------------------------


class TestFeedRegistration:
    def test_exactly_one_feed_type_is_registered(self):
        assert set(ALBUQUERQUE_FEED_SPECS) == {"permits"}

    def test_permits_spec_matches_live_csv(self):
        spec = get_albuquerque_dataset(FeedType.PERMITS)
        assert spec.platform == "csv"
        assert spec.endpoint == ALBUQUERQUE_PERMITS_ENDPOINT
        assert spec.watermark_col == "IssueDate"
        assert spec.watermark_type == "text"
        assert spec.watermark_format == "%Y%m%d"
        assert spec.watermark_exclude == ["20261224"]
        assert spec.id_keys == ["ApplicationPermitNumber"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Albuquerque, NM"
        assert spec.expected_cadence_days == 1
        assert spec.where == ALBUQUERQUE_PERMITS_WHERE
        assert spec.where == "Status NOT IN ('Expired')"
        assert spec.field_map is ALBUQUERQUE_PERMITS_FIELD_MAP

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.COMPLAINTS_311, FeedType.SLA, FeedType.DEEDS],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'albuquerque'.*available"):
            get_albuquerque_dataset(absent_feed)


# ---------------------------------------------------------------------------
# Field map mechanics
# ---------------------------------------------------------------------------


class TestAlbuquerqueFieldMaps:
    def test_permits_map_reads_original_catalog_columns(self):
        row = _PERMITS_ORIGINAL
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "job_id") == "BPR-2026-00781"
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "issuance_date") == "20260826"
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "job_type") == "Residential"
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "cost") == "10000"
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "status") == "Issued"
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "zipcode") == "87104"

    def test_permits_map_reads_normalized_csvclient_columns(self):
        row = _PERMITS_NORMALIZED
        assert "issuedate" in row
        assert "applicationpermitnumber" in row
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "job_id") == "BPR-2026-00781"
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "issuance_date") == "20260826"
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "cost") == "10000"
        assert first_mapped(row, ALBUQUERQUE_PERMITS_FIELD_MAP, "zipcode") == "87104"

    def test_field_map_lists_both_original_and_normalized_spellings(self):
        issuance = ALBUQUERQUE_PERMITS_FIELD_MAP["issuance_date"]
        assert "IssueDate" in issuance
        assert "issuedate" in issuance
        job_id = ALBUQUERQUE_PERMITS_FIELD_MAP["job_id"]
        assert "ApplicationPermitNumber" in job_id
        assert "applicationpermitnumber" in job_id

    def test_map_is_the_exported_field_map(self):
        assert FIELD_MAP["permits"] is ALBUQUERQUE_PERMITS_FIELD_MAP

    def test_geocode_context_is_albuquerque_nm(self):
        assert GEOCODE_CONTEXT == "Albuquerque, NM"

    def test_permits_has_no_coordinate_candidates(self):
        assert "latitude" not in ALBUQUERQUE_PERMITS_FIELD_MAP
        assert "longitude" not in ALBUQUERQUE_PERMITS_FIELD_MAP

    def test_raw_parts_are_not_a_geocodeable_address(self):
        # first_mapped on a raw CSV row hits SiteNumber / sitenumber ("1017"),
        # which is below geocode_row_if_declared's length-6 floor. Spine must
        # call compose_permit_address before geocoding.
        raw = first_mapped(_PERMITS_NORMALIZED, ALBUQUERQUE_PERMITS_FIELD_MAP, "address_street")
        assert raw == "1017"
        assert len(raw) < 6


class TestAddressComposition:
    def test_compose_from_normalized_parts(self):
        composed = compose_permit_address(_PERMITS_NORMALIZED)
        assert composed == "1017 22ND ST NW, Albuquerque, NM 87104"

    def test_compose_from_original_parts(self):
        composed = compose_permit_address(_PERMITS_ORIGINAL)
        assert composed == "1017 22ND ST NW, Albuquerque, NM 87104"

    def test_compose_skips_empty_directional(self):
        row = {**_PERMITS_NORMALIZED, "sitestreetdirectional": ""}
        assert compose_permit_address(row) == "1017 22ND ST, Albuquerque, NM 87104"

    def test_compose_without_zip_still_carries_city_context(self):
        row = {**_PERMITS_NORMALIZED, "sitezip": ""}
        assert compose_permit_address(row) == "1017 22ND ST NW, Albuquerque, NM"


# ---------------------------------------------------------------------------
# CSVClient predicates (leaf-only; do not edit csv_client.py)
# ---------------------------------------------------------------------------


CABQ_SAMPLE_CSV = (
    "ApplicationPermitNumber,SiteNumber,SiteStreet,SiteStreetType,"
    "SiteStreetDirectional,SiteZip,PlanCheckValuation,TypeofWork,IssueDate,Status\n"
    '"BPR-2026-00781","1017","22ND","ST","NW","87104","10000","Residential","20260826","Issued"\n'
    '"BPR-2025-01761","1601","ARROYO VISTA","","","87105","0","Residential","20261224","Issued"\n'
    '"BPR-2024-00001","100","CENTRAL","AVE","SW","87102","5000","Residential","20240101","Expired"\n'
    '"BPC-2026-00621","2201","MENAUL","BLVD","NE","87107","250000","Commercial","20260826","Complete"\n'
)


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class _FakeHTTP:
    def __init__(self, text):
        self.text = text

    def get(self, url):
        return _FakeResponse(self.text)


class TestCsvClientPredicates:
    def test_headers_normalize_to_issuedate(self):
        assert _normalize_header("IssueDate") == "issuedate"
        assert _normalize_header("ApplicationPermitNumber") == "applicationpermitnumber"
        client = CSVClient(http_client=_FakeHTTP(CABQ_SAMPLE_CSV))
        batches = list(client.paginate(ALBUQUERQUE_PERMITS_ENDPOINT))
        keys = set(batches[0][0].keys())
        assert "issuedate" in keys
        assert "applicationpermitnumber" in keys
        assert "IssueDate" not in keys

    def test_expired_not_in_drops_expired_majority(self):
        issued = {"status": "Issued"}
        complete = {"status": "Complete"}
        expired = {"status": "Expired"}
        assert _row_matches(ALBUQUERQUE_PERMITS_WHERE, issued) is True
        assert _row_matches(ALBUQUERQUE_PERMITS_WHERE, complete) is True
        assert _row_matches(ALBUQUERQUE_PERMITS_WHERE, expired) is False

    def test_status_in_clause_is_a_silent_noop(self):
        # CSVClient has no IN matcher; unknown clauses pass. Spine must not
        # ship Status IN ('Issued','Complete') — it would ingest Expired.
        expired = {"status": "Expired"}
        assert _row_matches("Status IN ('Issued','Complete')", expired) is True

    def test_watermark_exclude_drops_20261224_sentinels(self):
        sentinel = {"issuedate": "20261224"}
        live = {"issuedate": "20260826"}
        kwargs = dict(
            watermark_col="IssueDate",
            watermark_format="%Y%m%d",
            watermark_exclude=["20261224"],
        )
        assert _row_matches("IssueDate > '20260101'", sentinel, **kwargs) is False
        assert _row_matches("IssueDate > '20260101'", live, **kwargs) is True

    def test_paginate_applies_where_and_excludes_sentinels(self):
        client = CSVClient(http_client=_FakeHTTP(CABQ_SAMPLE_CSV))
        batches = list(
            client.paginate(
                ALBUQUERQUE_PERMITS_ENDPOINT,
                where_clause=f"({ALBUQUERQUE_PERMITS_WHERE}) AND (IssueDate > '20260101')",
                watermark_col="IssueDate",
                watermark_format="%Y%m%d",
                watermark_exclude=["20261224"],
            )
        )
        rows = [r for batch in batches for r in batch]
        ids = [r["applicationpermitnumber"] for r in rows]
        assert "BPR-2024-00001" not in ids  # Expired
        assert "BPR-2025-01761" not in ids  # 20261224 sentinel
        assert ids == ["BPR-2026-00781", "BPC-2026-00621"]


# ---------------------------------------------------------------------------
# Geocoding caveats (ADR 0004) — registry-free
# ---------------------------------------------------------------------------


class TestGeocodingCaveats:
    def test_street_only_has_no_state_token_so_context_appends(self):
        assert _STATE_RE.search("1017 22ND ST NW".upper()) is None

    def test_composed_address_already_has_nm(self):
        composed = compose_permit_address(_PERMITS_NORMALIZED)
        assert _STATE_RE.search(composed.upper()) is not None
        assert "ALBUQUERQUE, NM" in composed.upper()

    def test_unit_designator_normalization_preserves_context(self):
        norm = normalize_address("1017 22ND ST NW UNIT 2, ALBUQUERQUE, NM")
        assert "UNIT" not in norm
        assert "ALBUQUERQUE" in norm
        assert "NM" in norm

    def test_yyyymmdd_parses_via_fromisoformat(self):
        # Python 3.11+ datetime.fromisoformat accepts YYYYMMDD, which is the
        # first branch of _parse_datetime — no spine format-tuple edit needed.
        parsed = _parse_datetime("20260826")
        assert parsed is not None
        assert parsed.year == 2026 and parsed.month == 8 and parsed.day == 26


# ---------------------------------------------------------------------------
# Producer path with the Albuquerque field map injected (no spine registration)
# ---------------------------------------------------------------------------


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


def _patch_resolve_and_geocode(monkeypatch, geocode_side_effect):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["permits"],
    )
    captured = []

    def fake_geocode(city_id, feed_value, address, context=None):
        captured.append((city_id, feed_value, address, context))
        return geocode_side_effect

    monkeypatch.setattr(
        "src.spatial.geocoder.geocode_row_if_declared",
        fake_geocode,
    )
    return captured


class TestAlbuquerquePermitParsing:
    def test_address_only_permit_uses_declared_geocoder(self, permits, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, _GEOCODED)
        row = dict(_PERMITS_NORMALIZED)
        row["address_street"] = compose_permit_address(row)
        event = permits.parse_socrata_row(row, city_id="albuquerque")
        assert event is not None
        assert event.job_id == "BPR-2026-00781"
        assert event.city_id == "albuquerque"
        assert event.latitude == pytest.approx(35.0844)
        assert event.longitude == pytest.approx(-106.6504)
        assert event.h3_res7 is not None
        assert event.status == "Issued"
        assert event.issuance_date is not None
        assert event.issuance_date.year == 2026
        assert captured == [
            (
                "albuquerque",
                "permits",
                "1017 22ND ST NW, Albuquerque, NM 87104",
                None,
            )
        ]

    def test_original_header_row_also_parses(self, permits, monkeypatch):
        _patch_resolve_and_geocode(monkeypatch, _GEOCODED)
        row = dict(_PERMITS_ORIGINAL)
        row["address_street"] = compose_permit_address(row)
        event = permits.parse_socrata_row(row, city_id="albuquerque")
        assert event is not None
        assert event.job_id == "BPR-2026-00781"
        assert event.estimated_cost == pytest.approx(10000.0)

    def test_raw_house_number_alone_is_dropped(self, permits, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP["permits"],
        )
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        assert permits.parse_socrata_row(_PERMITS_NORMALIZED, city_id="albuquerque") is None
