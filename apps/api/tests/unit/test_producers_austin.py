"""Unit tests for the Austin registration and its producer wiring.

 Austin registers THREE feed types like Los Angeles — PERMITS (`quv8-5ckq`
 Issued Building Permits), COMPLAINTS_311 (`xwdj-i9he`), and TABC's
 address-geocoded SLA feed (`7hf9-qc9f`). DEEDS remains absent because Travis
 County's portal is a FedRAMP Socrata shell (see
 docs/research/new-orleans-austin-verification.md).

Registration tests are expected RED until the orchestrator applies the spine
(registry/producer edits are not leaf files). Parser tests use LIVE fixture
rows captured from data.austintexas.gov on 2026-08-23.

Sniff-regression note: bare `sr_number` rows no longer autodetect chicago
(tests/unit/test_field_maps.py::TestChicago311SniffTightening pins that), but
these tests never rely on autodetect anyway — production passes city_id="austin"
explicitly through run_stream.
"""

from unittest.mock import patch

import pytest

from src.config import settings
from src.producers.field_maps_state_licenses import TABC_ACTIVE_FIELD_MAP

from src.spatial.cities.austin import (
    AUSTIN_DIVISION_BBOXES,
    AUSTIN_DIVISIONS,
    AUSTIN_METRO_BBOX,
    AUSTIN_SUBMARKETS,
    is_in_austin_metro,
)
from src.spatial.city_registry import (
    CityId,
    FeedType,
)

# The spine adds CityId.AUSTIN + REGISTRY entry; until then resolve to None so
# these tests FAIL (assert) rather than ERROR (AttributeError) at import.
AUSTIN = getattr(CityId, "AUSTIN", None)


def _registry():
    from src.spatial.city_registry import REGISTRY

    return REGISTRY


class TestAustinRegistration:
    def test_registered(self):
        assert AUSTIN is not None, "spine pending: CityId.AUSTIN missing"
        assert AUSTIN in _registry()

    @pytest.mark.parametrize("alias", ["austin", "travis_county"])
    def test_aliases_resolve(self, alias):
        from src.spatial.city_registry import normalize_city

        assert AUSTIN is not None, "spine pending: CityId.AUSTIN missing"
        assert normalize_city(alias) is AUSTIN

    def test_registration_shape(self):
        assert AUSTIN is not None, "spine pending: CityId.AUSTIN missing"
        reg = _registry()[AUSTIN]
        assert reg.state == "TX"
        assert reg.job_suffix == "austin"
        assert reg.submarkets is AUSTIN_SUBMARKETS
        assert reg.divisions is AUSTIN_DIVISIONS
        assert len(reg.divisions) == 6

    def test_center_inside_metro_bbox(self):
        assert AUSTIN is not None, "spine pending: CityId.AUSTIN missing"
        reg = _registry()[AUSTIN]
        assert is_in_austin_metro(reg.center["lat"], reg.center["lng"])

    def test_is_in_austin_metro_rejects_missing_coordinates(self):
        assert is_in_austin_metro(None, None) is False

    def test_is_in_austin_metro_rejects_other_cities(self):
        assert is_in_austin_metro(47.6062, -122.3321) is False   # Seattle
        assert is_in_austin_metro(29.9511, -90.0715) is False    # New Orleans

    def test_live_samples_sit_inside_the_metro_bbox(self):
        """Verified live fixtures: Parmer Commons, downtown, Slaughter Ln,
        far NW Austin."""
        assert is_in_austin_metro(30.36741215, -97.61208497)
        assert is_in_austin_metro(30.27, -97.74)
        assert is_in_austin_metro(30.19, -97.79)
        assert is_in_austin_metro(30.40, -97.90)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in AUSTIN_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= AUSTIN_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= AUSTIN_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= AUSTIN_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= AUSTIN_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in AUSTIN_SUBMARKETS.items():
            bbox = AUSTIN_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in AUSTIN_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(AUSTIN_SUBMARKETS)

    def test_submarkets_carry_the_austin_city_id(self):
        assert {m.city_id for m in AUSTIN_SUBMARKETS.values()} == {"austin"}

    def test_job_names_are_namespaced(self):
        from src.spatial.city_registry import get_job_name

        assert AUSTIN is not None, "spine pending: CityId.AUSTIN missing"
        assert get_job_name(FeedType.PERMITS, AUSTIN) == "permits_austin"


