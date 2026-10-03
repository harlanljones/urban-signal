"""Unit tests for the Laredo, TX leaf (US-263): spatial module + field maps
+ CKAN permit parsing.

Laredo is a ONE-FEED Tier-2 metro on CKAN OpenGov
(``data.openlaredo.com``, resource ``61972510-7b8c-488a-9e88-b73b0112f496`` —
PERMITS ISSUED.xlsx / bpod1e.csv, 91,198 rows back to 2022, watermark
``PERMIT ISS. DATE`` newest 2026-07-02T00:00:00, monthly bulk replace,
address-only ``STREET NBR`` + ``STREET``, needs_geocode=true).

The producer tests pin the leaf-local field map through a resolve_field_map
patch, and coordinates come from the ADR-0004 geocode mock for the
non-spatial CKAN source (Boulder Table precedent).

Fixtures captured byte-verbatim 2026-08-30 from the live CKAN datastore
(``ORDER BY "PERMIT ISS. DATE" DESC LIMIT 3``).
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.spatial.cities.laredo import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    LAREDO_CENTER,
    LAREDO_CITY_ID,
    LAREDO_DIVISION_BBOXES,
    LAREDO_DIVISIONS,
    LAREDO_FEED_SPECS,
    LAREDO_METRO_BBOX,
    LAREDO_PERMITS_ENDPOINT,
    LAREDO_PERMITS_RESOURCE_ID,
    LAREDO_PERMITS_WATERMARK_ISO,
    LAREDO_SUBMARKETS,
    PERMITS_FIELD_MAP,
    REGISTRATION,
    compose_permit_address,
    compose_permit_type,
    is_in_greater_laredo_metro,
    is_in_laredo_metro,
)

# ---------------------------------------------------------------------------
# CKAN fixtures — byte-verbatim from datastore_search_sql
# ORDER BY "PERMIT ISS. DATE" DESC LIMIT 3, 2026-08-30.
# ---------------------------------------------------------------------------

_PERMIT_PALOMA = {
    "_id": 88449,
    "APP YR": 26,
    "APP NBR": 3696,
    "APP TYPE": "111 ",
    "APP TYPE DESC": "SOLAR PANEL                                  ",
    "APP STATUS": "IS",
    "APP STAT DESC": "PERMIT ISSUED            ",
    "PERMIT TYPE": "111",
    "PERMIT TYPE DESC": "SOLAR PANEL PERMIT            ",
    "PERMIT SEQUENCE": 0,
    "PERMIT STATUS": "PP",
    "PERMIT STATUS DESC": "PERMIT PRINTED           ",
    "PERMIT EXP. DATE": "12/29/26",
    "PERMIT SQ. FT.": 0,
    "PERMIT ISS. DATE": "2026-07-02T00:00:00",
    "APP DESC": "RT SOLAR PANEL INSTALL                            ",
    "APP SQ. FT.": 0,
    "STREET NBR": "801      ",
    "STREET": "              PALOMA                    CT           ",
    "VALUATION": 0,
    "PLANNED CHECK FEE": "0.00",
    "PERMIT FEE": "200.000000",
    "TOTAL FEE": "200.000000",
    "CONTRACTOR NAME": "                              ",
    "Permit Group Type": "Electrical",
    "Permit Group Tab": "Other Permits",
}

_PERMIT_PALOMA_EL = {
    "_id": 88450,
    "APP YR": 26,
    "APP NBR": 3696,
    "APP TYPE": "111 ",
    "APP TYPE DESC": "SOLAR PANEL                                  ",
    "APP STATUS": "IS",
    "APP STAT DESC": "PERMIT ISSUED            ",
    "PERMIT TYPE": "707",
    "PERMIT TYPE DESC": "EL-SOLAR PANELS               ",
    "PERMIT SEQUENCE": 0,
    "PERMIT STATUS": "PP",
    "PERMIT STATUS DESC": "PERMIT PRINTED           ",
    "PERMIT EXP. DATE": "12/29/26",
    "PERMIT SQ. FT.": 0,
    "PERMIT ISS. DATE": "2026-07-02T00:00:00",
    "APP DESC": "RT SOLAR PANEL INSTALL                            ",
    "APP SQ. FT.": 0,
    "STREET NBR": "5528     ",
    "STREET": "              LONE STAR                 LOOP         ",
    "VALUATION": 0,
    "PLANNED CHECK FEE": "0.00",
    "PERMIT FEE": "62.000000",
    "TOTAL FEE": "62.000000",
    "CONTRACTOR NAME": "                              ",
    "Permit Group Type": "Electrical",
    "Permit Group Tab": "Other Permits",
}

_PERMIT_SECRETARIA = {
    "_id": 89084,
    "APP YR": 26,
    "APP NBR": 4329,
    "APP TYPE": "101 ",
    "APP TYPE DESC": "SINGLE FAMILY HOUSE DETACHED                 ",
    "APP STATUS": "IS",
    "APP STAT DESC": "PERMIT ISSUED            ",
    "PERMIT TYPE": "701",
    "PERMIT TYPE DESC": "EL-RESIDENTIAL                ",
    "PERMIT SEQUENCE": 0,
    "PERMIT STATUS": "PP",
    "PERMIT STATUS DESC": "PERMIT PRINTED           ",
    "PERMIT EXP. DATE": "12/29/26",
    "PERMIT SQ. FT.": 1400,
    "PERMIT ISS. DATE": "2026-07-02T00:00:00",
    "APP DESC": "NEW RESIDENCE (ONE STORY HOME )                   ",
    "APP SQ. FT.": 1400,
    "STREET NBR": "1610     ",
    "STREET": "              SECRETARIA                LN           ",
    "VALUATION": 0,
    "PLANNED CHECK FEE": "0.00",
    "PERMIT FEE": "153.500000",
    "TOTAL FEE": "153.500000",
    "CONTRACTOR NAME": "                              ",
    "Permit Group Type": "Electrical",
    "Permit Group Tab": "Other Permits",
}

_WATERMARK_ISO = "2026-07-02T00:00:00"


# ======================================================================
# Spatial tests
# ======================================================================


class TestLaredoSpatial:
    def test_metro_bbox_sanity(self):
        assert LAREDO_METRO_BBOX["min_lat"] < LAREDO_METRO_BBOX["max_lat"]
        assert LAREDO_METRO_BBOX["min_lng"] < LAREDO_METRO_BBOX["max_lng"]

    def test_center_is_inside_metro(self):
        assert is_in_laredo_metro(LAREDO_CENTER["lat"], LAREDO_CENTER["lng"])

    def test_is_in_laredo_metro_rejects_missing_coordinates(self):
        assert is_in_laredo_metro(None, None) is False
        assert is_in_laredo_metro(27.5306, None) is False
        assert is_in_laredo_metro(None, -99.4803) is False

    def test_is_in_laredo_metro_rejects_other_cities(self):
        assert is_in_laredo_metro(29.7604, -95.3698) is False  # Houston
        assert is_in_laredo_metro(29.4241, -98.4936) is False  # San Antonio
        assert is_in_laredo_metro(31.7619, -106.4850) is False  # El Paso
        assert is_in_laredo_metro(32.7767, -96.7970) is False  # Dallas
        assert is_in_laredo_metro(30.2672, -97.7431) is False  # Austin

    def test_downtown_anchors_are_contained(self):
        assert is_in_laredo_metro(27.5306, -99.4803)  # City Hall area
        assert is_in_laredo_metro(27.5245, -99.5075)  # Downtown & San Agustin
        assert is_in_laredo_metro(27.5450, -99.5050)  # Heights & Del Mar
        assert is_in_laredo_metro(27.6200, -99.5600)  # Mines Road

    def test_live_fixture_addresses_geocode_inside_metro(self):
        # Reconstructed addresses geocode to roughly these WGS84 points
        # (ADR-0004 Census/Nominatim). Pin containment, not exact geocode.
        # Approximate geocodes for the three fixture addresses:
        assert is_in_laredo_metro(27.532, -99.505)  # ~801 PALOMA CT
        assert is_in_laredo_metro(27.618, -99.560)  # ~5528 LONE STAR LOOP
        assert is_in_laredo_metro(27.570, -99.485)  # ~1610 SECRETARIA LN

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LAREDO_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LAREDO_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LAREDO_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LAREDO_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LAREDO_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LAREDO_SUBMARKETS.items():
            bbox = LAREDO_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LAREDO_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LAREDO_SUBMARKETS)

    def test_submarkets_carry_the_laredo_city_id(self):
        assert {m.city_id for m in LAREDO_SUBMARKETS.values()} == {"laredo"}

    def test_city_id_and_registration_shape(self):
        assert LAREDO_CITY_ID == "laredo"
        assert LAREDO_CENTER["lat"] == 27.5306
        assert LAREDO_CENTER["lng"] == -99.4803
        assert REGISTRATION.metro_bbox is LAREDO_METRO_BBOX
        assert REGISTRATION.submarkets is LAREDO_SUBMARKETS
        assert REGISTRATION.division_bboxes is LAREDO_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_laredo_metro
        assert len(REGISTRATION.divisions) == 2
        assert 5 <= len(LAREDO_SUBMARKETS) <= 7

    def test_required_real_neighborhoods_present(self):
        assert set(LAREDO_SUBMARKETS) == {
            "Downtown & San Agustin",
            "Heights & Del Mar",
            "Zacate Creek & Washington",
            "South Laredo & Santa Rita",
            "Mines Road Corridor",
            "North Laredo & Winfield",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_laredo_metro is is_in_laredo_metro

    def test_borough_names_are_valid_divisions(self):
        for name, meta in LAREDO_SUBMARKETS.items():
            assert meta.borough in LAREDO_DIVISION_BBOXES, name

    def test_submarket_coordinates_are_numeric(self):
        for name, meta in LAREDO_SUBMARKETS.items():
            assert isinstance(meta.lat, float), name
            assert isinstance(meta.lng, float), name
            assert -90 <= meta.lat <= 90, name
            assert -180 <= meta.lng <= 180, name

    def test_division_submarket_counts_cover_all(self):
        total = sum(len(d.submarkets) for d in LAREDO_DIVISIONS.values())
        assert total == len(LAREDO_SUBMARKETS)


# ======================================================================
# Feed spec / endpoint tests
# ======================================================================


class TestLaredoFeedSpec:
    def test_feed_specs_permits_only(self):
        assert set(LAREDO_FEED_SPECS) == {"permits"}

    def test_permits_endpoint_is_ckan_datastore(self):
        assert "data.openlaredo.com/api/3/action/datastore_search" in LAREDO_PERMITS_ENDPOINT
        assert LAREDO_PERMITS_RESOURCE_ID == "61972510-7b8c-488a-9e88-b73b0112f496"
        assert LAREDO_PERMITS_RESOURCE_ID in LAREDO_PERMITS_ENDPOINT

    def test_permits_spec_matches_live_datastore(self):
        spec = LAREDO_FEED_SPECS["permits"]
        assert spec["platform"] == "ckan"
        assert spec["watermark_col"] == "PERMIT ISS. DATE"
        assert spec["needs_geocode"] is True
        assert spec["geocode_context"] == "Laredo, TX"
        assert spec["resource_id"] == LAREDO_PERMITS_RESOURCE_ID

    def test_watermark_iso_matches_live_probe(self):
        assert LAREDO_PERMITS_WATERMARK_ISO == "2026-07-02T00:00:00"
        assert LAREDO_PERMITS_WATERMARK_ISO == _WATERMARK_ISO

    def test_endpoint_resource_id_consistency(self):
        assert LAREDO_PERMITS_RESOURCE_ID in LAREDO_PERMITS_ENDPOINT
        assert LAREDO_FEED_SPECS["permits"]["endpoint"] == LAREDO_PERMITS_ENDPOINT


# ======================================================================
# Field map tests
# ======================================================================


class TestLaredoFieldMaps:
    def test_permits_map_reads_live_ckan_columns(self):
        # The datastore's own column names, spaces and dots included.
        assert PERMITS_FIELD_MAP == {
            "job_id": ["_id"],
            "issuance_date": ["PERMIT ISS. DATE"],
            "status": ["PERMIT STATUS DESC", "APP STAT DESC"],
            "job_type": ["Permit Group Type", "PERMIT TYPE DESC", "APP TYPE DESC"],
            "cost": ["VALUATION"],
            "address_street": ["address_street", "STREET"],
        }

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert GEOCODE_CONTEXT == "Laredo, TX"
        assert LAREDO_FEED_SPECS["permits"]["geocode_context"] == GEOCODE_CONTEXT

    def test_no_coordinate_candidates_in_permit_map(self):
        """CKAN permits are non-spatial — coordinates come from ADR-0004 geocode only."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        assert "lat" not in PERMITS_FIELD_MAP
        assert "lng" not in PERMITS_FIELD_MAP

    def test_contractor_name_is_dropped_pii(self):
        assert "CONTRACTOR NAME" in DROPPED_PII_COLUMNS
        for candidates in PERMITS_FIELD_MAP.values():
            assert "CONTRACTOR NAME" not in candidates

    def test_first_mapped_reads_the_raw_row(self):
        """A dotted key names the column when the row has one: the old map's
        sanitized keys ("PERMIT_ISS_DATE") matched nothing, so every permit
        went out with no issue date."""
        assert first_mapped(_PERMIT_PALOMA, PERMITS_FIELD_MAP, "job_id") == 88449
        assert first_mapped(_PERMIT_PALOMA, PERMITS_FIELD_MAP, "issuance_date") == _WATERMARK_ISO
        assert first_mapped(_PERMIT_PALOMA, PERMITS_FIELD_MAP, "status").strip() == "PERMIT PRINTED"
        assert first_mapped(_PERMIT_SECRETARIA, PERMITS_FIELD_MAP, "job_type") == "Electrical"

    def test_zero_valuation_reads_as_no_cost(self):
        # Fees are not a valuation, so a zero VALUATION leaves the cost unset.
        assert first_mapped(_PERMIT_PALOMA, PERMITS_FIELD_MAP, "cost") is None

    def test_all_fixtures_share_the_watermark(self):
        for row in (_PERMIT_PALOMA, _PERMIT_PALOMA_EL, _PERMIT_SECRETARIA):
            assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == _WATERMARK_ISO


