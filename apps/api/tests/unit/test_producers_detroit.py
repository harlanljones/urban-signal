"""Unit tests for the Detroit registration and its producer wiring.

Detroit is the first all-ArcGIS city: all four feeds register with
``platform="arcgis"`` through the existing ArcGISClient (same client Seattle's
King County deeds already uses). Live-probed 2026-08-23 against
services2.arcgis.com/qvkbeam7Wirps6zC:

* PERMITS   bseed_building_permits/FeatureServer/0      (points, 3,779 issued in 2026)
* 311       improve_detroit/FeatureServer/0            (points, flat longitude/latitude attrs)
* SLA       bseed_active_business_licenses/FeatureServer/0
* DEEDS     assessor_property_sales_view/FeatureServer/0 (534k+ points, grantor/grantee/price)

The business-licenses layer was listed "unverified table" in research but is a
geocoded point layer live — so unlike LA, Detroit registers all four families.

Two pinned quirks:
* Date fields on permits/licenses/sales are esriFieldTypeDateOnly and arrive
  as "YYYY-MM-DD" STRINGS — ArcGISClient's epoch-ms conversion is a no-op.
* The OID field is ``ObjectId`` (camelCase), not OBJECTID.

Registration tests are expected RED until the orchestrator applies the spine
(registry edits are not leaf files). Parser tests run against LIVE fixtures
captured from the FeatureServers on 2026-08-23; assertions that depend on the
pending registry field_map entries are marked xfail(strict=False) with the
exact pending entry named — they flip to passes when the spine lands.
"""

from unittest.mock import patch

import pytest

from src.spatial.cities.detroit import (
    DETROIT_DIVISION_BBOXES,
    DETROIT_DIVISIONS,
    DETROIT_METRO_BBOX,
    DETROIT_SUBMARKETS,
    is_in_detroit_metro,
)
from src.spatial.city_registry import (
    ALIASES,
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
    normalize_city,
)


class TestDetroitRegistration:
    def test_registered(self):
        assert CityId.DETROIT in REGISTRY

    @pytest.mark.parametrize("alias", ["detroit", "detroit_mi", "detroit-mi"])
    def test_aliases_resolve(self, alias):
        assert normalize_city(alias) is CityId.DETROIT

    def test_registration_shape(self):
        reg = REGISTRY[CityId.DETROIT]
        assert reg.state == "MI"
        assert reg.job_suffix == "detroit"
        assert reg.submarkets is DETROIT_SUBMARKETS
        assert reg.divisions is DETROIT_DIVISIONS
        assert len(reg.divisions) == 6

    def test_center_inside_metro_bbox(self):
        reg = REGISTRY[CityId.DETROIT]
        assert is_in_detroit_metro(reg.center["lat"], reg.center["lng"])

    def test_is_in_detroit_metro_rejects_missing_coordinates(self):
        assert is_in_detroit_metro(None, None) is False

    def test_is_in_detroit_metro_rejects_other_cities(self):
        assert is_in_detroit_metro(47.6062, -122.3321) is False   # Seattle
        assert is_in_detroit_metro(29.9511, -90.0715) is False    # New Orleans
        assert is_in_detroit_metro(42.3314 + 1.0, -83.0458) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in DETROIT_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= DETROIT_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= DETROIT_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= DETROIT_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= DETROIT_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in DETROIT_SUBMARKETS.items():
            bbox = DETROIT_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in DETROIT_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(DETROIT_SUBMARKETS)

    def test_submarkets_carry_the_detroit_city_id(self):
        assert {m.city_id for m in DETROIT_SUBMARKETS.values()} == {"detroit"}

    def test_job_names_are_namespaced(self):
        assert get_job_name(FeedType.PERMITS, CityId.DETROIT) == "permits_detroit"


