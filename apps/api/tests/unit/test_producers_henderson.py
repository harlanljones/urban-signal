"""Unit tests for the Henderson, NV leaf (US-325): spatial module + field maps
+ producer parse wiring.

Henderson is a TWO-FEED PARTIAL metro: DSC_Permits (ArcGIS FeatureServer/0,
Tier 1, native WGS84 GISX/GISY) and Active Business Licenses (CSV snapshot,
Tier 2, address-only → ADR 0004 geocode). 311 and deeds stay absent.

Tests pass WITHOUT a spine registration (no CityId.HENDERSON, no REGISTRY
assertions — "henderson" stays a plain string).

Live fixtures captured 2026-08-28 from services2.arcgis.com (DSC_Permits)
and the ArcGIS Hub Active Business Licenses CSV item 2b3fac57….
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_henderson import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.spatial.cities.henderson import (
    HENDERSON_CITY_ID,
    HENDERSON_DIVISION_BBOXES,
    HENDERSON_DIVISIONS,
    HENDERSON_FEED_SPECS,
    HENDERSON_GEOCODE_CONTEXT,
    HENDERSON_METRO_BBOX,
    HENDERSON_PERMITS_ENDPOINT,
    HENDERSON_SLA_ENDPOINT,
    HENDERSON_SUBMARKETS,
    REGISTRATION,
    compose_permit_address,
    get_henderson_dataset,
    is_in_henderson_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


# Newest permit by IssueDate on the 2026-08-28 re-probe (ObjectId 11127):
# a Fire Activity permit with NO GISX/GISY — the address-fallback path.
# Dates arrive epoch-ms and are ISO-normalized by ArcGISClient._flatten_feature.
_PERMITS_NO_GEO_FIXTURE = {
    "ApplyDate": "2026-08-04T18:08:00+00:00",
    "IssueDate": "2026-08-28T18:08:00+00:00",
    "PermitNumber": "FACT2026397633",
    "PermitType": "Fire - Activity",
    "WorkClass": "Activity",
    "PermitStatus": "Active - Issued",
    "Category": "Fire",
    "ValuationTotal": 0,
    "ParcelAddressNumber": "12300",
    "ParcelAddressPreDirection": "S",
    "ParcelAddressStreet": "LAS VEGAS",
    "ParcelAddressStreetType": "BLVD",
    "ParcelAddressCity": "HENDERSON",
    "ParcelAddressState": "NV",
    "ParcelAddressZip": None,
    "GISX": None,
    "GISY": None,
    "ObjectId": 11127,
}

# Newest coordinate-bearing permit (ObjectId 15810, IssueDate 2026-08-20):
# grading permit with native WGS84 GISX/GISY.
_PERMITS_GEO_FIXTURE = {
    "ApplyDate": "2026-06-30T19:06:00+00:00",
    "IssueDate": "2026-08-20T15:08:00+00:00",
    "PermitNumber": "BSGR2026393601",
    "PermitType": "BLDG - Grading",
    "WorkClass": "Grading",
    "PermitStatus": "Active - Issued",
    "Category": "Building & Fire Safety > Grading",
    "ValuationTotal": 2090.6,
    "ParcelAddressNumber": "405",
    "ParcelAddressPreDirection": None,
    "ParcelAddressStreet": "DRAKE",
    "ParcelAddressStreetType": "ST",
    "ParcelAddressCity": "HENDERSON",
    "ParcelAddressState": "NV",
    "ParcelAddressZip": None,
    "GISX": -114.9619305,
    "GISY": 36.04215361,
    "ObjectId": 15810,
}

# Second coordinate-bearing permit (ObjectId 8457, HVAC appliance replacement
# in Green Valley) — pins the 7d-window shape of the live feed.
_PERMITS_HVAC_FIXTURE = {
    "ApplyDate": "2026-08-20T15:08:00+00:00",
    "IssueDate": "2026-08-20T07:08:00+00:00",
    "PermitNumber": "BOTH2026399545",
    "PermitType": "BLDG - Appliance Replacement",
    "WorkClass": "HVAC",
    "PermitStatus": "Active - Issued",
    "Category": "Building & Fire Safety > Miscellaneous",
    "ValuationTotal": 0,
    "ParcelAddressNumber": "972",
    "ParcelAddressPreDirection": None,
    "ParcelAddressStreet": "TWILIGHT PEAK",
    "ParcelAddressStreetType": "AVE",
    "ParcelAddressCity": "HENDERSON",
    "ParcelAddressState": "NV",
    "ParcelAddressZip": None,
    "GISX": -115.0289885,
    "GISY": 36.02159836,
    "ObjectId": 8457,
}

# Two co-newest Active Business Licenses rows (Original Issue Date
# 2026-08-21, the live watermark on the 2026-08-28 re-probe).
_SLA_FIXTURE_COTTAGE = {
    "License Number": "2026336192",
    "Entity Name": "Paige Wright",
    "DBA": "Mommas 4 Little Jars",
    "Business Location": "296 Davis Hill Ct",
    "City": "Henderson",
    "State": "Nevada",
    "Zip Code": "89074",
    "Original Issue Date": "08/21/2026",
    "Expiration Date": "02/28/2027",
    "License Type": "Gross Revenue",
    "License Sub-Type": "Cottage Food Operation",
}

_SLA_FIXTURE_MEDICAL = {
    "License Number": "2026336258",
    "Entity Name": "DermaCore Wound Care. Professional Corporation",
    "DBA": "DermaCore Wound Care. Professional Corporation",
    "Business Location": "871 Coronado Center Dr",
    "City": "Henderson",
    "State": "Nevada",
    "Zip Code": "89052",
    "Original Issue Date": "08/21/2026",
    "Expiration Date": "02/28/2027",
    "License Type": "Medical Office",
    "License Sub-Type": "Medical Office",
}


class TestHendersonSpatial:
    def test_metro_bbox_sanity(self):
        assert HENDERSON_METRO_BBOX["min_lat"] < HENDERSON_METRO_BBOX["max_lat"]
        assert HENDERSON_METRO_BBOX["min_lng"] < HENDERSON_METRO_BBOX["max_lng"]

    def test_is_in_henderson_metro_rejects_missing_coordinates(self):
        assert is_in_henderson_metro(None, None) is False

    def test_is_in_henderson_metro_rejects_other_cities(self):
        assert is_in_henderson_metro(47.6062, -122.3321) is False   # Seattle
        assert is_in_henderson_metro(36.1699, -115.1398) is False  # Las Vegas strip core
        assert is_in_henderson_metro(36.1070, -115.1490) is False  # Summerlin, far west/north

    def test_live_fixture_coordinates_are_contained(self):
        assert is_in_henderson_metro(36.04215361, -114.9619305)
        assert is_in_henderson_metro(36.02159836, -115.0289885)
        assert is_in_henderson_metro(35.93279305, -115.086573)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in HENDERSON_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= HENDERSON_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= HENDERSON_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= HENDERSON_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= HENDERSON_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in HENDERSON_SUBMARKETS.items():
            bbox = HENDERSON_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in HENDERSON_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(HENDERSON_SUBMARKETS)

    def test_submarkets_carry_the_henderson_city_id(self):
        assert {m.city_id for m in HENDERSON_SUBMARKETS.values()} == {"henderson"}

    def test_city_id_and_registration_shape(self):
        assert HENDERSON_CITY_ID == "henderson"
        assert REGISTRATION.metro_bbox is HENDERSON_METRO_BBOX
        assert REGISTRATION.submarkets is HENDERSON_SUBMARKETS
        assert len(REGISTRATION.divisions) == 6
        assert len(HENDERSON_SUBMARKETS) == 8

    def test_required_real_neighborhoods_present(self):
        assert set(HENDERSON_SUBMARKETS) == {
            "Water Street District",
            "Green Valley",
            "Green Valley Ranch",
            "Anthem",
            "Seven Hills",
            "MacDonald Ranch",
            "Lake Las Vegas",
            "Innovation District",
        }


class TestHendersonFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["PermitNumber", "ObjectId"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["IssueDate"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["ApplyDate"]
        assert PERMITS_FIELD_MAP["cost"] == ["ValuationTotal"]

    def test_permits_gisy_is_latitude_and_gisx_is_longitude(self):
        row = {"GISX": -114.9619305, "GISY": 36.04215361}
        assert first_mapped(row, PERMITS_FIELD_MAP, "latitude") == 36.04215361
        assert first_mapped(row, PERMITS_FIELD_MAP, "longitude") == -114.9619305

    def test_permits_coordinates_are_wgs84_degrees_not_state_plane(self):
        """GISX/GISY verified live as geographic degrees (lng ≈ -115.09…
        -114.91, lat ≈ 35.93…36.09) — never feet, never Web Mercator meters.
        The producer's projected-coordinate guard must never trigger."""
        for row in (_PERMITS_GEO_FIXTURE, _PERMITS_HVAC_FIXTURE):
            lat = first_mapped(row, PERMITS_FIELD_MAP, "latitude")
            lng = first_mapped(row, PERMITS_FIELD_MAP, "longitude")
            assert abs(float(lat)) <= 90 and abs(float(lng)) <= 180
            assert 35.90 <= lat <= 36.10 and -115.15 <= lng <= -114.82

    def test_sla_map_reads_csv_headers(self):
        row = {"License Number": "2026336192", "DBA": "Mommas 4 Little Jars"}
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "2026336192"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "Mommas 4 Little Jars"
        assert first_mapped(_SLA_FIXTURE_COTTAGE, SLA_FIELD_MAP, "effective_date") == "08/21/2026"
        assert first_mapped(_SLA_FIXTURE_COTTAGE, SLA_FIELD_MAP, "address_street") == "296 Davis Hill Ct"

    def test_sla_map_declares_no_native_coordinates(self):
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP

    def test_geocode_context_is_henderson_nv(self):
        assert GEOCODE_CONTEXT == "Henderson, NV"
        assert HENDERSON_GEOCODE_CONTEXT == "Henderson, NV"

    def test_pii_columns_never_become_candidates(self):
        mapped = set(PERMITS_FIELD_MAP) | set(SLA_FIELD_MAP)
        for values in [*PERMITS_FIELD_MAP.values(), *SLA_FIELD_MAP.values()]:
            for col in values:
                assert col not in DROPPED_PII_COLUMNS
        assert mapped  # sanity: maps are non-empty


