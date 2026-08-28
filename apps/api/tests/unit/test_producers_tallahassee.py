"""Unit tests for the Tallahassee leaf (US-303): spatial module + field maps
+ PERMITS / COMPLAINTS_311 / DEEDS parse wiring.

Tallahassee / Leon County registers three native-space point layers on ONE
joint City/County ArcGIS Server 10.81 (``intervector.leoncountyfl.gov``, web-
adaptor base ``/intervector/rest/services/MapServices/``): active building
permits (``/TLC_OverlayPermitsActive_D_WM/MapServer/0``), Infor PublicWorks
311 service requests (``/LCPW_InforServiceRequest_D_WM/MapServer/1``), and a
rolling 3-year sales set (``/LCPA_Last3YearsSales_D_WM/MapServer/0``). All
three are native points with ``needs_geocode=False`; geometry (requested
``outSR=4326``) supplies WGS84 lat/lng, so the projected attribute coordinate
columns are never mapped (permits ``Latitude``/``Longitude`` are Web Mercator
meters; 311 ``GPSX``/``GPSY`` are FL State Plane North feet). No SLA — no BTR
dataset in the org.

Host/ordering contract (verified live 2026-08-28): no layer publishes an
``objectIdField``. Permits/Deeds carry ``OBJECTID`` (ordering OK); the 311
layer carries only ``ESRI_OID`` (``orderByFields=OBJECTID`` returns error 400).
The 311 spec carries ``where="CALLDTTM <= CURRENT_TIMESTAMP"`` to exclude the
future-dated sentinel and scheduled-fogging rows. The host is ANSI-date-
literal (bare ISO literals 400).

Tests pass WITHOUT a spine registration (no CityId.TALLAHASSEE): the
producers resolve city_id="tallahassee" as a plain string, the leaf-local field
maps are pinned via resolve_field_map patches, and geocoding is mocked at
src.spatial.geocoder.geocode_row_if_declared (Virginia Beach / Lynchburg
pattern). The native coordinate path means the geocode hook is never reached
for these feeds.

Live fixtures captured from the 2026-08-28 re-probe (all watermarks match
docs/research/se-probe-tallahassee.md; >=2 rows per feed, byte-verbatim
attribute values). Each fixture carries the geometry-derived
``latitude``/``longitude`` keys the ArcGIS client lifts (``outSR=4326``), with
the wire projected values noted in comments. ArcGIS epoch-ms dates are shown
flattened to the ISO strings the client produces.

Stability contract: these tests assert PARSE fields, job-type classification
from ``PermitTypeMapped``, H3-from-fixture-coordinates, bbox containment, and
field-map mappings — deliberately NOT division/borough resolution results and
NOT geocode-hook call counts, both of which shift when the spine lands.
"""