class TestFeedRegistration:
    """Detroit registers all four feeds, every one through platform="arcgis"."""

    def test_all_four_feeds_are_registered(self):
        assert set(REGISTRY[CityId.DETROIT].datasets) == {
            FeedType.PERMITS,
            FeedType.SLA,
            FeedType.COMPLAINTS_311,
            FeedType.DEEDS,
        }

    def test_every_feed_is_arcgis_platform(self):
        for feed, spec in REGISTRY[CityId.DETROIT].datasets.items():
            assert spec.platform == "arcgis", feed

    def test_watermarks_match_published_schemas(self):
        """Pinned against live layer metadata on 2026-08-23. Licenses has NO
        start/issue date at all — expiration_date is its only date column, so
        the watermark is renewal-driven (weak by design). Sales carries a
        '2925' typo-year sentinel (max seen '2925-12-24'); watermark queries
        should clamp to < CURRENT_DATE like NOLA's future-dated licenses."""
        assert get_dataset(CityId.DETROIT, FeedType.PERMITS).watermark_col == "issued_date"
        assert get_dataset(CityId.DETROIT, FeedType.COMPLAINTS_311).watermark_col == "created_at"
        assert get_dataset(CityId.DETROIT, FeedType.SLA).watermark_col == "expiration_date"
        assert get_dataset(CityId.DETROIT, FeedType.DEEDS).watermark_col == "sale_date"

    def test_arcgis_extras_pin_oid_field_and_page_cap(self):
        """Every Detroit layer reports objectIdField='ObjectId' (camelCase —
        NOT King County's OBJECTID) and maxRecordCount=1000 live."""
        for spec in REGISTRY[CityId.DETROIT].datasets.values():
            assert spec.extra["oid_field"] == "ObjectId"
            assert spec.extra["max_record_count"] == 1000

    def test_endpoints_resolve_to_live_layers(self):
        base = "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services"
        expected = {
            FeedType.PERMITS: f"{base}/bseed_building_permits/FeatureServer/0",
            FeedType.COMPLAINTS_311: f"{base}/improve_detroit/FeatureServer/0",
            FeedType.SLA: f"{base}/bseed_active_business_licenses/FeatureServer/0",
            FeedType.DEEDS: f"{base}/assessor_property_sales_view/FeatureServer/0",
        }
        for feed, url in expected.items():
            assert get_dataset(CityId.DETROIT, feed).endpoint == url

    def test_every_alias_target_is_registered(self):
        for alias, cid in ALIASES.items():
            assert cid in REGISTRY, f"alias {alias!r} resolves to unregistered {cid}"


DETROIT_FIELD_MAPS = {
    FeedType.PERMITS: {
        "job_id": ["record_id"],
        "cost": ["amt_permit_cost"],
    },
    FeedType.COMPLAINTS_311: {
        "incident_id": ["issue_id"],
        "closed_date": ["closed_at"],
    },
    FeedType.SLA: {
        "license_id": ["record_id"],
        "license_type": ["license_type", "license_category"],
    },
    FeedType.DEEDS: {
        "doc_id": ["sale_id"],
        "bbl": ["parcel_id"],
        "document_amount": ["amt_sale_price"],
    },
}


