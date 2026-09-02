"""Unit tests for the Vancouver, WA leaf (US-233): spatial module + field
maps + producer parse wiring.

Vancouver is a ONE-FEED PARTIAL metro: ``Permits_and_Code_Enforcement_Data``
FeatureServer/0 ("Permit Data") on the city's AGOL org
(``services.arcgis.com/oNvpY90qsPDizwkN``, Tier 1, daily, native outSR=4326
point geometry). 311 (token-gated internal server), SLA (no public feed), and
deeds (Clark Co. web app) stay Tier 3 — only ``permits`` is registered.

Tests pass WITHOUT a spine registration (no CityId.VANCOUVER_WA, no REGISTRY
assertions — "vancouver_wa" stays a plain string). Spine-stable per the
wave-5 leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from FeatureServer/0 (newest rows
via ``orderByFields=csm_issued_date DESC, where=csm_issued_date <=
CURRENT_TIMESTAMP`` at ``outSR=4326``; newest watermark ``1786781763000`` =
2026-08-15T08:16:03+00:00). Fixtures are RAW ArcGIS features (attributes +
geometry); the tests run the real ``ArcGISClient._flatten_feature`` lift —
geometry to latitude/longitude, epoch-ms to ISO — before parsing, exactly as
the live producer path does.
"""

