"""Contract tests for Columbus, OH (ArcGIS building permits, 311 and deeds)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.producers.scheduler import MunicipalIngestionScheduler
from src.producers.watermarks import ANSI_DATE_LITERAL_HOSTS, watermark_comparison
from src.schemas.models import Complaint311Event
from src.spatial.cities.columbus import (
    COLUMBUS_DIVISION_BBOXES,
    COLUMBUS_DIVISIONS,
    COLUMBUS_METRO_BBOX,
    COLUMBUS_SUBMARKETS,
    is_in_columbus_metro,
)
from src.spatial.city_registry import CityId, FeedType

# Recommended DatasetSpec.field_map for HJ-118. Every entry spells a
# column the shared producer fallback chains cannot reach (uppercase Accela
# schema); latitude/longitude need no entry because ArcGISClient lifts point
# geometry onto those exact keys before parsing.
COLUMBUS_FIELD_MAP = {
    "job_id": ["B1_ALT_ID"],
    "issuance_date": ["ISSUED_DT"],
    "cost": ["G3_VALUE_TTL"],
    "address_street": ["SITE_ADDRESS"],
    "zipcode": ["B1_SITUS_ZIP"],
    "status": ["PERMIT_STATUS"],
    "job_type": ["B1_PER_TYPE"],
}

# Recommended DatasetSpec.field_map for US-127 (Franklin County
# Auditor sales points). Dual old/new schema: Sale_Price + OWN1/OWN2 populate
# every row (1568/1568) while SALEPRICE (1543) and Instrument_Number/
# MUNINAME/NHBDNAME (0) are partial/empty layer-wide — hence the fully
# populated "new" side first on the price/parties candidates.
COLUMBUS_DEEDS_FIELD_MAP = {
    "doc_id": ["Instrument_Number", "PARCELID"],
    "bbl": ["PARCELID"],
    "document_amount": ["Sale_Price", "SALEPRICE"],
    "recorded_date": ["SALEDATE"],
    "party1_grantor": ["OWNERNME1"],
    "party2_grantee": ["OWN1", "OWN2"],
    "incident_address": ["SITEADDRESS"],
    "zipcode": ["ZIPCD"],
    "borough": ["MUNINAME", "NHBDNAME"],
}

# DatasetSpec.field_map for the City's "All Service Requests - Last 3 Years"
# layer. DATAHUB_ID is the request key (unique across all 920,928 rows on
# 2026-09-29); CASE_ID is not, because one CRM case can spawn up to eight
# requests. closed_date stays unmapped: STATUS_DATE is the last status change
# for every status, not a close time.
COLUMBUS_311_FIELD_MAP = {
    "incident_id": ["DATAHUB_ID"],
    "latitude": ["LATITUDE"],
    "longitude": ["LONGITUDE"],
    "created_date": ["REPORTED_DATE"],
    "status": ["STATUS"],
    "complaint_type": ["REQUEST_TYPE", "REQUEST_SUBCATEGORY", "REQUEST_CATEGORY"],
    "incident_address": ["STREET"],
    "zipcode": ["ZIPCODE", "ZIP"],
    "borough": ["COLUMBUSCOMMUNITY", "COUNCILDISTRICT"],
}


def test_columbus_geometry_is_self_consistent():
    assert is_in_columbus_metro(39.9612, -83.0007)
    assert is_in_columbus_metro(40.1553, -82.7928)  # observed live-row corner
    assert not is_in_columbus_metro(39.1031, -84.5120)  # Cincinnati
    assert not is_in_columbus_metro(None, None)
    for name, bbox in COLUMBUS_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= COLUMBUS_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= COLUMBUS_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= COLUMBUS_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= COLUMBUS_METRO_BBOX["max_lng"], name
    claimed = [name for division in COLUMBUS_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(COLUMBUS_SUBMARKETS)
    assert {meta.city_id for meta in COLUMBUS_SUBMARKETS.values()} == {"columbus"}


def test_columbus_registers_all_four_feed_families():
    from src.spatial.city_registry import REGISTRY, normalize_city

    city = CityId.COLUMBUS
    assert normalize_city("columbus") is city
    assert normalize_city("columbus_oh") is city
    assert REGISTRY[city].job_suffix == "cmoh"
    # US-364 adds the SNAP SLA slice (national FNS feed, State='OH'); the
    # 2026-09-30 depth pass adds the City's 311 layer.
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
        FeedType.DEEDS,
        FeedType.SLA,
    }

    permits = REGISTRY[city].datasets[FeedType.PERMITS]
    assert permits.platform == "arcgis"
    # Actual layer casing: the FeatureServer column is uppercase ISSUED_DT.
    assert permits.watermark_col == "ISSUED_DT"
    assert permits.interval_seconds == 300.0
    assert permits.producer_key == "permits"
    # HJ-118 quirk: B1_ALT_ID identifies the permit; OBJECTID must never join
    # the job-id chain (it is an edit counter, not a business key).
    assert "B1_ALT_ID" in permits.id_keys
    assert "OBJECTID" not in permits.id_keys
    assert permits.expected_cadence_days == 7
    assert permits.oid_field == "OBJECTID"
    assert permits.max_record_count == 2000
    assert permits.field_map == COLUMBUS_FIELD_MAP


def test_columbus_deeds_spec_pins_arcgis_annual_snapshot():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.COLUMBUS, FeedType.DEEDS)
    assert spec.platform == "arcgis"
    assert spec.endpoint == (
        "https://services1.arcgis.com/7r2Wl09a1Apy459r/arcgis/rest/services/"
        "FCAO_Sales_Dashboard_Last_Years_Sales_Points/FeatureServer/0"
    )
    # Actual layer casing: SALEDATE is the sale-date field on the wire.
    assert spec.watermark_col == "SALEDATE"
    assert spec.id_keys == ["PARCELID", "Instrument_Number", "OBJECTID"]
    assert spec.topic == "raw.municipal.deeds"
    assert spec.producer_key == "deeds"
    # Annual snapshot (lastEditDate 2026-07-31); the layer caps a page at 2000.
    assert spec.expected_cadence_days == 365
    assert spec.oid_field == "OBJECTID"
    assert spec.max_record_count == 2000
    assert spec.field_map == COLUMBUS_DEEDS_FIELD_MAP


def test_columbus_311_spec_pins_the_rolling_three_year_layer():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.COLUMBUS, FeedType.COMPLAINTS_311)
    assert spec.endpoint == settings.arcgis_columbus_311_url
    assert spec.endpoint == (
        "https://maps2.columbus.gov/arcgis/rest/services/Applications/"
        "ServiceRequests/MapServer/1"
    )
    assert spec.platform == "arcgis"
    assert spec.watermark_col == "REPORTED_DATE"
    assert spec.id_keys == ["DATAHUB_ID", "OBJECTID"]
    assert spec.topic == "raw.municipal.311"
    assert spec.producer_key == "311"
    assert spec.ingestion_mode == "incremental"
    assert not spec.needs_geocode
    # Newest first, so a poll after the daily extract lands on the new rows.
    assert spec.order_by == "REPORTED_DATE DESC, OBJECTID DESC"
    # "City Staff Requests" are call-centre notes, not service locations, and
    # the quarter of the layer without a point cannot be indexed.
    assert spec.where == "LATITUDE IS NOT NULL AND REQUEST_CATEGORY <> 'City Staff Requests'"
    # One extract a day, so three quiet days mean the extract stopped.
    assert spec.expected_cadence_days == 3
    assert spec.rolling_window_days == 1095
    assert spec.oid_field == "OBJECTID"
    assert spec.max_record_count == 2000
    # The daily extract tops 1,000 filtered rows on a third of weekdays (peak
    # 1,227 in the 90 days to 2026-09-28); a newest-first poll capped at the
    # default would never reach the morning's oldest rows.
    assert spec.batch_limit == 5000
    assert spec.field_map == COLUMBUS_311_FIELD_MAP


def test_columbus_311_watermark_renders_as_an_eastern_ansi_literal():
    # Verified live 2026-09-30: the server answers an ISO string in `where`
    # with a 400, accepts ANSI literals, and reads them in the layer's
    # Eastern time.
    assert "maps2.columbus.gov" in ANSI_DATE_LITERAL_HOSTS
    assert watermark_comparison(
        "REPORTED_DATE", ">", "2026-09-29T08:57:53", settings.arcgis_columbus_311_url,
        time_zone="America/New_York",
    ) == "REPORTED_DATE > timestamp '2026-09-29 04:57:53'"


CB_PERMIT_ROW = {
    # Live newest nonzero-valuation row via REST on 2026-08-24
    # (orderByFields=ISSUED_DT DESC), flattened exactly as
    # ArcGISClient._flatten_feature delivers it: attributes dict, point
    # geometry lifted to latitude/longitude, epoch-ms date fields re-encoded
    # to ISO 8601 UTC strings.
    "OBJECTID": 399023,
    "B1_ALT_ID": "RSWDR2633792",
    "B1_PER_GROUP": "Building",
    "B1_PER_TYPE": "1,2,3 Family",
    "B1_PER_SUB_TYPE": "Structural",
    "B1_PER_CATEGORY": "Roof, Siding, Windows, Doors",
    "GENERAL_TYPE": "1,2,3 Family - Other",
    "B1_PARCEL_NBR": "010267526",
    "COLS_KEY": 1209889,
    "SITE_ADDRESS": "5504 OCONNELL ST",
    "B1_SITUS_ZIP": "43110",
    "PERMIT_STATUS": "Permit Issued",
    "APPLICANT_BUS_NAME": "ROOF DETECTIVE",
    "SQFT": 2163,
    "G3_VALUE_TTL": 12630.05,
    "ISSUED_YEAR": 2026,
    "ISSUED_DT": "2026-08-22T00:00:00+00:00",
    "LAST_STATUS_DT": "2026-08-22T14:49:17+00:00",
    "CONST_TYPE_CODE": "434",
    "VALUE_DESC": "Additions, Alterations and Conversions - Residential",
    "UNITS": 1,
    "latitude": 39.893814520648746,
    "longitude": -82.84871670417796,
}

CB_ZERO_VALUATION_ROW = {
    # Live newest zero-valuation row via REST on 2026-08-24. G3_VALUE_TTL = 0
    # is legitimate and common (~63% of the newest 300 since 2026-07-01):
    # mechanical trade tickets carry no declared project cost.
    "OBJECTID": 104385,
    "B1_ALT_ID": "MMLSR2633793",
    "B1_PER_GROUP": "Building",
    "B1_PER_TYPE": "1,2,3 Family",
    "B1_PER_SUB_TYPE": "MEP",
    "B1_PER_CATEGORY": "Mechanical",
    "GENERAL_TYPE": "1,2,3 Family - Other",
    "B1_PARCEL_NBR": "010041404",
    "COLS_KEY": 160300,
    "SITE_ADDRESS": "1180 ELLSWORTH AVE",
    "B1_SITUS_ZIP": "43206",
    "PERMIT_STATUS": "Permit Issued",
    "APPLICANT_BUS_NAME": "AIRWAYS HEATING & COOLING LLC",
    "SQFT": None,
    "G3_VALUE_TTL": 0,
    "ISSUED_YEAR": 2026,
    "ISSUED_DT": "2026-08-22T00:00:00+00:00",
    "LAST_STATUS_DT": "2026-08-22T00:00:00+00:00",
    "CONST_TYPE_CODE": None,
    "VALUE_DESC": None,
    "UNITS": None,
    "latitude": 39.94206671489354,
    "longitude": -82.96107831565743,
}


class TestColumbusPermitParsing:
    """Parse pins against the shared DOBPermitsProducer.

    ``resolve_field_map`` is patched with the exact map recommended for the
    registration because the registry entry itself lands with the spine; the
    registration test above asserts the spec carries this same literal, so the
    two cannot drift once HJ-118 is wired.
    """

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=COLUMBUS_FIELD_MAP,
            ),
        ):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            yield DOBPermitsProducer()

    def test_live_newest_row_parses_uppercase_schema(self, producer):
        event = producer.parse_socrata_row(dict(CB_PERMIT_ROW), city_id="columbus")
        assert event is not None
        assert event.city_id == "columbus"
        assert event.job_id == "RSWDR2633792"  # B1_ALT_ID, never str(OBJECTID)
        assert event.status == "Permit Issued"
        assert event.address_street == "5504 OCONNELL ST"
        assert event.zipcode == "43110"
        assert event.estimated_cost == pytest.approx(12630.05)
        assert event.issuance_date is not None
        assert (event.issuance_date.year, event.issuance_date.month, event.issuance_date.day) == (
            2026,
            8,
            22,
        )
        assert event.latitude == pytest.approx(39.893814520648746)
        assert event.longitude == pytest.approx(-82.84871670417796)

    def test_zero_valuation_is_legitimate_not_a_parse_failure(self, producer):
        event = producer.parse_socrata_row(dict(CB_ZERO_VALUATION_ROW), city_id="columbus")
        assert event is not None
        assert event.job_id == "MMLSR2633793"
        assert event.estimated_cost == 0.0

    def test_objectid_never_rescues_a_missing_b1_alt_id(self, producer):
        # With B1_ALT_ID removed the id chain must come up empty even though
        # OBJECTID is present: the OID field stays out of the job-id chain.
        row = dict(CB_PERMIT_ROW)
        row.pop("B1_ALT_ID")
        assert producer.parse_socrata_row(row, city_id="columbus") is None


# Live newest-by-SALEDATE row captured 2026-08-25 from the FCAO sales points
# layer via query?where=1=1&orderByFields=SALEDATE DESC&outSR=4326, flattened
# exactly as ArcGISClient._flatten_feature delivers it: attributes dict, point
# geometry lifted to latitude/longitude, epoch-ms date fields re-encoded to
# ISO 8601 UTC strings.
CB_DEED_ROW = {
    "OBJECTID": 128,
    "PARCELID": "010-054436",
    "SALEPRICE": 360000,
    "Sale_Price": 360000,
    "OWNERNME1": "REESE JAMES M",
    "OWN1": "REESE JAMES M",
    "OWN2": "& REESE MICHELLE",
    "Instrument_Number": None,
    "Transfer_Date": None,
    "SITEADDRESS": "348 W FIRST AVE",
    "ZIPCD": "43201",
    "MUNINAME": None,
    "NHBDNAME": None,
    "SALEDATE": "2025-07-16T05:00:00+00:00",
    "latitude": 39.980748333568215,
    "longitude": -83.01376102795739,
}


class TestColumbusDeedParsing:
    """Parse a Franklin County Auditor sales point against the shared
    DeedsACRISProducer. Registration test above pins the same field map, so
    the two cannot drift. Production passes city_id="columbus", forcing the
    columbus branch (uppercase PARCELID + OWN1/OWNERNME1)."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            yield DeedsACRISProducer()

    def test_live_newest_row_parses_dual_schema(self, deeds):
        ev = deeds.parse_socrata_row(dict(CB_DEED_ROW), city_id="columbus")
        assert ev is not None
        assert ev.city_id == "columbus"
        # doc_id resolves to PARCELID because Instrument_Number is null.
        assert ev.doc_id == "010-054436"
        assert ev.bbl == "010-054436"
        assert ev.document_amount == 360000.0
        assert ev.party1_grantor == "REESE JAMES M"
        assert ev.party2_grantee == "REESE JAMES M"
        assert ev.recorded_date is not None
        assert (ev.recorded_date.year, ev.recorded_date.month, ev.recorded_date.day) == (
            2025,
            7,
            16,
        )
        assert ev.latitude == pytest.approx(39.980748333568215)
        assert ev.longitude == pytest.approx(-83.01376102795739)
        assert ev.h3_res7 is not None

    def test_disambiguates_old_vs_new_price_column(self, deeds):
        # Both price columns present -> the mapped "new" side (Sale_Price)
        # wins. On the 25 rows where SALEPRICE is null but Sale_Price is set,
        # the row still prices correctly.
        row = dict(CB_DEED_ROW)
        row["SALEPRICE"] = None
        ev = deeds.parse_socrata_row(row, city_id="columbus")
        assert ev is not None
        assert ev.document_amount == 360000.0

    def test_autodetects_columbus_without_city_id(self, deeds):
        ev = deeds.parse_socrata_row(dict(CB_DEED_ROW))
        assert ev is not None
        assert ev.city_id == "columbus"
        assert ev.doc_id == "010-054436"

    def test_coordinate_fallback_is_null_geometry_safe(self, deeds):
        # The layer is point-geocoded so every row hase coords, but the parser
        # must tolerate a null-lat/lng row (deeds-precedent) rather than crash.
        row = dict(CB_DEED_ROW)
        row["latitude"] = None
        row["longitude"] = None
        ev = deeds.parse_socrata_row(row, city_id="columbus")
        assert ev is not None
        assert ev.doc_id == "010-054436"
        assert ev.h3_res7 is None


