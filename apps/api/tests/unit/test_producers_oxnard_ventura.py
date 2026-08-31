"""Unit tests for the Oxnard–Ventura, CA leaf (US-232): spatial module + SLA /
311 / crime field maps and parse chains.

Anchored on the **City of San Buenaventura (City of Ventura)** — the
strongest single-jurisdiction anchor (three verified live feeds vs Oxnard's
one; ``miami_dade`` is the only composite). Three Tier-1 ArcGIS feeds on the
city's own Hub (AGO org ``dBVj4EXO3IdRPOqb``): SLA
(``OpenData_PSI_BusinessLicenses``), 311 (``Graffiti_Responses_Read_Only``),
and crime (``OpenData_Police_Crimes``). Tests pass WITHOUT a spine
registration (no ``CityId.OXNARD_VENTURA``; ``city_id="oxnard_ventura"``
strings only; no CityId imports, no REGISTRY/FeedType/scheduler/
division-resolution/geocode-call-count asserts).

Live fixtures captured 2026-08-28 from ``services.arcgis.com/
dBVj4EXO3IdRPOqb`` (orderByFields=<watermark> DESC, outFields=*, outSR=4326;
dates flattened epoch-ms → ISO 8601 UTC by ``ArcGISClient``):
SLA in-metro OBJECTID 2263 (ST. JOSEPH @ MAYFAIR OF LONDON, MIDTOWN) +
out-of-city edge OBJECTID 1641 (OUTFRONT MEDIA LLC, LOS ANGELES), 311 newest
objectid 25098 (ReportedOn 2026-08-28T19:00:00+00:00), crime newest ObjectID
85795 (Incident_Date_Start 2026-08-26T22:31:00+00:00).

CRS quirk pinned here: SLA ``BADDRX``/``BADDRY`` are a local vendor grid
(in-city ≈ 22589–24716 / 19570–20086; out-of-city 0.0) — neither degrees nor
a declared California State Plane zone, so no ``state_plane_*`` spec keys
are declared and the columns are pinned unmapped. Coordinates come from the
``outSR=4326`` geometry lift on all three feeds.
"""

from unittest.mock import patch