import h3
from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_tallahassee import (
    COMPLAINTS_311_FIELD_MAP,
    DEEDS_FIELD_MAP,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.producers.watermarks import newest_typed_watermark, typed_watermark_entry
from src.spatial.cities.tallahassee import (
    REGISTRATION,
    TALLAHASSEE_311_ENDPOINT,
    TALLAHASSEE_CENTER,
    TALLAHASSEE_CITY_ID,
    TALLAHASSEE_DEEDS_ENDPOINT,
    TALLAHASSEE_DIVISION_BBOXES,
    TALLAHASSEE_DIVISIONS,
    TALLAHASSEE_FEED_SPECS,
    TALLAHASSEE_GEOCODE_CONTEXT,
    TALLAHASSEE_METRO_BBOX,
    TALLAHASSEE_PERMITS_ENDPOINT,
    TALLAHASSEE_SUBMARKETS,
    get_tallahassee_dataset,
    is_in_tallahassee_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# ---------------------------------------------------------------------------
# Live fixtures (2026-08-28 re-probe, intervector.leoncountyfl.gov).
# ---------------------------------------------------------------------------

# Newest permit by AppliedDate DESC (OBJ 89) — a swimming-pool permit. The
# AppliedDate value "2026-08-18T00:00:00+00:00" is the ISO the ArcGIS client
# flattens from epoch-ms 1787011200000. Its geometry (outSR=4326) is the
# latitude/longitude below; the attribute Latitude/Longitude are Web Mercator
# meters and are NOT mapped.
PERMITS_ROW_SWIMMING = {
    "OBJECTID": 89,
    "PermitNum": "TPL260073",
    "Description": "Haifa",
    "AppliedDate": "2026-08-18T00:00:00+00:00",
    "IssuedDate": None,
    "CompletedDate": None,
    "StatusDate": "2026-08-18T00:00:00+00:00",
    "StatusCurrent": "PENDING",
    "OriginalAddress1": "7053 SAWLEY LN",
    "OriginalAddress2": None,
    "OriginalCity": "Tallahassee",
    "OriginalState": "FL",
    "OriginalZip": None,
    "Jurisdiction": "City of Tallahassee",
    "PermitClassMapped": "Swimming Pool",
    "WorkClassMapped": "Not Used",
    "PermitTypeMapped": "Swimming Pool",
    "PermitTypeDesc": "BI : Swimming Pool Permit",
    "TotalSqFt": 544.0,
    "EstProjectCost": 243.0,
    "HousingUnits": None,
    "PIN": "121721  A0230",
    "ContractorCompanyName": "SERVCO POOL SERVICES INC",
    "ContractorTrade": "CPC",
    "ProposedUse": None,
    "PubDte": None,
    "latitude": 30.481002487481497,
    "longitude": -84.15746971388482,
}

# Newest permit by AppliedDate DESC (OBJ 1115) — a new single-family residential
# permit. PermitTypeMapped "New" classifies as NB.
PERMITS_ROW_RESIDENTIAL = {
    "OBJECTID": 1115,
    "PermitNum": "TRB261011",
    "Description": "Construction of a Residential house at 2870 Ashbury Hill Dr.",
    "AppliedDate": "2026-08-18T00:00:00+00:00",
    "IssuedDate": None,
    "CompletedDate": None,
    "StatusDate": "2026-08-18T00:00:00+00:00",
    "StatusCurrent": "PENDING",
    "OriginalAddress1": "2870 ASBURY HILL",
    "OriginalAddress2": None,
    "OriginalCity": "Tallahassee",
    "OriginalState": "FL",
    "OriginalZip": None,
    "Jurisdiction": "City of Tallahassee",
    "PermitClassMapped": "One Family Detached",
    "WorkClassMapped": "Not Used",
    "PermitTypeMapped": "New",
    "PermitTypeDesc": "BI : Residential Building Permit",
    "TotalSqFt": 3753.0,
    "EstProjectCost": 1301.0,
    "HousingUnits": 0,
    "PIN": "1117700000070",
    "ContractorCompanyName": "FLORIDA DEVELOPERS INC. OF TALLAHASSEE",
    "ContractorTrade": "CGC",
    "ProposedUse": None,
    "PubDte": None,
    "latitude": 30.48240049696304,
    "longitude": -84.25971528578684,
}

# A recently-issued permit (OBJ 1412, IssuedDate 2026-08-17T18:00:00Z) used for
# the issuance-date parse test. WorkClassMapped "New"; EstProjectCost 372601.
PERMITS_ROW_ISSUED = {
    "OBJECTID": 1412,
    "PermitNum": "LB2601108",
    "Description": "model home single family 5 bed, 4baths w/ garage",
    "AppliedDate": "2026-07-28T18:00:00+00:00",
    "IssuedDate": "2026-08-17T18:00:00+00:00",
    "CompletedDate": None,
    "StatusDate": "2026-08-17T00:00:00+00:00",
    "StatusCurrent": "ISSUED",
    "OriginalAddress1": "",
    "OriginalAddress2": None,
    "OriginalCity": "Tallahassee",
    "OriginalState": "FL",
    "OriginalZip": None,
    "Jurisdiction": "Leon County",
    "PermitClassMapped": "Single Family Detached",
    "WorkClassMapped": "New",
    "PermitTypeMapped": "New",
    "PermitTypeDesc": "Residential Single Family",
    "TotalSqFt": 4221.0,
    "EstProjectCost": 372601.0,
    "HousingUnits": None,
    "PIN": "1220206300000",
    "ContractorCompanyName": "PREMIER CONSTRUCTION-RESIDENTIAL LLC",
    "ContractorTrade": "Contractor - Building",
    "ProposedUse": None,
    "PubDte": "2026-08-19T18:00:00+00:00",
    "latitude": 30.470559743364696,
    "longitude": -84.15703363122171,
}

# Newest real 311 row (SERVNO 483094, CALLDTTM 2026-08-28T11:03:00Z). The
# geometry (outSR=4326) WGS84 lat/lng is the latitude/longitude below;
# GPSX/GPSY are FL State Plane North feet and are NOT mapped.
COMPLAINT_ROW_FOGGING = {
    "SERVNO": 483094,
    "ESRI_OID": 171546,
    "COUNTY": "LEON",
    "DISTRICT": "4",
    "CALL_SOURCE": "Phone",
    "RESCODE": " ",
    "DESCRIPT": None,
    "RESP": "OPS",
    "CALLDTTM": "2026-08-28T11:03:00+00:00",
    "RESDTTM": None,
    "CATEGORY": 1035,
    "CATNAME": "Mosquito Control",
    "PROBCODE": "18",
    "PROBDESC": "Mosquito Control Property Truck Fogging",
    "GPSX": 2051411.96341401,
    "GPSY": 566119.72484885,
    "INSPECTR": "90005104",
    "LOC": None,
    "PRIMCALL": "Y",
    "INITCALL": "Y",
    "ADDRESS": "2756  MILLSTONE PLANTATION RD  ",
    "latitude": 30.556392252636098,
    "longitude": -84.23659120764816,
}

# A resolved 311 row (SERVNO 483073, RESDTTM set) used for the closed-date test.
COMPLAINT_ROW_RESOLVED = {
    "SERVNO": 483073,
    "ESRI_OID": 170400,
    "COUNTY": "LEON",
    "DISTRICT": "2",
    "CALL_SOURCE": "Phone",
    "RESCODE": "W/O",
    "DESCRIPT": "Workorder Completed",
    "RESP": "OPS",
    "CALLDTTM": "2026-08-27T13:47:00+00:00",
    "RESDTTM": "2026-08-27T00:00:00+00:00",
    "CATEGORY": 1035,
    "CATNAME": "Mosquito Control",
    "PROBCODE": "18",
    "PROBDESC": "Mosquito Control Property Truck Fogging",
    "GPSX": 1995360.81355754,
    "GPSY": 521588.28303622,
    "INSPECTR": "90005104",
    "LOC": None,
    "PRIMCALL": "Y",
    "INITCALL": "Y",
    "ADDRESS": "8039  BABY FARM CT  ",
    "latitude": 30.43418900908406,
    "longitude": -84.4147696317154,
}

# Newest deeds rows by SALES_SALEDT DESC. SALES_SALEKEY is the per-sale id;
# SALES_PARID is the space-padded fixed-width parcel id (bbl); the geometry
# (outSR=4326) WGS84 lat/lng is the latitude/longitude below. NO address column.
DEEDS_ROW_MONIZ = {
    "OBJECTID": 11222,
    "SALES_JUR": "47",
    "SALES_PARID": "110480  C0050",
    "SALES_SALEDT": "2026-08-24T00:00:00+00:00",
    "SALES_PRICE": 220100.0,
    "SALES_STAMPVAL": 1540.7,
    "SALES_SEQ": 0,
    "SALES_SALEKEY": 514646,
    "SALES_STATUS": None,
    "SALES_TRANSNO": None,
    "SALES_INSTRUNO": None,
    "SALES_INSTRTYP": "CT",
    "SALES_BOOK": "6204",
    "SALES_PAGE": "1030",
    "SALES_OLDOWN": "MONIZ WAYNE R &",
    "SALES_OLDOWN2": "MONIZ FRANCES R",
    "SALES_OWN1": "SANDEEP TYAGI",
    "SALES_OWN2": None,
    "SALES_SOURCE": "D",
    "SALES_SALETYPE": "I",
    "SALES_ASMT": None,
    "SALES_RECORDDT": "2026-08-24T00:00:00+00:00",
    "SALES_TRANSDT": None,
    "SALES_ADJAMT": None,
    "SALES_ADJPRICE": 220100.0,
    "SALES_MKTVALID": None,
    "latitude": 30.513649725030568,
    "longitude": -84.23133084764862,
}

DEEDS_ROW_NIX_WARRANTY = {
    "OBJECTID": 11625,
    "SALES_JUR": "47",
    "SALES_PARID": "113533  J0120",
    "SALES_SALEDT": "2026-08-21T00:00:00+00:00",
    "SALES_PRICE": 485000.0,
    "SALES_STAMPVAL": 3395.0,
    "SALES_SEQ": 4,
    "SALES_SALEKEY": 514411,
    "SALES_STATUS": None,
    "SALES_TRANSNO": None,
    "SALES_INSTRUNO": None,
    "SALES_INSTRTYP": "WD",
    "SALES_BOOK": "6203",
    "SALES_PAGE": "2194",
    "SALES_OLDOWN": "NIX SAMANTHA &",
    "SALES_OLDOWN2": "MILLS CHRISTOPHER",
    "SALES_OWN1": "HUYNH KENNETH T &",
    "SALES_OWN2": "THIEU TRAM BICH",
    "SALES_SOURCE": "D",
    "SALES_SALETYPE": "I",
    "SALES_ASMT": None,
    "SALES_RECORDDT": "2026-08-21T00:00:00+00:00",
    "SALES_TRANSDT": None,
    "SALES_ADJAMT": None,
    "SALES_ADJPRICE": 485000.0,
    "SALES_MKTVALID": None,
    "latitude": 30.442742484060897,
    "longitude": -84.1979794715909,
}


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


@pytest.fixture
def complaints():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        return Complaints311Producer()


@pytest.fixture
def deeds():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        return DeedsACRISProducer()


def _mock_geocode(monkeypatch):
    monkeypatch.setattr(
        "src.spatial.geocoder.geocode_row_if_declared",
        lambda *args, **kwargs: (30.44, -84.28),
    )


class TestTallahasseeSpatial:
    def test_city_id_constant(self):
        assert TALLAHASSEE_CITY_ID == "tallahassee"

    def test_metro_contains_registration_center(self):
        assert is_in_tallahassee_metro(
            TALLAHASSEE_CENTER["lat"], TALLAHASSEE_CENTER["lng"]
        ) is True

    def test_metro_contains_known_landmarks(self):
        assert is_in_tallahassee_metro(30.4383, -84.2807) is True  # Capitol downtown
        assert is_in_tallahassee_metro(30.4419, -84.3005) is True  # FSU campus
        assert is_in_tallahassee_metro(30.5383, -84.2101) is True  # Killearn
        assert is_in_tallahassee_metro(30.5255, -84.3825) is True  # Lake Jackson
        assert is_in_tallahassee_metro(30.4263, -84.1972) is True  # Southwood

    def test_metro_rejects_null_and_neighbors(self):
        assert is_in_tallahassee_metro(None, None) is False
        assert is_in_tallahassee_metro(30.1800, -84.3700) is False  # Crawfordville (Wakulla, S)
        assert is_in_tallahassee_metro(30.5450, -83.8700) is False  # Monticello (Jefferson, E)
        assert is_in_tallahassee_metro(30.6000, -84.9000) is False  # far W (Gulf / Gadsden)
        assert is_in_tallahassee_metro(30.1000, -84.3000) is False  # far S (Wakulla)

    def test_metro_bbox_grounded_in_deeds_extent(self):
        """Live deeds extent (sampled Sales-2026 rows, 2026-08-28): lat
        30.2997-30.6218, lng -84.6948 - -84.0605. The metro box must cover it."""
        assert TALLAHASSEE_METRO_BBOX["min_lat"] <= 30.2997
        assert TALLAHASSEE_METRO_BBOX["max_lat"] >= 30.6218
        assert TALLAHASSEE_METRO_BBOX["min_lng"] <= -84.6948
        assert TALLAHASSEE_METRO_BBOX["max_lng"] >= -84.0605

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in TALLAHASSEE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= TALLAHASSEE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= TALLAHASSEE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= TALLAHASSEE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= TALLAHASSEE_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in TALLAHASSEE_SUBMARKETS.items():
            bbox = TALLAHASSEE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in TALLAHASSEE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(TALLAHASSEE_SUBMARKETS)

    def test_submarkets_carry_tallahassee_city_id(self):
        assert {m.city_id for m in TALLAHASSEE_SUBMARKETS.values()} == {"tallahassee"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in TALLAHASSEE_DIVISIONS.items():
            bbox = TALLAHASSEE_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(TALLAHASSEE_DIVISIONS) == 6
        for div in TALLAHASSEE_DIVISIONS.values():
            assert div.city_id == "tallahassee"

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is TALLAHASSEE_METRO_BBOX
        assert REGISTRATION.submarkets is TALLAHASSEE_SUBMARKETS
        assert REGISTRATION.contains is is_in_tallahassee_metro


class TestFeedRegistration:
    def test_exactly_three_feed_types_are_registered(self):
        assert set(TALLAHASSEE_FEED_SPECS) == {"permits", "311", "deeds"}

    def test_all_endpoints_share_the_web_adaptor_base(self):
        base = "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices"
        assert TALLAHASSEE_PERMITS_ENDPOINT == f"{base}/TLC_OverlayPermitsActive_D_WM/MapServer/0"
        assert TALLAHASSEE_311_ENDPOINT == f"{base}/LCPW_InforServiceRequest_D_WM/MapServer/1"
        assert TALLAHASSEE_DEEDS_ENDPOINT == f"{base}/LCPA_Last3YearsSales_D_WM/MapServer/0"

    def test_permits_spec_matches_probe_contract(self):
        spec = get_tallahassee_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == TALLAHASSEE_PERMITS_ENDPOINT
        assert spec.watermark_col == "AppliedDate"
        assert spec.watermark_type is None
        assert spec.id_keys == ["PermitNum", "OBJECTID"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is False
        assert spec.order_by == "OBJECTID"
        assert spec.oid_field == "OBJECTID"
        assert spec.expected_cadence_days == 7
        assert spec.field_map is PERMITS_FIELD_MAP

    def test_311_spec_declares_where_and_esri_oid(self):
        spec = get_tallahassee_dataset(FeedType.COMPLAINTS_311)
        assert spec.platform == "arcgis"
        assert spec.endpoint == TALLAHASSEE_311_ENDPOINT
        assert spec.watermark_col == "CALLDTTM"
        assert spec.id_keys == ["SERVNO", "ESRI_OID"]
        assert spec.producer_key == "311"
        assert spec.needs_geocode is False
        assert spec.where == "CALLDTTM <= CURRENT_TIMESTAMP"
        # 311 layer carries no OBJECTID — ESRI_OID ordering is mandatory.
        assert spec.order_by == "ESRI_OID"
        assert spec.oid_field == "ESRI_OID"
        assert spec.expected_cadence_days == 1
        assert spec.field_map is COMPLAINTS_311_FIELD_MAP

    def test_deeds_spec_declares_no_parcel_join(self):
        spec = get_tallahassee_dataset(FeedType.DEEDS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == TALLAHASSEE_DEEDS_ENDPOINT
        assert spec.watermark_col == "SALES_SALEDT"
        assert spec.id_keys == ["SALES_SALEKEY", "OBJECTID"]
        assert spec.producer_key == "deeds"
        assert spec.needs_geocode is False
        assert spec.order_by == "OBJECTID"
        assert spec.oid_field == "OBJECTID"
        assert spec.expected_cadence_days == 1
        assert spec.parcel_join == {}
        assert spec.field_map is DEEDS_FIELD_MAP

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.SLA, FeedType.CRIME, FeedType.STR],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'tallahassee'.*available"):
            get_tallahassee_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["311"] is COMPLAINTS_311_FIELD_MAP
        assert FIELD_MAP["deeds"] is DEEDS_FIELD_MAP
        assert GEOCODE_CONTEXT == TALLAHASSEE_GEOCODE_CONTEXT == "Tallahassee, FL"
        assert "sla" not in FIELD_MAP


class TestTallahasseeFieldMaps:
    def test_permits_map_reads_live_columns(self):
        row = PERMITS_ROW_RESIDENTIAL
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "TRB261011"
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_type") == "New"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == "2870 ASBURY HILL"
        assert first_mapped(row, PERMITS_FIELD_MAP, "bbl") == "1117700000070"
        assert first_mapped(row, PERMITS_FIELD_MAP, "borough") == "City of Tallahassee"
        assert first_mapped(row, PERMITS_FIELD_MAP, "cost") == 1301.0
        assert first_mapped(row, PERMITS_FIELD_MAP, "status") == "PENDING"

    def test_permits_job_id_falls_back_to_objectid(self):
        row = {"PermitNum": None, "OBJECTID": 1115}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 1115

    def test_permits_map_never_maps_web_mercer_attribute_coordinates(self):
        """The Latitude/Longitude attributes are Web Mercator meters — the map
        must declare NO latitude/longitude candidates so only the geometry
        (outSR=4326) coordinates survive."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP

    def test_311_map_reads_live_columns(self):
        row = COMPLAINT_ROW_FOGGING
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_id") == 483094
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "complaint_type") == "Mosquito Control Property Truck Fogging"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "created_date") == "2026-08-28T11:03:00+00:00"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_address") == "2756  MILLSTONE PLANTATION RD  "
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "borough") == "4"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "status") == "OPS"

    def test_311_map_never_maps_state_plane_gps(self):
        """GPSX/GPSY are FL State Plane North feet — the map must declare NO
        latitude/longitude candidates so only the geometry (outSR=4326)
        coordinates survive."""
        assert "latitude" not in COMPLAINTS_311_FIELD_MAP
        assert "longitude" not in COMPLAINTS_311_FIELD_MAP
        assert "GPSX" not in COMPLAINTS_311_FIELD_MAP.get("latitude", [])
        assert "GPSY" not in COMPLAINTS_311_FIELD_MAP.get("longitude", [])
        assert "zipcode" not in COMPLAINTS_311_FIELD_MAP

    def test_deeds_map_reads_live_columns(self):
        row = DEEDS_ROW_MONIZ
        assert first_mapped(row, DEEDS_FIELD_MAP, "doc_id") == 514646
        assert first_mapped(row, DEEDS_FIELD_MAP, "bbl") == "110480  C0050"
        assert first_mapped(row, DEEDS_FIELD_MAP, "document_amount") == 220100.0
        assert first_mapped(row, DEEDS_FIELD_MAP, "recorded_date") == "2026-08-24T00:00:00+00:00"
        assert first_mapped(row, DEEDS_FIELD_MAP, "party1_grantor") == "MONIZ WAYNE R &"
        assert first_mapped(row, DEEDS_FIELD_MAP, "party2_grantee") == "SANDEEP TYAGI"

    def test_deeds_map_has_no_address_or_coordinate_candidates(self):
        """The sales layer has no address column and already serves parcel-
        centroid geometry, so the map declares neither address nor coordinate
        candidates and doc_type is left unmapped (defaults to DEED)."""
        assert "address_street" not in DEEDS_FIELD_MAP
        assert "incident_address" not in DEEDS_FIELD_MAP
        assert "latitude" not in DEEDS_FIELD_MAP
        assert "longitude" not in DEEDS_FIELD_MAP
        assert "doc_type" not in DEEDS_FIELD_MAP


class TestWatermarkTyping:
    """All three watermarks are true date columns — epoch-ms on the wire,
    ISO after ArcGISClient flatten, parsed under the default entry."""

    def test_permits_applieddate_iso_parses(self):
        entry = typed_watermark_entry("2026-08-18T00:00:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 18)

    def test_311_calldttm_iso_parses(self):
        entry = typed_watermark_entry("2026-08-28T11:03:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 28)

    def test_deeds_salessaledt_iso_parses(self):
        entry = typed_watermark_entry("2026-08-24T00:00:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 24)

    def test_newest_across_all_three_feeds_is_2026_08_28(self):
        newest = newest_typed_watermark(
            [
                "2026-08-18T00:00:00+00:00",  # permits AppliedDate
                "2026-08-28T11:03:00+00:00",  # 311 CALLDTTM
                "2026-08-24T00:00:00+00:00",  # deeds SALES_SALEDT
                "2026-08-27T13:47:00+00:00",  # 311 runner-up
            ]
        )
        assert newest is not None
        assert newest[0].startswith("2026-08-28")

    def test_empty_watermark_values_are_dropped(self):
        assert typed_watermark_entry("") is None
        assert typed_watermark_entry(None) is None


class TestTallahasseePermitParsing:
    def test_residential_permit_parses_with_geometry_coords(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        _mock_geocode(monkeypatch)
        event = permits.parse_socrata_row(PERMITS_ROW_RESIDENTIAL, city_id="tallahassee")
        assert event is not None
        assert event.city_id == "tallahassee"
        assert event.job_id == "TRB261011"
        assert event.address_street == "2870 ASBURY HILL"
        assert event.bbl == "1117700000070"
        assert event.latitude == pytest.approx(PERMITS_ROW_RESIDENTIAL["latitude"])
        assert event.longitude == pytest.approx(PERMITS_ROW_RESIDENTIAL["longitude"])
        assert event.h3_res7 == _h3_res7(
            PERMITS_ROW_RESIDENTIAL["latitude"],
            PERMITS_ROW_RESIDENTIAL["longitude"],
        )
        assert is_in_tallahassee_metro(event.latitude, event.longitude)

    def test_new_construction_maps_permit_type_to_nb(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        _mock_geocode(monkeypatch)
        event = permits.parse_socrata_row(PERMITS_ROW_RESIDENTIAL, city_id="tallahassee")
        assert event is not None
        assert event.job_type == JobType.NB

    def test_swimming_pool_permit_classifies_as_ot(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        _mock_geocode(monkeypatch)
        event = permits.parse_socrata_row(PERMITS_ROW_SWIMMING, city_id="tallahassee")
        assert event is not None
        assert event.job_id == "TPL260073"
        assert event.job_type == JobType.OT

    def test_issued_permit_parses_issuance_date(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        _mock_geocode(monkeypatch)
        event = permits.parse_socrata_row(PERMITS_ROW_ISSUED, city_id="tallahassee")
        assert event is not None
        assert event.job_id == "LB2601108"
        assert str(event.issuance_date).startswith("2026-08-17")
        assert event.estimated_cost == 372601.0
        assert event.status == "ISSUED"

    def test_source_neighborhood_is_jurisdiction(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        _mock_geocode(monkeypatch)
        event = permits.parse_socrata_row(PERMITS_ROW_SWIMMING, city_id="tallahassee")
        assert event is not None
        assert event.source_neighborhood == "City of Tallahassee"

    def test_permit_fixture_coordinates_sit_inside_metro(self):
        for row in (PERMITS_ROW_SWIMMING, PERMITS_ROW_RESIDENTIAL, PERMITS_ROW_ISSUED):
            assert is_in_tallahassee_metro(row["latitude"], row["longitude"])


class TestTallahasseeComplaintsParsing:
    def test_311_parses_with_geometry_coords(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        _mock_geocode(monkeypatch)
        event = complaints.parse_socrata_row(COMPLAINT_ROW_FOGGING, city_id="tallahassee")
        assert event is not None
        assert event.city_id == "tallahassee"
        assert event.incident_id == "483094"
        assert event.complaint_type == "Mosquito Control Property Truck Fogging"
        assert event.incident_address == "2756  MILLSTONE PLANTATION RD  "
        assert event.latitude == pytest.approx(COMPLAINT_ROW_FOGGING["latitude"])
        assert event.longitude == pytest.approx(COMPLAINT_ROW_FOGGING["longitude"])
        assert event.h3_res7 == _h3_res7(
            COMPLAINT_ROW_FOGGING["latitude"],
            COMPLAINT_ROW_FOGGING["longitude"],
        )
        assert event.h3_res9 is not None
        assert is_in_tallahassee_metro(event.latitude, event.longitude)

    def test_311_calldttm_parses_to_created_date(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        _mock_geocode(monkeypatch)
        event = complaints.parse_socrata_row(COMPLAINT_ROW_FOGGING, city_id="tallahassee")
        assert event is not None
        assert str(event.created_date).startswith("2026-08-28")

    def test_311_resolved_row_parses_closed_date(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        _mock_geocode(monkeypatch)
        event = complaints.parse_socrata_row(COMPLAINT_ROW_RESOLVED, city_id="tallahassee")
        assert event is not None
        assert event.incident_id == "483073"
        assert str(event.closed_date).startswith("2026-08-27")

    def test_311_fixture_coordinates_sit_inside_metro(self):
        for row in (COMPLAINT_ROW_FOGGING, COMPLAINT_ROW_RESOLVED):
            assert is_in_tallahassee_metro(row["latitude"], row["longitude"])


class TestTallahasseeDeedsParsing:
    def test_deed_parses_with_geometry_coords(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_MONIZ, city_id="tallahassee")
        assert event is not None
        assert event.city_id == "tallahassee"
        assert event.doc_id == "514646"
        assert event.bbl == "110480  C0050"
        assert event.document_amount == 220100.0
        assert event.party1_grantor == "MONIZ WAYNE R &"
        assert event.party2_grantee == "SANDEEP TYAGI"
        assert event.latitude == pytest.approx(DEEDS_ROW_MONIZ["latitude"])
        assert event.longitude == pytest.approx(DEEDS_ROW_MONIZ["longitude"])
        assert event.h3_res7 == _h3_res7(
            DEEDS_ROW_MONIZ["latitude"], DEEDS_ROW_MONIZ["longitude"]
        )
        assert event.h3_res8 is not None and event.h3_res9 is not None
        assert is_in_tallahassee_metro(event.latitude, event.longitude)

    def test_saledate_parses_to_recorded_date(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_NIX_WARRANTY, city_id="tallahassee")
        assert event is not None
        assert event.doc_id == "514411"
        assert str(event.recorded_date).startswith("2026-08-21")
        assert event.document_amount == 485000.0

    def test_doc_type_defaults_to_deed(self, deeds, monkeypatch):
        """doc_type is left unmapped so the producer defaults to 'DEED' instead
        of emitting the shorthand SALES_INSTRTYP literal (CT/WD)."""
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_NIX_WARRANTY, city_id="tallahassee")
        assert event is not None
        assert event.doc_type == "DEED"

    def test_leaves_geometry_coordinates_present_without_geocode(self, deeds, monkeypatch):
        """The sales layer serves native parcel-centroid points — the deed parses
        with coordinates from the geometry and never reaches the geocode hook."""
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_MONIZ, city_id="tallahassee")
        assert event is not None
        assert event.latitude is not None and event.longitude is not None

    def test_deed_fixture_coordinates_sit_inside_metro(self):
        for row in (DEEDS_ROW_MONIZ, DEEDS_ROW_NIX_WARRANTY):
            assert is_in_tallahassee_metro(row["latitude"], row["longitude"])


class TestGeocodingCaveats:
    def test_tallahassee_context_is_a_state_token(self):
        assert _STATE_RE.search("TALLAHASSEE FL".upper()) is not None
        assert GEOCODE_CONTEXT == "Tallahassee, FL"

    def test_unit_designator_normalization_preserves_city(self):
        norm = normalize_address("2756 MILLSTONE PLANTATION RD APT 2, TALLAHASSEE, FL")
        assert "APT" not in norm
        assert "TALLAHASSEE" in norm

    def test_context_would_append_when_street_has_no_state(self):
        # needs_geocode is False for all three feeds, so the geocode hook stays
        # unreached; this only guards the context string itself.
        assert _STATE_RE.search("2756 MILLSTONE PLANTATION RD".upper()) is None
