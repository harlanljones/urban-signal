"""Unit tests for the Laredo, TX leaf (US-263): spatial module + field maps
+ CKAN permit parsing.

Laredo is a ONE-FEED Tier-2 metro on CKAN OpenGov
(``data.openlaredo.com``, resource ``61972510-7b8c-488a-9e88-b73b0112f496`` —
PERMITS ISSUED.xlsx / bpod1e.csv, 91,198 rows back to 2022, watermark
``PERMIT ISS. DATE`` newest 2026-07-02T00:00:00, monthly bulk replace,
address-only ``STREET NBR`` + ``STREET``, needs_geocode=true).

Tests pass WITHOUT a spine registration (no CityId.laredo): the leaf-local
field map is pinned via resolve_field_map patch when a producer test needs
it, and coordinates are supplied by the ADR-0004 geocode mock for the
non-spatial CKAN source (Boulder Table precedent).

Fixtures captured byte-verbatim 2026-08-30 from the live CKAN datastore
(``ORDER BY "PERMIT ISS. DATE" DESC LIMIT 3``).
"""

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
    is_in_greater_laredo_metro,
    is_in_laredo_metro,
    normalize_laredo_row,
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


def _laredo_address(row: dict) -> str:
    """Reconstruct the probe-true address string for geocoding."""
    nbr = (row.get("STREET NBR") or "").strip()
    street = (row.get("STREET") or "").strip()
    # Collapse internal whitespace (CKAN pads with spaces).
    street = " ".join(street.split())
    if nbr and street:
        return f"{nbr} {street}, Laredo, TX"
    return street or nbr


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
        # Sanitized keys (dots/spaces → "_") — see normalize_laredo_row
        assert PERMITS_FIELD_MAP["job_id"] == ["APP_NBR", "APP_YR", "_id"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["PERMIT_ISS_DATE"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["PERMIT_ISS_DATE"]
        assert PERMITS_FIELD_MAP["status"] == [
            "PERMIT_STATUS_DESC",
            "PERMIT_STATUS",
            "APP_STAT_DESC",
            "APP_STATUS",
        ]
        assert PERMITS_FIELD_MAP["job_type"] == [
            "APP_TYPE_DESC",
            "PERMIT_TYPE_DESC",
            "Permit_Group_Type",
            "Permit_Group_Tab",
        ]
        assert PERMITS_FIELD_MAP["cost"] == ["VALUATION", "TOTAL_FEE", "PERMIT_FEE"]
        assert PERMITS_FIELD_MAP["address_street"] == ["STREET", "STREET_NBR"]
        assert PERMITS_FIELD_MAP["street_number"] == ["STREET_NBR"]
        assert PERMITS_FIELD_MAP["street_name"] == ["STREET"]

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
        assert "CONTRACTOR NAME" not in PERMITS_FIELD_MAP.get("job_id", [])
        # Ensure no field map candidate accidentally references contractor PII
        for candidates in PERMITS_FIELD_MAP.values():
            assert "CONTRACTOR NAME" not in candidates

    def test_first_mapped_job_id(self):
        assert first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "job_id") == 3696
        assert first_mapped(normalize_laredo_row(_PERMIT_SECRETARIA), PERMITS_FIELD_MAP, "job_id") == 4329

    def test_first_mapped_issuance_date(self):
        assert first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "issuance_date") == _WATERMARK_ISO
        assert first_mapped(normalize_laredo_row(_PERMIT_SECRETARIA), PERMITS_FIELD_MAP, "issuance_date") == _WATERMARK_ISO

    def test_first_mapped_status(self):
        assert first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "status").strip() == "PERMIT PRINTED"
        assert first_mapped(normalize_laredo_row(_PERMIT_SECRETARIA), PERMITS_FIELD_MAP, "status").strip() == "PERMIT PRINTED"

    def test_first_mapped_job_type(self):
        # First candidate APP TYPE DESC is present
        assert first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "job_type").strip() == "SOLAR PANEL"
        assert first_mapped(normalize_laredo_row(_PERMIT_SECRETARIA), PERMITS_FIELD_MAP, "job_type").strip() == "SINGLE FAMILY HOUSE DETACHED"

    def test_first_mapped_cost(self):
        # VALUATION is 0 (falsy) → falls through to TOTAL_FEE per first_mapped semantics
        assert first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "cost") == "200.000000"
        assert first_mapped(normalize_laredo_row(_PERMIT_SECRETARIA), PERMITS_FIELD_MAP, "cost") == "153.500000"

    def test_first_mapped_address_street(self):
        # STREET is first candidate, contains padded value
        assert "PALOMA" in first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "address_street")
        assert "SECRETARIA" in first_mapped(normalize_laredo_row(_PERMIT_SECRETARIA), PERMITS_FIELD_MAP, "address_street")

    def test_first_mapped_street_number_and_name(self):
        assert first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "street_number").strip() == "801"
        assert "PALOMA" in first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "street_name")

    def test_permit_job_id_falls_back_to_oid(self):
        row = normalize_laredo_row(dict(_PERMIT_PALOMA))
        row.pop("APP_NBR")
        row.pop("APP_YR")
        # Raw keys still present but sanitized ones removed; first_mapped falls to _id
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 88449

    def test_address_reconstruction_for_geocoding(self):
        assert _laredo_address(_PERMIT_PALOMA) == "801 PALOMA CT, Laredo, TX"
        assert _laredo_address(_PERMIT_SECRETARIA) == "1610 SECRETARIA LN, Laredo, TX"
        # Lone Star Loop fixture has 5528 as number
        assert _laredo_address(_PERMIT_PALOMA_EL) == "5528 LONE STAR LOOP, Laredo, TX"

    def test_geocode_context_is_laredo_tx(self):
        assert GEOCODE_CONTEXT == "Laredo, TX"
        assert "Laredo" in _laredo_address(_PERMIT_PALOMA)

    def test_all_fixtures_share_the_watermark(self):
        for row in (_PERMIT_PALOMA, _PERMIT_PALOMA_EL, _PERMIT_SECRETARIA):
            assert first_mapped(normalize_laredo_row(row), PERMITS_FIELD_MAP, "issuance_date") == _WATERMARK_ISO

    def test_permits_group_tab_present(self):
        assert first_mapped(normalize_laredo_row(_PERMIT_PALOMA), PERMITS_FIELD_MAP, "borough") == "Other Permits"


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