import h3
import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_oxnard_ventura import (
    COMPLAINTS_311_FIELD_MAP,
    CRIME_FIELD_MAP,
    DROPPED_NONADDRESS_COLUMNS,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.cities.oxnard_ventura import (
    OXNARD_VENTURA_311_ENDPOINT,
    OXNARD_VENTURA_CITY_ID,
    OXNARD_VENTURA_CRIME_ENDPOINT,
    OXNARD_VENTURA_DIVISION_BBOXES,
    OXNARD_VENTURA_DIVISIONS,
    OXNARD_VENTURA_FEED_SPECS,
    OXNARD_VENTURA_GEOCODE_CONTEXT,
    OXNARD_VENTURA_METRO_BBOX,
    OXNARD_VENTURA_SLA_ENDPOINT,
    OXNARD_VENTURA_SUBMARKETS,
    REGISTRATION,
    get_oxnard_ventura_dataset,
    is_in_oxnard_ventura_metro,
)
from src.spatial.geocoder import _STATE_RE
from src.spatial.submarkets import SubmarketMeta

# Newest SLA row inside the metro on the 2026-08-28 re-probe (DATEISSUE
# 2026-08-27T07:00:00+00:00; the vendor grid BADDRX/BADDRY reads in-city
# values, NOT coordinates — latitude/longitude come from the outSR=4326
# geometry lift). Byte-verbatim except the ArcGISClient date flatten.
SLA_ROW_MIDTOWN = {
    "ACCTNO": "1148612",
    "STATUSDESC": "Licensed",
    "NAICS_CODE": "812112",
    "NAICS_DESC": "Beauty Salons",
    "COMPNAME": "ST. JOSEPH, LYDIA",
    "DBA": "ST. JOSEPH, LYDIA @ MAYFAIR OF LONDON",
    "ADDRESS": "2043 E MAIN ST",
    "CITY": "VENTURA",
    "STATE": "CA",
    "ZIPCODE": "93001-3505",
    "BUSPHONE": "(805)494-4401",
    "BUSNOTE": "COSMETOLOGIST  205750",
    "BADDRX": 24716,
    "BADDRY": 19570,
    "BUSTYPE": "SERVICES",
    "BADDPARCEL": 730094110,
    "CONTRACTNO": " ",
    "DATESTART": "2014-01-06T08:00:00+00:00",
    "DATEISSUE": "2026-08-27T07:00:00+00:00",
    "DATEEXPIRE": "2027-06-30T07:00:00+00:00",
    "LOCCODE": "Commercial CITY",
    "OBJECTID": 2263,
    "GlobalID": "8b54571d-d1cc-4110-bdd6-8725a4135c80",
    "EconDevAreas": "MIDTOWN",
    "latitude": 34.2780692942269,
    "longitude": -119.26970431616101,
}

# SLA watermark-co-newest row that is a licensed out-of-city contractor
# (LOCCODE "Out of CITY", LOS ANGELES): the registry holds out-of-city
# accounts and their coordinates land OUTSIDE the metro bbox. Pinned to
# document that such rows still flow (honest grain), not to claim they
# resolve into Ventura divisions.
SLA_ROW_OUT_OF_CITY = {
    "ACCTNO": "331053",
    "STATUSDESC": "Licensed",
    "NAICS_CODE": "237310",
    "NAICS_DESC": "Highway, Street, and Bridge Construction",
    "COMPNAME": "OUTFRONT MEDIA LLC",
    "DBA": "OUTFRONT MEDIA LLC",
    "ADDRESS": "1731 WORKMAN ST",
    "CITY": "LOS ANGELES",
    "STATE": "CA",
    "ZIPCODE": "90031-3334",
    "BUSPHONE": "(602)246-9569",
    "BUSNOTE": "CONTRACTOR/OUTDOOR ADVERTISING",
    "BADDRX": 0,
    "BADDRY": 0,
    "BUSTYPE": "CONTRACTORS",
    "BADDPARCEL": 0,
    "CONTRACTNO": "993407",
    "DATESTART": "2004-07-26T07:00:00+00:00",
    "DATEISSUE": "2026-08-27T07:00:00+00:00",
    "DATEEXPIRE": "2027-06-30T07:00:00+00:00",
    "LOCCODE": "Out of CITY",
    "OBJECTID": 1641,
    "GlobalID": "309d299a-b778-4b12-a5be-b0dae73f4ec9",
    "EconDevAreas": "",
    "latitude": 34.223411618621334,
    "longitude": -119.35064335726362,
}

# Newest graffiti response request on the re-probe (objectid 25098). Staff
# accounts (Username/Creator/Editor) and gang-tagging Monikers ride on the
# raw layer and are dropped by the map. No address column exists.
GRAFFITI_ROW = {
    "objectid": 25098,
    "globalid": "5d859047-ba5e-4ddb-83d2-c55cee6dfb4c",
    "Username": "jivanovich@cityofventura.ca.gov_CityofVentura",
    "DateEnded": "2026-08-28T14:50:48.068000+00:00",
    "ReportedOn": "2026-08-28T19:00:00+00:00",
    "ReportedBy": "Phone",
    "Structures": "Wall",
    "PrivateProperty": "No",
    "DateNotified": None,
    "ResponseOn": "2026-08-28T19:00:00+00:00",
    "ResponseWindow": "1to24",
    "StaffTime": "1",
    "StaffTimeNumber": 1,
    "SquareFeet": 240,
    "Notes": None,
    "PhotoNote": None,
    "CreationDate": "2026-08-28T14:50:53.810000+00:00",
    "Creator": "jivanovich@cityofventura.ca.gov_CityofVentura",
    "EditDate": "2026-08-28T14:50:53.810000+00:00",
    "Editor": "jivanovich@cityofventura.ca.gov_CityofVentura",
    "Monikers": "Sker,cdrizie,",
    "latitude": 34.278392619485295,
    "longitude": -119.30283324804091,
}

# Newest crime incident on the re-probe (ObjectID 85795). GeneralizedAddress
# is block-level ("1600 Block WALTER ST") and deliberately not declared for
# geocoding — coordinates are the locator.
CRIME_ROW = {
    "ObjectID": 85795,
    "Offense_Order": 1,
    "event_rin": 1047335,
    "Report_Number": "VE202653540",
    "EventOffenseKey": "VE202653540-01",
    "GeneralizedAddress": "1600 Block WALTER ST",
    "Incident_Date_Start": "2026-08-26T22:31:00+00:00",
    "Incident_Date_End": None,
    "Council_District": "District 6",
    "Beat": "BEAT 2",
    "ReportingDistrict": "RD 65",
    "offensegroup": "Group A",
    "Crimes_Against_Category": "Crimes Against Property",
    "Offense_Category": "Motor Vehicle Theft",
    "Offense_Type": "Motor Vehicle Theft",
    "GlobalID": "6e147c48-ec87-4b1d-87e7-05d5e226b08e",
    "created_user": "SiteAdmin_CityOfVentura",
    "created_date": "2026-08-28T16:26:54.614000+00:00",
    "last_edited_user": "SiteAdmin_CityOfVentura",
    "last_edited_date": "2026-08-28T16:26:54.614000+00:00",
    "Community_Council": "District 6 Community Council",
    "Commercial": "",
    "CommercialYN": "No",
    "Park": "",
    "ParkYN": "No",
    "ResidentialYN": "No",
    "School": "",
    "SchoolYN": "No",
    "latitude": 34.25774061785711,
    "longitude": -119.23946100017902,
}

LIVE_FIXTURE_COORDS = (
    (SLA_ROW_MIDTOWN["latitude"], SLA_ROW_MIDTOWN["longitude"]),
    (GRAFFITI_ROW["latitude"], GRAFFITI_ROW["longitude"]),
    (CRIME_ROW["latitude"], CRIME_ROW["longitude"]),
)

_SUBMARKET_FIELDS = (
    "name",
    "borough",
    "lat",
    "lng",
    "zoom",
    "pitch",
    "base_lims",
    "capex",
    "permit_vel",
    "shift_ratio",
    "sla",
    "description",
    "city_id",
)


class TestOxnardVenturaSpatial:
    def test_city_id_constant(self):
        assert OXNARD_VENTURA_CITY_ID == "oxnard_ventura"

    def test_metro_contains_known_places(self):
        assert is_in_oxnard_ventura_metro(34.2795, -119.2970) is True  # Downtown core
        assert is_in_oxnard_ventura_metro(34.2600, -119.2700) is True  # Pierpont Bay
        assert is_in_oxnard_ventura_metro(34.2445, -119.2590) is True  # Ventura Harbor
        assert is_in_oxnard_ventura_metro(34.2900, -119.1680) is True  # Wells corridor
        assert is_in_oxnard_ventura_metro(34.2780, -119.1540) is True  # Saticoy

    def test_metro_rejects_oxnard_plain_and_foreign(self):
        # The bbox deliberately excludes the Oxnard plain so no future Oxnard
        # rows can resolve into Ventura divisions.
        assert is_in_oxnard_ventura_metro(34.1970, -119.1770) is False  # Oxnard downtown
        assert is_in_oxnard_ventura_metro(34.4208, -119.6982) is False  # Santa Barbara
        assert is_in_oxnard_ventura_metro(34.0522, -118.2437) is False  # Los Angeles
        assert is_in_oxnard_ventura_metro(None, None) is False

    def test_live_fixture_coords_sit_inside_the_metro_bbox(self):
        for lat, lng in LIVE_FIXTURE_COORDS:
            assert is_in_oxnard_ventura_metro(lat, lng), (lat, lng)

    def test_live_fixture_coords_land_in_exactly_one_division(self):
        for lat, lng in LIVE_FIXTURE_COORDS:
            hits = [
                name
                for name, bbox in OXNARD_VENTURA_DIVISION_BBOXES.items()
                if bbox["min_lat"] <= lat <= bbox["max_lat"]
                and bbox["min_lng"] <= lng <= bbox["max_lng"]
            ]
            assert len(hits) == 1, (lat, lng, hits)

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in OXNARD_VENTURA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= OXNARD_VENTURA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= OXNARD_VENTURA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= OXNARD_VENTURA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= OXNARD_VENTURA_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in OXNARD_VENTURA_SUBMARKETS.items():
            bbox = OXNARD_VENTURA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in OXNARD_VENTURA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(OXNARD_VENTURA_SUBMARKETS)

    def test_submarkets_carry_city_id_and_all_meta_fields(self):
        assert {m.city_id for m in OXNARD_VENTURA_SUBMARKETS.values()} == {
            "oxnard_ventura"
        }
        assert 10 <= len(OXNARD_VENTURA_SUBMARKETS) <= 18
        for name, meta in OXNARD_VENTURA_SUBMARKETS.items():
            assert isinstance(meta, SubmarketMeta), name
            for field in _SUBMARKET_FIELDS:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"
                if field == "description":
                    assert len(value) > 20, name

    def test_division_count_and_centers(self):
        assert 5 <= len(OXNARD_VENTURA_DIVISIONS) <= 8
        for name, meta in OXNARD_VENTURA_DIVISIONS.items():
            assert meta.city_id == "oxnard_ventura"
            bbox = OXNARD_VENTURA_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_spatial_registration_references_module_constants(self):
        assert REGISTRATION.metro_bbox is OXNARD_VENTURA_METRO_BBOX
        assert REGISTRATION.submarkets is OXNARD_VENTURA_SUBMARKETS
        assert REGISTRATION.divisions is OXNARD_VENTURA_DIVISIONS
        assert REGISTRATION.contains is is_in_oxnard_ventura_metro


class TestFeedRegistration:
    def test_exactly_three_feed_types_are_registered(self):
        assert set(OXNARD_VENTURA_FEED_SPECS) == {"sla", "311", "crime"}

    def test_sla_spec_matches_live_layer(self):
        spec = get_oxnard_ventura_dataset("sla")
        assert spec.platform == "arcgis"
        assert spec.endpoint == OXNARD_VENTURA_SLA_ENDPOINT
        assert "OpenData_PSI_BusinessLicenses/FeatureServer/0" in spec.endpoint
        assert spec.watermark_col == "DATEISSUE"
        assert spec.id_keys == ["ACCTNO", "GlobalID", "OBJECTID"]
        assert spec.producer_key == "sla"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Ventura, CA"
        assert spec.ingestion_mode == "snapshot"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 16000
        assert spec.order_by == "DATEISSUE DESC"
        assert spec.field_map == SLA_FIELD_MAP
        # Local vendor grid, not a declared state-plane zone.
        assert spec.state_plane_crs is None
        assert spec.state_plane_x_col is None
        assert spec.state_plane_y_col is None

    def test_311_spec_matches_live_layer(self):
        spec = get_oxnard_ventura_dataset("311")
        assert spec.platform == "arcgis"
        assert spec.endpoint == OXNARD_VENTURA_311_ENDPOINT
        assert "Graffiti_Responses_Read_Only/FeatureServer/0" in spec.endpoint
        assert spec.watermark_col == "ReportedOn"
        assert spec.id_keys == ["globalid", "objectid"]
        assert spec.producer_key == "311"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is False
        assert spec.oid_field == "objectid"
        assert spec.max_record_count == 10000
        assert spec.order_by == "ReportedOn DESC"
        assert spec.field_map == COMPLAINTS_311_FIELD_MAP

    def test_crime_spec_matches_live_layer(self):
        spec = get_oxnard_ventura_dataset("crime")
        assert spec.platform == "arcgis"
        assert spec.endpoint == OXNARD_VENTURA_CRIME_ENDPOINT
        assert "OpenData_Police_Crimes/FeatureServer/0" in spec.endpoint
        assert spec.watermark_col == "Incident_Date_Start"
        assert spec.id_keys == ["EventOffenseKey", "Report_Number", "ObjectID"]
        assert spec.producer_key == "crime"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is False
        assert spec.oid_field == "ObjectID"
        assert spec.max_record_count == 2000
        assert spec.order_by == "Incident_Date_Start DESC"
        assert spec.field_map == CRIME_FIELD_MAP

    @pytest.mark.parametrize("absent_feed", ["permits", "deeds", "evictions", "street_cut"])
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'oxnard_ventura'.*available"):
            get_oxnard_ventura_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert FIELD_MAP["311"] is COMPLAINTS_311_FIELD_MAP
        assert FIELD_MAP["crime"] is CRIME_FIELD_MAP
        assert GEOCODE_CONTEXT == OXNARD_VENTURA_GEOCODE_CONTEXT == "Ventura, CA"
        assert "permits" not in FIELD_MAP
        assert "deeds" not in FIELD_MAP


class TestOxnardVenturaFieldMaps:
    def test_sla_map_reads_live_columns(self):
        row = SLA_ROW_MIDTOWN
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "1148612"
        assert (
            first_mapped(row, SLA_FIELD_MAP, "dba")
            == "ST. JOSEPH, LYDIA @ MAYFAIR OF LONDON"
        )
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "ST. JOSEPH, LYDIA"
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "SERVICES"
        assert first_mapped(row, SLA_FIELD_MAP, "status") == "Licensed"
        assert first_mapped(row, SLA_FIELD_MAP, "effective_date") == (
            "2014-01-06T08:00:00+00:00"
        )
        assert first_mapped(row, SLA_FIELD_MAP, "expiration_date") == (
            "2027-06-30T07:00:00+00:00"
        )
        assert first_mapped(row, SLA_FIELD_MAP, "address_street") == "2043 E MAIN ST"

    def test_sla_map_never_maps_local_grid_or_coordinates(self):
        """BADDRX/BADDRY are the PSI vendor grid (in-city ≈ 22589–24716 /
        19570–20086) — never degrees, never a state-plane zone. The SLA
        parser has no out-of-range guard, so mapping them would emit grid
        units as degrees."""
        mapped = {c for cols in SLA_FIELD_MAP.values() for c in cols}
        assert "BADDRX" not in mapped
        assert "BADDRY" not in mapped
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP
        # The live layer column is BADDRY (not BADDY); the drop list pins it.
        assert "BADDRX" in DROPPED_NONADDRESS_COLUMNS
        assert "BADDRY" in DROPPED_NONADDRESS_COLUMNS
        assert "BADDY" not in DROPPED_NONADDRESS_COLUMNS

    def test_311_map_reads_live_columns(self):
        row = GRAFFITI_ROW
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_id") == (
            "5d859047-ba5e-4ddb-83d2-c55cee6dfb4c"
        )
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "created_date") == (
            "2026-08-28T19:00:00+00:00"
        )
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "closed_date") == (
            "2026-08-28T14:50:48.068000+00:00"
        )

    def test_311_map_has_no_complaint_type_or_address_candidates(self):
        # Graffiti-only layer: no request-type column (classifies honestly as
        # Unknown) and no address column (null-geometry rows drop).
        assert "complaint_type" not in COMPLAINTS_311_FIELD_MAP
        assert "borough" not in COMPLAINTS_311_FIELD_MAP
        assert "incident_address" not in COMPLAINTS_311_FIELD_MAP
        assert "zipcode" not in COMPLAINTS_311_FIELD_MAP
        assert "latitude" not in COMPLAINTS_311_FIELD_MAP
        assert "longitude" not in COMPLAINTS_311_FIELD_MAP

    def test_crime_map_reads_live_columns(self):
        row = CRIME_ROW
        assert first_mapped(row, CRIME_FIELD_MAP, "incident_id") == "VE202653540-01"
        assert first_mapped(row, CRIME_FIELD_MAP, "offense_type") == "Motor Vehicle Theft"
        assert first_mapped(row, CRIME_FIELD_MAP, "occurred_date") == (
            "2026-08-26T22:31:00+00:00"
        )
        assert first_mapped(row, CRIME_FIELD_MAP, "borough") == (
            "District 6 Community Council"
        )

    def test_crime_map_never_maps_generalized_address_for_geocode(self):
        mapped = {c for cols in CRIME_FIELD_MAP.values() for c in cols}
        assert "GeneralizedAddress" not in mapped
        assert "latitude" not in CRIME_FIELD_MAP
        assert "longitude" not in CRIME_FIELD_MAP

    def test_dropped_pii_and_nonaddress_columns_are_never_candidates(self):
        mapped_311 = {c for cols in COMPLAINTS_311_FIELD_MAP.values() for c in cols}
        for col in DROPPED_PII_COLUMNS:
            assert col not in mapped_311, col
        assert "Username" in DROPPED_PII_COLUMNS
        assert "Monikers" in DROPPED_PII_COLUMNS

        mapped_sla = {c for cols in SLA_FIELD_MAP.values() for c in cols}
        for col in DROPPED_NONADDRESS_COLUMNS:
            assert col not in mapped_sla, col


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


