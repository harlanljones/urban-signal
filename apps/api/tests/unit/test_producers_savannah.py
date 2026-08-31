"""Unit tests for the Savannah leaf (US-298): spatial module + field maps
+ PERMITS parse wiring.

Savannah / Chatham County is a PARTIAL metro on ONE ArcGIS Server FeatureServer
(``pub.sagis.org`` ``Savannah/BuildingPermit_FC``): ``/1`` Residential is the
PERMITS dataset; ``/0`` Commercial is the spine-level companion
``commercial_building_permits`` (same schema, not a separate FeedType). The
watermark ``IssuedDate_DATE`` is a true date column, so ArcGISClient flattens
epoch-ms to ISO and no ADR-0005 text-watermark declaration is needed; the text
mirror ``IssuedDate`` (MM/DD/YYYY) is only a secondary issuance candidate.

Both layers are native-point (WKID 2239 GA State Plane E ft, served WGS84 by the
client's ``outSR=4326``), so the ArcGISClient lifts each feature's point onto
``latitude``/``longitude`` keys and nearly every row carries native coordinates;
ADR-0004 address geocoding is the fallback for the residual coordinate-less rows.

Tests pass WITHOUT a spine registration (no CityId.SAVANNAH): the producers
resolve city_id="savannah" as a plain string, the leaf-local field map is pinned
via resolve_field_map patches, and geocoding is mocked at
src.spatial.geocoder.geocode_row_if_declared (Lynchburg pattern).

Live fixtures are byte-verbatim from the 2026-08-28 re-probe (both watermarks
match docs/research/se-probe-savannah.md). ArcGIS epoch-ms dates are shown
flattened to the ISO strings the client produces; point geometry is shown as the
client-injected latitude/longitude keys.

Stability contract: these tests assert PARSE fields, source-neighborhood
passthrough, H3-from-fixture-coordinates, bbox containment, and field-map
mappings — deliberately NOT division/borough resolution results and NOT
geocode-hook call counts, both of which shift when the spine lands.
"""

