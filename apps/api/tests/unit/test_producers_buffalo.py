"""Unit tests for the Buffalo, NY leaf (US-349): spatial module + field maps
+ SLA producer parse wiring.

Buffalo is a ONE-FEED PARTIAL metro: Restaurant Licenses (Socrata
``4pp3-qkuj``, Tier 1, native WGS84 latitude/longitude). Permits (broken
backends), 311 (frozen 2024-05-10), and deeds stay absent.

Tests pass WITHOUT a spine registration (no CityId.BUFFALO, no REGISTRY
assertions — "buffalo" stays a plain string). Division/borough resolution
and geocode-hook call counts are deliberately NOT asserted: both change
when the spine lands.

Live fixtures captured byte-verbatim 2026-08-27 from
data.buffalony.gov/resource/4pp3-qkuj.json ($where=issdttm IS NOT NULL,
$order=issdttm DESC) — newest rows by watermark, watermark 2026-08-20.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_buffalo import (
    FIELD_MAP,
    NEVER_CANDIDATE_COLUMNS,
    SLA_FIELD_MAP,
)
from src.spatial.cities.buffalo import (
    BUFFALO_CITY_ID,
    BUFFALO_DIVISION_BBOXES,
    BUFFALO_DIVISIONS,
    BUFFALO_FEED_SPECS,
    BUFFALO_METRO_BBOX,
    BUFFALO_SLA_ENDPOINT,
    BUFFALO_SUBMARKETS,
    REGISTRATION,
    get_buffalo_dataset,
    is_in_buffalo_metro,
)

# Newest row on the live re-probe (uniqkey 10012214…, TRATTORIA AROMA,
# 305 BRYANT — source neighborhood "Elmwood Bryant"). Native
# latitude/longitude WGS84; note gpsx/gpsy happen to be degrees on THIS row.
_SLA_FIXTURE_TRATTORIA = {
    "aplickey": "10012214",
    "uniqkey": "100122141004500004016000",
    "licenseno": "RST11-545572",
    "businessname": "TRATTORIA AROMA",
    "code": "RST",
    "descript": "Restaurant",
    "licensedttm": "2007-02-06T00:00:00.000",
    "licstatus": "Active",
    "statusdttm": "2026-08-20T00:00:00.000",
    "expdttm": "2027-09-01T00:00:00.000",
    "prclid": "1004500004016000",
    "gpsx": "-78.87831433",
    "gpsy": "42.90915051",
    "issdttm": "2026-08-20T00:00:00.000",
    "address": "305 BRYANT",
    "city": "BUFFALO",
    "state": "NY",
    "zip": "14222",
    "location": {"type": "Point", "coordinates": [-78.87831431760974, 42.90915049281779]},
    "latitude": "42.90915049281779",
    "longitude": "-78.87831431760974",
    "neighborhood": "Elmwood Bryant",
    "council_district": "ELLICOTT",
    "police_district": "District B",
    "census_tract": "67.01",
    "census_block_group": "2",
    "census_block": "2003",
    "census_tract_2010": "67.01",
    "census_block_group_2010": "3",
    "census_block_2010": "3003",
    "tractce20": "006701",
    "geoid20_tract": "36029006701",
    "geoid20_blockgroup": "360290067012",
    "geoid20_block": "360290067012003",
}

# Second co-newest row (KIM EXPRESS, 1829 GENESEE — "Genesee-Moselle"):
# the State Plane-feet gpsx/gpsy row that pins the mixed-CRS caveat.
_SLA_FIXTURE_KIM = {
    "aplickey": "10013621",
    "uniqkey": "100136211014900001003000",
    "licenseno": "RTO11-517017",
    "businessname": "KIM EXPRESS",
    "code": "RTO",
    "descript": "Restaurant Take Out",
    "licensedttm": "2001-08-28T00:00:00.000",
    "licstatus": "Active",
    "statusdttm": "2026-08-20T00:00:00.000",
    "expdttm": "2027-09-01T00:00:00.000",
    "prclid": "1014900001003000",
    "gpsx": "1063508.89269",
    "gpsy": "1062476.00952",
    "issdttm": "2026-08-20T00:00:00.000",
    "address": "1829 GENESEE",
    "city": "BUFFALO",
    "state": "NY",
    "zip": "14211",
    "location": {"type": "Point", "coordinates": [-78.81397609337903, 42.91247127855801]},
    "latitude": "42.91247127855801",
    "longitude": "-78.81397609337903",
    "neighborhood": "Genesee-Moselle",
    "council_district": "LOVEJOY",
    "police_district": "District C",
    "census_tract": "37",
    "census_block_group": "4",
    "census_block": "4010",
    "census_tract_2010": "37",
    "census_block_group_2010": "3",
    "census_block_2010": "3004",
    "tractce20": "003700",
    "geoid20_tract": "36029003700",
    "geoid20_blockgroup": "360290037004",
    "geoid20_block": "360290037004010",
}

# Third co-newest row (JUST PIZZA, 2350 DELAWARE — "North Park").
_SLA_FIXTURE_JUST_PIZZA = {
    "aplickey": "10013716",
    "uniqkey": "100137160786300005002100",
    "licenseno": "RTO11-526209",
    "businessname": "JUST PIZZA",
    "code": "RTO",
    "descript": "Restaurant Take Out",
    "licensedttm": "2002-10-22T00:00:00.000",
    "licstatus": "Active",
    "statusdttm": "2026-08-20T00:00:00.000",
    "expdttm": "2027-09-01T00:00:00.000",
    "prclid": "0786300005002100",
    "gpsx": "-78.868963",
    "gpsy": "42.94815391",
    "issdttm": "2026-08-20T00:00:00.000",
    "address": "2350 DELAWARE",
    "city": "BUFFALO",
    "state": "NY",
    "zip": "14216",
    "location": {"type": "Point", "coordinates": [-78.86862854081987, 42.94825983377587]},
    "latitude": "42.94825983377587",
    "longitude": "-78.86862854081987",
    "neighborhood": "North Park",
    "council_district": "NORTH",
    "police_district": "District D",
    "census_tract": "50",
    "census_block_group": "1",
    "census_block": "1004",
    "census_tract_2010": "50",
    "census_block_group_2010": "1",
    "census_block_2010": "1004",
    "tractce20": "005000",
    "geoid20_tract": "36029005000",
    "geoid20_blockgroup": "360290050001",
    "geoid20_block": "360290050001004",
}


def _patch_resolve(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["sla"],
    )


class TestBuffaloSpatial:
    def test_metro_bbox_sanity(self):
        assert BUFFALO_METRO_BBOX["min_lat"] < BUFFALO_METRO_BBOX["max_lat"]
        assert BUFFALO_METRO_BBOX["min_lng"] < BUFFALO_METRO_BBOX["max_lng"]

    def test_is_in_buffalo_metro_rejects_missing_coordinates(self):
        assert is_in_buffalo_metro(None, None) is False

    def test_is_in_buffalo_metro_rejects_other_cities(self):
        assert is_in_buffalo_metro(43.1566, -77.6088) is False  # Rochester
        assert is_in_buffalo_metro(43.0481, -76.1474) is False  # Syracuse
        assert is_in_buffalo_metro(40.7128, -74.0060) is False  # NYC
        assert is_in_buffalo_metro(42.8864, -79.5) is False     # west of the river (Fort Erie)

    def test_live_fixture_coordinates_are_contained(self):
        for row in (_SLA_FIXTURE_TRATTORIA, _SLA_FIXTURE_KIM, _SLA_FIXTURE_JUST_PIZZA):
            assert is_in_buffalo_metro(float(row["latitude"]), float(row["longitude"]))

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in BUFFALO_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= BUFFALO_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= BUFFALO_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= BUFFALO_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= BUFFALO_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in BUFFALO_SUBMARKETS.items():
            bbox = BUFFALO_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in BUFFALO_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(BUFFALO_SUBMARKETS)

    def test_submarkets_carry_the_buffalo_city_id(self):
        assert {m.city_id for m in BUFFALO_SUBMARKETS.values()} == {"buffalo"}

    def test_city_id_and_registration_shape(self):
        assert BUFFALO_CITY_ID == "buffalo"
        assert REGISTRATION.metro_bbox is BUFFALO_METRO_BBOX
        assert REGISTRATION.submarkets is BUFFALO_SUBMARKETS
        assert len(REGISTRATION.divisions) == 6
        assert len(BUFFALO_SUBMARKETS) == 8

    def test_required_real_neighborhoods_present(self):
        assert set(BUFFALO_SUBMARKETS) == {
            "Canalside",
            "Larkinville",
            "Allentown",
            "Elmwood Village",
            "Hertel Avenue",
            "Black Rock",
            "Broadway-Fillmore",
            "University Heights",
        }


class TestBuffaloFeedSpecs:
    def test_sla_spec_shape(self):
        spec = BUFFALO_FEED_SPECS["sla"]
        assert spec["endpoint"] == BUFFALO_SLA_ENDPOINT
        assert BUFFALO_SLA_ENDPOINT == "https://data.buffalony.gov/resource/4pp3-qkuj.json"
        assert spec["platform"] == "socrata"
        assert spec["watermark_col"] == "issdttm"
        assert spec["id_keys"] == ["uniqkey", "licenseno", "aplickey"]
        assert spec["producer_key"] == "sla"
        assert spec["topic_key"] == "topic_sla"

    def test_null_guard_and_order_are_pinned(self):
        extra = BUFFALO_FEED_SPECS["sla"]["extra"]
        # Socrata orders NULLs first on issdttm DESC; 2/1429 rows are null.
        assert extra["where"] == "issdttm IS NOT NULL"
        assert extra["order_by"] == "issdttm DESC"
        assert extra["needs_geocode"] is False

    def test_get_buffalo_dataset_resolves_sla(self, monkeypatch):
        _patch_resolve(monkeypatch)
        from src.spatial.city_registry import FeedType

        spec = get_buffalo_dataset(FeedType.SLA)
        assert spec.endpoint == BUFFALO_SLA_ENDPOINT
        assert spec.platform == "socrata"
        assert spec.watermark_col == "issdttm"
        assert spec.where == "issdttm IS NOT NULL"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.needs_geocode is False

    def test_get_buffalo_dataset_rejects_unregistered_feeds(self):
        class _Feed:
            value = "permits"

        with pytest.raises(KeyError, match="buffalo"):
            get_buffalo_dataset(_Feed())


class TestBuffaloFieldMaps:
    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["licenseno", "uniqkey"]
        assert SLA_FIELD_MAP["dba"] == ["businessname"]
        assert SLA_FIELD_MAP["premises_name"] == ["businessname"]
        assert SLA_FIELD_MAP["license_type"] == ["descript", "code"]
        assert SLA_FIELD_MAP["effective_date"] == ["issdttm"]
        assert SLA_FIELD_MAP["expiration_date"] == ["expdttm"]
        assert SLA_FIELD_MAP["status"] == ["licstatus"]
        assert SLA_FIELD_MAP["address_street"] == ["address"]

    def test_source_neighborhood_column_maps_to_borough_slot(self):
        assert SLA_FIELD_MAP["borough"] == ["neighborhood"]
        row = dict(_SLA_FIXTURE_TRATTORIA)
        assert first_mapped(row, SLA_FIELD_MAP, "borough") == "Elmwood Bryant"
        assert first_mapped(_SLA_FIXTURE_KIM, SLA_FIELD_MAP, "borough") == "Genesee-Moselle"

    def test_native_wgs84_coordinates_are_the_candidates(self):
        row = dict(_SLA_FIXTURE_TRATTORIA)
        assert first_mapped(row, SLA_FIELD_MAP, "latitude") == "42.90915049281779"
        assert first_mapped(row, SLA_FIELD_MAP, "longitude") == "-78.87831431760974"

    def test_mixed_crs_state_plane_columns_never_become_candidates(self):
        """gpsx/gpsy are mixed CRS live (degrees on some rows, State Plane
        feet on others — e.g. KIM EXPRESS's 1063508.89) — they must never be
        coordinate candidates for Buffalo."""
        assert "latitude" not in SLA_FIELD_MAP or SLA_FIELD_MAP["latitude"] == ["latitude"]
        for canonical, candidates in SLA_FIELD_MAP.items():
            for col in candidates:
                assert col not in ("gpsx", "gpsy"), (canonical, col)
        for values in SLA_FIELD_MAP.values():
            for col in values:
                assert col not in NEVER_CANDIDATE_COLUMNS

    def test_fixture_coordinates_are_wgs84_degrees_in_metro(self):
        """latitude/longitude are authoritative even on State Plane gpsx rows."""
        row = _SLA_FIXTURE_KIM
        lat = float(first_mapped(row, SLA_FIELD_MAP, "latitude"))
        lng = float(first_mapped(row, SLA_FIELD_MAP, "longitude"))
        assert abs(lat) <= 90 and abs(lng) <= 180
        assert is_in_buffalo_metro(lat, lng)
        # The State Plane gpsx/gpsy values are NOT degrees.
        assert abs(float(row["gpsx"])) > 180 and abs(float(row["gpsy"])) > 90

    def test_license_id_falls_through_to_uniqkey(self):
        row = dict(_SLA_FIXTURE_TRATTORIA)
        row.pop("licenseno")
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "100122141004500004016000"


class TestBuffaloSLAParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_newest_fixture_parses_through_real_producer_path(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_TRATTORIA, city_id="buffalo")
        assert event is not None
        assert event.city_id == "buffalo"
        assert event.license_id == "RST11-545572"
        assert event.dba == "TRATTORIA AROMA"
        assert event.premises_name == "TRATTORIA AROMA"
        assert event.license_type == "Restaurant"
        assert event.license_status == "Active"
        assert event.address == "305 BRYANT"
        assert event.source_neighborhood == "Elmwood Bryant"

    def test_effective_date_is_the_issuance_stream_not_the_original_license(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_TRATTORIA, city_id="buffalo")
        assert event is not None
        # issdttm (2026-08-20), NOT licensedttm (2007-02-06).
        assert str(event.effective_date).startswith("2026-08-20")
        assert str(event.expiration_date).startswith("2027-09-01")

    def test_coordinates_and_h3_come_from_fixture_latlng(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_TRATTORIA, city_id="buffalo")
        assert event is not None
        assert event.latitude == pytest.approx(42.90915049281779)
        assert event.longitude == pytest.approx(-78.87831431760974)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert is_in_buffalo_metro(event.latitude, event.longitude)

    def test_take_out_fixture_parses_and_is_contained(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_JUST_PIZZA, city_id="buffalo")
        assert event is not None
        assert event.license_id == "RTO11-526209"
        assert event.license_type == "Restaurant Take Out"
        assert event.source_neighborhood == "North Park"
        assert event.latitude == pytest.approx(42.94825983377587)
        assert event.longitude == pytest.approx(-78.86862854081987)
        assert is_in_buffalo_metro(event.latitude, event.longitude)

    def test_state_plane_row_still_geolocates_from_native_columns(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_KIM, city_id="buffalo")
        assert event is not None
        assert event.source_neighborhood == "Genesee-Moselle"
        assert event.latitude == pytest.approx(42.91247127855801)
        assert event.longitude == pytest.approx(-78.81397609337903)
        assert is_in_buffalo_metro(event.latitude, event.longitude)

    def test_license_id_falls_back_to_uniqkey(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        row = dict(_SLA_FIXTURE_TRATTORIA)
        row["licenseno"] = ""
        event = sla.parse_socrata_row(row, city_id="buffalo")
        assert event is not None
        assert event.license_id == "100122141004500004016000"

    def test_renewal_rows_are_distinct_events(self, sla, monkeypatch):
        """licenseno repeats across renewals (probe caveat); two rows sharing
        a license number but differing on issdttm parse to distinct events."""
        _patch_resolve(monkeypatch)
        renewal = dict(_SLA_FIXTURE_TRATTORIA)
        renewal["uniqkey"] = "100122141004500004016001"
        renewal["issdttm"] = "2025-08-21T00:00:00.000"
        first = sla.parse_socrata_row(_SLA_FIXTURE_TRATTORIA, city_id="buffalo")
        second = sla.parse_socrata_row(renewal, city_id="buffalo")
        assert first is not None and second is not None
        assert first.license_id == second.license_id
        assert first.effective_date != second.effective_date
        assert str(second.effective_date).startswith("2025-08-21")