class DetroitParsingBase:
    """Fixtures are REAL attribute dicts pulled from each layer via REST
    (`query?f=json&outFields=*&outSR=4326`) on 2026-08-23 — exactly the flat
    dicts ArcGISClient._flatten_feature hands to producers."""

    @pytest.fixture
    def permits(self):

        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            import src.producers.sla_licenses_producer as module

            cls = next(
                getattr(module, n)
                for n in dir(module)
                if n.endswith("Producer") and "Base" not in n
            )
            return cls()

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @pytest.fixture
    def permit_row(self):
        # Live newest-by-issued_date row from bseed_building_permits (2026-08-23).
        return {
            "record_id": "RES2026-02969",
            "address": "1729 Lee Pl",
            "submitted_date": "2026-08-22",
            "issued_date": "2026-08-22",
            "work_description": None,
            "permit_type": "Alteration",
            "construction_type": None,
            "current_use_type": "Two Family",
            "proposed_use_type": None,
            "use_group": None,
            "zoning_designation": None,
            "num_stories": None,
            "num_units": None,
            "amt_permit_cost": 1374.46,
            "amt_estimated_contractor_cost": 38000,
            "amt_estimated_department_cost": None,
            "pmr_id": None,
            "is_open_to_elements": "No",
            "is_missing_portions_of_building": "No",
            "is_purchased_from_dlba": "Yes",
            "is_in_dlba_compliance": "No",
            "has_change_in_units": "No",
            "is_vacant": "Yes",
            "neighborhood": "Virginia Park Community",
            "council_district": "5",
            "zip_code": "48206",
            "street_number": 1729,
            "street_prefix": None,
            "street_name": "Lee",
            "street_type": "Pl",
            "parcel_id": "08002303.",
            "address_id": 59338,
            "longitude": -83.096228367,
            "latitude": 42.372649167,
            "ObjectId": 43090,
        }

    @pytest.fixture
    def complaint_row(self):
        # Live newest-by-created_at row from improve_detroit (2026-08-23).
        # created_at arrives as epoch-ms and is converted to ISO by the
        # client; point geometry was null on this row — coordinates come from
        # the flat longitude/latitude ATTRIBUTES.
        return {
            "issue_id": 22585263,
            "address": "James Couzens Fwy & Schaefer Hwy",
            "request_type": "Traffic Signal Issue",
            "status": "Open",
            "report_method": "direct",
            "priority_code": "2",
            "created_at": "2026-08-20T14:57:16+00:00",
            "acknowledged_at": None,
            "updated_at": "2026-08-20T14:57:18+00:00",
            "closed_at": None,
            "reopened_at": None,
            "num_days_to_close": None,
            "num_hours_to_close": None,
            "issue_url": "https://seeclickfix.com/issues/22585263",
            "neighborhood": None,
            "council_district": None,
            "zip_code": None,
            "street_number": None,
            "street_prefix": None,
            "street_name": None,
            "street_type": None,
            "address_id": None,
            "longitude": -83.180263363,
            "latitude": 42.42524333,
            "ObjectId": 742589,
        }

    @pytest.fixture
    def sla_row(self):
        # Live row from bseed_active_business_licenses (2026-08-23).
        return {
            "record_id": "BUS2023-00202",
            "business_name": "AMC PETRO, INC.",
            "address": "13600 Fenkell St",
            "license_type": "Gas Station License",
            "license_category": "GasStation",
            "expiration_date": "2028-08-31",
            "neighborhood": "Bethune Community",
            "council_district": "7",
            "zip_code": "48227",
            "street_number": 13600,
            "street_prefix": None,
            "street_name": "Fenkell",
            "street_type": "St",
            "parcel_id": "22011494.002L",
            "address_id": 87534,
            "longitude": -83.17962,
            "latitude": 42.402411,
            "ObjectId": 1,
        }

    @pytest.fixture
    def deed_row(self):
        # Live near-newest real sale from assessor_property_sales_view
        # (2026-08-23). Lowercase keys — NOT King County PascalCase — so the
        # KC sniffing branch never fires; production passes city_id="detroit".
        return {
            "sale_id": 4855071,
            "parcel_id": "21046770.",
            "address": "450 ALGONQUIN",
            "sale_date": "2026-03-26",
            "amt_sale_price": 33500,
            "grantor": "CONERSTONE FUND TWO LLC",
            "grantee": "GROVE OWNER 1 LLC",
            "liber_page": "2026038953",
            "term_of_sale": "03-ARM'S LENGTH",
            "sale_verification": None,
            "sale_instrument": "WD",
            "sale_number": 1,
            "pct_property_transferred": 100,
            "is_multi_parcel_sale": "False",
            "property_class_code": "401",
            "property_class_description": "RESIDENTIAL",
            "ecf_neighborhood": "4R421",
            "neighborhood": "Jefferson Chalmers",
            "council_district": "4",
            "zip_code": "48215",
            "street_number": 450,
            "street_prefix": None,
            "street_name": "ALGONQUIN",
            "street_type": None,
            "unit_number": None,
            "longitude": -82.951148751,
            "latitude": 42.361904,
            "ObjectId": 1040050,
        }