# ======================================================================
# 311 service requests (maps2.columbus.gov ServiceRequests/MapServer/1)
# ======================================================================

# The layer's date fields; ArcGISClient re-encodes them from epoch ms to ISO
# 8601 UTC. The server stores them in Eastern time and serves UTC epochs.
_SR_DATE_FIELDS = {"STATUS_DATE", "REPORTED_DATE", "REQUEST_MODIFIED", "SLA_1", "SLA_2"}


def _service_request(
    *,
    datahub_id,
    object_id,
    case_id,
    status,
    status_ms,
    reported_ms,
    category,
    request_type,
    street,
    zip_code,
    community,
    district,
    lat,
    lng,
    point,
):
    """One raw feature as the layer serves it (attributes trimmed to the
    columns the spec reads plus their neighbours; values verbatim)."""
    return {
        "attributes": {
            "OBJECTID": object_id,
            "STATUS": status,
            "STATUS_DATE": status_ms,
            "DATAHUB_ID": datahub_id,
            "CASE_ID": case_id,
            "REPORTED_DATE": reported_ms,
            "REQUEST_CATEGORY": category,
            "REQUEST_SUBCATEGORY": category,
            "REQUEST_TYPE": request_type,
            "STREET": street,
            "CITY": "Columbus",
            "ZIP": zip_code,
            "COLUMBUSCOMMUNITY": community,
            "COUNCILDISTRICT": district,
            "ZIPCODE": zip_code,
            "LATITUDE": lat,
            "LONGITUDE": lng,
            "SLA_1": None,
            "SLA_2": None,
        },
        "geometry": {"x": point[0], "y": point[1]},
    }