class TestLaredoAddress:
    def test_number_and_street_join_without_padding(self):
        assert compose_permit_address(_PERMIT_PALOMA) == "801 PALOMA CT"
        assert compose_permit_address(_PERMIT_PALOMA_EL) == "5528 LONE STAR LOOP"
        assert compose_permit_address(_PERMIT_SECRETARIA) == "1610 SECRETARIA LN"

    def test_street_without_number_and_no_street(self):
        assert compose_permit_address({**_PERMIT_PALOMA, "STREET NBR": "        "}) == "PALOMA CT"
        assert compose_permit_address({**_PERMIT_PALOMA, "STREET": "      "}) is None
        assert compose_permit_address({}) is None


def _laredo_permit(group: str, tab: str, kind: str) -> dict:
    """A fixture row with another group, report tab and kind, padded the way
    the datastore pads ``PERMIT TYPE DESC``."""
    return {**_PERMIT_SECRETARIA, "Permit Group Type": group, "Permit Group Tab": tab, "PERMIT TYPE DESC": f"{kind:<30}"}


class TestLaredoPermitType:
    """The group names a trade or a class; a year of permits (2025-10-01 to
    2026-10-02, 17,925 rows) shows which groups need the kind as well."""

    def test_new_homes_and_commercial_buildings_read_as_new_construction(self):
        row = _laredo_permit("Residential", "New Construction", "SINGLE FAMILY DETACHED")
        assert compose_permit_type(row) == "New construction: SINGLE FAMILY DETACHED"
        row = _laredo_permit("Commercial Construction", "New Construction", "OFFICES, BANKS")
        assert compose_permit_type(row) == "New construction: OFFICES, BANKS"

    def test_a_mobile_home_installation_is_not_a_new_building(self):
        for kind in ("INSTALLATION PERMIT", "INSTALLATION PERMIT/MH-PENALTY"):
            assert compose_permit_type(_laredo_permit("Residential", "New Construction", kind)) is None

    def test_an_alteration_names_its_kind(self):
        # The group's own name says "Conversions", which read every reroof
        # and fence as a change of use.
        row = _laredo_permit("Additions, Alterations, and Conversions", "New Construction", "RES REROOF")
        assert compose_permit_type(row) == "Alteration: RES REROOF"

    def test_an_other_permit_is_its_kind(self):
        assert compose_permit_type(_laredo_permit("Other", "Other Permits", "SIGN PERMIT")) == "SIGN PERMIT"

    def test_trade_permits_read_their_group(self):
        assert compose_permit_type(_PERMIT_SECRETARIA) is None
        assert compose_permit_type({}) is None


