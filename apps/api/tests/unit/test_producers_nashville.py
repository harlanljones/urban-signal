"""Contract tests for Nashville, TN (ArcGIS building permits + residential STR licenses)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.nashville import (
    NASHVILLE_DIVISION_BBOXES,
    NASHVILLE_DIVISIONS,
    NASHVILLE_METRO_BBOX,
    NASHVILLE_SUBMARKETS,
    is_in_nashville_metro,
)
from src.spatial.city_registry import CityId, FeedType

PERMITS_FIELD_MAP = {
    "job_id": ["Permit__"],
    "issuance_date": ["Date_Issued"],
    "filing_date": ["Date_Entered"],
    "cost": ["Const_Cost"],
    "latitude": ["Lat"],
    "longitude": ["Lon"],
}

SLA_FIELD_MAP = {
    "license_id": ["Permit__"],
    "effective_date": ["Date_Issued"],
    "expiration_date": ["Expiration_Date"],
    "license_type": ["Permit_Subtype_Description", "Permit_Type"],
    "status": ["Permit_Status"],
    "latitude": ["Lat"],
    "longitude": ["Lon"],
}

COMPLAINTS_311_FIELD_MAP = {
    "incident_id": ["Request__"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
    "created_date": ["Date_Time_Opened"],
    "closed_date": ["Date_Time_Closed"],
    "status": ["Status"],
    "complaint_type": ["Request_Type", "Subrequest_Type"],
    "incident_address": ["Address"],
    "zipcode": ["ZIP"],
    "borough": ["Council_District"],
}


def test_nashville_geometry_is_self_consistent():
    assert is_in_nashville_metro(36.1627, -86.7818)
    # Live row coordinates captured 2026-08-24 (Madison, Buena Vista Pike, Antioch).
    assert is_in_nashville_metro(36.24903084, -86.73702419)
    assert is_in_nashville_metro(36.21180885, -86.81742299)
    assert is_in_nashville_metro(36.0542215, -86.58464554)
    assert not is_in_nashville_metro(35.1495, -90.0490)  # Memphis
    assert not is_in_nashville_metro(None, None)
    for name, bbox in NASHVILLE_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= NASHVILLE_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= NASHVILLE_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= NASHVILLE_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= NASHVILLE_METRO_BBOX["max_lng"], name
    claimed = [name for division in NASHVILLE_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(NASHVILLE_SUBMARKETS)
    assert {meta.city_id for meta in NASHVILLE_SUBMARKETS.values()} == {"nashville"}
    assert {meta.borough for meta in NASHVILLE_SUBMARKETS.values()} == set(NASHVILLE_DIVISIONS)


def test_nashville_registers_permits_str_and_311_feeds():
    from src.spatial.city_registry import REGISTRY, normalize_city

    city = CityId.NASHVILLE
    assert normalize_city("nashville") is city
    assert normalize_city("nashville_tn") is city
    assert REGISTRY[city].job_suffix == "bna"
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS, FeedType.SLA, FeedType.COMPLAINTS_311}


def test_nashville_permit_spec_pins_the_live_schema():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.NASHVILLE, FeedType.PERMITS)
    assert spec.platform == "arcgis"
    assert spec.endpoint.endswith("/Building_Permits_Issued_2/FeatureServer/0")
    assert spec.watermark_col == "Date_Issued"
    assert spec.id_keys == ["Permit__", "ObjectId"]
    assert spec.extra["expected_cadence_days"] == 7
    assert spec.extra["oid_field"] == "ObjectId"
    assert spec.extra["max_record_count"] == 1000
    assert spec.extra["field_map"] == PERMITS_FIELD_MAP


def test_nashville_str_spec_pins_the_live_schema():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.NASHVILLE, FeedType.SLA)
    assert spec.platform == "arcgis"
    assert spec.endpoint.endswith("/Residential_Short_Term_Rental_Permits_view/FeatureServer/0")
    assert spec.watermark_col == "Date_Issued"
    assert spec.id_keys == ["Permit__", "ObjectId"]
    assert spec.extra["expected_cadence_days"] == 14
    assert spec.extra["oid_field"] == "ObjectId"
    assert spec.extra["max_record_count"] == 1000
    assert spec.extra["field_map"] == SLA_FIELD_MAP


def test_nashville_311_spec_pins_the_live_schema():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.NASHVILLE, FeedType.COMPLAINTS_311)
    assert spec.platform == "arcgis"
    assert spec.endpoint.endswith("/hubNashville_311_Service_Requests_Current_Year_view/FeatureServer/0")
    assert spec.watermark_col == "Date_Time_Opened"
    assert spec.id_keys == ["Request__", "GlobalID", "OBJECTID"]
    assert spec.extra["expected_cadence_days"] == 7
    assert spec.extra["oid_field"] == "OBJECTID"
    assert spec.extra["max_record_count"] == 2000
    assert spec.extra["where"] == "Latitude IS NOT NULL"
    assert spec.extra["field_map"] == COMPLAINTS_311_FIELD_MAP


def test_nashville_registers_hubnashville_311_and_hard_excludes_deeds():
    """US-131 re-adjudicated the HJ-119 hubNashville 311 exclusion positive: the
    Current_Year view now carries 2026 rows, so COMPLAINTS_311 registers.
    DEEDS stays hard-excluded (no verified sales feed)."""
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.NASHVILLE, FeedType.COMPLAINTS_311)
    assert spec.platform == "arcgis"
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(CityId.NASHVILLE, FeedType.DEEDS)


def _flatten_feature(attributes: dict, geometry: dict, extra_date_fields: tuple[str, ...] = ()) -> dict:
    """Run a raw ArcGIS feature through the production flattener so parser tests
    see exactly what DOBPermitsProducer.parse_socrata_row sees after paginate."""
    from src.producers.arcgis_client import ArcGISClient

    date_fields = {"Date_Entered", "Date_Issued", *extra_date_fields}
    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry}, date_fields=date_fields
    )


PERMITS_ROW = {
    # Live newest-by-Date_Issued row (ObjectId 682) via REST on 2026-08-24;
    # Purpose/contact/owner boilerplate columns elided, asserted fields verbatim.
    "Permit__": "2022080152",
    "Permit_Type_Description": "Building Commercial - Shell",
    "Permit_Subtype_Description": "Multifamily, Apt / Twnhome > 5 Unit Bldg",
    "Parcel": "05106005800",
    "Date_Entered": 1669615200000,
    "Date_Issued": 1787202000000,
    "Const_Cost": 15368596,
    "Address": "607 W DUE WEST AVE",
    "City": "MADISON",
    "State": "TN",
    "Per_Ty": "CACH",
    "Council_Dist": 5,
    "Census_Tract": 37010802,
    "Lon": -86.73702419,
    "Lat": 36.24903084,
    "ObjectId": 682,
    "ZIP": "37115",
}
PERMITS_GEOMETRY = {"x": -86.73702419040738, "y": 36.24903083977531}


STR_ROW = {
    # Live newest-by-Date_Issued row (ObjectId 15749) via REST on 2026-08-24;
    # Purpose/applicant/phone/owner-address boilerplate elided, rest verbatim.
    "Permit__": "2026066064",
    "Permit_Subtype_Description": "Short Term Rental – Not Owner Occupied",
    "Date_Entered": 1786338000000,
    "Date_Issued": 1787288400000,
    "Expiration_Date": 1818806400000,
    "Address": "542 C ROSEDALE AVE",
    "City": "NASHVILLE",
    "State": "TN",
    "Permit_Type": "CASR",
    "Permit_SubType": "CAZ10A003",
    "Permit_Status": "ISSUED",
    "Council_Dist": 17,
    "Lon": -86.76200547,
    "Lat": 36.12424521,
    "ObjectId": 15749,
    "ZIP": "37211",
}
STR_GEOMETRY = {"x": -86.76200546978785, "y": 36.12424520967618}


COMPLAINTS_311_ROW = {
    # Live newest-by-Date_Time_Opened geocoded row (OBJECTID 186947) via REST
    # on 2026-08-25; boilerplate elided, asserted fields verbatim. ArcGISClient
    # converts Date_Time_Opened/Date_Time_Closed epoch-ms to ISO on flatten.
    "Request__": "2270024",
    "GlobalID": "f6832cb7-45f6-4c61-a392-34be2afe45ba",
    "OBJECTID": 186947,
    "Latitude": 36.0546092,
    "Longitude": -86.65544,
    "Date_Time_Opened": 1787639972000,
    "Date_Time_Closed": 1787639972000,
    "Status": "Closed",
    "Request_Type": "Public Safety",
    "Subrequest_Type": "Control Number Request for Towing",
    "Address": "1421 Rural Hill Rd, Antioch, TN 37013, USA",
    "City": "ANTIOCH",
    "ZIP": "37013",
    "Council_District": 28,
}
COMPLAINTS_311_GEOMETRY = {"x": -86.65544, "y": 36.0546092}


class TestNashvillePermitParsing:
    @pytest.fixture
    def permits(self, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city_value, feed: PERMITS_FIELD_MAP if feed is FeedType.PERMITS else {},
        )
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def _row(self):
        return _flatten_feature(PERMITS_ROW, PERMITS_GEOMETRY)

    def test_live_newest_row_parses(self, permits):
        event = permits.parse_socrata_row(self._row(), city_id="nashville")
        assert event is not None
        assert event.city_id == "nashville"

    def test_job_id_comes_from_permit_number(self, permits):
        event = permits.parse_socrata_row(self._row(), city_id="nashville")
        assert event.job_id == "2022080152"

    def test_const_cost_becomes_estimated_cost(self, permits):
        event = permits.parse_socrata_row(self._row(), city_id="nashville")
        assert event.estimated_cost == 15368596.0

    def test_two_date_model_maps_both_watermark_and_filing_date(self, permits):
        event = permits.parse_socrata_row(self._row(), city_id="nashville")
        assert str(event.issuance_date).startswith("2026-08-20")
        assert str(event.filing_date).startswith("2022-11-28")

    def test_missing_permit_number_drops_the_row(self, permits):
        attrs = {k: v for k, v in PERMITS_ROW.items() if k != "Permit__"}
        row = _flatten_feature(attrs, PERMITS_GEOMETRY)
        assert permits.parse_socrata_row(row, city_id="nashville") is None

    def test_unmapped_type_description_defaults_to_major_a1(self, permits):
        """The shared classifier never matches Metro Nashville's free-text
        Permit_Type_Description, so rows take the parser's literal ``"A1"``
        default and land on JobType.A1."""
        from src.schemas.models import JobType

        event = permits.parse_socrata_row(self._row(), city_id="nashville")
        assert event.job_type is JobType.A1
        assert event.status == "ISSUED"


class TestNashvilleMixedCaseCoordinateContract:
    """The shared chains only try lowercase latitude/lat and longitude/lng/lon,
    and ArcGISClient lifts point geometry into lowercase keys via setdefault.
    These tests prove Lat/Lon resolution comes from the registered field_map,
    not from any generic fallback."""

    @pytest.fixture
    def permits(self, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city_value, feed: PERMITS_FIELD_MAP if feed is FeedType.PERMITS else {},
        )
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_lat_lon_resolve_without_the_geometry_lift(self, permits):
        row = self._strip_lift(_flatten_feature(PERMITS_ROW, PERMITS_GEOMETRY))
        event = permits.parse_socrata_row(row, city_id="nashville")
        assert event.latitude == pytest.approx(36.24903084)
        assert event.longitude == pytest.approx(-86.73702419)

    def test_rows_do_not_parse_today_without_the_field_map(self):
        """With an empty map the mixed-case columns are invisible to every
        generic chain, so the row drops. Pins why the registration must land
        with the field_map intact (the resolver is patched empty explicitly —
        post-registration the real map would otherwise kick in)."""
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            producer = DOBPermitsProducer()
        with patch("src.producers.field_maps.resolve_field_map", lambda city_value, feed: {}):
            row = self._strip_lift(_flatten_feature(PERMITS_ROW, PERMITS_GEOMETRY))
            event = producer.parse_socrata_row(row, city_id="nashville")
        assert event is None

    @staticmethod
    def _strip_lift(row: dict) -> dict:
        stripped = dict(row)
        stripped.pop("latitude", None)
        stripped.pop("longitude", None)
        return stripped


class TestNashvilleStrLicenseParsing:
    @pytest.fixture
    def sla(self, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city_value, feed: SLA_FIELD_MAP if feed is FeedType.SLA else {},
        )
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def _row(self):
        return _flatten_feature(STR_ROW, STR_GEOMETRY, extra_date_fields=("Expiration_Date",))

    def test_live_newest_str_row_parses(self, sla):
        event = sla.parse_socrata_row(self._row(), city_id="nashville")
        assert event is not None
        assert event.city_id == "nashville"
        assert event.license_id == "2026066064"

    def test_license_type_reads_the_str_subtype(self, sla):
        event = sla.parse_socrata_row(self._row(), city_id="nashville")
        assert event.license_type == "Short Term Rental – Not Owner Occupied"

    def test_status_effective_and_expiration_map(self, sla):
        event = sla.parse_socrata_row(self._row(), city_id="nashville")
        assert event.license_status == "ISSUED"
        assert str(event.effective_date).startswith("2026-08-21")
        assert str(event.expiration_date).startswith("2027-08-21")

    def test_lat_lon_resolve_without_the_geometry_lift(self, sla):
        row = dict(self._row())
        row.pop("latitude", None)
        row.pop("longitude", None)
        event = sla.parse_socrata_row(row, city_id="nashville")
        assert event.latitude == pytest.approx(36.12424521)
        assert event.longitude == pytest.approx(-86.76200547)


class TestNashville311Parsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def _row(self):
        return _flatten_feature(
            COMPLAINTS_311_ROW,
            COMPLAINTS_311_GEOMETRY,
            extra_date_fields=("Date_Time_Opened", "Date_Time_Closed"),
        )

    def test_live_newest_row_parses(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="nashville")
        assert event is not None
        assert event.city_id == "nashville"
        assert event.incident_id == "2270024"

    def test_lat_lon_resolve_from_capital_columns_without_the_geometry_lift(self, complaints):
        row = self._row()
        row.pop("latitude", None)
        row.pop("longitude", None)
        event = complaints.parse_socrata_row(row, city_id="nashville")
        assert event.latitude == pytest.approx(36.0546092)
        assert event.longitude == pytest.approx(-86.65544)

    def test_watermark_and_closed_dates_map_from_epoch_ms(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="nashville")
        assert event.created_date.date().isoformat() == "2026-08-25"
        assert event.created_date.hour == 6
        assert event.closed_date == event.created_date

    def test_status_and_request_type_map_via_field_map(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="nashville")
        assert event.status == "Closed"
        assert event.complaint_type == "Public Safety"

    def test_address_zip_and_borough_map(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="nashville")
        assert event.incident_address == "1421 Rural Hill Rd, Antioch, TN 37013, USA"
        assert event.zipcode == "37013"
        assert event.borough is not None

    def test_null_latitude_row_drops_without_geometry(self, complaints):
        """The `where: Latitude IS NOT NULL` filter keeps the stream 100%
        geocoded; a row that still carries NULL coords (e.g. the 28.5%
        published gap) must be dropped at parse, not filed under a bogus H3."""
        row = dict(self._row())
        row.pop("latitude", None)
        row.pop("longitude", None)
        row.pop("Latitude", None)
        row.pop("Longitude", None)
        assert complaints.parse_socrata_row(row, city_id="nashville") is None
