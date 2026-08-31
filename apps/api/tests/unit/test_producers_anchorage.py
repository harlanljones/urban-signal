"""Unit tests for the Anchorage, AK leaf (US-330): spatial module + field map
+ DEEDS parse wiring.

Anchorage is a DEEDS-only Tier-1 metro: the only registered feed is the
assessor's property file (PropertyInformation_Hosted/FeatureServer/0 on
services2.arcgis.com/Ce3DhLRthdwbHlfF), a last-deed-per-parcel snapshot with
native parcel polygon geometry. Permits (MJ_Permits_Hosted, frozen 2023),
311, and SLA are Tier 3 — none are registered.

Tests pass WITHOUT a spine registration (no CityId.ANCHORAGE): the producer
resolves city_id="anchorage" as a plain string, the leaf-local field map is
pinned via the resolve_field_map patch (Durham precedent), and coordinates
come from the production ArcGIS flatten (outSR=4326 rings reduced to a
centroid) — no geocode hook is involved (needs_geocode is False).

Live fixtures captured from the 2026-08-28 implementation re-probe
(attributes byte-verbatim from f=json; ring verbatim at outSR=4326; the two
compact rows on the newest non-future date). All watermarks match
docs/research/probe-anchorage.md at re-probe: newest NON-future Deed_Date
2026-08-25 (the five future sentinels still pin the lexical top, max
2035-03-03), PUBDATE max 2026-08-26T23:23:21Z — the daily batch republish
continues.

Deliberate non-assertions (wave-5 contract): division/borough resolution
via the shared registry (get_division_for_coordinate) and geocode-hook call
counts — both change when the spine lands. Fixture geometry containment is
asserted against THIS module's leaf constants, which the spine copies.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_anchorage import DEEDS_FIELD_MAP, FIELD_MAP
from src.spatial.cities.anchorage import (
    ANCHORAGE_CENTER,
    ANCHORAGE_CITY_ID,
    ANCHORAGE_DEEDS_ENDPOINT,
    ANCHORAGE_DIVISION_BBOXES,
    ANCHORAGE_DIVISIONS,
    ANCHORAGE_FEED_SPECS,
    ANCHORAGE_METRO_BBOX,
    ANCHORAGE_SUBMARKETS,
    REGISTRATION,
    get_anchorage_dataset,
    is_in_anchorage,
    is_in_anchorage_metro,
)
from src.spatial.city_registry import FeedType


# ---------------------------------------------------------------------------
# Live fixtures (2026-08-28 re-probe, services2.arcgis.com
# PropertyInformation_Hosted/FeatureServer/0, outSR=4326). Attributes
# byte-verbatim; rings byte-verbatim (the full first ring of the parcel
# polygon). Centroids below were computed live from these rings via the same
# shapely reduction ArcGISClient._geometry_to_lng_lat performs. Both rows sit
# on the newest NON-future Deed_Date (2026-08-25, noon-UTC epoch-ms stamps).
# ---------------------------------------------------------------------------

# 2101 W 47TH AVE, North Star #1 BLK D2 LT 6, deed book 2026/page 312670.
DEEDS_ROW_W_47TH_AVE = {
    "OBJECTID": 211515894,
    "Appraisal_Year": 2026,
    "Parcel_ID": "01023351000",
    "Parcel_ID_URL": "https://property.muni.org/Datalets/Datalet.aspx?UseSearch=no&pin=01023351000",
    "Parcel_URL_Description": "010-233-51-000",
    "Property_Type": "Residential",
    "Class": "Residential",
    "Land_Use": "Residential 1 Family",
    "Owner_Line_1": "TAUINAOLA TOGIMANU & SERA",
    "Owner_Line_2": None,
    "Owner_Line_3": None,
    "Owner_Line_4": "2101 WEST 47TH AVENUE",
    "Owner_Name": "TAUINAOLA TOGIMANU & SERA",
    "Owner_Address": "2101 WEST 47TH AVENUE",
    "Owner_City": "ANCHORAGE",
    "Owner_State": "AK",
    "Owner_Zip": "99517-    ",
    "Legal_Description_1": "NORTH STAR #1",
    "Legal_Description_2": "BLK D2 LT 6",
    "Legal_Description_3": None,
    "Legal_Description": "NORTH STAR #1 BLK D2 LT 6",
    "Parcel_Address": "2101 W 47TH AVE",
    "Condo_Unit_Number": None,
    "Total_Living_Units": 1,
    "Lot_Size": 8122,
    "Zoning_District": "R1",
    "Grid_Map": "SW1828",
    "HRA_Number": None,
    "Tax_District": "3",
    "Deed_Book": 2026,
    "Deed_Page": 312670,
    "Plat_Number": "P-220B",
    "Appraised_Land_Value": 109600,
    "Appraised_Building_Value": 283300,
    "Appraised_Total_Value": 392900,
    "Exemption_1_Type": None,
    "Exemption_1_Amount": None,
    "Exemption_2_Type": None,
    "Exemption_2_Amount": None,
    "Exemption_5_Type": None,
    "Exemption_5_Amount": None,
    "Exemption_6_Type": None,
    "Exemption_6_Amount": None,
    "Total_Exemptions": None,
    "Taxable_Value": 392900,
    "Land_Value_Previous": 99700,
    "Building_Value_Previous": 294300,
    "Total_Value_Previous": 394000,
    "Land_Value_Previous_2": 99700,
    "Building_Value_Previous_2": 276800,
    "Total_Value_Previous_2": 376500,
    "YearBuilt": "1970",
    "YearBuilt_Min": 1970,
    "YearBuilt_Max": 1970,
    "EffectiveYear": "1970",
    "Location": None,
    "CBook_Page": "010-23",
    "GIS_Category": "Parcel",
    "GIS_Card_Number": "01",
    "GIS_Site_Street_Name": "47TH",
    "GIS_Site_Street_Number": "2101",
    "GIS_Site_Street_Pre": "W",
    "GIS_Site_Street_Suf": "",
    "GIS_Site_Street_Type": "AVE",
    "GIS_Site_City": "Anchorage",
    "GIS_Site_State": "AK",
    "GIS_Site_Zipcode": "99517",
    "GIS_Economic_Unit": None,
    "GIS_ParcelNum8": "01023351",
    "GIS_ParcelNum8Formatted": "010-233-51",
    "GIS_ParcelNum11": "01023351000",
    "GIS_ParcelNum11Formatted": "010-233-51-000",
    "PUBDATE": 1787786481000,
    "Exemption_Types_All": "",
    "Exemption_Type_Group": "No Exemptions",
    "CAMA_Acreage": 0.18645546,
    "GIS_MeanPercentSlope": 8.12881057,
    "NetTaxableValue": 392900,
    "Deed_Date": 1787659200000,
    "Parcel_ID_Count": 1,
    "Tax_District_CurrApprYear": "3",
    "Shape__Area": 3327.65625,
    "Shape__Length": 245.38943068058796,
    "GlobalID": "72bbc599-3f5b-4385-86ad-134df12ee385",
}

W_47TH_AVE_RING = [
    [-149.921329151562, 61.1782161937564],
    [-149.921698844152, 61.178215672041],
    [-149.921689905831, 61.1785714538598],
    [-149.921677791921, 61.1785714908325],
    [-149.921377102337, 61.1785723693824],
    [-149.921332399659, 61.1785724995899],
    [-149.921329151562, 61.1782161937564],
]
W_47TH_AVE_CENTROID = (-149.92151254, 61.17839296)  # (lng, lat) — shapely, live

# 6620 CIMARRON CIR, CIMARRON BLK 1 LT 37, deed book 2026/page 312660,
# primary-residence exemption $75,000 — east-side row (zip 99504).
DEEDS_ROW_CIMARRON_CIR = {
    "OBJECTID": 211522925,
    "Appraisal_Year": 2026,
    "Parcel_ID": "00717441000",
    "Parcel_ID_URL": "https://property.muni.org/Datalets/Datalet.aspx?UseSearch=no&pin=00717441000",
    "Parcel_URL_Description": "007-174-41-000",
    "Property_Type": "Residential",
    "Class": "Residential",
    "Land_Use": "Residential 1 Family",
    "Owner_Line_1": "VAONA KRISTIN",
    "Owner_Line_2": None,
    "Owner_Line_3": None,
    "Owner_Line_4": "616 W GIBRALTAR LN",
    "Owner_Name": "VAONA KRISTIN",
    "Owner_Address": "616 W GIBRALTAR LN",
    "Owner_City": "PHOENIX",
    "Owner_State": "AZ",
    "Owner_Zip": "85023-    ",
    "Legal_Description_1": "CIMARRON",
    "Legal_Description_2": "BLK 1 LT 37",
    "Legal_Description_3": None,
    "Legal_Description": "CIMARRON BLK 1 LT 37",
    "Parcel_Address": "6620 CIMARRON CIR",
    "Condo_Unit_Number": None,
    "Total_Living_Units": 1,
    "Lot_Size": 2297,
    "Zoning_District": "R2A",
    "Grid_Map": "SW1639",
    "HRA_Number": None,
    "Tax_District": "3",
    "Deed_Book": 2026,
    "Deed_Page": 312660,
    "Plat_Number": "820254",
    "Appraised_Land_Value": 80200,
    "Appraised_Building_Value": 240100,
    "Appraised_Total_Value": 320300,
    "Exemption_1_Type": None,
    "Exemption_1_Amount": None,
    "Exemption_2_Type": None,
    "Exemption_2_Amount": None,
    "Exemption_5_Type": None,
    "Exemption_5_Amount": None,
    "Exemption_6_Type": "OWNERS PRIMARY RESIDENCE",
    "Exemption_6_Amount": 75000,
    "Total_Exemptions": 75000,
    "Taxable_Value": 245300,
    "Land_Value_Previous": 80200,
    "Building_Value_Previous": 220400,
    "Total_Value_Previous": 300600,
    "Land_Value_Previous_2": 80200,
    "Building_Value_Previous_2": 201700,
    "Total_Value_Previous_2": 281900,
    "YearBuilt": "1983",
    "YearBuilt_Min": 1983,
    "YearBuilt_Max": 1983,
    "EffectiveYear": "1983",
    "Location": None,
    "CBook_Page": "007-17",
    "GIS_Category": "Parcel",
    "GIS_Card_Number": "01",
    "GIS_Site_Street_Name": "CIMARRON",
    "GIS_Site_Street_Number": "6620",
    "GIS_Site_Street_Pre": "",
    "GIS_Site_Street_Suf": "",
    "GIS_Site_Street_Type": "CIR",
    "GIS_Site_City": "Anchorage",
    "GIS_Site_State": "AK",
    "GIS_Site_Zipcode": "99504",
    "GIS_Economic_Unit": None,
    "GIS_ParcelNum8": "00717441",
    "GIS_ParcelNum8Formatted": "007-174-41",
    "GIS_ParcelNum11": "00717441000",
    "GIS_ParcelNum11Formatted": "007-174-41-000",
    "PUBDATE": 1787786497000,
    "Exemption_Types_All": "OWNERS PRIMARY RESIDENCE",
    "Exemption_Type_Group": "Other",
    "CAMA_Acreage": 0.05273186,
    "GIS_MeanPercentSlope": 6.79735118,
    "NetTaxableValue": 245300,
    "Deed_Date": 1787659200000,
    "Parcel_ID_Count": 1,
    "Tax_District_CurrApprYear": "3",
    "Shape__Area": 890.1875,
    "Shape__Length": 143.98696755340768,
    "GlobalID": "a9c938f4-f7dc-4da2-b529-d6027cc41a6a",
}

CIMARRON_CIR_RING = [
    [-149.756110168531, 61.1943342683312],
    [-149.756109069735, 61.1942675776449],
    [-149.756613499383, 61.1942665398396],
    [-149.756614211992, 61.1943371438225],
    [-149.756110168531, 61.1943342683312],
]
CIMARRON_CIR_CENTROID = (-149.75636413, 61.19430138)  # (lng, lat) — shapely, live

# Deed_Date and PUBDATE are the layer's only esriFieldTypeDate columns — the
# real flatten converts both epoch-ms values to ISO 8601 UTC strings.
_DATE_FIELDS = {"Deed_Date", "PUBDATE"}


def _flatten_feature(attributes: dict, geometry: dict) -> dict:
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry},
        date_fields=set(_DATE_FIELDS),
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


class TestAnchorageSpatial:
    def test_city_id_constant(self):
        assert ANCHORAGE_CITY_ID == "anchorage"

    def test_metro_contains_registration_center(self):
        assert is_in_anchorage_metro(
            ANCHORAGE_CENTER["lat"], ANCHORAGE_CENTER["lng"]
        ) is True

    def test_metro_contains_all_submarkets(self):
        for name, meta in ANCHORAGE_SUBMARKETS.items():
            assert is_in_anchorage_metro(meta.lat, meta.lng) is True, name

    def test_metro_contains_eagle_river_chugiak_corridor(self):
        # 12,927 live GIS_Site_City parcels evidence the corridor; both
        # community anchors must sit inside the municipality box.
        assert is_in_anchorage_metro(61.3220, -149.5480) is True  # Eagle River
        assert is_in_anchorage_metro(61.3900, -149.4700) is True  # Chugiak

    def test_metro_rejects_null_and_neighbors(self):
        assert is_in_anchorage_metro(None, None) is False
        # Mat-Su Borough (north), Kenai Peninsula (south), and the Panhandle
        # all sit outside the municipality box.
        assert is_in_anchorage_metro(61.5814, -149.4394) is False  # Wasilla
        assert is_in_anchorage_metro(61.5997, -149.1128) is False  # Palmer
        assert is_in_anchorage_metro(60.4869, -151.0583) is False  # Soldotna
        assert is_in_anchorage_metro(64.8378, -147.7164) is False  # Fairbanks
        assert is_in_anchorage_metro(58.3019, -134.4197) is False  # Juneau
        assert is_in_anchorage_metro(60.9000, -151.5000) is False  # Cook Inlet

    def test_alias_delegates_to_metro(self):
        assert is_in_anchorage(61.2176, -149.8997) is True
        assert is_in_anchorage(61.5814, -149.4394) is False

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in ANCHORAGE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ANCHORAGE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ANCHORAGE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ANCHORAGE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ANCHORAGE_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in ANCHORAGE_SUBMARKETS.items():
            bbox = ANCHORAGE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in ANCHORAGE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ANCHORAGE_SUBMARKETS)

    def test_submarkets_carry_anchorage_city_id(self):
        assert {m.city_id for m in ANCHORAGE_SUBMARKETS.values()} == {"anchorage"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in ANCHORAGE_DIVISIONS.items():
            bbox = ANCHORAGE_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(ANCHORAGE_DIVISIONS) == 5
        for div in ANCHORAGE_DIVISIONS.values():
            assert div.city_id == "anchorage"

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is ANCHORAGE_METRO_BBOX
        assert REGISTRATION.submarkets is ANCHORAGE_SUBMARKETS
        assert REGISTRATION.contains is is_in_anchorage_metro


class TestFeedRegistration:
    def test_exactly_one_feed_type_is_registered(self):
        assert set(ANCHORAGE_FEED_SPECS) == {"deeds"}

    def test_deeds_spec_matches_probe_contract(self):
        spec = get_anchorage_dataset(FeedType.DEEDS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == ANCHORAGE_DEEDS_ENDPOINT
        assert spec.watermark_col == "Deed_Date"
        assert spec.id_keys == ["Parcel_ID", "GIS_ParcelNum11", "OBJECTID"]
        assert spec.producer_key == "deeds"
        assert spec.topic == "raw.municipal.deeds"
        # Native parcel polygons supply coordinates — no ADR-0004 hook.
        assert spec.needs_geocode is False
        assert spec.geocode_context is None
        assert spec.non_spatial is False
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.field_map == DEEDS_FIELD_MAP

    def test_deeds_spec_declares_future_sentinel_where_guard(self):
        spec = get_anchorage_dataset(FeedType.DEEDS)
        assert spec.where == "Deed_Date <= CURRENT_TIMESTAMP"
        assert spec.order_by == "Deed_Date DESC"
        # watermark_exclude is CSV-client-only and the arcgis path ignores
        # it — the spec must not pretend otherwise.
        assert spec.watermark_exclude == []

    def test_deeds_spec_declares_batch_publication_cadence(self):
        spec = get_anchorage_dataset(FeedType.DEEDS)
        assert spec.expected_cadence_days == 3
        scope = ANCHORAGE_FEED_SPECS["deeds"]["extra"]["scope"]
        assert "BATCH" in scope
        assert "SENTINELS" in scope
        assert "weekend" in scope

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.PERMITS, FeedType.SLA, FeedType.COMPLAINTS_311],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'anchorage'.*available"):
            get_anchorage_dataset(absent_feed)

    def test_spec_accepts_feed_name_string(self):
        spec = get_anchorage_dataset("deeds")
        assert spec.watermark_col == "Deed_Date"

    def test_field_map_export_keys(self):
        assert FIELD_MAP["deeds"] is DEEDS_FIELD_MAP
        assert "permits" not in FIELD_MAP
        assert "sla" not in FIELD_MAP
        assert "311" not in FIELD_MAP


class TestAnchorageFieldMaps:
    def test_deeds_map_reads_live_columns(self):
        row = DEEDS_ROW_W_47TH_AVE
        assert first_mapped(row, DEEDS_FIELD_MAP, "doc_id") == "01023351000"
        assert first_mapped(row, DEEDS_FIELD_MAP, "bbl") == "01023351000"
        assert first_mapped(row, DEEDS_FIELD_MAP, "recorded_date") == 1787659200000
        assert first_mapped(row, DEEDS_FIELD_MAP, "borough") == "Anchorage"
        assert first_mapped(row, DEEDS_FIELD_MAP, "party2_grantee") == (
            "TAUINAOLA TOGIMANU & SERA"
        )
        assert first_mapped(row, DEEDS_FIELD_MAP, "address_street") == "2101 W 47TH AVE"
        assert first_mapped(row, DEEDS_FIELD_MAP, "zipcode") == "99517"

    def test_document_amount_is_deliberately_unmapped(self):
        """No sale-price/consideration column exists on the assessor file;
        assessed values must not masquerade as deed amounts (NOLA sold-
        properties precedent) — document_amount parses 0.0 by design."""
        assert "document_amount" not in DEEDS_FIELD_MAP
        for assessed in (
            "Appraised_Land_Value",
            "Appraised_Building_Value",
            "Appraised_Total_Value",
            "Taxable_Value",
        ):
            assert assessed in DEEDS_ROW_W_47TH_AVE  # live, never a candidate

    def test_no_grantor_or_coordinate_candidates(self):
        # Snapshot grain: the current owner is the GRANTEE (party2); the
        # seller does not exist on this feed. Coordinates come from the
        # polygon flatten, never the field map.
        assert "party1_grantor" not in DEEDS_FIELD_MAP
        assert "latitude" not in DEEDS_FIELD_MAP
        assert "longitude" not in DEEDS_FIELD_MAP

    def test_doc_type_not_mapped(self):
        """No deed-type column; the producer's generic chain picks up
        Property_Type (e.g. "RESIDENTIAL") — the map stays out of the way."""
        assert "doc_type" not in DEEDS_FIELD_MAP
        assert first_mapped(DEEDS_ROW_W_47TH_AVE, DEEDS_FIELD_MAP, "doc_type") is None

    def test_all_map_candidates_exist_on_the_live_row(self):
        # "id" is the generic fallback candidate (Durham precedent) and is
        # not a live column; every other candidate must be real.
        candidates = {key for cands in DEEDS_FIELD_MAP.values() for key in cands}
        live_columns = set(DEEDS_ROW_W_47TH_AVE)
        assert candidates - {"id"} <= live_columns


class TestWatermarkTyping:
    """Deed_Date is esriFieldTypeDate: epoch-ms on the wire, ISO 8601 UTC
    after the ArcGISClient flatten, stamped noon UTC (not local-midnight
    AKST/AKDT)."""

    def test_epoch_ms_flattens_to_noon_utc_iso(self):
        from src.producers.arcgis_client import ArcGISClient

        assert (
            ArcGISClient._epoch_ms_to_iso(1787659200000)
            == "2026-08-25T12:00:00+00:00"
        )

    def test_flattened_watermark_parses(self):
        from src.producers.watermarks import typed_watermark_entry

        iso = "2026-08-25T12:00:00+00:00"
        entry = typed_watermark_entry(iso)
        assert entry is not None
        assert entry[0] == iso
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 25)

    def test_future_sentinel_sorts_above_real_newest(self):
        """THE TRAP: a naive ORDER BY Deed_Date DESC returns the 2035
        sentinel as 'newest'. The spec's where guard (source exclusion)
        plus the scheduler's US-111 future guard are both mandatory."""
        from src.producers.watermarks import compare_watermarks

        assert (
            compare_watermarks("2035-03-03T12:00:00+00:00", "2026-08-25T12:00:00+00:00")
            > 0
        )

    def test_null_watermark_stays_null_through_flatten(self):
        from src.producers.arcgis_client import ArcGISClient

        assert ArcGISClient._epoch_ms_to_iso(None) is None


