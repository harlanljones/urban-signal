"""Unit tests for the Philadelphia registration and its producer wiring.

Philadelphia is the first all-CARTO city: all four feeds register with
``platform="carto"`` through CartoClient against phl.carto.com.
Live-probed 2026-08-23 via ``GET /api/v2/sql?q=SELECT * ... LIMIT 1``
(full flat rows verified with ``python3 -m json.tool``):

* PERMITS   permits            (~932k rows; keyset permitissuedate)
* 311       public_cases_fc    (~5.9M rows; keyset requested_datetime)
* SLA       business_licenses  (keyset mostrecentissuedate — year-3200 sentinel SEEN LIVE)
* DEEDS     rtt_summary        (~1.16M real docs incl. mortgages; document_date frequently NULL)

Pinned quirks (all observed live):
* geocode_x/geocode_y on permits/business_licenses are PA South state-plane
  FEET (~2.7M / ~233k), NOT lng/lat, and neither table has lat/lng columns —
  real coordinates live only in the_geom (hex WKB SRID 4326). Proposed spec
  extra: select="*, ST_Y(the_geom) AS latitude, ST_X(the_geom) AS longitude".
  Fixtures below carry latitude/longitude keys exactly as that select yields.
* rtt_summary.document_date carries its own sentinel years ("9798-06-12" seen
  on a real SATISFACTION OF MORTGAGE row) AND is frequently NULL even on real
  docs — so recorded_date maps to recording_date instead; ingest-time-default
  fallback is last resort only. NULL consideration on mortgages →
  document_amount 0.0 (accepted caveat, NORA zero-price precedent).
* Sentinel exclusion for business_licenses is CLIENT-side (CartoClient's
  "< '2101-01-01'" WHERE fragment); parsers never see those rows.

Registration tests are expected RED until the orchestrator applies the spine
(registry edits are not leaf files). Parser tests run against LIVE fixtures
captured 2026-08-23; assertions depending on pending field_map entries patch
resolve_field_map with the EXACT proposal from .streams/city-philadelphia.md
and are plain passes today.
"""

from unittest.mock import patch

import pytest

from src.spatial.cities.philadelphia import (
    PHL_DIVISION_BBOXES,
    PHL_DIVISIONS,
    PHILADELPHIA_METRO_BBOX,
    PHL_SUBMARKETS,
    is_in_philadelphia_metro,
)

try:
    from src.spatial.city_registry import (
        ALIASES,
        REGISTRY,
        CityId,
        FeedType,
        get_dataset,
        get_job_name,
        normalize_city,
    )

    HAS_PHILLY_SPINE = getattr(CityId, "PHILADELPHIA", None) is not None
except ImportError:  # pragma: no cover
    HAS_PHILLY_SPINE = False

SPINE_REASON = (
    "RED until orchestrator spine registers CityId.PHILADELPHIA "
    "(city_registry.py + producer wiring are spine files)"
)


class TestPhiladelphiaGeometry:
    """Passes today — pure spatial-layer assertions."""

    def test_is_in_philadelphia_metro_rejects_missing_coordinates(self):
        assert is_in_philadelphia_metro(None, None) is False

    def test_is_in_philadelphia_metro_rejects_other_cities(self):
        assert is_in_philadelphia_metro(47.6062, -122.3321) is False   # Seattle
        assert is_in_philadelphia_metro(42.3314, -83.0458) is False    # Detroit
        assert is_in_philadelphia_metro(39.87 - 0.01, -75.10) is False
        assert is_in_philadelphia_metro(40.00, -74.95 + 0.01) is False

    def test_live_fixture_coordinates_sit_inside_the_metro_bbox(self):
        """All four live-captured row coordinates (2026-08-23)."""
        coords = [
            (39.945473500559494, -75.14495345971721),   # permits the_geom WKB
            (39.982432990544055, -75.09346843987747),   # business_licenses WKB
            (39.97569357029587, -75.14251851025277),    # rtt_summary WKB
            (40.1004174, -75.0434667),                  # public_cases_fc lat/lon
        ]
        for lat, lng in coords:
            assert is_in_philadelphia_metro(lat, lng), (lat, lng)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in PHL_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= PHILADELPHIA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= PHILADELPHIA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= PHILADELPHIA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= PHILADELPHIA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in PHL_SUBMARKETS.items():
            bbox = PHL_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in PHL_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(PHL_SUBMARKETS)

    def test_submarkets_carry_the_philadelphia_city_id(self):
        assert {m.city_id for m in PHL_SUBMARKETS.values()} == {"philadelphia"}

    def test_metric_ranges_are_bounded(self):
        for name, m in PHL_SUBMARKETS.items():
            assert 0.52 <= m.base_lims <= 0.92, name
            assert 2_000_000 <= m.capex <= 11_000_000, name
            assert 20 <= m.permit_vel <= 56, name
            assert 1.10 <= m.shift_ratio <= 1.68, name
            assert 26 <= m.sla <= 72, name