# Five live rows captured 2026-09-30 from the extract loaded at ~05:00 ET on
# 2026-09-29 (orderByFields=REPORTED_DATE DESC, outSR=4326). The layer carries
# no requester name, contact or free text.
_SR_ABANDONED_VEHICLE = _service_request(
    datahub_id=3050458,
    object_id=11135271,
    case_id="CAS-3176453-Z7V5V1",
    status="Received",
    status_ms=None,
    reported_ms=1790672273000,  # 2026-09-29T08:57:53Z, the newest row
    category="Public Safety and Traffic Enforcement Issues",
    request_type="Abandoned Vehicle On Street/R.O.W.",
    street="2630 SAVILLE ROW",
    zip_code="43224",
    community="Northeast",
    district="District 5",
    lat=40.0544305096,
    lng=-82.9463160038,
    point=(-82.9463160041976, 40.05443050996114),
)
_SR_STREET_LIGHT = _service_request(
    datahub_id=3050428,
    object_id=11137595,
    case_id="CAS-3176423-S2N4S8",
    status="In Progress",
    status_ms=1790647393000,  # last status change, not a close time
    reported_ms=1790643982000,
    category="Streets, Sidewalks, Street Lighting, Sign and Signal Issues",
    request_type="Repair Of Street Lighting",
    street="3716 KELLEN DR",
    zip_code="43230",
    community="Northland",
    district="District 5",
    lat=40.0721257677,
    lng=-82.9139762088,
    point=(-82.91397620857005, 40.07212576750038),
)
_SR_ALLEY_MATERIALS = _service_request(
    datahub_id=3050427,
    object_id=11137631,
    case_id="CAS-3176421-G2N2S6",
    status="Received",
    status_ms=None,
    reported_ms=1790642820000,
    category="Trash, Recycling, Yard Waste and Illegal Dumping Issues",
    request_type="Illegal Materials in the Alley",
    street="1288 MANCHESTER AVE",
    zip_code="43211",
    community="North Linden",
    district="District 4",
    lat=40.02246,
    lng=-82.9771425,
    point=(-82.97714250023307, 40.02246000041479),
)
_SR_WATER_LINE_BREAK = _service_request(
    datahub_id=3050391,
    object_id=11135821,
    case_id="CAS-3176379-Q2D1M4",
    status="Received",
    status_ms=None,
    reported_ms=1790637635000,
    category="Water, Drinking Water, Storm Water, Flooding, Sewer Issues",
    request_type="Water Line Break",
    street="4825 WINTERSET DR",
    zip_code="43220",
    community="Northwest",
    district="District 3",
    lat=40.056435,
    lng=-83.057805,
    point=(-83.0578049998324, 40.05643500042103),
)
_SR_CLOSED_ABANDONED_VEHICLE = _service_request(
    datahub_id=3050105,
    object_id=11135131,
    case_id="CAS-3176083-V8S3D3",
    status="Closed",
    status_ms=1790643812000,
    reported_ms=1790626271000,
    category="Public Safety and Traffic Enforcement Issues",
    request_type="Abandoned Vehicle On Street/R.O.W.",
    street="5587 MILLWHEEL CT",
    zip_code="43026",
    community="Far West",
    district="District 2",
    lat=40.004118,
    lng=-83.157795,
    point=(-83.15779500034826, 40.004118000084965),
)
# In the server's order: newest REPORTED_DATE first.
_SR_FIXTURES = [
    _SR_ABANDONED_VEHICLE,
    _SR_STREET_LIGHT,
    _SR_ALLEY_MATERIALS,
    _SR_WATER_LINE_BREAK,
    _SR_CLOSED_ABANDONED_VEHICLE,
]