@pytest.fixture
def complaints():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        return Complaints311Producer()


@pytest.fixture
def crime():
    with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
        from src.producers.crime_incidents_producer import CrimeIncidentsProducer

        return CrimeIncidentsProducer()


class TestOxnardVenturaSlaParsing:
    def test_midtown_row_parses_geometry_without_geocoder(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *a, **k: (0.0, 0.0),
        )
        event = sla.parse_socrata_row(SLA_ROW_MIDTOWN, city_id="oxnard_ventura")
        assert event is not None
        assert event.city_id == "oxnard_ventura"
        assert event.license_id == "1148612"
        assert event.dba == "ST. JOSEPH, LYDIA @ MAYFAIR OF LONDON"
        assert event.premises_name == "ST. JOSEPH, LYDIA"
        assert event.license_type == "SERVICES"
        assert event.address == "2043 E MAIN ST"
        assert event.license_status == "Licensed"
        assert event.latitude == pytest.approx(34.2780692942269)
        assert event.longitude == pytest.approx(-119.26970431616101)
        assert is_in_oxnard_ventura_metro(event.latitude, event.longitude)
        assert event.h3_res7 is not None
        assert event.effective_date.year == 2014
        assert event.expiration_date.year == 2027

    def test_out_of_city_row_still_flows_as_honest_grain(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(SLA_ROW_OUT_OF_CITY, city_id="oxnard_ventura")
        assert event is not None
        assert event.license_id == "331053"
        assert event.license_type == "CONTRACTORS"
        assert event.dba == "OUTFRONT MEDIA LLC"
        # Out-of-city contractor row: coordinates exist but sit outside the
        # Ventura metro bbox — documented, not hidden.
        assert is_in_oxnard_ventura_metro(event.latitude, event.longitude) is False
        assert event.h3_res7 is not None

    def test_local_grid_never_becomes_coordinates(self, sla, monkeypatch):
        """Null-geometry SLA row: the vendor grid BADDRX/BADDRY must never
        be read as degrees. Under an unregistered (spine-pending) city the
        geocode path returns None, so the row emits null-coordinate events —
        grid units are never emitted."""
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared", lambda *a, **k: None
        )
        row = {k: v for k, v in SLA_ROW_MIDTOWN.items() if k not in {"latitude", "longitude"}}
        event = sla.parse_socrata_row(row, city_id="oxnard_ventura")
        assert event is not None
        assert event.license_id == "1148612"
        assert event.latitude is None
        assert event.longitude is None
        assert event.latitude != SLA_ROW_MIDTOWN["BADDRX"]
        assert event.longitude != SLA_ROW_MIDTOWN["BADDRY"]
        assert event.h3_res7 is None