class TestPhiladelphiaRegistration:
    """Expected RED until the spine registers Philadelphia."""

    def test_registered(self):
        assert CityId.PHILADELPHIA in REGISTRY

    @pytest.mark.parametrize("alias", ["philadelphia", "philly", "phl"])
    def test_aliases_resolve(self, alias):
        assert normalize_city(alias) is CityId.PHILADELPHIA

    def test_registration_shape(self):
        reg = REGISTRY[CityId.PHILADELPHIA]
        assert reg.state == "PA"
        # DECIDED: job_suffix is "philadelphia", NOT "philly".
        assert reg.job_suffix == "philadelphia"
        assert reg.submarkets is PHL_SUBMARKETS
        assert reg.divisions is PHL_DIVISIONS
        assert len(reg.divisions) == 8

    def test_job_names_are_namespaced(self):
        assert get_job_name(FeedType.PERMITS, CityId.PHILADELPHIA) == "permits_philadelphia"


class TestFeedRegistration:
    """All four feeds, every one platform="carto". Watermarks pinned to the
    live-verified keyset columns."""

    def test_all_four_feeds_are_registered(self):
        assert set(REGISTRY[CityId.PHILADELPHIA].datasets) == {
            FeedType.PERMITS,
            FeedType.SLA,
            FeedType.COMPLAINTS_311,
            FeedType.DEEDS,
        }

    def test_every_feed_is_carto_platform_with_carto_uri_endpoints(self):
        for feed, spec in REGISTRY[CityId.PHILADELPHIA].datasets.items():
            assert spec.platform == "carto", feed
            assert spec.endpoint.startswith("carto://phl.carto.com/"), feed

    def test_watermarks_match_verified_keyset_columns(self):
        """Pinned against live CARTO table schemas on 2026-08-23; deeds moved
        to recording_date per docs/research/deeds-watermark-audit.md
        (2026-08-24) after document_date sentinels poisoned the watermark."""
        assert get_dataset(CityId.PHILADELPHIA, FeedType.PERMITS).watermark_col == "permitissuedate"
        assert get_dataset(CityId.PHILADELPHIA, FeedType.COMPLAINTS_311).watermark_col == "requested_datetime"
        assert get_dataset(CityId.PHILADELPHIA, FeedType.SLA).watermark_col == "mostrecentissuedate"
        assert get_dataset(CityId.PHILADELPHIA, FeedType.DEEDS).watermark_col == "recording_date"
        assert get_dataset(CityId.PHILADELPHIA, FeedType.DEEDS).extra["order_by"] == "recording_date"

    def test_extras_pin_keyset_id_and_geometry_select(self):
        """Keyset tie-breaker is cartodb_id (every CARTO table carries it);
        permits/licenses/rtt need ST_Y/ST_X select because geocode_x/y are
        state-plane feet, not lng/lat."""
        for feed in (FeedType.PERMITS, FeedType.SLA, FeedType.DEEDS):
            spec = get_dataset(CityId.PHILADELPHIA, feed)
            assert spec.extra["id_col"] == "cartodb_id"
            assert "ST_Y(the_geom) AS latitude" in spec.extra["select"]
            assert "ST_X(the_geom) AS longitude" in spec.extra["select"]
        three11 = get_dataset(CityId.PHILADELPHIA, FeedType.COMPLAINTS_311)
        assert three11.extra["id_col"] == "cartodb_id"

    def test_every_alias_target_is_registered(self):
        for alias, cid in ALIASES.items():
            assert cid in REGISTRY, f"alias {alias!r} resolves to unregistered {cid}"