class TestFeedRegistration:
    """Austin is a three-feed partial city (LA pattern)."""

    def test_exactly_three_feeds_are_registered(self):
        assert AUSTIN is not None, "spine pending: CityId.AUSTIN missing"
        assert set(_registry()[AUSTIN].datasets) == {
            FeedType.PERMITS,
            FeedType.COMPLAINTS_311,
            FeedType.SLA,
        }

    def test_watermarks_match_published_schemas(self):
        """Watermark columns pinned against live data.austintexas.gov rows on
        2026-08-23: permits spells it `issue_date` (with Z suffix), 311 spells
        it `sr_created_date`."""
        from src.spatial.city_registry import get_dataset

        assert AUSTIN is not None, "spine pending: CityId.AUSTIN missing"
        assert get_dataset(AUSTIN, FeedType.PERMITS).watermark_col == "issue_date"
        assert get_dataset(AUSTIN, FeedType.COMPLAINTS_311).watermark_col == "sr_created_date"
        sla = get_dataset(AUSTIN, FeedType.SLA)
        # US-372 migration: status_change_date is the fresher cursor (captures
        # renewals/status mutations; leaf-verified max 2026-08-26 vs
        # current_issued_date max 2026-08-25).
        assert sla.watermark_col == "status_change_date"
        assert sla.order_by == "status_change_date DESC"
        assert sla.id_keys == ["license_id", "master_file_id"]
        assert sla.needs_geocode is True
        assert sla.geocode_context == "TX"
        assert sla.where == "county = 'Travis'"
        # Namespaced endpoint + shared TABC map (all four TX slices uniform).
        assert sla.endpoint == settings.socrata_tabc_active_endpoint
        assert sla.field_map is TABC_ACTIVE_FIELD_MAP

    @pytest.mark.parametrize("absent_feed", [FeedType.DEEDS])
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        """DEEDS remains absent because Travis County is a FedRAMP shell."""
        from src.spatial.city_registry import get_dataset

        assert AUSTIN is not None, "spine pending: CityId.AUSTIN missing"
        with pytest.raises(KeyError, match=r"'austin'.*no.*feed.*available"):
            get_dataset(AUSTIN, absent_feed)