class TestLaredoRegisteredSpec:
    @pytest.fixture
    def spec(self):
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        return get_dataset(CityId.LAREDO, FeedType.PERMITS)

    def test_composite_id_keeps_each_trade_permit(self, spec):
        """A house and its electrical, plumbing and mechanical permits share
        APP NBR; keyed by it, 571 of 1,000 rows dropped as duplicates."""
        assert spec.id_keys == ["APP YR", "APP NBR", "PERMIT SEQUENCE", "PERMIT TYPE"]
        assert spec.composite_id is True
        assert spec.field_map == PERMITS_FIELD_MAP

    def test_filter_drops_groups_that_are_not_building_permits(self, spec):
        for group in ("Vendor", "Internal use", "Business", "Fire Dept", "Right-of-Way/Utility", "NEZ and Pave/Parking"):
            assert f"'{group}'" in spec.where
        assert spec.where.startswith('"Permit Group Type" NOT IN (')

    def test_select_leaves_the_contractor_and_description_out(self, spec):
        selected = spec.select.split(",")
        assert "CONTRACTOR NAME" not in selected
        assert "APP DESC" not in selected
        for candidates in PERMITS_FIELD_MAP.values():
            for column in candidates:
                assert column == "address_street" or column in selected
        assert {"STREET NBR", "STREET"} <= set(selected)
        # compose_permit_type reads the group's report tab.
        assert "Permit Group Tab" in selected


class TestLaredoPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            yield DOBPermitsProducer()

    def test_row_geocodes_its_joined_address(self, permits):
        from src.features.permit_taxonomy import NormalizedPermitType
        from src.schemas.models import JobType

        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append(address)
            return (27.532, -99.505)

        with (
            patch("src.producers.field_maps.resolve_field_map", return_value=PERMITS_FIELD_MAP),
            patch("src.spatial.geocoder.geocode_row_if_declared", fake_geocode),
        ):
            event = permits.parse_socrata_row(dict(_PERMIT_PALOMA), city_id="laredo")
        assert event is not None
        assert captured == ["801 PALOMA CT"]
        assert event.job_id == "88449"
        assert event.issuance_date == datetime.fromisoformat(_WATERMARK_ISO)
        assert event.address_street == "801 PALOMA CT"
        assert event.estimated_cost == 0.0
        # An electrical permit is a trade permit.
        assert event.job_type is JobType.A2
        assert event.normalized_permit_type == NormalizedPermitType.MECHANICAL_ELECTRICAL_PLUMBING.value

    @pytest.mark.parametrize(
        ("group", "tab", "kind", "job_type", "normalized"),
        [
            ("Residential", "New Construction", "SINGLE FAMILY DETACHED", "NB", "NEW_CONSTRUCTION"),
            ("Commercial Construction", "New Construction", "5 OR MORE FAMILY BLDG", "NB", "NEW_CONSTRUCTION"),
            ("Residential", "New Construction", "INSTALLATION PERMIT", "OT", "MINOR_ALTERATION"),
            ("Additions, Alterations, and Conversions", "New Construction", "RES REROOF", "A2", "MINOR_ALTERATION"),
            (
                "Additions, Alterations, and Conversions",
                "New Construction",
                "RES REMODEL 1001 - 2000 SQFT",
                "A2",
                "MAJOR_RENOVATION",
            ),
            ("Other", "Other Permits", "SIGN PERMIT", "SG", "MINOR_ALTERATION"),
            ("Plumbing", "Other Permits", "PL-RESIDENTIAL", "A2", "MECHANICAL_ELECTRICAL_PLUMBING"),
        ],
    )
    def test_job_type_reads_group_tab_and_kind(self, permits, group, tab, kind, job_type, normalized):
        with (
            patch("src.producers.field_maps.resolve_field_map", return_value=PERMITS_FIELD_MAP),
            patch("src.spatial.geocoder.geocode_row_if_declared", return_value=(27.570, -99.485)),
        ):
            event = permits.parse_socrata_row(_laredo_permit(group, tab, kind), city_id="laredo")
        assert event is not None
        assert (event.job_type.value, event.normalized_permit_type) == (job_type, normalized)