# ---------------------------------------------------------------------------
# Proposed field maps (see .streams/city-philadelphia.md Decisions).
# ---------------------------------------------------------------------------

PHL_FIELD_MAPS = {
    FeedType.PERMITS: {
        "job_id": ["permitnumber"],
        "issuance_date": ["permitissuedate"],
        "borough": ["council_district"],
        "zipcode": ["zip"],
    },
    FeedType.COMPLAINTS_311: {
        "incident_id": ["service_request_id"],
        "created_date": ["requested_datetime"],
        "closed_date": ["closed_datetime"],  # belt-and-braces: chain also has it
        "complaint_type": ["service_name"],
        # SURPRISE: the shared 311 longitude chain reads
        # latitude/longitude/lng/long but NOT `lon` — Philly's spelling.
        "latitude": ["lat"],
        "longitude": ["lon"],
    },
    FeedType.SLA: {
        "license_id": ["licensenum"],
        "license_type": ["licensetype"],
        "effective_date": ["initialissuedate"],
        "expiration_date": ["expirationdate"],
    },
    FeedType.DEEDS: {
        "doc_id": ["document_id"],
        "recorded_date": ["recording_date"],
        "document_amount": ["total_consideration"],
        "bbl": ["opa_account_num"],
        "party1_grantor": ["grantors"],
        "party2_grantee": ["grantees"],
        "doc_type": ["document_type"],
    },
}


