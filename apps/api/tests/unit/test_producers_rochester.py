"""Unit tests for the Rochester, NY leaf (US-351): spatial module + field map
+ DEEDS parse wiring.

Rochester is a DEEDS-led partial metro: the only registered feed is the city
Hub's Tax Parcel Records layer (Tax_Parcels_Open_Data/FeatureServer/0 on the
on-prem server maps.cityofrochester.gov), which carries per-parcel sale
fields AND native parcel polygon geometry. Permits and SLA/licenses are
absent from the Hub; COMPLAINTS_311 is a frozen 2022 archive — none are
registered.

Tests pass WITHOUT a spine registration (no CityId.ROCHESTER): the producer
resolves city_id="rochester" as a plain string, the leaf-local field map is
pinned via the resolve_field_map patch, and coordinates come from the
production ArcGIS flatten (outSR=4326 rings reduced to a centroid) — no
geocode hook is involved (needs_geocode is False).

Live fixtures captured from the 2026-08-28 implementation re-probe
(attributes byte-verbatim from f=json; rings verbatim at outSR=4326; ≥2
rows). All watermarks match docs/research/probe-rochester.md: 64,746 total
parcels, 2026 YTD 2,279, Jul 141 / Jun 350 / May 485, Aug 0 (monthly-roll
lag holds), newest sale 07/22/2026 — the probe's headline row (547 Avis St,
$110,000, W) re-confirmed exactly as OBJECTID 5294.

Deliberate non-assertions (wave-5 contract): division/borough resolution
via the shared registry (get_division_for_coordinate) and geocode-hook call
counts — both change when the spine lands. Fixture geometry containment is
asserted against THIS module's leaf constants, which the spine copies.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_rochester import (
    DEEDS_FIELD_MAP,
    FIELD_MAP,
    NON_CANDIDATE_METADATA_COLUMNS,
)
from src.producers.watermarks import (
    compare_watermarks,
    newest_typed_watermark,
    typed_watermark_entry,
)
from src.spatial.cities.rochester import (
    REGISTRATION,
    ROCHESTER_CENTER,
    ROCHESTER_CITY_ID,
    ROCHESTER_DEEDS_ENDPOINT,
    ROCHESTER_DIVISION_BBOXES,
    ROCHESTER_DIVISIONS,
    ROCHESTER_FEED_SPECS,
    ROCHESTER_METRO_BBOX,
    ROCHESTER_SUBMARKETS,
    get_rochester_dataset,
    is_in_rochester,
    is_in_rochester_metro,
)
from src.spatial.city_registry import FeedType

# ---------------------------------------------------------------------------
# Live fixtures (2026-08-28 re-probe, maps.cityofrochester.gov
# Open_Data/Tax_Parcels_Open_Data/FeatureServer/0, outSR=4326).
# Attributes byte-verbatim; rings byte-verbatim (the full first ring of the
# parcel polygon). Centroids below were computed live from these rings via
# the same shapely reduction ArcGISClient._geometry_to_lng_lat performs.
# ---------------------------------------------------------------------------

# Newest sale on the layer (probe headline row): 547 Avis St, $110,000,
# DEED_TYPE='W' (warranty), BOOK 13214 / PAGE 320, recorded 07/22/2026.
DEEDS_ROW_AVIS_ST = {
    "OBJECTID": 5294,
    "PARCELID": "09040000020190000000",
    "PRINTKEY": "090.40-2-19",
    "STREET_NUM": "547",
    "STREET_NAME": "Avis St",
    "SITEADDRESS": "547 Avis St",
    "CITY": "ROCHESTER",
    "ZIP5": "14615",
    "CLASSCD": "220",
    "CLASSDSCRP": "2 Family Residential",
    "PROPERTYTYPE": "Residential",
    "LOT_FRONTAGE": 40.0,
    "LOT_DEPTH": 100.0,
    "STATEDAREA": "0.00",
    "CURRENT_LAND_VALUE": 6800,
    "CURRENT_TOTAL_VALUE": 112200,
    "CURRENT_TAXABLE_VALUE": 112200,
    "TENTATIVE_LAND_VALUE": 6800,
    "TENTATIVE_TOTAL_VALUE": 112200,
    "TENTATIVE_TAXABLE_VALUE": 112200,
    "SALE_DATE": "07/22/2026",
    "SALE_PRICE": 110000,
    "BOOK": "13214",
    "PAGE": "320",
    "DEED_TYPE": "W",
    "VALID": "",
    "RESCOM": "R",
    "SHAPEACRES": 0.09216996,
    "BISZONING": "R-1",
    "OWNERSHIPCODE": " ",
    "NORESUNITS": 2,
    "LOW_STREET_NUM": "547",
    "HIGH_STREET_NUM": "547",
    "LOW_STREET_SORT": 547.0,
    "MultiSale": "0",
    "PARCEL_SOURCE": "MCRPS",
    "Shape__Area": 702.11030448,
    "Shape__Length": 117.07525515035447,
}

AVIS_ST_RING = [
    [-77.64813202884588, 43.195171761545545],
    [-77.64812981270208, 43.19544483990562],
    [-77.64797890202256, 43.19544427080397],
    [-77.64798044712485, 43.195171164935765],
    [-77.64813202884588, 43.195171761545545],
]
AVIS_ST_CENTROID = (-77.6480553, 43.19530791)  # (lng, lat) — shapely, live

# $1 quitclaim noise fixture: 396 Brooks Ave, DEED_TYPE='Q', recorded
# 07/21/2026 — kept at ingest per the leaf noise contract.
DEEDS_ROW_BROOKS_AVE = {
    "OBJECTID": 61058,
    "PARCELID": "13533000010690000000",
    "PRINTKEY": "135.33-1-69",
    "STREET_NUM": "396",
    "STREET_NAME": "Brooks Ave",
    "SITEADDRESS": "396 Brooks Ave",
    "CITY": "ROCHESTER",
    "ZIP5": "14619",
    "CLASSCD": "210",
    "CLASSDSCRP": "1 Family Residential",
    "PROPERTYTYPE": "Residential",
    "LOT_FRONTAGE": 40.89,
    "LOT_DEPTH": 129.95,
    "STATEDAREA": "0.00",
    "CURRENT_LAND_VALUE": 11500,
    "CURRENT_TOTAL_VALUE": 134500,
    "CURRENT_TAXABLE_VALUE": 134500,
    "TENTATIVE_LAND_VALUE": 11500,
    "TENTATIVE_TOTAL_VALUE": 134500,
    "TENTATIVE_TAXABLE_VALUE": 134500,
    "SALE_DATE": "07/21/2026",
    "SALE_PRICE": 1,
    "BOOK": "13214",
    "PAGE": "7",
    "DEED_TYPE": "Q",
    "VALID": "",
    "RESCOM": "R",
    "SHAPEACRES": 0.11761382,
    "BISZONING": "R-1",
    "OWNERSHIPCODE": " ",
    "NORESUNITS": 1,
    "LOW_STREET_NUM": "396",
    "HIGH_STREET_NUM": "396",
    "LOW_STREET_SORT": 396.0,
    "MultiSale": "0",
    "PARCEL_SOURCE": "MCRPS",
    "Shape__Area": 894.0676225,
    "Shape__Length": 140.5544984908903,
}

BROOKS_AVE_RING = [
    [-77.64593914242268, 43.13144272072234],
    [-77.64593781111941, 43.13109176598903],
    [-77.64608660357149, 43.131090443023034],
    [-77.64608770310942, 43.13120254036295],
    [-77.64608875862986, 43.13131014414939],
    [-77.64608982852337, 43.131419302124954],
    [-77.6460900531022, 43.13144219691475],
    [-77.64593914242268, 43.13144272072234],
]
BROOKS_AVE_CENTROID = (-77.64601343, 43.13126719)  # (lng, lat) — shapely, live

# SALE_DATE is TEXT on the wire — no epoch-ms date fields to flatten.
def _flatten_feature(attributes: dict, geometry: dict) -> dict:
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry}, date_fields=set()
    )


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


@pytest.fixture
def deeds():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        return DeedsACRISProducer()


class TestRochesterSpatial:
    def test_city_id_constant(self):
        assert ROCHESTER_CITY_ID == "rochester"

    def test_metro_contains_registration_center(self):
        assert is_in_rochester_metro(
            ROCHESTER_CENTER["lat"], ROCHESTER_CENTER["lng"]
        ) is True

    def test_metro_contains_parcel_verified_submarkets(self):
        for name, meta in ROCHESTER_SUBMARKETS.items():
            assert is_in_rochester_metro(meta.lat, meta.lng) is True, name

    def test_metro_rejects_null_and_neighbors(self):
        assert is_in_rochester_metro(None, None) is False
        # Pittsford village (43.0906, -77.5164) hit 0 parcels on the city
        # layer — the probe's conditional submarket is NOT evidenced and
        # must stay outside the box.
        assert is_in_rochester_metro(43.0906, -77.5164) is False
        assert is_in_rochester_metro(43.3000, -77.6000) is False  # Lake Ontario
        assert is_in_rochester_metro(43.0330, -77.4450) is False  # Fairport
        assert is_in_rochester_metro(43.0481, -76.1474) is False  # Syracuse
        assert is_in_rochester_metro(42.8864, -78.8784) is False  # Buffalo
        assert is_in_rochester_metro(42.6526, -73.7562) is False  # Albany

    def test_alias_delegates_to_metro(self):
        assert is_in_rochester(43.1560, -77.6120) is True
        assert is_in_rochester(43.0906, -77.5164) is False

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in ROCHESTER_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ROCHESTER_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ROCHESTER_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ROCHESTER_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ROCHESTER_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in ROCHESTER_SUBMARKETS.items():
            bbox = ROCHESTER_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in ROCHESTER_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ROCHESTER_SUBMARKETS)

    def test_submarkets_carry_rochester_city_id(self):
        assert {m.city_id for m in ROCHESTER_SUBMARKETS.values()} == {"rochester"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in ROCHESTER_DIVISIONS.items():
            bbox = ROCHESTER_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(ROCHESTER_DIVISIONS) == 6
        for div in ROCHESTER_DIVISIONS.values():
            assert div.city_id == "rochester"

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is ROCHESTER_METRO_BBOX
        assert REGISTRATION.submarkets is ROCHESTER_SUBMARKETS
        assert REGISTRATION.contains is is_in_rochester_metro


class TestFeedRegistration:
    def test_exactly_one_feed_type_is_registered(self):
        assert set(ROCHESTER_FEED_SPECS) == {"deeds"}

    def test_deeds_spec_matches_probe_contract(self):
        spec = get_rochester_dataset(FeedType.DEEDS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == ROCHESTER_DEEDS_ENDPOINT
        assert spec.watermark_col == "SALE_DATE"
        assert spec.watermark_type == "text"
        assert spec.watermark_format == "%m/%d/%Y"
        assert spec.id_keys == ["PRINTKEY", "PARCELID", "SALE_DATE"]
        assert spec.producer_key == "deeds"
        assert spec.topic == "raw.municipal.deeds"
        # Native parcel polygons supply coordinates — no ADR-0004 hook.
        assert spec.needs_geocode is False
        assert spec.geocode_context is None
        assert spec.non_spatial is False
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 100000
        assert spec.field_map is DEEDS_FIELD_MAP

    def test_deeds_spec_declares_monthly_roll_cadence(self):
        spec = get_rochester_dataset(FeedType.DEEDS)
        assert spec.expected_cadence_days == 30
        scope = ROCHESTER_FEED_SPECS["deeds"]["extra"]["scope"]
        assert "MONTHLY" in scope
        assert "stalled" in scope
        assert "quitclaim" in scope

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.PERMITS, FeedType.SLA, FeedType.COMPLAINTS_311],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'rochester'.*available"):
            get_rochester_dataset(absent_feed)

    def test_spec_accepts_feed_name_string(self):
        spec = get_rochester_dataset("deeds")
        assert spec.watermark_col == "SALE_DATE"

    def test_field_map_export_keys(self):
        assert FIELD_MAP["deeds"] is DEEDS_FIELD_MAP
        assert "permits" not in FIELD_MAP
        assert "sla" not in FIELD_MAP
        assert "311" not in FIELD_MAP


class TestRochesterFieldMaps:
    def test_deeds_map_reads_live_columns(self):
        row = DEEDS_ROW_AVIS_ST
        assert first_mapped(row, DEEDS_FIELD_MAP, "doc_id") == "090.40-2-19"
        assert first_mapped(row, DEEDS_FIELD_MAP, "bbl") == "09040000020190000000"
        assert first_mapped(row, DEEDS_FIELD_MAP, "doc_type") == "W"
        assert first_mapped(row, DEEDS_FIELD_MAP, "document_amount") == 110000
        assert first_mapped(row, DEEDS_FIELD_MAP, "recorded_date") == "07/22/2026"
        assert first_mapped(row, DEEDS_FIELD_MAP, "address_street") == "547 Avis St"
        assert first_mapped(row, DEEDS_FIELD_MAP, "borough") == "ROCHESTER"
        assert first_mapped(row, DEEDS_FIELD_MAP, "zipcode") == "14615"

    def test_doc_id_falls_back_to_parcelid_when_printkey_blank(self):
        row = {"PRINTKEY": "", "PARCELID": "09040000020190000000"}
        assert first_mapped(row, DEEDS_FIELD_MAP, "doc_id") == "09040000020190000000"

    def test_map_has_no_party_or_coordinate_or_geocode_candidates(self):
        assert "party1_grantor" not in DEEDS_FIELD_MAP
        assert "party2_grantee" not in DEEDS_FIELD_MAP
        assert "latitude" not in DEEDS_FIELD_MAP
        assert "longitude" not in DEEDS_FIELD_MAP

    def test_metadata_columns_are_never_map_candidates(self):
        candidates = {key for cands in DEEDS_FIELD_MAP.values() for key in cands}
        assert candidates.isdisjoint(NON_CANDIDATE_METADATA_COLUMNS)
        for col in ("VALID", "MultiSale", "PARCEL_SOURCE", "BOOK", "PAGE"):
            assert col in DEEDS_ROW_AVIS_ST  # live row carries them — unmapped


class TestWatermarkTyping:
    """SALE_DATE is TEXT MM/DD/YYYY per the probe contract (ADR 0005)."""

    def test_mmddyyyy_text_watermark(self):
        entry = typed_watermark_entry("07/22/2026", fmt="%m/%d/%Y")
        assert entry is not None
        assert entry[0] == "07/22/2026"
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 7, 22)

    def test_typed_comparison_beats_lexical_order(self):
        """THE TRAP: "12/31/2025" sorts lexically ABOVE "07/22/2026" but is
        the older date. The probe's first pass "max 12/31/2025" was exactly
        this error; typed comparison must pick the true newest."""
        assert compare_watermarks("12/31/2025", "07/22/2026") < 0
        newest = newest_typed_watermark(
            ["07/22/2026", "12/31/2025", "07/01/2026"], fmt="%m/%d/%Y"
        )
        assert newest is not None
        assert newest[0] == "07/22/2026"

    def test_empty_watermark_values_are_dropped(self):
        assert typed_watermark_entry("", fmt="%m/%d/%Y") is None
        assert typed_watermark_entry(None, fmt="%m/%d/%Y") is None


class TestRochesterDeedsParsing:
    def test_priced_warranty_sale_parses_with_polygon_centroid(
        self, deeds, monkeypatch
    ):
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_AVIS_ST, {"rings": [AVIS_ST_RING]})
        event = deeds.parse_socrata_row(row, city_id="rochester")
        assert event is not None
        assert event.city_id == "rochester"
        assert event.doc_id == "090.40-2-19"
        assert event.bbl == "09040000020190000000"
        assert event.doc_type == "W"
        assert event.document_amount == pytest.approx(110000.0)
        assert str(event.recorded_date).startswith("2026-07-22")
        # H3 derived from the fixture ring's centroid (not geocoded).
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None

    def test_fixture_centroids_match_live_reduction(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_AVIS_ST, {"rings": [AVIS_ST_RING]})
        event = deeds.parse_socrata_row(row, city_id="rochester")
        assert event is not None
        assert event.latitude == pytest.approx(AVIS_ST_CENTROID[1], abs=1e-6)
        assert event.longitude == pytest.approx(AVIS_ST_CENTROID[0], abs=1e-6)

    def test_fixture_coords_contained_by_leaf_bboxes(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_AVIS_ST, {"rings": [AVIS_ST_RING]})
        event = deeds.parse_socrata_row(row, city_id="rochester")
        assert event is not None
        assert is_in_rochester_metro(event.latitude, event.longitude) is True
        bbox = ROCHESTER_DIVISION_BBOXES["NORTHWEST_GORGE"]
        assert bbox["min_lat"] <= event.latitude <= bbox["max_lat"]
        assert bbox["min_lng"] <= event.longitude <= bbox["max_lng"]

    def test_source_neighborhood_is_raw_city_passthrough(self, deeds, monkeypatch):
        """The CITY column passes through as source_neighborhood verbatim;
        division RESOLUTION (event.borough) is deliberately not asserted —
        it changes when the spine lands."""
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_BROOKS_AVE, {"rings": [BROOKS_AVE_RING]})
        event = deeds.parse_socrata_row(row, city_id="rochester")
        assert event is not None
        assert event.source_neighborhood == "ROCHESTER"

    def test_dollar_quitclaim_is_kept_with_its_price(self, deeds, monkeypatch):
        """$1 DEED_TYPE='Q' quitclaims are present on the live layer and are
        KEPT at ingest (no per-city where; VB zero-price precedent) — the
        arm's-length VALID flag is empty layer-wide, so market-sale
        filtering is analysis-side."""
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_BROOKS_AVE, {"rings": [BROOKS_AVE_RING]})
        event = deeds.parse_socrata_row(row, city_id="rochester")
        assert event is not None
        assert event.doc_type == "Q"
        assert event.document_amount == pytest.approx(1.0)
        assert str(event.recorded_date).startswith("2026-07-21")
        assert event.latitude == pytest.approx(BROOKS_AVE_CENTROID[1], abs=1e-6)
        assert event.longitude == pytest.approx(BROOKS_AVE_CENTROID[0], abs=1e-6)

    def test_brooks_ave_fixture_contained_by_southwest_ward(self):
        assert is_in_rochester_metro(*BROOKS_AVE_CENTROID[::-1]) is True
        bbox = ROCHESTER_DIVISION_BBOXES["SOUTHWEST_WARD"]
        assert bbox["min_lat"] <= BROOKS_AVE_CENTROID[1] <= bbox["max_lat"]
        assert bbox["min_lng"] <= BROOKS_AVE_CENTROID[0] <= bbox["max_lng"]

    def test_no_owner_columns_so_parties_and_block_lot_stay_none(
        self, deeds, monkeypatch
    ):
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_AVIS_ST, {"rings": [AVIS_ST_RING]})
        event = deeds.parse_socrata_row(row, city_id="rochester")
        assert event is not None
        assert event.party1_grantor is None
        assert event.party2_grantee is None
        assert event.block is None
        assert event.lot is None

    def test_both_newest_reprobe_rows_parse(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        for attrs, ring in (
            (DEEDS_ROW_AVIS_ST, AVIS_ST_RING),
            (DEEDS_ROW_BROOKS_AVE, BROOKS_AVE_RING),
        ):
            row = _flatten_feature(attrs, {"rings": [ring]})
            assert deeds.parse_socrata_row(row, city_id="rochester") is not None

    def test_row_without_geometry_or_address_still_yields_lossless_event(
        self, deeds, monkeypatch
    ):
        """A flatten miss (no geometry) leaves the row lossless with null
        coordinates/H3 — needs_geocode is False so no hook can rescue it."""
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_AVIS_ST, {})
        event = deeds.parse_socrata_row(row, city_id="rochester")
        assert event is not None
        assert event.doc_id == "090.40-2-19"
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None