import h3
from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_savannah import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.producers.watermarks import newest_typed_watermark, typed_watermark_entry
from src.spatial.cities.savannah import (
    REGISTRATION,
    SAVANNAH_CENTER,
    SAVANNAH_CITY_ID,
    SAVANNAH_COMMERCIAL_ENDPOINT,
    SAVANNAH_DIVISION_BBOXES,
    SAVANNAH_DIVISIONS,
    SAVANNAH_FEED_SPECS,
    SAVANNAH_GEOCODE_CONTEXT,
    SAVANNAH_METRO_BBOX,
    SAVANNAH_PERMITS_ENDPOINT,
    SAVANNAH_SUBMARKETS,
    get_savannah_dataset,
    is_in_savannah_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# ---------------------------------------------------------------------------
# Live fixtures (2026-08-28 re-probe, pub.sagis.org BuildingPermit_FC).
# ---------------------------------------------------------------------------

# Newest Residential by IssuedDate_DATE DESC — wire epoch-ms 1787616000000 flattens
# to the fixture ISO. Newest row 2026-08-20; 7d=0, 60d=294, total=1,933. Native
# point (outSR=4326) lifted onto latitude/longitude by the ArcGISClient.
PERMITS_ROW_DEMOLITION = {
    "OBJECTID": 20511,
    "ADDID2": "40723",
    "Address": "131 KING ST",
    "ApplicantName": "William  Sellers",
    "Description": "Demo and removal of debris",
    "District": "Woodville",
    "FinalizedDate": None,
    "FinalizedDate_DATE": None,
    "IssuedDate": "08/20/2026",
    "IssuedDate_DATE": "2026-08-20T00:00:00+00:00",
    "PIN": "20715 01016",
    "PermitNumber": "26-07908-BR",
    "PermitStatus": "Issued",
    "PermitType": "Building Residential Permit",
    "Permit_Value": 11000.0,
    "WorkClass": "Demolition-Total",
    "latitude": 32.08887888048572,
    "longitude": -81.14179009323823,
}

PERMITS_ROW_NEW_SFD = {
    "OBJECTID": 104121,
    "ADDID2": "191022",
    "Address": "145 ORKNEY RD",
    "ApplicantName": " ",
    "Description": "New Single Family Dwelling\n\n**Smoke and carbon monoxide alarms are required.**",
    "District": "Godley Station",
    "FinalizedDate": None,
    "FinalizedDate_DATE": None,
    "IssuedDate": "08/20/2026",
    "IssuedDate_DATE": "2026-08-20T00:00:00+00:00",
    "PIN": "21016H15001",
    "PermitNumber": "26-06373-BR",
    "PermitStatus": "Issued",
    "PermitType": "Building Residential Permit",
    "Permit_Value": 388400.0,
    "WorkClass": "New",
    "latitude": 32.18143212012366,
    "longitude": -81.2590233510153,
}

# Null IssuedDate_DATE — an In Review row still carrying native point geometry;
# it must parse losslessly with issuance_date None (date surfaces at issuance).
PERMITS_ROW_IN_REVIEW = {
    "OBJECTID": 109073,
    "ADDID2": "124111",
    "Address": "4113 WALTON ST",
    "ApplicantName": "Shaun Williams",
    "Description": "VERIFY PIN/ADDRESS - 4013 WALTON ST\nNew Construction.",
    "District": "Liberty City/Summerside/Southover/Richfield",
    "FinalizedDate": None,
    "FinalizedDate_DATE": None,
    "IssuedDate": None,
    "IssuedDate_DATE": None,
    "PIN": "20593 06008",
    "PermitNumber": "26-07506-BR",
    "PermitStatus": "In Review",
    "PermitType": "Building Residential Permit",
    "Permit_Value": 210000.0,
    "WorkClass": "New",
    "latitude": 32.04812125059816,
    "longitude": -81.12795042675612,
}

# Newest Commercial by IssuedDate_DATE DESC (companion /0, same schema). Newest row
# 2026-08-21; 7d=1, 60d=61, total=666. Proves the same field map serves /0.
PERMITS_ROW_COMMERCIAL = {
    "OBJECTID": 106422,
    "ADDID2": "198076",
    "Address": "7000 BUSINESS CENTER DR",
    "ApplicantName": "Jessica Vargas",
    "Description": "New Construction of 124 room, 4-story hotel, Type V-A construction, R-1 Occupancy",
    "District": "Chatham Parkway",
    "FinalizedDate": None,
    "FinalizedDate_DATE": None,
    "IssuedDate": "08/21/2026",
    "IssuedDate_DATE": "2026-08-21T00:00:00+00:00",
    "PIN": "20835 01049",
    "PermitNumber": "26-00953-BC",
    "PermitStatus": "Issued",
    "PermitType": "Building Commercial Permit",
    "Permit_Value": 6425000.0,
    "WorkClass": "New",
    "latitude": 32.05122327333703,
    "longitude": -81.16553464768928,
}

# Mocked ADR-0004 geocodes (address-plausible, inside the metro bbox):
SAVANNAH_GEOCODE_KING_ST = (32.0900, -81.1400)     # 131 KING ST
SAVANNAH_GEOCODE_BUSINESS_CTR = (32.0510, -81.1660)  # 7000 BUSINESS CENTER DR


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


class TestSavannahSpatial:
    def test_city_id_constant(self):
        assert SAVANNAH_CITY_ID == "savannah"

    def test_metro_contains_registration_center(self):
        assert is_in_savannah_metro(
            SAVANNAH_CENTER["lat"], SAVANNAH_CENTER["lng"]
        ) is True

    def test_metro_contains_known_landmarks_and_annexations(self):
        assert is_in_savannah_metro(32.0767, -81.0943) is True  # Downtown
        assert is_in_savannah_metro(32.0637, -81.0943) is True  # Forsyth Park
        assert is_in_savannah_metro(32.1814, -81.2590) is True  # Godley Station annex
        assert is_in_savannah_metro(32.1300, -81.3505) is True  # New Hampstead annex

    def test_metro_rejects_null_and_neighbors(self):
        assert is_in_savannah_metro(None, None) is False
        assert is_in_savannah_metro(32.4480, -81.7830) is False  # Statesboro
        assert is_in_savannah_metro(31.1500, -81.4900) is False  # Brunswick
        assert is_in_savannah_metro(32.7765, -79.9311) is False  # Charleston
        assert is_in_savannah_metro(31.9200, -80.8500) is False  # Tybee Island edge

    def test_metro_bbox_grounded_in_layer_extent(self):
        """Live layer extent (2026-08-28, outSR=4326): lat 31.93395-32.18642,
        lng -81.36534 - -81.04491. The metro box must cover it with margin."""
        assert SAVANNAH_METRO_BBOX["min_lat"] <= 31.93395
        assert SAVANNAH_METRO_BBOX["max_lat"] >= 32.18642
        assert SAVANNAH_METRO_BBOX["min_lng"] <= -81.36534
        assert SAVANNAH_METRO_BBOX["max_lng"] >= -81.04491

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in SAVANNAH_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SAVANNAH_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SAVANNAH_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SAVANNAH_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SAVANNAH_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in SAVANNAH_SUBMARKETS.items():
            bbox = SAVANNAH_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in SAVANNAH_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(SAVANNAH_SUBMARKETS)

    def test_submarkets_carry_savannah_city_id(self):
        assert {m.city_id for m in SAVANNAH_SUBMARKETS.values()} == {"savannah"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in SAVANNAH_DIVISIONS.items():
            bbox = SAVANNAH_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(SAVANNAH_DIVISIONS) == 5
        for div in SAVANNAH_DIVISIONS.values():
            assert div.city_id == "savannah"

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is SAVANNAH_METRO_BBOX
        assert REGISTRATION.submarkets is SAVANNAH_SUBMARKETS
        assert REGISTRATION.contains is is_in_savannah_metro


class TestFeedRegistration:
    def test_exactly_one_feed_type_is_registered(self):
        assert set(SAVANNAH_FEED_SPECS) == {"permits"}

    def test_endpoints_split_on_the_one_featureserver(self):
        base = "https://pub.sagis.org/arcgis/rest/services/Savannah/BuildingPermit_FC/FeatureServer"
        assert SAVANNAH_PERMITS_ENDPOINT == f"{base}/1"
        assert SAVANNAH_COMMERCIAL_ENDPOINT == f"{base}/0"

    def test_permits_spec_matches_probe_contract(self):
        spec = get_savannah_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == SAVANNAH_PERMITS_ENDPOINT
        assert spec.watermark_col == "IssuedDate_DATE"
        # True date column — client flattens to ISO; no ADR-0005 declaration.
        assert spec.watermark_type is None
        assert spec.watermark_format is None
        assert spec.id_keys == ["PermitNumber", "OBJECTID"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Savannah, GA"
        assert spec.order_by == "OBJECTID"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 7
        # Native-point layer is NOT a non-spatial table.
        assert spec.non_spatial in (None, False)
        assert spec.field_map == PERMITS_FIELD_MAP

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.COMPLAINTS_311, FeedType.CRIME, FeedType.SLA, FeedType.DEEDS, FeedType.STR],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'savannah'.*available"):
            get_savannah_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert set(FIELD_MAP) == {"permits"}
        assert GEOCODE_CONTEXT == SAVANNAH_GEOCODE_CONTEXT == "Savannah, GA"


class TestSavannahFieldMaps:
    def test_permits_map_reads_live_columns(self):
        row = PERMITS_ROW_DEMOLITION
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "26-07908-BR"
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_type") == "Demolition-Total"
        assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == "2026-08-20T00:00:00+00:00"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == "131 KING ST"
        assert first_mapped(row, PERMITS_FIELD_MAP, "bbl") == "20715 01016"
        assert first_mapped(row, PERMITS_FIELD_MAP, "borough") == "Woodville"
        assert first_mapped(row, PERMITS_FIELD_MAP, "cost") == 11000.0
        assert first_mapped(row, PERMITS_FIELD_MAP, "status") == "Issued"

    def test_permits_job_id_falls_back_when_permit_number_is_null(self):
        row = {"PermitNumber": None, "OBJECTID": 20511}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 20511

    def test_permits_map_declares_no_lat_lng_candidates(self):
        """Native point geometry is injected by the ArcGISClient and read through
        the producer's generic row.get('latitude'/'longitude') chain, so the map
        must NOT declare coordinate candidates."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP

    def test_applicant_name_is_not_mapped(self):
        """ApplicantName is PII — deliberately absent from the field map."""
        assert "applicant_name" not in PERMITS_FIELD_MAP
        assert "owner_name" not in PERMITS_FIELD_MAP


class TestWatermarkTyping:
    """IssuedDate_DATE is a true date column (ISO after ArcGISClient flatten);
    the text mirror IssuedDate parses under the default multi-format parser."""

    def test_issueddate_date_iso_parses(self):
        entry = typed_watermark_entry("2026-08-20T00:00:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 20)

    def test_issueddate_text_mirror_parses(self):
        entry = typed_watermark_entry("08/20/2026")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 20)

    def test_newest_across_both_layers_is_2026_08_21(self):
        newest = newest_typed_watermark(
            [
                "2026-08-20T00:00:00+00:00",  # residential IssuedDate_DATE
                "2026-08-21T00:00:00+00:00",  # commercial IssuedDate_DATE
                "2026-08-20T00:00:00+00:00",  # residential runner-up
            ]
        )
        assert newest is not None
        assert newest[0].startswith("2026-08-21")

    def test_empty_watermark_values_are_dropped(self):
        assert typed_watermark_entry("") is None
        assert typed_watermark_entry(None) is None


class TestSavannahPermitParsing:
    def test_native_permits_row_parses_with_native_coords(self, permits, monkeypatch):
        """A row carrying client-injected native point coordinates parses without
        the geocode hook, derives its H3 cells from those coordinates, and lands
        inside the metro bbox."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_DEMOLITION, city_id="savannah")
        assert event is not None
        assert event.city_id == "savannah"
        assert event.job_id == "26-07908-BR"
        assert event.latitude == pytest.approx(PERMITS_ROW_DEMOLITION["latitude"])
        assert event.longitude == pytest.approx(PERMITS_ROW_DEMOLITION["longitude"])
        assert event.h3_res7 == _h3_res7(*(
            PERMITS_ROW_DEMOLITION["latitude"], PERMITS_ROW_DEMOLITION["longitude"]
        ))
        assert is_in_savannah_metro(event.latitude, event.longitude)

    def test_permits_geocode_sits_inside_metro(self):
        assert is_in_savannah_metro(*SAVANNAH_GEOCODE_KING_ST)
        assert is_in_savannah_metro(*SAVANNAH_GEOCODE_BUSINESS_CTR)

    def test_date_typed_issueddate_parses_to_event_issuance(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_NEW_SFD, city_id="savannah")
        assert event is not None
        assert str(event.issuance_date).startswith("2026-08-20")

    def test_district_passes_through_as_source_neighborhood(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_NEW_SFD, city_id="savannah")
        assert event is not None
        assert event.source_neighborhood == "Godley Station"

    def test_workclass_new_classifies_as_nb(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_NEW_SFD, city_id="savannah")
        assert event is not None
        assert event.job_id == "26-06373-BR"
        assert event.job_type == JobType.NB

    def test_workclass_demolition_classifies_as_dm(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_DEMOLITION, city_id="savannah")
        assert event is not None
        assert event.job_type == JobType.DM

    def test_workclass_renovation_classifies_as_a2(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        row = {**PERMITS_ROW_COMMERCIAL, "WorkClass": "Renovation"}
        event = permits.parse_socrata_row(row, city_id="savannah")
        assert event is not None
        assert event.job_type == JobType.A2

    def test_permit_value_maps_to_estimated_cost(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_NEW_SFD, city_id="savannah")
        assert event is not None
        assert event.estimated_cost == 388400.0

    def test_null_issueddate_in_review_row_parses_lossless(self, permits, monkeypatch):
        """An In Review / Approved row with null IssuedDate_DATE still carries
        native point geometry so it parses; its date surfaces at issuance."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_IN_REVIEW, city_id="savannah")
        assert event is not None
        assert event.job_id == "26-07506-BR"
        assert event.issuance_date is None
        assert event.status == "In Review"
        assert event.latitude == pytest.approx(PERMITS_ROW_IN_REVIEW["latitude"])
        assert event.h3_res7 == _h3_res7(*(
            PERMITS_ROW_IN_REVIEW["latitude"], PERMITS_ROW_IN_REVIEW["longitude"]
        ))

    def test_address_fallback_geocode_drives_coordinates(self, permits, monkeypatch):
        """A row without native geometry falls through to the mocked ADR-0004
        geocode; the event then derives its H3 cells from the returned point."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SAVANNAH_GEOCODE_KING_ST,
        )
        row = {k: v for k, v in PERMITS_ROW_DEMOLITION.items()
               if k not in ("latitude", "longitude")}
        assert "latitude" not in row and "longitude" not in row
        event = permits.parse_socrata_row(row, city_id="savannah")
        assert event is not None
        assert event.latitude == pytest.approx(SAVANNAH_GEOCODE_KING_ST[0])
        assert event.longitude == pytest.approx(SAVANNAH_GEOCODE_KING_ST[1])
        assert event.h3_res7 == _h3_res7(*SAVANNAH_GEOCODE_KING_ST)
        assert is_in_savannah_metro(event.latitude, event.longitude)

    def test_geocode_failure_drops_address_only_permit(self, permits, monkeypatch):
        """Permits producer tolerance: a coordinate-less row whose geocode
        resolves to nothing returns None (row dropped) rather than emitting a
        null-coordinate permit."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        row = {k: v for k, v in PERMITS_ROW_DEMOLITION.items()
               if k not in ("latitude", "longitude")}
        assert permits.parse_socrata_row(row, city_id="savannah") is None

    def test_commercial_companion_row_parses_with_same_field_map(self, permits, monkeypatch):
        """/0 Commercial shares /1's schema, so the same field map parses it and
        the commercial new-construction classifies as NB."""
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_COMMERCIAL, city_id="savannah")
        assert event is not None
        assert event.job_id == "26-00953-BC"
        assert event.job_type == JobType.NB
        assert event.estimated_cost == 6425000.0
        assert event.source_neighborhood == "Chatham Parkway"
        assert str(event.issuance_date).startswith("2026-08-21")


class TestGeocodingCaveats:
    def test_savannah_street_has_no_state_token_so_context_appends(self):
        assert _STATE_RE.search("131 KING ST".upper()) is None

    def test_context_with_ga_is_a_state_token(self):
        assert _STATE_RE.search("131 KING ST, SAVANNAH, GA".upper()) is not None

    def test_unit_designator_truncates_after_hash(self):
        """normalize_address splits on '#' (a unit suffix) and drops the tail,
        including the appended city context — the query is rebuilt losslessly by
        the geocode hook. This matches the shared geocoder design (US-74)."""
        norm = normalize_address("7000 BUSINESS CENTER DR #2, SAVANNAH, GA")
        assert norm == "7000 BUSINESS CENTER DR"