class PhillyParsingBase:
    """Fixtures are REAL rows pulled from phl.carto.com/api/v2/sql on
    2026-08-23 — exactly the flat dicts CartoClient._fetch_rows hands to
    producers (plus simulated latitude/longitude keys where the proposed
    ST_Y/ST_X select applies)."""

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
        # Live newest-by-permitissuedate row from `permits` (2026-08-23),
        # plus latitude/longitude as the proposed ST_Y/ST_X select yields
        # (decoded from this row's actual the_geom WKB hex).
        return {
            "cartodb_id": 590418,
            "permitnumber": "ZP-2026-007949",
            "addressobjectid": "654673420",
            "parcel_id_num": "414644",
            "permittype": "Zoning",
            "permitdescription": "Zoning Permit",
            "commercialorresidential": "Commercial",
            "typeofwork": "Change of Use",
            "approvedscopeofwork": "Residential - Household Living - Multi-Family",
            "permitissuedate": "2026-08-22T19:13:14Z",
            "status": "Issued",
            "applicanttype": "Professional / Tradesperson",
            "contractorname": "Canary Architecture LLC",
            "contractoraddress1": "Canary Architecture LLC\n753 Bradford Terrace\nSpringfield, PA  19064\nUSA",
            "mostrecentinsp": None,
            "opa_account_num": "888052230",
            "address": "210 LOCUST ST",
            "unit_type": "APT",
            "unit_num": "APT 11GW",
            "zip": "19106-0137",
            "censustract": "001002",
            "council_district": "1",
            "opa_owner": "SPAGNOLETTI JAMES T",
            "systemofrecord": "ECLIPSE",
            "geocode_x": 2698810.56973357,
            "geocode_y": 233766.75561967,
            "posse_jobid": "1006794733",
            "objectid": 590376,
            "usecategories": "Residential - Household Living - Multi-Family",
            "latitude": 39.945473500559494,
            "longitude": -75.14495345971721,
        }

    @pytest.fixture
    def complaint_row(self):
        # Live newest-by-requested_datetime row WITH coordinates from
        # public_cases_fc (2026-08-23). The absolute newest row had NULL
        # lat/lon AND null the_geom — see the rejection test below.
        return {
            "cartodb_id": 5908551,
            "service_request_id": 19901761,
            "status": "Open",
            "status_notes": None,
            "service_name": "Maintenance Complaint",
            "service_code": None,
            "agency_responsible": "License & Inspections",
            "service_notice": None,
            "requested_datetime": "2026-08-22T23:07:26Z",
            "updated_datetime": "2026-08-22T23:13:33Z",
            "expected_datetime": None,
            "closed_datetime": None,
            "address": "896 PINE HILL RD",
            "zipcode": "19115",
            "lat": 40.1004174,
            "lon": -75.0434667,
            "subject": None,
            "media_url": None,
            "service_type": "Exterior High Weeds",
        }

    @pytest.fixture
    def sla_row(self):
        # Live newest-by-mostrecentissuedate row from business_licenses
        # (2026-08-23) — NOTE this very row demonstrates the year-3200
        # sentinel in mostrecentissuedate; in production CartoClient's
        # sentinel WHERE fragment excludes it before parsing. Coordinates via
        # proposed select (decoded from this row's the_geom WKB).
        return {
            "cartodb_id": 304425,
            "objectid": 304373,
            "posse_jobid": "9418049",
            "council_district": "6",
            "address": "3007-11 E ONTARIO ST",
            "zip": "19134-6307",
            "parcel_id_num": "526430",
            "opa_account_num": "885985800",
            "opa_owner": "3007 INC",
            "licensenum": "379773",
            "revenuecode": "3311",
            "licensetype": "Motor Vehicle Repair / Fuel Dispensing",
            "initialissuedate": "2006-08-02T14:11:00Z",
            "mostrecentissuedate": "3200-12-31T05:00:00Z",
            "expirationdate": "2009-12-31T05:00:00Z",
            "inactivedate": "2012-07-24T20:35:18Z",
            "licensestatus": "Inactive",
            "legalname": "JOHN EVANS",
            "business_name": "JOHN EVANS (DBA: 3007 INC)",
            "geocode_x": 2712834.85636216,
            "geocode_y": 247654.3206992609,
            "latitude": 39.982432990544055,
            "longitude": -75.09346843987747,
        }

    @pytest.fixture
    def deed_row(self):
        # Live newest-by-document_date (non-null) row from rtt_summary
        # (2026-08-23) — deliberately chosen because it exhibits BOTH quirks:
        # a year-9798 document_date sentinel AND null consideration fields on
        # a real mortgage-satisfaction document. Coordinates via proposed
        # select (decoded from this row's the_geom WKB).
        return {
            "cartodb_id": 5084420,
            "document_id": 54531949,
            "document_type": "SATISFACTION OF MORTGAGE",
            "display_date": "9798-06-12T08:00:00Z",
            "street_address": "1618 GERMANTOWN AVE UNIT A",
            "zip_code": None,
            "ward": "18",
            "grantors": "MORTGAGE ELECTRONIC REGISTRATION SYSTEMS INC;ROCKET MORTGAGE LLC",
            "grantees": "ADAMS DAVID J III",
            "cash_consideration": None,
            "other_consideration": None,
            "total_consideration": None,
            "assessed_value": None,
            "fair_market_value": None,
            "receipt_date": "2026-03-20T20:19:37Z",
            "recording_date": "2026-03-20T20:52:57Z",
            "document_date": "9798-06-12T08:00:00Z",
            "condo_name": "1618 GERMANTOWN AVE ",
            "unit_num": "A",
            "street_name": "GERMANTOWN",
            "street_suffix": "AVE",
            "opa_account_num": None,
            "property_count": 1,
            "record_id": "545319490",
            "objectid": 5084402,
            "latitude": 39.97569357029587,
            "longitude": -75.14251851025277,
        }


class TestPhiladelphiaChainsToday(PhillyParsingBase):
    """Bare fallback chains, no registry map — what runs if a row arrives
    before the spine. Only ids/dates whose spellings already match a chain
    term survive; everything else needs the proposed map."""

    def test_311_survives_with_map_longitude_lon(self, complaints, complaint_row, monkeypatch):
        import src.producers.field_maps as fm

        monkeypatch.setattr(
            fm,
            "resolve_field_map",
            lambda city_value, feed: PHL_FIELD_MAPS.get(feed, {}),
            raising=True,
        )
        ev = complaints.parse_socrata_row(complaint_row, city_id="philadelphia")
        assert ev.incident_id == "19901761"
        assert str(ev.created_date).startswith("2026-08-22")
        assert ev.latitude == pytest.approx(40.1004174)
        assert ev.longitude == pytest.approx(-75.0434667)

    def test_deed_doc_id_matches_chain_document_id_term(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="philadelphia")
        assert ev.doc_id == "54531949"