class TestOxnardVentura311Parsing:
    def test_graffiti_row_parses_geometry_without_geocoder(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(GRAFFITI_ROW, city_id="oxnard_ventura")
        assert event is not None
        assert event.city_id == "oxnard_ventura"
        assert event.incident_id == "5d859047-ba5e-4ddb-83d2-c55cee6dfb4c"
        assert event.complaint_type == "Unknown"
        assert event.category.value == "OTHER"
        assert event.zipcode == ""
        assert event.incident_address is None
        assert event.latitude == pytest.approx(34.278392619485295)
        assert event.longitude == pytest.approx(-119.30283324804091)
        assert is_in_oxnard_ventura_metro(event.latitude, event.longitude)
        assert event.h3_res7 is not None
        assert (event.created_date.year, event.created_date.month, event.created_date.day) == (
            2026,
            8,
            28,
        )
        assert (event.closed_date.year, event.closed_date.month, event.closed_date.day) == (
            2026,
            8,
            28,
        )

    def test_null_geometry_row_drops_not_geocoded(self, complaints, monkeypatch):
        """needs_geocode stays False: no address column means a geocoder has
        nothing to geocode, so null-geometry rows drop."""
        _patch_resolve(monkeypatch, "311")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared", lambda *a, **k: None
        )
        row = {k: v for k, v in GRAFFITI_ROW.items() if k not in {"latitude", "longitude"}}
        event = complaints.parse_socrata_row(row, city_id="oxnard_ventura")
        assert event is None

    def test_staff_pii_never_surfaces(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(GRAFFITI_ROW, city_id="oxnard_ventura")
        assert event is not None
        assert event.complaint_type == "Unknown"
        assert event.incident_address is None
        assert "jivanovich" not in (event.incident_address or "")
        assert "Sker" not in (event.complaint_type or "")


class TestOxnardVenturaCrimeParsing:
    def test_crime_row_parses_geometry_without_geocoder(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(CRIME_ROW, city_id="oxnard_ventura")
        assert event is not None
        assert event.city_id == "oxnard_ventura"
        assert event.incident_id == "VE202653540-01"
        assert event.offense_type == "Motor Vehicle Theft"
        assert event.offense_class == "PART1"
        assert event.source_neighborhood == "District 6 Community Council"
        assert event.latitude == pytest.approx(34.25774061785711)
        assert event.longitude == pytest.approx(-119.23946100017902)
        assert is_in_oxnard_ventura_metro(event.latitude, event.longitude)
        assert event.h3_res7 is not None
        assert (event.occurred_date.year, event.occurred_date.month, event.occurred_date.day) == (
            2026,
            8,
            26,
        )

    def test_crime_address_stays_none_generalized_address_not_declared(self, crime, monkeypatch):
        """GeneralizedAddress is block-level and NOT geocode-declared; the
        producer does not surface it as an address (it is not a locator)."""
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(CRIME_ROW, city_id="oxnard_ventura")
        assert event is not None
        assert event.address is None
        assert event.latitude == pytest.approx(34.25774061785711)

    def test_crime_h3_hierarchy_is_consistent(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(CRIME_ROW, city_id="oxnard_ventura")
        assert event is not None
        assert h3.cell_to_parent(event.h3_res9, 8) == event.h3_res8
        assert h3.cell_to_parent(event.h3_res9, 7) == event.h3_res7


class TestGeocodingCaveats:
    def test_sla_street_has_no_state_token_so_context_appends(self):
        # needs_geocode is True for the SLA feed; ADR-0004 parity with
        # sibling leaves — the raw street carries no state token, so a
        # registered geocode would append the "Ventura, CA" context.
        assert _STATE_RE.search("2043 E MAIN ST".upper()) is None
