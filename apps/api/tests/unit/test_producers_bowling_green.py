"""Unit tests for the Bowling Green leaf (US-300): spatial module + field map
+ PERMITS parse wiring.

Bowling Green (Warren County, KY) registers ONE feed on the city ArcGIS
Server (``webgis.bgky.org`` ``CCPC/CCPC_Building_Permits_2010``): PERMITS
(``/5`` "Building Permits 2010+", ArcGIS Server 11.5). The layer is a
**native point** layer in KY-North State Plane 102680/2247; the client always
requests ``outSR=4326``, so coordinates ride in as WGS84
``latitude``/``longitude`` and ``needs_geocode`` is declared defensively
only. ``non_spatial`` is deliberately NOT set.

Host quirk verified live: ``webgis.bgky.org`` is **ANSI-date-literal** — a
bare ISO watermark comparison (``created_date >= '2026-08-20T00:00:00+00:00'``)
returns ArcGIS error 400, while ``created_date >= DATE '2026-08-20 00:00:00'``
verifies. Because ``created_date`` is a true date-typed column (ISO after
client flatten) no ADR-0005 text-watermark declaration is needed. The ANSI
note is carried in the stream log / spine delta; ``watermarks.py`` is not
edited.

FIELD_MAP caveat: the layer has NO single street line — the address is split
across ``St_Number`` / ``St_Name`` — and no neighborhood/parcel key. Because
native geometry carries the coordinate, ``address_street`` is deliberately
left unmapped so the producer never emits a number-only half-address.

Tests pass WITHOUT a spine registration (no CityId.BOWLING_GREEN): the
producers resolve city_id="bowling_green" as a plain string, the leaf-local
field map is pinned via a resolve_field_map patch, and geocoding is mocked at
src.spatial.geocoder.geocode_row_if_declared (Virginia Beach / Lynchburg
pattern). The floats in the fixtures are post-flatten: ArcGIS epoch-ms
dates are shown as the ISO the client produces, and the point geometry is
pre-folded into ``latitude``/``longitude`` keys.

Live fixtures captured from the 2026-08-28 re-probe (all watermark and
coordinate values byte-verbatim from the /5 query ordered by created_date
DESC). Newest created_date 2026-08-24T18:06:08+00:00; 7d=22, 60d=386,
total=29,691.

Stability contract: these tests assert PARSE fields, H3-from-fixture
coordinates, bbox containment, and field-map mappings — deliberately NOT
division/borough resolution results and NOT geocode-hook call counts, both of
which shift when the spine lands.
"""