class TestPhiladelphiaWithProposedFieldMap(PhillyParsingBase):
    """Patches resolve_field_map to hand back the EXACT field_map proposed in
    .streams/city-philadelphia.md, proving the proposal resolves every
    Philadelphia spelling before the orchestrator applies it."""

    @pytest.fixture(autouse=True)
    def _proposed_maps(self, monkeypatch):
        import src.producers.field_maps as fm

        monkeypatch.setattr(
            fm,
            "resolve_field_map",
            lambda city_value, feed: PHL_FIELD_MAPS.get(feed, {}),
            raising=True,
        )

    # -- PERMITS -------------------------------------------------------------

    def test_permit_id_dates_type_status_through_map_and_chains(
        self, permits, permit_row
    ):
        ev = permits.parse_socrata_row(permit_row, city_id="philadelphia")
        assert ev.job_id == "ZP-2026-007949"
        assert str(ev.issuance_date).startswith("2026-08-22")
        assert ev.filing_date is None  # no filed-date column exists on the table
        assert ev.job_type is not None
        assert ev.status == "Issued"
        assert ev.zipcode == "19106-0137"

    def test_permit_reads_select_derived_coordinates_not_state_plane(
        self, permits, permit_row
    ):
        ev = permits.parse_socrata_row(permit_row, city_id="philadelphia")
        assert ev.latitude == pytest.approx(39.945473500559494)
        assert ev.longitude == pytest.approx(-75.14495345971721)

    def test_permit_has_no_cost_column_anywhere(self, permits, permit_row):
        """Accepted: the permits table carries no valuation/cost column, so
        estimated_cost lands on the chain default 0.0."""
        ev = permits.parse_socrata_row(permit_row, city_id="philadelphia")
        assert ev.estimated_cost == 0.0

    # -- 311 -----------------------------------------------------------------

    def test_311_closed_datetime_comes_from_the_proposed_map(
        self, complaints, complaint_row
    ):
        complaint_row["closed_datetime"] = "2026-08-23T01:42:00Z"
        ev = complaints.parse_socrata_row(complaint_row, city_id="philadelphia")
        assert str(ev.closed_date).startswith("2026-08-23")

    def test_311_rejects_null_coordinate_rows(self, complaints, complaint_row):
        """The true newest requested_datetime row has NULL lat/lon AND null
        the_geom — the coordinate guard must drop it, not crash."""
        complaint_row["lat"] = None
        complaint_row["lon"] = None
        assert complaints.parse_socrata_row(complaint_row, city_id="philadelphia") is None

    def test_311_rejects_null_island_placeholder(self, complaints, complaint_row):
        complaint_row["lat"] = 0.0
        complaint_row["lon"] = 0.0
        assert complaints.parse_socrata_row(complaint_row, city_id="philadelphia") is None

    # -- LICENSES --------------------------------------------------------------

    def test_license_fields_through_proposed_map(self, sla, sla_row):
        ev = sla.parse_socrata_row(sla_row, city_id="philadelphia")
        assert ev.license_id == "379773"
        assert ev.license_type == "Motor Vehicle Repair / Fuel Dispensing"
        assert str(ev.effective_date).startswith("2006-08-02")
        assert str(ev.expiration_date).startswith("2009-12-31")

    def test_license_status_reads_the_licensestatus_spelling(self, sla, sla_row):
        """The table spells it `licensestatus` (no underscore); the registry's
        field_map carries status=['licensestatus'] and the SLA parser reads it
        via first_mapped — Inactive licenses must not fall to the ACTIVE
        end-date heuristic."""
        assert sla_row["licensestatus"] == "Inactive"
        ev = sla.parse_socrata_row(sla_row, city_id="philadelphia")
        assert ev.license_status == "Inactive"

    def test_license_dba_and_type_through_proposed_map(self, sla, sla_row):
        ev = sla.parse_socrata_row(sla_row, city_id="philadelphia")
        assert ev.dba == "JOHN EVANS (DBA: 3007 INC)"
        assert ev.license_type == "Motor Vehicle Repair / Fuel Dispensing"

    def test_business_licenses_sentinel_exclusion_is_client_side(self):
        """PINNED: the year-3200 mostrecentissuedate sentinel never reaches
        the parser — CartoClient emits the NULL+window WHERE fragment
        CLIENT-side for date-named order columns. Exact-text pin."""
        from src.producers.carto_client import CartoClient

        client = CartoClient()
        fragment = client._sentinel_filter("mostrecentissuedate", None)
        assert fragment == (
            "mostrecentissuedate IS NOT NULL "
            "AND mostrecentissuedate >= '1900-01-01' "
            "AND mostrecentissuedate < '2101-01-01'"
        )
        q = client._join_where(
            None,
            "mostrecentissuedate",
            None,
        )
        assert fragment in q
        # And the full page query carries it too (paginate path).
        q = client._build_query(
            table="business_licenses",
            order_col="mostrecentissuedate",
            id_col="cartodb_id",
            where_clause=client._join_where(None, "mostrecentissuedate", None),
            limit=1000,
            last_keyset=None,
            direction="ASC",
        )
        assert fragment in q

    # -- DEEDS -----------------------------------------------------------------

    def test_deed_recorded_date_prefers_recording_date_over_null_sentinel_document_date(
        self, deeds, deed_row
    ):
        """ACCEPTED CAVEAT (NORA zero-price precedent): document_date is
        frequently NULL and carries sentinel years (this live row says
        9798-06-12). The proposed map points recorded_date at
        recording_date, which is populated even here."""
        assert deed_row["document_date"].startswith("9798-")
        ev = deeds.parse_socrata_row(deed_row, city_id="philadelphia")
        assert str(ev.recorded_date).startswith("2026-03-20")

    def test_deed_mortgage_consideration_is_null_so_amount_is_zero(
        self, deeds, deed_row
    ):
        """~Half of rtt_summary documents are mortgages/satisfactions with
        NULL total_consideration → document_amount 0.0 by design."""
        ev = deeds.parse_socrata_row(deed_row, city_id="philadelphia")
        assert ev.document_amount == 0.0
        assert ev.doc_type == "SATISFACTION OF MORTGAGE"

    def test_deed_parties_read_semicolon_joined_grantors_grantees(
        self, deeds, deed_row
    ):
        ev = deeds.parse_socrata_row(deed_row, city_id="philadelphia")
        assert ev.party1_grantor.startswith("MORTGAGE ELECTRONIC")
        assert ev.party2_grantee == "ADAMS DAVID J III"

    def test_deed_full_h3_events_from_select_derived_coordinates(
        self, deeds, deed_row
    ):
        ev = deeds.parse_socrata_row(deed_row, city_id="philadelphia")
        assert ev.latitude == pytest.approx(39.97569357029587)
        assert ev.h3_res7 is not None
        assert ev.h3_res8 is not None
        assert ev.h3_res9 is not None

    def test_deed_parses_even_without_coordinates(self, deeds, deed_row):
        """If the spine skips the ST_Y/ST_X select, the deeds parser still
        tolerates missing coords (None lat/lng, no H3) rather than dropping
        the row — unlike permits/licenses which hard-drop."""
        deed_row.pop("latitude")
        deed_row.pop("longitude")
        ev = deeds.parse_socrata_row(deed_row, city_id="philadelphia")
        assert ev is not None
        assert ev.latitude is None
        assert ev.h3_res7 is None