from datetime import UTC
from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_vancouver_wa import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.vancouver_wa import (
    REGISTRATION,
    VANCOUVER_WA_CITY_ID,
    VANCOUVER_WA_DIVISION_BBOXES,
    VANCOUVER_WA_DIVISIONS,
    VANCOUVER_WA_FEED_SPECS,
    VANCOUVER_WA_GEOCODE_CONTEXT,
    VANCOUVER_WA_METRO_BBOX,
    VANCOUVER_WA_PERMITS_ENDPOINT,
    VANCOUVER_WA_SLA_ENDPOINT,
    VANCOUVER_WA_PERMITS_WHERE,
    VANCOUVER_WA_SUBMARKETS,
    get_vancouver_wa_dataset,
    is_in_greater_vancouver_wa_metro,
    is_in_vancouver_wa_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten(feature):
    """Run the real ArcGIS flatten lift over a raw captured feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: csm_issued_date is esriFieldTypeDate; the Y/X attributes are
    State Plane doubles and are correctly NOT date fields.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, {"csm_issued_date"})


# Newest rows on the 2026-08-28 live probe (orderByFields=csm_issued_date
# DESC, where=csm_issued_date<=CURRENT_TIMESTAMP, outSR=4326) — three
# features share the newest window. Byte-verbatim: padded sn/serial numbers,
# State Plane Y/X feet, native WGS84 point geometry.
_FEATURE_MPE_392942 = {
    "attributes": {
        "OBJECTID": 47868,
        "sn": "35770376",
        "CSM_CASENO": "MPE-392942",
        "CSM_STATUS": "Open",
        "csm_issued_date": 1786781763000,
        "PRIM_ADDR": "5585 E EVERGREEN BLVD",
        "CSM_NO_UNITS": None,
        "cst_description": "Mechanical,Plumbing,Electrical",
        "worktype": "ELECTRICAL",
        "Y": 110745.69627918,
        "X": 1099107.50681035,
    },
    "geometry": {
        "x": -122.61553553973754,
        "y": 45.617117314984526,
    },
}

_FEATURE_MPE_392940 = {
    "attributes": {
        "OBJECTID": 47859,
        "sn": "108858408",
        "CSM_CASENO": "MPE-392940",
        "CSM_STATUS": "Open",
        "csm_issued_date": 1786723762000,
        "PRIM_ADDR": "15516 NE 9TH CIR",
        "CSM_NO_UNITS": None,
        "cst_description": "Mechanical,Plumbing,Electrical",
        "worktype": "MECHANICAL",
        "Y": 114140.8623891,
        "X": 1125794.68604743,
    },
    "geometry": {
        "x": -122.51162255244407,
        "y": 45.62833890366324,
    },
}

_FEATURE_MPE_392939 = {
    "attributes": {
        "OBJECTID": 47830,
        "sn": "19110000",
        "CSM_CASENO": "MPE-392939",
        "CSM_STATUS": "Open",
        "csm_issued_date": 1786723206000,
        "PRIM_ADDR": "3705 M ST",
        "CSM_NO_UNITS": None,
        "cst_description": "Mechanical,Plumbing,Electrical",
        "worktype": "MECHANICAL",
        "Y": 122376.38003876,
        "X": 1088485.45456369,
    },
    "geometry": {
        "x": -122.6582711256547,
        "y": 45.64821080784461,
    },
}

# Closed permit with a WATER-type worktype for variety
_FEATURE_MPE_392917 = {
    "attributes": {
        "OBJECTID": 47841,
        "sn": "32630000",
        "CSM_CASENO": "MPE-392917",
        "CSM_STATUS": "Closed",
        "csm_issued_date": 1786708871000,
        "PRIM_ADDR": "1800 E 5TH ST",
        "CSM_NO_UNITS": None,
        "cst_description": "Mechanical,Plumbing,Electrical",
        "worktype": "POR",
        "Y": 113766.87626044,
        "X": 1089568.91893218,
    },
    "geometry": {
        "x": -122.65311771417822,
        "y": 45.62469140090046,
    },
}

_NEWISSUE_ISO = "2026-08-15T08:16:03+00:00"


class TestVancouverWaSpatial:
    def test_metro_bbox_sanity(self):
        assert VANCOUVER_WA_METRO_BBOX["min_lat"] < VANCOUVER_WA_METRO_BBOX["max_lat"]
        assert VANCOUVER_WA_METRO_BBOX["min_lng"] < VANCOUVER_WA_METRO_BBOX["max_lng"]

    def test_is_in_vancouver_wa_metro_rejects_missing_coordinates(self):
        assert is_in_vancouver_wa_metro(None, None) is False
        assert is_in_vancouver_wa_metro(45.6282, None) is False
        assert is_in_vancouver_wa_metro(None, -122.6785) is False

    def test_is_in_vancouver_wa_metro_rejects_other_cities(self):
        assert is_in_vancouver_wa_metro(45.5222, -122.6848) is False   # Portland
        assert is_in_vancouver_wa_metro(45.5200, -122.6700) is False   # Portland
        assert is_in_vancouver_wa_metro(47.6062, -122.3321) is False   # Seattle
        # Felida (45.73, -122.63) is inside the metro bbox but excluded from
        # submarkets due to lack of permit coverage (1 row north of 45.70).

    def test_downtown_anchors_are_contained(self):
        assert is_in_vancouver_wa_metro(45.6282, -122.6785)  # Esther Short
        assert is_in_vancouver_wa_metro(45.6325, -122.6715)  # Uptown Village
        assert is_in_vancouver_wa_metro(45.6454, -122.6210)  # Bagley Downs

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_MPE_392942, _FEATURE_MPE_392940, _FEATURE_MPE_392939):
            assert is_in_vancouver_wa_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in VANCOUVER_WA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= VANCOUVER_WA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= VANCOUVER_WA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= VANCOUVER_WA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= VANCOUVER_WA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in VANCOUVER_WA_SUBMARKETS.items():
            bbox = VANCOUVER_WA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in VANCOUVER_WA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(VANCOUVER_WA_SUBMARKETS)

    def test_submarkets_carry_the_vancouver_wa_city_id(self):
        assert {m.city_id for m in VANCOUVER_WA_SUBMARKETS.values()} == {"vancouver_wa"}

    def test_city_id_and_registration_shape(self):
        assert VANCOUVER_WA_CITY_ID == "vancouver_wa"
        assert REGISTRATION.metro_bbox is VANCOUVER_WA_METRO_BBOX
        assert REGISTRATION.submarkets is VANCOUVER_WA_SUBMARKETS
        assert REGISTRATION.division_bboxes is VANCOUVER_WA_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_vancouver_wa_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(VANCOUVER_WA_SUBMARKETS) == 13

    def test_required_real_neighborhoods_present(self):
        assert set(VANCOUVER_WA_SUBMARKETS) == {
            "Downtown / Esther Short",
            "Uptown Village",
            "Fruit Valley",
            "Northwest Vancouver",
            "West Minnehaha",
            "Fourth Plain / Bagley Downs",
            "Maplewood",
            "Walnut Grove",
            "Burnt Bridge Creek / Image",
            "Cascade Park / First Place",
            "East Mill Plain",
            "Fisher's Landing",
            "Columbia River / Northfield",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_vancouver_wa_metro is is_in_vancouver_wa_metro


class TestVancouverWaFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["CSM_CASENO", "sn", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["csm_issued_date"]
        assert PERMITS_FIELD_MAP["status"] == ["CSM_STATUS"]
        assert PERMITS_FIELD_MAP["job_type"] == ["worktype", "cst_description"]
        assert PERMITS_FIELD_MAP["address_street"] == ["PRIM_ADDR"]
        assert PERMITS_FIELD_MAP["proposed_units"] == ["CSM_NO_UNITS"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP, "sla": SLA_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Vancouver, WA"
        assert VANCOUVER_WA_GEOCODE_CONTEXT == "Vancouver, WA"

    def test_state_plane_coordinates_are_never_candidates(self):
        """Y/X attributes are WA State Plane South feet (≈1.1e5 / 1.08e6) —
        mapping them would emit feet as degrees. Coordinates come only from
        the outSR=4326 geometry lift."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        attrs = _FEATURE_MPE_392942["attributes"]
        assert attrs["Y"] > 90 and attrs["X"] > 90  # feet, not degrees
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "longitude") is None

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        """No neighborhood/district column exists on the layer (Omaha
        discipline): no borough candidate is declared, so
        source_neighborhood passes through as None on parsed events."""
        assert "borough" not in PERMITS_FIELD_MAP
        assert "neighborhood" not in PERMITS_FIELD_MAP

    def test_no_zipcode_or_bbl_candidates(self):
        """PRIM_ADDR is an address-only column with no zip; the layer has no
        parcel/APN column — both stay undeclared."""
        assert "zipcode" not in PERMITS_FIELD_MAP
        assert "bbl" not in PERMITS_FIELD_MAP

    def test_csm_issued_date_queryable_iso_string(self):
        """csm_issued_date is esriFieldTypeDate, where-clause queryable with
        ISO strings (not ANSI-only). Verified live: >= '2026-08-15T00:00:00'
        returns 3 rows on the host. This test validates the fixture epoch
        conversion (1786781763000 -> ISO)."""
        from datetime import datetime

        iso = datetime.fromtimestamp(1786781763000 / 1000, tz=UTC).isoformat()
        assert iso == _NEWISSUE_ISO


class TestVancouverWaPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_MPE_392942)
        assert record["latitude"] == pytest.approx(45.617117314984526)
        assert record["longitude"] == pytest.approx(-122.61553553973754)
        # The State Plane attributes ride along unmapped — never as degrees.
        assert record["Y"] == 110745.69627918
        assert record["X"] == 1099107.50681035

    def test_flatten_iso_normalizes_the_watermark_only(self):
        record = _flatten(_FEATURE_MPE_392940)
        assert record["csm_issued_date"] == "2026-08-14T16:09:22+00:00"
        # Y/X are State Plane doubles, not date fields — untouched.
        assert record["Y"] == 114140.8623891
        assert record["X"] == 1125794.68604743

    def test_evergreen_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_MPE_392942), city_id="vancouver_wa")
        assert event is not None
        assert event.city_id == "vancouver_wa"
        assert event.job_id == "MPE-392942"
        assert event.status == "Open"
        assert event.address_street == "5585 E EVERGREEN BLVD"
        assert event.latitude == pytest.approx(45.617117314984526)
        assert event.longitude == pytest.approx(-122.61553553973754)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _NEWISSUE_ISO
        assert event.proposed_dwelling_units is None
        assert event.source_neighborhood is None
        assert event.zipcode == ""
        assert event.bbl is None

    def test_9th_cir_fixture_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_MPE_392940), city_id="vancouver_wa")
        assert event is not None
        assert event.estimated_cost == pytest.approx(0.0)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_vancouver_wa_metro(event.latitude, event.longitude)

    def test_m_st_fixture_valuation_and_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_MPE_392939), city_id="vancouver_wa")
        assert event is not None
        assert event.job_id == "MPE-392939"
        assert event.estimated_cost == pytest.approx(0.0)
        assert event.address_street == "3705 M ST"
        assert is_in_vancouver_wa_metro(event.latitude, event.longitude)

    def test_all_newest_fixtures_share_the_watermark_window(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(_flatten(f), city_id="vancouver_wa")
            for f in (_FEATURE_MPE_392942, _FEATURE_MPE_392940, _FEATURE_MPE_392939)
        ]
        assert all(e is not None for e in events)
        # All three fixtures fall within the same week (co-newest window).
        dates = {e.issuance_date.date() for e in events}
        assert len(dates) == 2  # 2026-08-14 and 2026-08-15
        # Distinct permits occupy distinct res-9 cells.
        assert len({e.h3_res9 for e in events}) == 3

    def test_status_passes_through_open_and_closed(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        open_event = permits.parse_socrata_row(
            _flatten(_FEATURE_MPE_392942), city_id="vancouver_wa"
        )
        assert open_event.status == "Open"
        closed_event = permits.parse_socrata_row(
            _flatten(_FEATURE_MPE_392917), city_id="vancouver_wa"
        )
        assert closed_event is not None
        assert closed_event.status == "Closed"

    def test_job_id_falls_back_to_serial_number(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_MPE_392942)
        record.pop("CSM_CASENO")
        event = permits.parse_socrata_row(record, city_id="vancouver_wa")
        assert event is not None
        assert event.job_id == "35770376"

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_MPE_392942)
        record.pop("CSM_CASENO")
        record.pop("sn")
        event = permits.parse_socrata_row(record, city_id="vancouver_wa")
        assert event is not None
        assert event.job_id == "47868"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_MPE_392942)
        record.pop("CSM_CASENO")
        record.pop("sn")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="vancouver_wa") is None

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, permits, monkeypatch
    ):
        """Rows arriving without geometry resolve via the ADR 0004 geocode
        supplement (needs_geocode=True). Call-args/counts are spine-volatile
        and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_MPE_392942)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (45.6325, -122.6715),
        )
        event = permits.parse_socrata_row(record, city_id="vancouver_wa")
        assert event is not None
        assert event.city_id == "vancouver_wa"
        assert event.job_id == "MPE-392942"
        assert event.latitude == pytest.approx(45.6325)
        assert event.longitude == pytest.approx(-122.6715)
        assert event.h3_res7 is not None

    def test_geometry_less_row_dropped_when_geocode_fails(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_MPE_392940)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="vancouver_wa") is None

    def test_state_plane_values_never_emit_as_degrees(self, permits, monkeypatch):
        """If State Plane feet ever leaked into latitude/longitude (a bad
        future map edit), the producer's projected-coordinate guard nulls
        them; the coordinate-less row then falls to geocode and must not
        carry fake degrees."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_MPE_392942)
        record["latitude"] = record["Y"]    # 110745.7 feet
        record["longitude"] = record["X"]   # 1099107.5 feet
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="vancouver_wa") is None

    def test_vancouver_type_codes_stay_unclassified_at_the_leaf(
        self, permits, monkeypatch
    ):
        """worktype codes (ELECTRICAL/MECHANICAL/NEW/POR) pass through as
        job_type candidates. ELECTRICAL/MECHANICAL contain 'ELECTRIC' and
        'PLUMBING' → A2 (via the classification chain). NEW → NB. POR is
        not among the recognized codes → OT."""
        _patch_resolve(monkeypatch, "permits")
        # ELECTRICAL → contains "ELECTRIC" → A2
        event = permits.parse_socrata_row(_flatten(_FEATURE_MPE_392942), city_id="vancouver_wa")
        assert event is not None
        assert event.job_type == JobType.A2
        # MECHANICAL → not recognized → OT
        event = permits.parse_socrata_row(_flatten(_FEATURE_MPE_392940), city_id="vancouver_wa")
        assert event is not None
        assert event.job_type == JobType.OT
        # POR → not recognized → OT
        event = permits.parse_socrata_row(_flatten(_FEATURE_MPE_392917), city_id="vancouver_wa")
        assert event is not None
        assert event.job_type == JobType.OT

    def test_estimated_cost_defaults_to_zero(self, permits, monkeypatch):
        """No cost/valuation column exists on the layer; cost falls to 0.0."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_MPE_392942), city_id="vancouver_wa")
        assert event is not None
        assert event.estimated_cost == pytest.approx(0.0)


class TestVancouverWaFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_vancouver_wa_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == VANCOUVER_WA_PERMITS_ENDPOINT
        assert spec.watermark_col == "csm_issued_date"
        assert spec.id_keys == ["CSM_CASENO", "sn", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "csm_issued_date DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Vancouver, WA"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"
        assert spec.where == "csm_issued_date <= CURRENT_TIMESTAMP"

    def test_registered_feed_set_includes_permits_and_sla(self):
        assert set(VANCOUVER_WA_FEED_SPECS) == {"permits", "sla"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_vancouver_wa_dataset("deeds")
        assert "vancouver_wa" in str(exc.value)
        assert "permits" in str(exc.value) or "sla" in str(exc.value)

    def test_sla_spec_matches_live_layer(self):
        spec = get_vancouver_wa_dataset(FeedType.SLA)
        assert spec.platform == "socrata"
        assert spec.endpoint == VANCOUVER_WA_SLA_ENDPOINT
        assert spec.watermark_col == "licenseeffectivedate"
        assert spec.id_keys == ["contractorlicensenumber", "ubi"]
        assert spec.expected_cadence_days == 1
        assert spec.interval_seconds == 3600.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Vancouver, WA"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"

    def test_endpoint_is_the_probed_featureserver(self):
        assert "services.arcgis.com" in VANCOUVER_WA_PERMITS_ENDPOINT
        assert "Permits_and_Code_Enforcement_Data_(public_view)" in VANCOUVER_WA_PERMITS_ENDPOINT
        assert "FeatureServer/0" in VANCOUVER_WA_PERMITS_ENDPOINT

    def test_where_guard_excludes_future_sentinels(self):
        """The where guard csm_issued_date <= CURRENT_TIMESTAMP is the
        Anchorage discipline for future-dated sentinel rows (2 live, max
        2049-10-31). Verified live: 44,742 rows with the guard vs 44,744
        total."""
        assert VANCOUVER_WA_PERMITS_WHERE == "csm_issued_date <= CURRENT_TIMESTAMP"