class TestDetroitChainsToday(DetroitParsingBase):
    """Bare fallback chains, no registry map (exactly what runs if a row
    arrives before the spine). Every Detroit feed's id column matches NO
    chain term, so the id guard drops the WHOLE ROW — one xfail pin per feed.
    """

    def test_permits_whole_row_survives_the_id_guard(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="detroit")
        assert ev.job_id == "RES2026-02969"

    def test_311_whole_row_survives_the_id_guard(self, complaints, complaint_row):
        ev = complaints.parse_socrata_row(complaint_row, city_id="detroit")
        assert ev.incident_id == "22585263"

    def test_licenses_whole_row_survives_the_id_guard(self, sla, sla_row):
        ev = sla.parse_socrata_row(sla_row, city_id="detroit")
        assert ev.license_id == "BUS2023-00202"

    def test_deeds_whole_row_survives_the_id_guard(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="detroit")
        assert ev.doc_id == "4855071"


class TestDetroitWithProposedFieldMap(DetroitParsingBase):
    """Patches resolve_field_map to hand back the EXACT field_map proposed in
    .streams/city-detroit.md, proving the proposal resolves every Detroit
    spelling before the orchestrator applies it. Plain passes today; once the
    spine registers the same maps these double as their regression net."""

    @pytest.fixture(autouse=True)
    def _proposed_maps(self, monkeypatch):
        import src.producers.field_maps as fm

        monkeypatch.setattr(
            fm,
            "resolve_field_map",
            lambda city_value, feed: DETROIT_FIELD_MAPS.get(feed, {}),
            raising=True,
        )

    # -- PERMITS -------------------------------------------------------------

    def test_permit_dates_are_dateonly_strings_that_parse(
        self, permits, permit_row
    ):
        """PINNED QUIRK: issued/submitted arrive as 'YYYY-MM-DD' STRINGS (the
        client's epoch-ms conversion is a no-op on esriFieldTypeDateOnly) and
        must parse into real datetimes anyway."""
        ev = permits.parse_socrata_row(permit_row, city_id="detroit")
        assert str(ev.issuance_date).startswith("2026-08-22")
        assert str(ev.filing_date).startswith("2026-08-22")

    def test_permit_reads_direct_coordinates(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="detroit")
        assert ev.latitude == pytest.approx(42.372649167)
        assert ev.longitude == pytest.approx(-83.096228367)

    def test_permit_ids_and_cost_come_from_the_proposed_map(
        self, permits, permit_row
    ):
        ev = permits.parse_socrata_row(permit_row, city_id="detroit")
        assert ev.job_id == "RES2026-02969"
        assert ev.estimated_cost == 1374.46

    def test_permit_classification_zipcode_and_neighborhood(
        self, permits, permit_row
    ):
        ev = permits.parse_socrata_row(permit_row, city_id="detroit")
        assert ev.job_type is not None
        assert ev.zipcode == "48206"
        assert ev.source_neighborhood == "Virginia Park Community"

    def test_permit_resolves_to_a_division_by_coordinate(
        self, permits, permit_row
    ):
        ev = permits.parse_socrata_row(permit_row, city_id="detroit")
        assert ev.borough == "NORTH_END_HIGHLAND_PARK"

    # -- 311 ------------------------------------------------------------------

    def test_311_reads_flat_attribute_coordinates_without_geometry(
        self, complaints, complaint_row
    ):
        """ANSWER PIN: Improve Detroit geocodes via flat longitude/latitude
        ATTRIBUTES even when its point geometry comes back null — no
        dotted-path field_map entries needed and no client change required."""
        ev = complaints.parse_socrata_row(complaint_row, city_id="detroit")
        assert ev.latitude == pytest.approx(42.42524333)
        assert ev.longitude == pytest.approx(-83.180263363)

    def test_311_complaint_type_created_date_status_through_chains(
        self, complaints, complaint_row
    ):
        ev = complaints.parse_socrata_row(complaint_row, city_id="detroit")
        assert ev.complaint_type == "Traffic Signal Issue"
        assert str(ev.created_date).startswith("2026-08-20")
        assert ev.status == "Open"

    def test_311_ids_and_closed_date_come_from_the_proposed_map(
        self, complaints, complaint_row
    ):
        complaint_row["closed_at"] = "2026-08-21T09:12:00+00:00"
        ev = complaints.parse_socrata_row(complaint_row, city_id="detroit")
        assert ev.incident_id == "22585263"
        assert str(ev.closed_date).startswith("2026-08-21")

    def test_311_rejects_null_island_placeholder(self, complaints, complaint_row):
        complaint_row["latitude"] = 0.0
        complaint_row["longitude"] = 0.0
        assert complaints.parse_socrata_row(complaint_row, city_id="detroit") is None

    # -- LICENSES ---------------------------------------------------------------

    def test_license_layer_is_geocoded_so_sla_stays_in_scope(self, sla_row):
        """VERDICT PIN: research flagged this layer 'table / geocoding
        unverified'; live it is an esriGeometryPoint layer with populated
        longitude/latitude — so it stays IN registration scope (no LA-style
        partial-city exclusion)."""
        assert is_in_detroit_metro(sla_row["latitude"], sla_row["longitude"])

    def test_license_dba_type_and_expiration_read_through_chains(
        self, sla, sla_row
    ):
        ev = sla.parse_socrata_row(sla_row, city_id="detroit")
        assert ev.dba == "AMC PETRO, INC."
        assert ev.license_type == "Gas Station License"
        assert str(ev.expiration_date).startswith("2028-08-31")

    def test_license_effective_date_is_none_by_design(self, sla, sla_row):
        """The feed carries ONLY expiration_date (DateOnly) — no start/issue
        column exists anywhere, so effective_date parses None while
        expiration lands. The renewal-driven watermark tradeoff."""
        ev = sla.parse_socrata_row(sla_row, city_id="detroit")
        assert ev.effective_date is None
        assert ev.expiration_date is not None

    def test_license_ids_from_the_proposed_map(self, sla, sla_row):
        ev = sla.parse_socrata_row(sla_row, city_id="detroit")
        assert ev.license_id == "BUS2023-00202"

    # -- DEEDS -------------------------------------------------------------------

    def test_deed_full_h3_events_from_direct_coordinates(self, deeds, deed_row):
        """Unlike King County's polygon parcels, Detroit sales carry flat
        longitude/latitude attrs, so every row yields full H3 events."""
        ev = deeds.parse_socrata_row(deed_row, city_id="detroit")
        assert ev.latitude == pytest.approx(42.361904)
        assert ev.longitude == pytest.approx(-82.951148751)
        assert ev.h3_res7 is not None
        assert ev.h3_res8 is not None
        assert ev.h3_res9 is not None

    def test_deed_parties_read_lowercase_keys_not_kc_pascalcases(
        self, deeds, deed_row
    ):
        """Detroit attrs are lowercase (grantor/grantee), not KC's
        Sellername/Buyername PascalCase — party chains match directly, no
        map entry needed."""
        ev = deeds.parse_socrata_row(deed_row, city_id="detroit")
        assert ev.party1_grantor == "CONERSTONE FUND TWO LLC"
        assert ev.party2_grantee == "GROVE OWNER 1 LLC"

    def test_deed_recorded_date_is_a_dateonly_string_that_parses(
        self, deeds, deed_row
    ):
        ev = deeds.parse_socrata_row(deed_row, city_id="detroit")
        assert str(ev.recorded_date).startswith("2026-03-26")

    def test_deed_doc_id_bbl_and_price_come_from_the_proposed_map(
        self, deeds, deed_row
    ):
        ev = deeds.parse_socrata_row(deed_row, city_id="detroit")
        assert ev.doc_id == "4855071"
        assert ev.bbl == "21046770."
        assert ev.document_amount == 33500.0

    def test_deed_sentinel_year_rows_still_parse(self, deeds, deed_row):
        """Live max sale_date includes a '2925-12-24' typo-year sentinel;
        rows must parse (watermark skew tolerated, NOLA future-date
        precedent) rather than crash or be rejected."""
        deed_row["sale_date"] = "2925-12-24"
        ev = deeds.parse_socrata_row(deed_row, city_id="detroit")
        assert str(ev.recorded_date).startswith("2925-12-24")