class TestProducerWiring:
    """Producers must expose a CartoClient instance once the spine wires
    platform="carto" dispatch (mirrors .socrata/.arcgis)."""

    def _producers(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"), patch(
            "src.producers.complaints_311_producer.BaseKafkaProducer"
        ), patch("src.producers.sla_licenses_producer.BaseKafkaProducer"), patch(
            "src.producers.deeds_acris_producer.BaseKafkaProducer"
        ):
            from src.producers.dob_permits_producer import DOBPermitsProducer
            from src.producers.complaints_311_producer import Complaints311Producer
            import src.producers.sla_licenses_producer as sla_module
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            sla_cls = next(
                getattr(sla_module, n)
                for n in dir(sla_module)
                if n.endswith("Producer") and "Base" not in n
            )
            return [
                DOBPermitsProducer(),
                Complaints311Producer(),
                sla_cls(),
                DeedsACRISProducer(),
            ]

    def test_every_producer_carries_a_carto_client(self):
        from src.producers.carto_client import CartoClient

        for producer in self._producers():
            assert hasattr(producer, "carto"), type(producer).__name__
            assert isinstance(producer.carto, CartoClient)

    def test_client_for_dispatches_carto_platform(self):
        for producer in self._producers():
            assert producer._client_for("carto") is producer.carto