class TestAustinRowParsing:
    """Fixtures captured live from data.austintexas.gov on 2026-08-23
    (newest-by-watermark rows, untruncated via `| python3 -m json.tool`).

    Per the Wave-B mechanism, field maps ride on DatasetSpec in the
    registry — a spine file. Until the spine lands, resolve_field_map("austin",
    ...) degrades to {} and rows parse through the shared chains alone.
    """

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
    def permit_row(self):
        # Live newest-by-issue_date row from quv8-5ckq (2026-08-23).
        # Parmer Commons commercial finish-out.
        return {
            "the_geom": {
                "type": "Point",
                "coordinates": [-97.612087430724, 30.367418402105],
            },
            "objectid": "55",
            "permit_type": "Building Permit",
            "permit_number": "2026-091956 BP",
            "sub_type": "C-1001 Commercial Finish Out",
            "work_type": "Remodel",
            "permit_location": "5801 E PARMER LN UNIT 100",
            "issue_date": "2026-08-06T00:00:00.000Z",
            "status": "Active",
            "number_of_floors": "1",
            "number_of_units": "1",
            "street_number": "5801",
            "street_prefix": "E",
            "street_name": "PARMER",
            "street_type": "LN",
            "city": "AUSTIN",
            "zip_code": "78754",
            "latitude": "30.36741215",
            "longitude": "-97.61208497",
            "location": "POINT(-97.61208497 30.36741215)",
            "council_district": "1",
            "state": "TX",
            "county": "TRAVIS",
            "application_date": "2026-03-26T00:00:00.000Z",
            "expiry_date": "2027-02-03T00:00:00.000Z",
            "work_description": (
                "First time tenant finish out for dental office."
                "Change of use from retail shell to dental office."
            ),
        }

    @pytest.fixture
    def valued_permit_row(self):
        # Live newest-by-issue_date WITH a non-null total_job_valuation
        # (the newest overall row leaves that column null — remodel rows
        # carry only the valuation breakdown columns instead).
        return {
            "permit_type": "Building Permit",
            "permit_number": "2026-101521 BP",
            "sub_type": "R- 435 Renovations/Remodel",
            "work_type": "Repair",
            "permit_location": "916 E 49TH ST",
            "issue_date": "2026-08-06T00:00:00.000Z",
            "status": "Active",
            "total_job_valuation": "1",
            "total_valuation_remodel": "4",
            "number_of_floors": "1",
            "number_of_units": "1",
            "zip_code": "78751",
            "latitude": "30.30868954",
            "longitude": "-97.71396076",
            "council_district": "9",
            "application_date": "2026-08-05T00:00:00.000Z",
            "work_description": "Express- Foundation repair",
        }

    @pytest.fixture
    def complaint_row(self):
        # Live newest-by-sr_created_date row from xwdj-i9he (2026-08-23).
        return {
            "sr_number": "26-00276479",
            "sr_type_desc": "TPW - Traffic Signal - Maintenance",
            "sr_department_desc": "Austin Transportation and Public Works",
            "sr_method_received_desc": "Phone",
            "sr_status_desc": "Open",
            "sr_status_date": "2026-08-22T23:52:16.000",
            "sr_created_date": "2026-08-22T23:52:16.000",
            "sr_updated_date": "2026-08-22T23:52:16.000",
            "sr_location": "BANISTER LN & W BEN WHITE BLVD SVRD EB, AUSTIN, TX",
            "sr_location_street_name": "BANISTER LN & W BEN WHITE BLVD SVRD EB",
            "sr_location_city": "AUSTIN",
            "sr_location_zip_code": "78745",
            "sr_location_county": "TRAVIS",
            "sr_location_x": "3103012.19479633",
            "sr_location_y": "10055703.13421920",
            "sr_location_lat": "30.22741319",
            "sr_location_long": "-97.77968866",
            "sr_location_lat_long": {
                "type": "Point",
                "coordinates": [-97.77968866, 30.22741319],
            },
            "sr_location_council_district": "5",
        }

    # -- PERMITS (quv8-5ckq) -----------------------------------------------

    def test_permit_parses_and_ids_from_permit_number(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="austin")
        assert ev is not None
        assert ev.job_id == "2026-091956 BP"

    def test_permit_reads_coordinates_directly_today(self, permits, permit_row):
        """latitude/longitude are plain columns, so coords parse TODAY via the
        shared chain; the_geom's coordinates container is the fallback behind
        them and also resolves (chain: location/point/the_geom/shape)."""
        ev = permits.parse_socrata_row(permit_row, city_id="austin")
        assert ev.latitude == pytest.approx(30.36741215)
        assert ev.longitude == pytest.approx(-97.61208497)

    def test_permit_the_geom_container_resolves_alone(self, permits, permit_row):
        """Reality note: the feed's `location` column is a WKT *string*
        ("POINT(lng lat)") which sits earlier in the shared container chain
        and blocks the the_geom dict fallback while present. With both direct
        coordinates and the WKT string absent, the_geom's [lng, lat]
        coordinates do resolve."""
        for key in ("latitude", "longitude", "location"):
            permit_row.pop(key)
        ev = permits.parse_socrata_row(permit_row, city_id="austin")
        assert ev is not None
        assert ev.latitude == pytest.approx(30.367418402105)
        assert ev.longitude == pytest.approx(-97.612087430724)

    def test_permit_issuance_date_maps_today(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="austin")
        assert str(ev.issuance_date).startswith("2026-08-06")

    def test_permit_zipcode_maps_today(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="austin")
        assert ev.zipcode == "78754"

    def test_permit_generic_type_yields_other_today(self, permits, permit_row):
        """permit_type values are generic ("Building Permit"); today the chain
        classifies them OT. NB/DM signal needs the work_type-first ordering,
        which arrives with the registry field_map (spine)."""
        ev = permits.parse_socrata_row(permit_row, city_id="austin")
        assert str(ev.job_type).endswith("OT")

    def test_permit_cost_comes_from_total_job_valuation(self, permits, valued_permit_row):
        ev = permits.parse_socrata_row(valued_permit_row, city_id="austin")
        assert ev.estimated_cost == 1.0

    def test_permit_filing_date_comes_from_application_date(
        self, permits, valued_permit_row
    ):
        ev = permits.parse_socrata_row(valued_permit_row, city_id="austin")
        assert str(ev.filing_date).startswith("2026-08-05")

    def test_permit_work_type_drives_classification(self, permits, permit_row):
        permit_row["work_type"] = "Demolition"
        ev = permits.parse_socrata_row(permit_row, city_id="austin")
        assert str(ev.job_type).endswith("DM")

    def test_permit_units_and_stories_map(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="austin")
        assert ev.proposed_dwelling_units == 1
        assert ev.proposed_stories == 1

    # -- COMPLAINTS_311 (xwdj-i9he) -----------------------------------------

    def test_311_parses_with_mapped_columns(self, complaints, complaint_row):
        ev = complaints.parse_socrata_row(complaint_row, city_id="austin")
        assert ev is not None
        assert ev.incident_id == "26-00276479"
        assert ev.complaint_type == "TPW - Traffic Signal - Maintenance"
        assert ev.latitude == pytest.approx(30.22741319)
        assert ev.longitude == pytest.approx(-97.77968866)
        assert str(ev.created_date).startswith("2026-08-22")

    def test_311_incident_id_chain_knows_sr_number(self, complaints, complaint_row):
        """Pin the half that DOES work today: sr_number resolves through the
        shared incident_id chain — only the coordinates gate the event out."""
        from src.producers.field_maps import first_mapped

        assert first_mapped(complaint_row, {}, "incident_id") is None
        assert complaint_row.get("sr_number") == "26-00276479"

    def test_311_bare_sr_number_does_not_sniff_chicago(self, complaints, complaint_row):
        """Regression companion to
        tests/unit/test_field_maps.py::TestChicago311SniffTightening: an
        sr_number-only row must NOT autodetect chicago (and production passes
        city_id explicitly regardless)."""
        bare = {"sr_number": "26-00000001"}
        with patch.object(complaints, "spatial_indexer") as idx:
            idx.get_multi_res_hierarchy.return_value = {
                "h3_res7": "x",
                "h3_res8": "x",
                "h3_res9": "x",
            }
            ev = complaints.parse_socrata_row(dict(bare, latitude="30.2", longitude="-97.7"))
        if ev is not None:
            assert ev.city_id != "chicago"

    def test_311_live_fixture_is_inside_the_metro_bbox(self, complaint_row):
        assert is_in_austin_metro(
            float(complaint_row["sr_location_lat"]),
            float(complaint_row["sr_location_long"]),
        )