import h3
from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_bowling_green import (
    BOWLING_GREEN_PERMITS_FIELD_MAP,
    FIELD_MAP,
    GEOCODE_CONTEXT,
)
from src.producers.watermarks import newest_typed_watermark, typed_watermark_entry
from src.spatial.cities.bowling_green import (
    BOWLING_GREEN_CENTER,
    BOWLING_GREEN_CITY_ID,
    BOWLING_GREEN_DIVISION_BBOXES,
    BOWLING_GREEN_DIVISIONS,
    BOWLING_GREEN_FEED_SPECS,
    BOWLING_GREEN_GEOCODE_CONTEXT,
    BOWLING_GREEN_METRO_BBOX,
    BOWLING_GREEN_PERMITS_ENDPOINT,
    BOWLING_GREEN_SUBMARKETS,
    REGISTRATION,
    get_bowling_green_dataset,
    is_in_bowling_green_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# ---------------------------------------------------------------------------
# Live fixtures (2026-08-28 re-probe, webgis.bgky.org CCPC /FeatureServer/5).
# Post-flatten shape: created_date ISO + latitude/longitude folded from the
# native point geometry. Wire dates were epoch-ms; values byte-verbatim.
# ---------------------------------------------------------------------------

# Newest row (PermitNum 2026-1314) — a 24-unit apartment at 2633 Mt Victor
# Lane. created_date wire 1787594768000 -> 2026-08-24T18:06:08+00:00.
PERMITS_ROW_APARTMENT = {
    "OBJECTID": 113479,
    "PermitNum": "2026-1314",
    "PermitUse": "APARTMENT",
    "St_Number": "2633",
    "St_Name": "MT VICTOR LANE",
    "PermitSqFt": 27312,
    "Year": 2026,
    "PermitCost": 750000.0,
    "Units": 24,
    "GlobalID": "{262CABCC-16A7-4FA0-8D05-FBE92E823F25}",
    "SPID": "2025-86-SDP",
    "created_user": "NIROJ.SHRESTHA@BGKY.ORG",
    "created_date": "2026-08-24T18:06:08+00:00",
    "last_edited_user": "NIROJ.SHRESTHA@BGKY.ORG",
    "last_edited_date": "2026-08-24T18:11:59+00:00",
    "latitude": 36.97789868557926,
    "longitude": -86.39380187748583,
}

# Same project parcel, OBJECTID 113476. Wire 1787594461000 -> 18:01:01.
PERMITS_ROW_APARTMENT_2 = {
    "OBJECTID": 113476,
    "PermitNum": "2026-1316",
    "PermitUse": "APARTMENT",
    "St_Number": "2633",
    "St_Name": "MT VICTOR LANE",
    "PermitSqFt": 24729,
    "Year": 2026,
    "PermitCost": 750000.0,
    "Units": 24,
    "GlobalID": "{51674C75-8639-43DE-8FF5-E227AECBDE7F}",
    "SPID": "2025-86-SDP",
    "created_user": "NIROJ.SHRESTHA@BGKY.ORG",
    "created_date": "2026-08-24T18:01:01+00:00",
    "last_edited_user": "NIROJ.SHRESTHA@BGKY.ORG",
    "last_edited_date": "2026-08-24T18:11:27+00:00",
    "latitude": 36.9781795906834,
    "longitude": -86.39452761123859,
}

# A permit with null value columns (SqFt/Units/SPID all null). Wire
# 1787591674000 -> 2026-08-24T17:14:34+00:00.
PERMITS_ROW_FENCE = {
    "OBJECTID": 113475,
    "PermitNum": "2026-1312",
    "PermitUse": "FENCE",
    "St_Number": "2040",
    "St_Name": "BARBERRY COURT",
    "PermitSqFt": None,
    "Year": 2026,
    "PermitCost": 1200.0,
    "Units": None,
    "GlobalID": "{96F9B088-B709-4D0A-95BE-BD72D94B7FE0}",
    "SPID": None,
    "created_user": "NIROJ.SHRESTHA@BGKY.ORG",
    "created_date": "2026-08-24T17:14:34+00:00",
    "last_edited_user": "NIROJ.SHRESTHA@BGKY.ORG",
    "last_edited_date": "2026-08-24T17:15:26+00:00",
    "latitude": 36.970871784353896,
    "longitude": -86.460453093736,
}

# Accessory-storage permit. Wire 1787591599000 -> 2026-08-24T17:13:19+00:00.
PERMITS_ROW_SHED = {
    "OBJECTID": 113474,
    "PermitNum": "2026-1308",
    "PermitUse": "STORAGE SHED",
    "St_Number": "1506",
    "St_Name": "HIGH STREET",
    "PermitSqFt": 170,
    "Year": 2026,
    "PermitCost": 500.0,
    "Units": None,
    "GlobalID": "{568EB87F-A64D-4655-B6A1-A86E5249E065}",
    "SPID": None,
    "created_user": "NIROJ.SHRESTHA@BGKY.ORG",
    "created_date": "2026-08-24T17:13:19+00:00",
    "last_edited_user": "NIROJ.SHRESTHA@BGKY.ORG",
    "last_edited_date": "2026-08-24T17:14:00+00:00",
    "latitude": 36.98257023384943,
    "longitude": -86.44738433971757,
}

# A coordinate a state-plane leak would look like — the producer's >90/>180
# guard must null it and fall through, mock-recovered by the geocoder.
PERMITS_ROW_STATE_PLANE_LEAK = {
    **PERMITS_ROW_APARTMENT,
    "latitude": 4102849.0,   # KY-North feet, not degrees
    "longitude": 1287263.0,
}

# Mocked ADR-0004 fallback geocode (only reached if native coords were
# nulled — defensive recovery, not the normal path):
PERMITS_GEOCODE_RECOVER = (36.9780, -86.3940)


def _h3_res7(lat: float, lng: float) -> str:
    return h3.cell_to_parent(h3.latlng_to_cell(lat, lng, 9), 7)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


class TestBowlingGreenSpatial:
    def test_city_id_constant(self):
        assert BOWLING_GREEN_CITY_ID == "bowling_green"

    def test_metro_contains_registration_center(self):
        assert is_in_bowling_green_metro(
            BOWLING_GREEN_CENTER["lat"], BOWLING_GREEN_CENTER["lng"]
        ) is True

    def test_metro_contains_known_landmarks(self):
        assert is_in_bowling_green_metro(36.9900, -86.4420) is True  # Fountain Square
        assert is_in_bowling_green_metro(36.9865, -86.4580) is True  # WKU
        assert is_in_bowling_green_metro(36.9780, -86.3940) is True  # Mt Victor
        assert is_in_bowling_green_metro(36.9800, -86.3050) is True  # KY Transpark
        assert is_in_bowling_green_metro(37.0200, -86.5600) is True  # Russellville Rd

    def test_metro_rejects_null_and_neighbors(self):
        assert is_in_bowling_green_metro(None, None) is False
        assert is_in_bowling_green_metro(36.7200, -86.3100) is False  # Plano (Simpson-ish south)
        assert is_in_bowling_green_metro(37.4100, -86.5200) is False  # Leitchfield (Grayson)
        assert is_in_bowling_green_metro(37.0100, -86.0300) is False  # Glasgow (Barren)
        assert is_in_bowling_green_metro(36.6600, -86.1300) is False  # Virginia city edge

    def test_metro_bbox_grounded_in_feed_extent(self):
        """Live /5 feed extent (2026-08-28, outSR=4326): lat 36.795-37.179,
        lng -86.661--86.125. The metro box must cover it with margin."""
        assert BOWLING_GREEN_METRO_BBOX["min_lat"] <= 36.795
        assert BOWLING_GREEN_METRO_BBOX["max_lat"] >= 37.179
        assert BOWLING_GREEN_METRO_BBOX["min_lng"] <= -86.661
        assert BOWLING_GREEN_METRO_BBOX["max_lng"] >= -86.125

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in BOWLING_GREEN_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= BOWLING_GREEN_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= BOWLING_GREEN_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= BOWLING_GREEN_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= BOWLING_GREEN_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in BOWLING_GREEN_SUBMARKETS.items():
            bbox = BOWLING_GREEN_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in BOWLING_GREEN_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(BOWLING_GREEN_SUBMARKETS)

    def test_submarkets_carry_green_city_id(self):
        assert {m.city_id for m in BOWLING_GREEN_SUBMARKETS.values()} == {"bowling_green"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in BOWLING_GREEN_DIVISIONS.items():
            bbox = BOWLING_GREEN_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(BOWLING_GREEN_DIVISIONS) == 7
        for div in BOWLING_GREEN_DIVISIONS.values():
            assert div.city_id == "bowling_green"

    def test_submarket_count(self):
        assert len(BOWLING_GREEN_SUBMARKETS) == 10

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is BOWLING_GREEN_METRO_BBOX
        assert REGISTRATION.submarkets is BOWLING_GREEN_SUBMARKETS
        assert REGISTRATION.contains is is_in_bowling_green_metro


class TestFeedRegistration:
    def test_only_permits_is_registered(self):
        assert set(BOWLING_GREEN_FEED_SPECS) == {"permits"}

    def test_endpoint_matches_city_arcgis_server(self):
        assert BOWLING_GREEN_PERMITS_ENDPOINT == (
            "https://webgis.bgky.org/server/rest/services/CCPC/"
            "CCPC_Building_Permits_2010/FeatureServer/5"
        )

    def test_permits_spec_matches_probe_contract(self):
        spec = get_bowling_green_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == BOWLING_GREEN_PERMITS_ENDPOINT
        assert spec.watermark_col == "created_date"
        # True date column — client flattens to ISO; no ADR-0005 declaration.
        assert spec.watermark_type is None
        assert spec.watermark_format is None
        assert spec.id_keys == ["PermitNum", "OBJECTID"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Bowling Green, KY"
        assert spec.order_by == "OBJECTID"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        # Native-point layer: NOT non-spatial, no parcel join, no state-plane
        # columns (the client requests outSR=4326).
        assert spec.non_spatial is None
        assert spec.parcel_join == {}
        assert spec.state_plane_x_col is None
        assert spec.state_plane_y_col is None
        assert spec.field_map is BOWLING_GREEN_PERMITS_FIELD_MAP

    def test_absent_feeds_raise_readable_errors(self):
        for absent_feed in (FeedType.COMPLAINTS_311, FeedType.SLA, FeedType.DEEDS, FeedType.STR):
            with pytest.raises(KeyError, match=r"'bowling_green'.*available"):
                get_bowling_green_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is BOWLING_GREEN_PERMITS_FIELD_MAP
        assert GEOCODE_CONTEXT == BOWLING_GREEN_GEOCODE_CONTEXT == "Bowling Green, KY"
        # No other family is mapped — partial registration.
        assert "sla" not in FIELD_MAP
        assert "deeds" not in FIELD_MAP
        assert "complaints_311" not in FIELD_MAP


class TestBowlingGreenFieldMap:
    def test_permit_map_reads_live_columns(self):
        row = PERMITS_ROW_APARTMENT
        assert first_mapped(row, BOWLING_GREEN_PERMITS_FIELD_MAP, "job_id") == "2026-1314"
        assert first_mapped(row, BOWLING_GREEN_PERMITS_FIELD_MAP, "job_type") == "APARTMENT"
        assert first_mapped(row, BOWLING_GREEN_PERMITS_FIELD_MAP, "issuance_date") == "2026-08-24T18:06:08+00:00"
        assert first_mapped(row, BOWLING_GREEN_PERMITS_FIELD_MAP, "cost") == 750000.0

    def test_job_id_falls_back_to_objectid(self):
        row = {"PermitNum": None, "OBJECTID": 113479}
        assert first_mapped(row, BOWLING_GREEN_PERMITS_FIELD_MAP, "job_id") == 113479

    def test_permits_map_has_no_parcel_or_neighborhood_key(self):
        assert "bbl" not in BOWLING_GREEN_PERMITS_FIELD_MAP
        assert "borough" not in BOWLING_GREEN_PERMITS_FIELD_MAP
        assert "zipcode" not in BOWLING_GREEN_PERMITS_FIELD_MAP

    def test_permits_map_has_no_split_address_candidate(self):
        """The layer splits the address across St_Number/St_Name with no
        single line; left unmapped so the producer never emits a number-only
        half-address, and no coordinate candidate either (geometry-supplied).
        """
        assert "address_street" not in BOWLING_GREEN_PERMITS_FIELD_MAP
        assert "latitude" not in BOWLING_GREEN_PERMITS_FIELD_MAP
        assert "longitude" not in BOWLING_GREEN_PERMITS_FIELD_MAP
        assert first_mapped(
            {"St_Number": "2633", "St_Name": "MT VICTOR LANE"},
            BOWLING_GREEN_PERMITS_FIELD_MAP,
            "address_street",
        ) is None


class TestWatermarkTyping:
    def test_created_date_iso_parses(self):
        entry = typed_watermark_entry("2026-08-24T18:06:08+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 24)

    def test_newest_across_fixtures_is_2026_08_24(self):
        newest = newest_typed_watermark(
            [
                "2026-08-24T18:06:08+00:00",  # permit 2026-1314
                "2026-08-24T18:01:01+00:00",  # permit 2026-1316
                "2026-08-24T17:14:34+00:00",  # fence
                "2026-08-24T17:13:19+00:00",  # shed
            ]
        )
        assert newest is not None
        assert newest[0].startswith("2026-08-24T18:06")

    def test_empty_watermark_values_are_dropped(self):
        assert typed_watermark_entry("") is None
        assert typed_watermark_entry(None) is None


class TestBowlingGreenPermitParsing:
    def test_native_coord_permit_parses(self, permits, monkeypatch):
        """Native point geometry folds in latitude/longitude, so the parse
        never needs the geocoder — the event carries them straight through."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_APARTMENT, city_id="bowling_green")
        assert event is not None
        assert event.city_id == "bowling_green"
        assert event.job_id == "2026-1314"
        assert event.latitude == pytest.approx(PERMITS_ROW_APARTMENT["latitude"])
        assert event.longitude == pytest.approx(PERMITS_ROW_APARTMENT["longitude"])
        assert event.h3_res7 == _h3_res7(
            PERMITS_ROW_APARTMENT["latitude"], PERMITS_ROW_APARTMENT["longitude"]
        )
        assert is_in_bowling_green_metro(event.latitude, event.longitude)

    def test_native_coord_never_uses_geocoder(self, permits, monkeypatch):
        """Defensive needs_geocode but native coords present: even if the
        geocoder returns None the row must still parse off its geometry."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        for row in (PERMITS_ROW_FENCE, PERMITS_ROW_SHED):
            event = permits.parse_socrata_row(row, city_id="bowling_green")
            assert event is not None
            assert event.latitude == pytest.approx(row["latitude"])
            assert event.longitude == pytest.approx(row["longitude"])

    def test_created_date_parses_to_issuance(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_APARTMENT, city_id="bowling_green")
        assert event is not None
        assert str(event.issuance_date).startswith("2026-08-24")
        assert "18:06:08" in str(event.issuance_date)

    def test_cost_maps_from_permit_cost(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_FENCE, city_id="bowling_green")
        assert event is not None
        assert event.estimated_cost == 1200.0

    def test_permit_use_vocab_slips_to_ot(self, permits, monkeypatch):
        """The layer's only type column is PermitUse with no subtype/filing
        column, so APARTMENT and FENCE fall through to the OT default."""
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        for row in (PERMITS_ROW_APARTMENT, PERMITS_ROW_FENCE, PERMITS_ROW_SHED):
            event = permits.parse_socrata_row(row, city_id="bowling_green")
            assert event is not None
            assert event.job_type == JobType.OT

    def test_registered_city_resolves_borough(self, permits, monkeypatch):
        """'bowling_green' is now registered (wave-6 spine), so borough
        resolution runs and maps the row into a declared division; it never
        raises and never yields a stray metro."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_APARTMENT, city_id="bowling_green")
        assert event is not None
        assert event.borough is not None
        assert event.borough in BOWLING_GREEN_DIVISIONS

    def test_state_plane_leak_is_guarded_and_recovered(self, permits, monkeypatch):
        """A state-plane-coordinate leak (>90 lat) is nulled by the producer,
        then a mocked geocode recovers a plausible point (defensive path)."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_RECOVER,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_STATE_PLANE_LEAK, city_id="bowling_green")
        assert event is not None
        assert event.latitude == pytest.approx(PERMITS_GEOCODE_RECOVER[0])
        assert event.longitude == pytest.approx(PERMITS_GEOCODE_RECOVER[1])
        assert is_in_bowling_green_metro(event.latitude, event.longitude)

    def test_geocode_recover_point_stays_in_metro(self):
        assert is_in_bowling_green_metro(*PERMITS_GEOCODE_RECOVER)


class TestGeocodingCaveats:
    def test_mt_victor_is_state_re_false_positive(self):
        """'MT' in 'MT VICTOR LANE' is matched as the MT state token by
        _STATE_RE, so an address context append would be skipped for a Mt
        Victor geocode fallback (host quirk, documented only — native coords
        mean the fallback is never taken)."""
        assert _STATE_RE.search("MT VICTOR LANE") is not None
        assert _STATE_RE.search("MT VICTOR LANE").group(0) == "MT"

    def test_non_mt_streets_have_no_state_token(self):
        assert _STATE_RE.search("2040 BARBERRY COURT") is None
        assert _STATE_RE.search("1506 HIGH STREET") is None

    def test_context_with_ky_is_a_state_token(self):
        assert _STATE_RE.search("2633 MT VICTOR LANE, BOWLING GREEN, KY") is not None

    def test_normalize_drops_unit_designators_but_keeps_street(self):
        norm = normalize_address("2633 MT VICTOR LANE UNIT 2")
        assert "UNIT" not in norm
        assert "MT VICTOR LANE" in norm