class TestComposePermitAddress:
    def test_composes_full_address_with_zip(self):
        row = {**_PERMITS_NO_GEO_FIXTURE, "ParcelAddressZip": "89044"}
        assert compose_permit_address(row) == "12300 S LAS VEGAS BLVD, Henderson, NV 89044"

    def test_composes_without_zip(self):
        assert compose_permit_address(_PERMITS_NO_GEO_FIXTURE) == "12300 S LAS VEGAS BLVD, Henderson, NV"

    def test_skips_missing_parts(self):
        row = {
            "ParcelAddressNumber": "405",
            "ParcelAddressPreDirection": None,
            "ParcelAddressStreet": "DRAKE",
            "ParcelAddressStreetType": "ST",
        }
        assert compose_permit_address(row) == "405 DRAKE ST, Henderson, NV"

    def test_returns_none_without_street_parts(self):
        assert compose_permit_address(_PERMITS_GEO_FIXTURE | {
            "ParcelAddressNumber": None,
            "ParcelAddressStreet": None,
            "ParcelAddressStreetType": None,
            "ParcelAddressPreDirection": None,
        }) is None


class TestHendersonPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_geocoded_row_parses_with_native_gis_coords(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            return_value=(0.0, 0.0),
        ) as geocode:
            event = permits.parse_socrata_row(_PERMITS_GEO_FIXTURE, city_id="henderson")
        assert event is not None
        assert event.city_id == "henderson"
        assert event.job_id == "BSGR2026393601"
        assert event.latitude == pytest.approx(36.04215361)
        assert event.longitude == pytest.approx(-114.9619305)
        geocode.assert_not_called()

    def test_geocoded_row_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_PERMITS_GEO_FIXTURE, city_id="henderson")
        assert event is not None
        assert event.h3_res7 is not None
        assert event.h3_res9 is not None
        assert is_in_henderson_metro(event.latitude, event.longitude)

    def test_second_geocoded_fixture_is_contained(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_PERMITS_HVAC_FIXTURE, city_id="henderson")
        assert event is not None
        assert event.latitude == pytest.approx(36.02159836)
        assert event.longitude == pytest.approx(-115.0289885)
        assert is_in_henderson_metro(event.latitude, event.longitude)

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        row = {**_PERMITS_GEO_FIXTURE, "PermitNumber": None}
        event = permits.parse_socrata_row(row, city_id="henderson")
        assert event is not None
        assert event.job_id == "15810"

    def test_issuance_and_filing_dates_map(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_PERMITS_GEO_FIXTURE, city_id="henderson")
        assert event is not None
        assert str(event.issuance_date).startswith("2026-08-20")
        assert str(event.filing_date).startswith("2026-06-30")

    def test_valuation_total_carries_cost(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_PERMITS_GEO_FIXTURE, city_id="henderson")
        assert event is not None
        assert event.estimated_cost == pytest.approx(2090.6)

    def test_coordinate_less_row_geocode_fallback_passes_first_mapped_part(self, permits, monkeypatch):
        """The ~11.8% GISX/GISY-null rows resolve through the ADR 0004
        geocode supplement. Without the spine, the hook receives the first
        mapped part (the street number) — the SPINE FALLBACK NOTE is to wire
        ``compose_permit_address`` into dob_permits_producer alongside
        albuquerque's branch so the hook receives the composed street
        (pinned by TestComposePermitAddress)."""
        _patch_resolve(monkeypatch, "permits")
        row = dict(_PERMITS_NO_GEO_FIXTURE)
        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return (35.9869, -115.1470)  # M Resort corridor geocode

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = permits.parse_socrata_row(row, city_id="henderson")
        assert event is not None
        assert event.latitude == pytest.approx(35.9869)
        assert event.longitude == pytest.approx(-115.1470)
        assert event.h3_res7 is not None
        assert captured == [("henderson", "permits", "12300", None)]

    def test_geocode_failure_drops_coordinate_less_rows(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        row = {
            k: v
            for k, v in _PERMITS_NO_GEO_FIXTURE.items()
            if k not in {"GISX", "GISY"}
        }
        assert permits.parse_socrata_row(row, city_id="henderson") is None

    def test_permit_spec_matches_live_layer(self):
        spec = get_henderson_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == HENDERSON_PERMITS_ENDPOINT
        assert spec.watermark_col == "IssueDate"
        assert spec.id_keys == ["PermitNumber", "ObjectId"]
        assert spec.oid_field == "ObjectId"
        assert spec.max_record_count == 1000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "IssueDate DESC"
        assert spec.needs_geocode is True  # supplement for the ~11.8% nulls
        assert spec.geocode_context == "Henderson, NV"


class TestHendersonSlaParsing:
    """The Active Business Licenses CSV is address-only: rows resolve
    coordinates at parse time via the ADR 0004 hook; context composition
    ("{street}, Henderson, NV") happens inside geocode_row_if_declared from
    the registered spec's geocode_context."""

    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_license_row_geocodes_at_parse(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        captured = []

        def fake_resolve(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return (36.0126, -115.0296)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_resolve)
        event = sla.parse_socrata_row(_SLA_FIXTURE_COTTAGE, city_id="henderson")
        assert event is not None
        assert event.city_id == "henderson"
        assert event.license_id == "2026336192"
        assert event.dba == "Mommas 4 Little Jars"
        assert event.premises_name == "Paige Wright"
        assert event.license_type == "Gross Revenue"
        assert event.address == "296 Davis Hill Ct"
        # The hook receives the raw street line; the "Henderson, NV" suffix
        # is appended inside the geocoder from the spec context.
        assert captured == [("henderson", "sla", "296 Davis Hill Ct", None)]

    def test_geocoded_row_indexes_h3_and_sits_in_metro(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (36.0126, -115.0296),
        )
        event = sla.parse_socrata_row(_SLA_FIXTURE_COTTAGE, city_id="henderson")
        assert event is not None
        assert event.latitude == pytest.approx(36.0126)
        assert event.longitude == pytest.approx(-115.0296)
        assert event.h3_res7 is not None
        assert event.h3_res9 is not None
        assert is_in_henderson_metro(event.latitude, event.longitude)

    def test_second_license_fixture_maps_all_fields(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (36.0231, -115.0085),
        )
        event = sla.parse_socrata_row(_SLA_FIXTURE_MEDICAL, city_id="henderson")
        assert event is not None
        assert event.license_id == "2026336258"
        assert event.license_type == "Medical Office"
        assert event.address == "871 Coronado Center Dr"
        assert event.effective_date is not None and event.effective_date.year == 2026
        assert event.effective_date.month == 8 and event.effective_date.day == 21
        assert event.expiration_date is not None and event.expiration_date.year == 2027
        assert is_in_henderson_metro(event.latitude, event.longitude)

    def test_geocode_failure_keeps_null_coord_event(self, sla, monkeypatch):
        """Coordinate-less SLA rows that fail geocoding stay as null-lat/lng
        /null-H3 events (DC-precedent tolerance), unlike the permits feed."""
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(_SLA_FIXTURE_COTTAGE, city_id="henderson")
        assert event is not None
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None
        assert event.address == "296 Davis Hill Ct"

    def test_sla_spec_matches_published_csv(self):
        spec = get_henderson_dataset(FeedType.SLA)
        assert spec.platform == "csv"
        assert spec.endpoint == HENDERSON_SLA_ENDPOINT
        assert spec.watermark_col == "Original Issue Date"
        assert spec.watermark_type == "text"
        assert spec.watermark_format == "%m/%d/%Y"
        assert spec.id_keys == ["License Number"]
        assert spec.producer_key == "sla"
        assert spec.ingestion_mode == "snapshot"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Henderson, NV"
        assert spec.field_map["license_id"] == ["License Number"]
        assert spec.field_map["address_street"] == ["Business Location"]
        mjbl = spec.companion_endpoints["mjbl"]
        assert "6c470a95e83e4051a4d1222afa056ed6" in mjbl["endpoint"]
        assert mjbl["filter"] == "Jurisdiction='HENDERSON'"

    def test_sla_context_composes_geocode_query(self):
        """The composed geocode query for an SLA row is
        '{Business Location}, Henderson, NV' — pinned here so the spine's
        REGISTRY copy carries the same geocode_context."""
        from src.spatial.geocoder import _STATE_RE

        spec = get_henderson_dataset(FeedType.SLA)

        def compose(query: str) -> str:
            suffix = spec.geocode_context
            if suffix and suffix.upper() not in query.upper() and not _STATE_RE.search(query.upper()):
                query = f"{query}, {suffix}"
            return query

        assert compose("871 Coronado Center Dr") == "871 Coronado Center Dr, Henderson, NV"

    def test_sla_court_suffix_trips_the_state_detector(self):
        """Live quirk pinned: _STATE_RE matches two-letter codes with word
        boundaries, and 'Ct' (Court) IS a state code — so Court-suffixed
        streets skip the 'Henderson, NV' suffix and geocode on the bare
        street line. Documented here so a future geocoder fix is deliberate;
        the spec's geocode_context itself is unchanged."""
        from src.spatial.geocoder import _STATE_RE

        assert _STATE_RE.search("296 DAVIS HILL CT") is not None
        assert _STATE_RE.search("871 CORONADO CENTER DR") is None


class TestLeafFeedSpecContract:
    def test_registered_feed_set(self):
        assert set(HENDERSON_FEED_SPECS) == {"permits", "sla"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_henderson_dataset("311")
        assert "henderson" in str(exc.value)
        assert "permits" in str(exc.value)

    def test_endpoint_hosts_are_the_probed_ones(self):
        permits = HENDERSON_FEED_SPECS["permits"]
        sla = HENDERSON_FEED_SPECS["sla"]
        assert "services2.arcgis.com/naGsY5NZWVbd6bwD" in permits["endpoint"]
        assert "DSC_Permits/FeatureServer/0" in permits["endpoint"]
        assert "www.arcgis.com/sharing/rest/content/items" in sla["endpoint"]
        assert sla["endpoint"].endswith("2b3fac57210542229afc4bfddd6cd6e8/data")