class TestAnchorageDeedsParsing:
    def test_newest_deed_parses_with_polygon_centroid(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_W_47TH_AVE, {"rings": [W_47TH_AVE_RING]})
        event = deeds.parse_socrata_row(row, city_id="anchorage")
        assert event is not None
        assert event.city_id == "anchorage"
        assert event.doc_id == "01023351000"
        assert event.bbl == "01023351000"
        assert event.doc_type == "RESIDENTIAL"
        # No sale-price column: assessed values must not masquerade.
        assert event.document_amount == pytest.approx(0.0)
        assert str(event.recorded_date).startswith("2026-08-25")
        # H3 derived from the fixture ring's centroid (not geocoded).
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None

    def test_fixture_centroid_matches_live_reduction(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_W_47TH_AVE, {"rings": [W_47TH_AVE_RING]})
        event = deeds.parse_socrata_row(row, city_id="anchorage")
        assert event is not None
        assert event.latitude == pytest.approx(W_47TH_AVE_CENTROID[1], abs=1e-6)
        assert event.longitude == pytest.approx(W_47TH_AVE_CENTROID[0], abs=1e-6)

    def test_fixture_coords_contained_by_leaf_bboxes(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_W_47TH_AVE, {"rings": [W_47TH_AVE_RING]})
        event = deeds.parse_socrata_row(row, city_id="anchorage")
        assert event is not None
        assert is_in_anchorage_metro(event.latitude, event.longitude) is True
        bbox = ANCHORAGE_DIVISION_BBOXES["WEST_ANCH"]
        assert bbox["min_lat"] <= event.latitude <= bbox["max_lat"]
        assert bbox["min_lng"] <= event.longitude <= bbox["max_lng"]

    def test_source_neighborhood_is_raw_city_passthrough(self, deeds, monkeypatch):
        """GIS_Site_City passes through as source_neighborhood verbatim;
        division RESOLUTION (event.borough) is deliberately not asserted —
        it changes when the spine lands."""
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_CIMARRON_CIR, {"rings": [CIMARRON_CIR_RING]})
        event = deeds.parse_socrata_row(row, city_id="anchorage")
        assert event is not None
        assert event.source_neighborhood == "Anchorage"

    def test_grantee_is_current_owner_and_grantor_stays_none(
        self, deeds, monkeypatch
    ):
        """Snapshot grain: Owner_Name is the last recorded deed's GRANTEE
        (the buyer side). party1_grantor (the seller) does not exist on this
        feed; block/lot columns do not either."""
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_W_47TH_AVE, {"rings": [W_47TH_AVE_RING]})
        event = deeds.parse_socrata_row(row, city_id="anchorage")
        assert event is not None
        assert event.party2_grantee == "TAUINAOLA TOGIMANU & SERA"
        assert event.party1_grantor is None
        assert event.block is None
        assert event.lot is None

    def test_east_side_fixture_contained_by_east_anchorage(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_CIMARRON_CIR, {"rings": [CIMARRON_CIR_RING]})
        event = deeds.parse_socrata_row(row, city_id="anchorage")
        assert event is not None
        assert event.latitude == pytest.approx(CIMARRON_CIR_CENTROID[1], abs=1e-6)
        assert event.longitude == pytest.approx(CIMARRON_CIR_CENTROID[0], abs=1e-6)
        assert is_in_anchorage_metro(event.latitude, event.longitude) is True
        bbox = ANCHORAGE_DIVISION_BBOXES["EAST_ANCHORAGE"]
        assert bbox["min_lat"] <= event.latitude <= bbox["max_lat"]
        assert bbox["min_lng"] <= event.longitude <= bbox["max_lng"]
        assert str(event.recorded_date).startswith("2026-08-25")

    def test_both_newest_reprobe_rows_parse(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        for attrs, ring in (
            (DEEDS_ROW_W_47TH_AVE, W_47TH_AVE_RING),
            (DEEDS_ROW_CIMARRON_CIR, CIMARRON_CIR_RING),
        ):
            row = _flatten_feature(attrs, {"rings": [ring]})
            assert deeds.parse_socrata_row(row, city_id="anchorage") is not None

    def test_row_without_geometry_still_yields_lossless_event(
        self, deeds, monkeypatch
    ):
        """A flatten miss (no geometry) leaves the row lossless with null
        coordinates/H3 — needs_geocode is False so no hook can rescue it."""
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_W_47TH_AVE, {})
        event = deeds.parse_socrata_row(row, city_id="anchorage")
        assert event is not None
        assert event.doc_id == "01023351000"
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None

    def test_pubdate_and_book_page_ride_unmapped(self, deeds, monkeypatch):
        """PUBDATE (publish vintage) and Deed_Book/Deed_Page (recorded-deed
        references) are live columns that stay OUT of the field map — the
        watermark is Deed_Date alone and id_keys carry the parcel keys."""
        _patch_resolve(monkeypatch, "deeds")
        row = _flatten_feature(DEEDS_ROW_W_47TH_AVE, {"rings": [W_47TH_AVE_RING]})
        event = deeds.parse_socrata_row(row, city_id="anchorage")
        assert event is not None
        for col in ("PUBDATE", "Deed_Book", "Deed_Page"):
            assert col in DEEDS_ROW_W_47TH_AVE
            for cands in DEEDS_FIELD_MAP.values():
                assert col not in cands