def _flatten_sr(feature):
    """Flatten a 311 fixture exactly as the production ArcGIS client does."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields=_SR_DATE_FIELDS)


class TestColumbus311Parsing:
    """The registered field map resolves through the shared 311 producer."""

    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            yield Complaints311Producer()

    def test_every_captured_row_parses_inside_the_metro(self, complaints):
        for feature in _SR_FIXTURES:
            event = complaints.parse_socrata_row(_flatten_sr(feature), city_id="columbus")
            assert event is not None, feature["attributes"]["DATAHUB_ID"]
            assert event.city_id == "columbus"
            assert event.incident_id == str(feature["attributes"]["DATAHUB_ID"])
            assert is_in_columbus_metro(event.latitude, event.longitude)
            assert event.h3_res7 is not None

    def test_newest_row_maps_every_declared_field(self, complaints):
        event = complaints.parse_socrata_row(
            _flatten_sr(_SR_ABANDONED_VEHICLE), city_id="columbus"
        )
        assert event is not None
        assert event.incident_id == "3050458"  # DATAHUB_ID, never CASE_ID
        assert event.complaint_type == "Abandoned Vehicle On Street/R.O.W."
        assert event.status == "Received"
        assert event.incident_address == "2630 SAVILLE ROW"
        assert event.zipcode == "43224"
        assert event.source_neighborhood == "Northeast"
        assert event.created_date == datetime(2026, 9, 29, 8, 57, 53, tzinfo=UTC)
        assert event.latitude == pytest.approx(40.0544305096)
        assert event.longitude == pytest.approx(-82.9463160038)
        assert event.closed_date is None

    def test_status_date_is_never_read_as_a_close_time(self, complaints):
        in_progress = complaints.parse_socrata_row(
            _flatten_sr(_SR_STREET_LIGHT), city_id="columbus"
        )
        closed = complaints.parse_socrata_row(
            _flatten_sr(_SR_CLOSED_ABANDONED_VEHICLE), city_id="columbus"
        )
        assert in_progress.status == "In Progress"
        assert closed.status == "Closed"
        assert in_progress.closed_date is None
        assert closed.closed_date is None

    def test_complaint_type_falls_back_to_the_category(self, complaints):
        record = _flatten_sr(_SR_WATER_LINE_BREAK)
        record["REQUEST_TYPE"] = None
        event = complaints.parse_socrata_row(record, city_id="columbus")
        assert event.complaint_type == (
            "Water, Drinking Water, Storm Water, Flooding, Sewer Issues"
        )

    def test_row_without_a_point_is_dropped_not_geocoded(self, complaints):
        # The spec filters these server-side; the parser must not guess.
        feature = {
            "attributes": {**_SR_ALLEY_MATERIALS["attributes"], "LATITUDE": None, "LONGITUDE": None},
            "geometry": None,
        }
        assert complaints.parse_socrata_row(_flatten_sr(feature), city_id="columbus") is None


_NOW = datetime(2026, 9, 30, 3, 15, tzinfo=UTC)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return _NOW if tz is None else _NOW.astimezone(tz)


@pytest.fixture
def scheduler():
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        sched = MunicipalIngestionScheduler(
            dlq_producer=MagicMock(),
            rate_limit_delay_seconds=0.0,
            dedup_capacity=1000,
        )
    wrapper = sched.producers["311"]
    wrapper.producer = MagicMock()
    wrapper.arcgis.paginate = MagicMock(return_value=[])
    return sched


class TestColumbus311SchedulerWiring:
    JOB = "311_cmoh"
    BASE_WHERE = "(LATITUDE IS NOT NULL AND REQUEST_CATEGORY <> 'City Staff Requests')"

    def test_job_is_registered_from_the_spec(self, scheduler):
        meta = scheduler.job_metadata[self.JOB]
        assert meta["platform"] == "arcgis"
        assert meta["producer_key"] == "311"
        assert meta["topic"] == "raw.municipal.311"
        assert meta["watermark_col"] == "REPORTED_DATE"
        assert meta["city_id"] == "columbus"
        assert meta["endpoint"] == settings.arcgis_columbus_311_url
        assert scheduler.configs[self.JOB].batch_limit == 5000
        assert scheduler._extract_record_id(self.JOB, _flatten_sr(_SR_ABANDONED_VEHICLE)) == (
            "311_cmoh:3050458"
        )

    def test_poll_publishes_by_request_id_and_watermarks_the_newest_report(
        self, scheduler, monkeypatch
    ):
        monkeypatch.setattr("src.producers.scheduler.datetime", _FrozenDatetime)
        complaints = scheduler.producers["311"]
        complaints.arcgis.paginate = MagicMock(
            return_value=[[_flatten_sr(feature) for feature in _SR_FIXTURES]]
        )

        result = scheduler.poll_job(self.JOB, limit=100)

        assert result["status"] == "SUCCESS"
        assert result["records_fetched"] == len(_SR_FIXTURES)
        assert result["records_published"] == len(_SR_FIXTURES)
        assert result["duplicates_skipped"] == 0
        assert scheduler.dlq_producer.route_to_dlq.call_count == 0

        produced = complaints.producer.produce.call_args_list
        assert [c.kwargs["key"] for c in produced] == [
            f"columbus:{f['attributes']['DATAHUB_ID']}" for f in _SR_FIXTURES
        ]
        assert {c.kwargs["topic"] for c in produced} == {"raw.municipal.311"}
        assert all(isinstance(c.kwargs["payload"], Complaint311Event) for c in produced)
        assert result["high_watermark"] == "2026-09-29T08:57:53"

        _, first_call = complaints.arcgis.paginate.call_args
        assert first_call["where_clause"] == self.BASE_WHERE
        assert first_call["endpoint_url"] == settings.arcgis_columbus_311_url
        assert first_call["order_by"] == "REPORTED_DATE DESC, OBJECTID DESC"

        # Next poll: the watermark as an ANSI literal in the layer's Eastern
        # time. A row the server sends again dedups instead of publishing twice.
        complaints.arcgis.paginate = MagicMock(
            return_value=[[_flatten_sr(_SR_ABANDONED_VEHICLE)]]
        )
        complaints.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": "America/New_York"})
        second = scheduler.poll_job(self.JOB, limit=100)
        _, second_call = complaints.arcgis.paginate.call_args
        assert second_call["where_clause"] == (
            f"{self.BASE_WHERE} AND REPORTED_DATE > timestamp '2026-09-29 04:57:53'"
        )
        assert second["records_published"] == 0
        assert second["duplicates_skipped"] == 1
        assert second["high_watermark"] == "2026-09-29T08:57:53"

