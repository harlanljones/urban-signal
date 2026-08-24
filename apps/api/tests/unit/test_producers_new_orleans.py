"""Unit tests for the New Orleans Metro registration and its producer wiring.

New Orleans registers all four feed types. The deeds stand-in is NORA's "Sold
Properties" feed (`hpm5-48nj`) and is heavily caveated by design: it records
redevelopment-authority disposals (Lot Next Door, auctions, development
dispositions), NOT market deeds — it under-counts ordinary transactions and
carries no price column at all, so `document_amount` is always 0.0 (an
accepted loss documented in docs/research/new-orleans-austin-verification.md).

Registration tests are expected RED until the orchestrator applies the spine
(registry/producer edits are not leaf files). Parser tests use LIVE fixture
rows captured from data.nola.gov on 2026-08-23.
"""

from unittest.mock import patch

import pytest

from src.spatial.cities.new_orleans import (
    NOLA_DIVISION_BBOXES,
    NOLA_DIVISIONS,
    NEW_ORLEANS_METRO_BBOX,
    NOLA_SUBMARKETS,
    is_in_new_orleans_metro,
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


class TestNewOrleansRegistration:
    def test_registered(self):
        assert CityId.NEW_ORLEANS in REGISTRY

    @pytest.mark.parametrize("alias", ["new_orleans", "nola", "orleans_parish"])
    def test_aliases_resolve(self, alias):
        assert normalize_city(alias) is CityId.NEW_ORLEANS

    def test_registration_shape(self):
        reg = REGISTRY[CityId.NEW_ORLEANS]
        assert reg.state == "LA"
        assert reg.job_suffix == "nola"
        assert reg.submarkets is NOLA_SUBMARKETS
        assert reg.divisions is NOLA_DIVISIONS
        assert len(reg.divisions) == 9

    def test_center_inside_metro_bbox(self):
        reg = REGISTRY[CityId.NEW_ORLEANS]
        assert is_in_new_orleans_metro(reg.center["lat"], reg.center["lng"])

    def test_is_in_new_orleans_metro_rejects_missing_coordinates(self):
        assert is_in_new_orleans_metro(None, None) is False

    def test_is_in_new_orleans_metro_rejects_other_cities(self):
        assert is_in_new_orleans_metro(47.6062, -122.3321) is False   # Seattle
        assert is_in_new_orleans_metro(34.0522, -118.2437) is False   # Los Angeles
        # North-shore leak: the licenses feed carries St. Tammany rows around
        # Madisonville (~30.38 lat). The metro bbox must exclude them.
        assert is_in_new_orleans_metro(30.38, -90.07) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in NOLA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= NEW_ORLEANS_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= NEW_ORLEANS_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= NEW_ORLEANS_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= NEW_ORLEANS_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in NOLA_SUBMARKETS.items():
            bbox = NOLA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in NOLA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(NOLA_SUBMARKETS)

    def test_submarkets_carry_the_nola_city_id(self):
        assert {m.city_id for m in NOLA_SUBMARKETS.values()} == {"new_orleans"}

    def test_job_names_are_namespaced(self):
        assert get_job_name(FeedType.PERMITS, CityId.NEW_ORLEANS) == "permits_nola"


class TestFeedRegistration:
    """New Orleans is a full four-feed city (with a caveated deeds stand-in)."""

    def test_all_four_feeds_are_registered(self):
        assert set(REGISTRY[CityId.NEW_ORLEANS].datasets) == {
            FeedType.PERMITS,
            FeedType.SLA,
            FeedType.COMPLAINTS_311,
            FeedType.DEEDS,
        }

    def test_watermarks_match_published_schemas(self):
        """Watermark columns pinned against live data.nola.gov rows on
        2026-08-23. Note 311 spells it `date_created` (the roadmap table's
        `createddate` was wrong); permits is `issuedate`, one word."""
        assert get_dataset(CityId.NEW_ORLEANS, FeedType.PERMITS).watermark_col == "issuedate"
        assert get_dataset(CityId.NEW_ORLEANS, FeedType.COMPLAINTS_311).watermark_col == "date_created"
        assert get_dataset(CityId.NEW_ORLEANS, FeedType.SLA).watermark_col == "businessstartdate"
        assert get_dataset(CityId.NEW_ORLEANS, FeedType.DEEDS).watermark_col == "sale_date"

    def test_every_alias_target_is_registered(self):
        for alias, cid in ALIASES.items():
            assert cid in REGISTRY, f"alias {alias!r} resolves to unregistered {cid}"


class TestNewOrleansRowParsing:
    """Fixtures captured live from data.nola.gov on 2026-08-23 (one newest row
    per feed, untruncated via `| python3 -m json.tool`).

    The registry's field_map entries carry every NOLA spelling (see
    src/spatial/city_registry.py); the shared chains alone know none of them —
    including the id columns — so these assertions double as the map's
    regression net.
    """

    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

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
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @pytest.fixture
    def permit_row(self):
        # Live newest-by-issuedate geocoded row from rcm3-fn58 (2026-08-23).
        return {
            "address": "518 Gravier St FIRE PUMP",
            "owner": "518 Gravier LLC",
            "description": "Install (1) 5 ton HP system, (2) 4 ton HP systems, "
            "(6) 3 ton HP systems, (2) 2 ton heat pump systems and (1) 7.5 ton HP package unit",
            "numstring": "26-24265-HVAC",
            "type": "Mechanical HVAC",
            "code": "HVAC",
            "filingdate": "2026-08-18T14:50:25.000",
            "issuedate": "2026-08-22T10:27:29.000",
            "currentstatus": "Permit Issued",
            "landuse": "Business Use",
            "constrval": "446500.0",
            "pin": "104100912",
            "subdivision": "Central Business District",
            "zoning": "CBD-2",
            "historicdistrict": "Picayune Place",
            "location_1": {
                "latitude": "29.95072022729879",
                "longitude": "-90.06829880990524",
            },
        }

    @pytest.fixture
    def sla_row(self):
        # Live newest-by-businessstartdate row from hjcd-grvu (2026-08-23).
        # businessstartdate is FUTURE-dated (2027-02-27): the city licenses
        # renewals ahead of term start; the watermark tolerates this rather
        # than rejecting the row.
        return {
            "ownername": "JOHN BOSS COLLECTION LLC",
            "businesstype": "Graphic Design Services",
            "businesslicensenumber": "105070793",
            "businessstartdate": "2027-02-27T00:00:00.000",
            "address": "6017 FRANKLIN AVE",
            "city": "NEW ORLEANS",
            "state": "LA",
            "zip": "70122-6423",
            "latitude": "30.020842932422095",
            "longitude": "-90.05145819580764",
            "location": {
                "latitude": "30.020842932422095",
                "longitude": "-90.05145819580764",
            },
        }

    @pytest.fixture
    def complaint_row(self):
        # Live newest-by-date_created row from 2jgv-pqrq (2026-08-23).
        return {
            "service_request": "2026-1312210",
            "request_type": "Trash/Recycling",
            "request_reason": "Request a Large Item Pick Up",
            "date_created": "2026-08-22T23:39:56.000",
            "date_modified": "2026-08-22T23:39:58.000",
            "request_status": "Pending",
            "responsible_agency": "Department of Sanitation",
            "final_address": "7049 Whitmore Pl",
            "address_councildis": "E",
            "status": "Assigned to Contractor",
            "rowid": "1312210",
            "longitude": "-89.94828453583602",
            "latitude": "30.058393176520628",
            "geocoded_column": {
                "latitude": "30.058393176520628",
                "longitude": "-89.94828453583602",
            },
        }

    @pytest.fixture
    def deed_row(self):
        # Live newest-by-sale_date geocoded row from hpm5-48nj (2026-08-23).
        # NOTE: NORA redevelopment-authority disposal, not a market deed;
        # there is no price column anywhere in the schema.
        return {
            "identifier": "ORL059301",
            "property_address": "7542 Avon Park Blvd",
            "zip_code": "70128",
            "geopin": "41114961",
            "council_district": "E",
            "disposition_channel": "Lot Next Door",
            "sale_date": "2026-07-22T00:00:00.000",
            "geocoded_column": {
                "latitude": "30.06672",
                "longitude": "-89.94491",
                "human_address": "{\"address\": \"7542 Avon Park Blvd\", \"city\": \"New Orleans\", \"state\": \"LA\", \"zip\": \"70128\"}",
            },
        }

    # -- PERMITS (rcm3-fn58) -----------------------------------------------

    def test_permit_parses_and_ids_from_numstring(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="new_orleans")
        assert ev is not None
        assert ev.job_id == "26-24265-HVAC"

    def test_permit_reads_the_location_1_container(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="new_orleans")
        assert ev.latitude == pytest.approx(29.95072022729879)
        assert ev.longitude == pytest.approx(-90.06829880990524)

    def test_permit_cost_comes_from_constrval(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="new_orleans")
        assert ev.estimated_cost == 446500.0

    def test_permit_dates_map(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="new_orleans")
        assert str(ev.issuance_date).startswith("2026-08-22")
        assert str(ev.filing_date).startswith("2026-08-18")

    def test_permit_job_type_classification(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="new_orleans")
        assert ev.job_type is not None

    def test_permit_resolves_to_a_division_by_coordinate(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="new_orleans")
        assert ev.borough is not None

    # -- LICENSES (hjcd-grvu) ----------------------------------------------

    def test_future_dated_license_still_parses(self, sla, sla_row):
        """Watermark-tolerance pin: businessstartdate runs up to ~2027-02-27
        because renewals predate their term. The row must parse, not be
        rejected for being future-dated."""
        ev = sla.parse_socrata_row(sla_row, city_id="new_orleans")
        assert ev is not None
        assert ev.license_id == "105070793"
        assert str(ev.effective_date).startswith("2027-02-27")

    def test_license_out_of_parish_rows_are_outside_the_metro_bbox(self):
        """The state-wide licenses feed leaks north-shore rows (Madisonville,
        ~30.38 lat). Spatial filtering must drop them; this is why max_lat is
        30.16, not 31."""
        assert is_in_new_orleans_metro(30.38, -90.07) is False

    def test_license_rejects_null_island_placeholder(self, sla, sla_row):
        """~24% of license rows carry 0.0/0.0; the Wave A guard files them nowhere."""
        sla_row["latitude"] = "0.0"
        sla_row["longitude"] = "0.0"
        assert sla.parse_socrata_row(sla_row, city_id="new_orleans") is None

    def test_license_live_fixture_is_inside_the_metro_bbox(self, sla_row):
        assert is_in_new_orleans_metro(float(sla_row["latitude"]), float(sla_row["longitude"]))

    # -- 311 (2jgv-pqrq) ---------------------------------------------------

    def test_311_parses_with_direct_coordinates(self, complaints, complaint_row):
        ev = complaints.parse_socrata_row(complaint_row, city_id="new_orleans")
        assert ev is not None
        assert ev.incident_id == "2026-1312210"
        assert ev.complaint_type == "Trash/Recycling"
        assert ev.latitude == pytest.approx(30.058393176520628)
        assert ev.longitude == pytest.approx(-89.94828453583602)
        assert str(ev.created_date).startswith("2026-08-22")

    def test_311_live_fixture_is_inside_the_metro_bbox(self, complaint_row):
        assert is_in_new_orleans_metro(float(complaint_row["latitude"]), float(complaint_row["longitude"]))

    def test_311_rejects_null_island_placeholder(self, complaints, complaint_row):
        """~4% of 311 rows carry 0.0/0.0 coordinates."""
        complaint_row["latitude"] = "0.0"
        complaint_row["longitude"] = "0.0"
        assert complaints.parse_socrata_row(complaint_row, city_id="new_orleans") is None

    # -- DEEDS (hpm5-48nj, NORA Sold Properties) ---------------------------

    def test_deed_parses_and_ids_from_identifier(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="new_orleans")
        assert ev is not None
        assert ev.doc_id == "ORL059301"

    def test_deed_document_amount_is_always_zero(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="new_orleans")
        assert ev.document_amount == 0.0

    def test_deed_recorded_date_reads_sale_date(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="new_orleans")
        assert str(ev.recorded_date).startswith("2026-07-22")

    def test_deed_reads_the_geocoded_column_container(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="new_orleans")
        assert ev.latitude == pytest.approx(30.06672)
        assert ev.longitude == pytest.approx(-89.94491)

    def test_deed_has_no_party_columns(self, deed_row):
        """The NORA schema carries no grantor/grantee parties at all — after the
        spine lands party1_grantor/party2_grantee should still be None."""
        assert "party1_grantor" not in deed_row
        assert "grantee" not in deed_row
        assert "seller" not in deed_row

    def test_deed_bbl_comes_from_geopin(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="new_orleans")
        assert ev.bbl == "41114961"

    def test_deed_live_fixture_is_inside_the_metro_bbox(self, deed_row):
        geo = deed_row["geocoded_column"]
        assert is_in_new_orleans_metro(float(geo["latitude"]), float(geo["longitude"]))