# ======================================================================
# CKAN row-level / staleness contract tests
# ======================================================================


class TestLaredoCKANContract:
    def test_watermark_is_timestamp_string(self):
        # CKAN returns timestamp as ISO string with T separator
        for row in (_PERMIT_PALOMA, _PERMIT_PALOMA_EL, _PERMIT_SECRETARIA):
            val = row["PERMIT ISS. DATE"]
            assert "T" in val
            assert val == _WATERMARK_ISO

    def test_street_fields_are_padded_but_present(self):
        for row in (_PERMIT_PALOMA, _PERMIT_SECRETARIA):
            assert row["STREET NBR"] is not None
            assert row["STREET"] is not None
            assert row["STREET"].strip() != ""
            assert row["STREET NBR"].strip() != ""

    def test_valuation_and_fees_are_numeric_strings_or_ints(self):
        assert isinstance(_PERMIT_PALOMA["VALUATION"], int)
        assert isinstance(_PERMIT_PALOMA["TOTAL FEE"], str)
        assert float(_PERMIT_PALOMA["TOTAL FEE"]) == 200.0

    def test_permit_group_type_present(self):
        assert _PERMIT_PALOMA["Permit Group Type"] == "Electrical"
        assert _PERMIT_SECRETARIA["Permit Group Type"] == "Electrical"

    def test_ckan_row_ids_are_ints(self):
        assert isinstance(_PERMIT_PALOMA["_id"], int)
        assert isinstance(_PERMIT_SECRETARIA["_id"], int)

    def test_staleness_flag_is_pinned(self):
        """58 days behind at probe (2026-07-02 → 2026-08-30). Document the flag."""
        # This is the live watermark; if the feed advances the watermark,
        # this test must be updated and the probe re-cut.
        assert LAREDO_PERMITS_WATERMARK_ISO == "2026-07-02T00:00:00"
        # 30-day window at probe was 0 (monthly batch lag), 60-day had 86
        # — pinned as the staleness contract for this marginal Tier 2.
        assert _WATERMARK_ISO == "2026-07-02T00:00:00"
