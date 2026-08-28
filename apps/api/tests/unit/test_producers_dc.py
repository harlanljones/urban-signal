"""Unit tests for the Washington DC registration and its producer wiring.

DC is the first YEAR-SLICED ArcGIS city: PERMITS and COMPLAINTS_311 publish
one layer per calendar year on maps2.dcgis.dc.gov and resolve through
``city_registry.resolve_endpoint``; SLA (Basic Business Licenses) and DEEDS
(Property Sales CAMA) are coordinate-less TABLES. US-74 split their fates:

* SLA   upgrades to a geocoded-premises feed: PREMISEADDRESS resolves at
  parse time via extra={"needs_geocode": True, "geocode_context":
  "Washington, DC"} (ADR 0004), keeping Avro doubles real. The layer's own
  LATITUDE/LONGITUDE columns are null or sentinel junk (39/-77) on every
  sampled row, so the field_map must NOT bridge them.
* DEEDS publishes ZERO address-like fields, so the producer enriches CAMA
  rows through the verified SSL → Parcel Lots polygon join before parsing.
  Unmatched rows still retain nullable lat/lng/H3, preserving the deeds
  precedent while the matched path emits centroid coordinates.

Live-probed 2026-08-24:

* PERMITS   FEEDS/DCRA/FeatureServer/18            (points, newest ISSUE_DATE 2026-08-17)
* 311       DCGIS_DATA/ServiceRequests/FeatureServer/21 (points, newest ADDDATE 2026-08-23)
* SLA       FEEDS/DCRA/FeatureServer/0             (table; PREMISEADDRESS 97.7-100%
            usable over 300-row windows; BILLINGADDRESS is mailing-only and never mapped;
            PREMISEINDC='No' rows carry out-of-state premises ~24% of the watermark window)
* DEEDS     DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/57
            (table; SSL parcel key only; newest-by-OBJECTID rows carry SALE_DATE=1900 sentinels)

Quirks pinned here:
* Coordinate attrs are UPPERCASE (LATITUDE/LONGITUDE) — chains are lowercase,
  so field_map entries are REQUIRED for geocoded feeds.
* The server rejects returnCountOnly queries carrying where-clauses; recency
  checks page newest-first (orderByFields=<col> DESC) instead.
* Watermarks reset at New Year rollover when resolve_endpoint switches layers
  (docs/expansion-roadmap.md §8.2).

Registration tests are expected RED until the orchestrator applies the spine
(registry edits are not leaf files). Parser tests run against LIVE fixtures
captured from the FeatureServers on 2026-08-23/24.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.spatial.city_registry import (
    FeedType,
    get_job_name,
    resolve_endpoint,
)

DCGIS = "https://maps2.dcgis.dc.gov/dcgis/rest/services"
PERMITS_BY_YEAR = {
    "2023": f"{DCGIS}/FEEDS/DCRA/FeatureServer/15",
    "2024": f"{DCGIS}/FEEDS/DCRA/FeatureServer/16",
    "2025": f"{DCGIS}/FEEDS/DCRA/FeatureServer/17",
    "2026": f"{DCGIS}/FEEDS/DCRA/FeatureServer/18",
}
THREE11_BY_YEAR = {
    "2022": f"{DCGIS}/DCGIS_DATA/ServiceRequests/FeatureServer/14",
    "2023": f"{DCGIS}/DCGIS_DATA/ServiceRequests/FeatureServer/15",
    "2024": f"{DCGIS}/DCGIS_DATA/ServiceRequests/FeatureServer/16",
    "2025": f"{DCGIS}/DCGIS_DATA/ServiceRequests/FeatureServer/18",
    "2026": f"{DCGIS}/DCGIS_DATA/ServiceRequests/FeatureServer/21",
}


class TestDcSpatial:
    def _module(self):
        from src.spatial.cities import washington_dc as dc

        return dc

    def test_metro_bbox_covers_live_samples(self):
        dc = self._module()
        assert dc.is_in_dc_metro(38.92595847, -77.07651245)   # permits sample
        assert dc.is_in_dc_metro(38.9509324, -77.06956514)    # 311 sample
        assert dc.is_in_dc_metro(38.8676, -76.9846)           # Anacostia HD

    def test_is_in_rejects_missing_coordinates(self):
        assert self._module().is_in_dc_metro(None, None) is False

    def test_alias(self):
        from src.spatial.cities.washington_dc import (
            is_in_dc_metro,
            is_in_washington_dc_metro,
        )

        assert is_in_washington_dc_metro is is_in_dc_metro

    def test_is_in_rejects_other_cities(self):
        dc = self._module()
        assert dc.is_in_dc_metro(47.6062, -122.3321) is False   # Seattle
        assert dc.is_in_dc_metro(42.3314, -83.0458) is False    # Detroit
        # The SLA feed's live sentinel junk row: LATITUDE=39, LONGITUDE=-77.
        assert dc.is_in_dc_metro(39.0, -77.0) is False

    def test_division_count_and_nesting(self):
        dc = self._module()
        assert len(dc.DC_DIVISION_BBOXES) == 8
        for name, bbox in dc.DC_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= dc.DC_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= dc.DC_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= dc.DC_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= dc.DC_METRO_BBOX["max_lng"], name

    def test_submarkets_sit_inside_their_division(self):
        dc = self._module()
        assert 15 <= len(dc.DC_SUBMARKETS) <= 18
        for name, meta in dc.DC_SUBMARKETS.items():
            bbox = dc.DC_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_exactly_once(self):
        dc = self._module()
        claimed = [s for d in dc.DC_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(dc.DC_SUBMARKETS)

    def test_city_id_consistency(self):
        dc = self._module()
        assert {m.city_id for m in dc.DC_SUBMARKETS.values()} == {"washington_dc"}
        assert {d.city_id for d in dc.DC_DIVISIONS.values()} == {"washington_dc"}


class TestResolveEndpointYearSlicing:
    """The D3 mechanism DC's year-sliced feeds plug into (already on spine)."""

    def _spec(self, by_year, endpoint="fallback"):
        return SimpleNamespace(endpoint=endpoint, endpoint_by_year=by_year)

    def test_resolves_current_year_layer(self):
        import datetime as dt

        spec = self._spec(PERMITS_BY_YEAR)
        assert (
            resolve_endpoint(spec, dt.date(2026, 8, 23))
            == PERMITS_BY_YEAR["2026"]
        )

    def test_rollover_falls_back_to_newest_past_year(self):
        """New Year rollover: before the ETL publishes a 2027 layer, resolution
        steps back to 2026 instead of failing."""
        import datetime as dt

        spec = self._spec(PERMITS_BY_YEAR)
        assert (
            resolve_endpoint(spec, dt.date(2027, 1, 1))
            == PERMITS_BY_YEAR["2026"]
        )


class TestWashingtonDcRegistration:
    """RED until the orchestrator applies the spine (expected)."""

    def test_registered_under_washington_dc_enum_name(self):
        from src.spatial.city_registry import REGISTRY, CityId

        assert CityId.WASHINGTON_DC.value == "washington_dc"
        assert CityId.WASHINGTON_DC in REGISTRY

    @pytest.mark.parametrize("alias", ["washington_dc", "dc", "district_of_columbia"])
    def test_aliases_resolve(self, alias):
        from src.spatial.city_registry import ALIASES, CityId

        assert ALIASES.get(alias) is CityId.WASHINGTON_DC

    def test_registration_shape(self):
        from src.spatial.cities.washington_dc import (
            DC_DIVISIONS,
            DC_METRO_BBOX,
            DC_SUBMARKETS,
        )
        from src.spatial.city_registry import REGISTRY, CityId

        reg = REGISTRY[CityId.WASHINGTON_DC]
        assert reg.state == "DC"
        assert reg.job_suffix == "dc"
        assert reg.submarkets is DC_SUBMARKETS
        assert reg.divisions is DC_DIVISIONS
        assert reg.metro_bbox is DC_METRO_BBOX
        assert len(reg.divisions) == 8

    def test_registered_feeds_preserve_original_arcgis_contract(self):
        from src.spatial.city_registry import REGISTRY, CityId, FeedType

        datasets = REGISTRY[CityId.WASHINGTON_DC].datasets
        original_feeds = {
            FeedType.PERMITS,
            FeedType.COMPLAINTS_311,
            FeedType.SLA,
            FeedType.DEEDS,
        }
        assert original_feeds <= set(datasets)
        for feed in original_feeds:
            assert datasets[feed].platform == "arcgis", feed
        assert datasets[FeedType.GBFS].platform == "gbfs"

    def test_job_names_are_namespaced(self):
        from src.spatial.city_registry import CityId, FeedType

        assert get_job_name(FeedType.PERMITS, CityId.WASHINGTON_DC) == "permits_dc"

    def test_watermarks_match_published_schemas(self):
        """All four watermark columns verified against live layer metadata
        2026-08-23 (esriFieldTypeDate fields)."""
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        assert get_dataset(CityId.WASHINGTON_DC, FeedType.PERMITS).watermark_col == "ISSUE_DATE"
        assert get_dataset(CityId.WASHINGTON_DC, FeedType.COMPLAINTS_311).watermark_col == "ADDDATE"
        assert get_dataset(CityId.WASHINGTON_DC, FeedType.SLA).watermark_col == "INITIALISSUEDATE"
        assert get_dataset(CityId.WASHINGTON_DC, FeedType.DEEDS).watermark_col == "SALE_DATE"

    @pytest.mark.parametrize(
        ("feed", "by_year"),
        [
            (FeedType.PERMITS, PERMITS_BY_YEAR),
            (FeedType.COMPLAINTS_311, THREE11_BY_YEAR),
        ],
    )
    def test_year_sliced_feeds_carry_endpoint_by_year_maps(self, feed, by_year):
        from src.spatial.city_registry import CityId, get_dataset

        spec = get_dataset(CityId.WASHINGTON_DC, feed)
        extra_years = spec.endpoint_by_year
        assert len(extra_years) >= 2
        current = str(__import__("datetime").date.today().year)
        assert extra_years[current] == by_year[current]
        for year, url in extra_years.items():
            assert url.startswith(DCGIS), year

    def test_oid_field_and_page_caps_pinned(self):
        """objectIdField is OBJECTID everywhere; maxRecordCount is 2000 on
        FEEDS/DCRA and Property_and_Land, 1000 on ServiceRequests (live layer
        JSON, 2026-08-23)."""
        from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset

        dc = CityId.WASHINGTON_DC
        for feed in set(REGISTRY[dc].datasets) - {FeedType.GBFS}:
            spec = get_dataset(dc, feed)
            assert spec.oid_field == "OBJECTID", feed
        assert get_dataset(dc, FeedType.PERMITS).max_record_count == 2000
        assert get_dataset(dc, FeedType.SLA).max_record_count == 2000
        assert get_dataset(dc, FeedType.DEEDS).max_record_count == 2000
        assert get_dataset(dc, FeedType.COMPLAINTS_311).max_record_count == 1000

    def test_sla_declares_geocoded_premises_contract(self):
        """US-74: SLA upgrades from non_spatial to address-string geocoding
        (ADR 0004). RED until the spine swaps the extra dict — the registry
        still carries non_spatial=True."""
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        extra = get_dataset(CityId.WASHINGTON_DC, FeedType.SLA)
        assert extra.needs_geocode is True
        assert extra.geocode_context == "Washington, DC"
        assert extra.expected_cadence_days or 0 >= 1
        assert extra.non_spatial is not True
        assert extra.field_map["address_street"] == ["PREMISEADDRESS"]

    def test_sla_field_map_never_bridges_sentinel_coordinate_columns(self):
        """The layer's LATITUDE/LONGITUDE columns hold null or the sentinel
        pair 39/-77 on every sampled row (300-row windows, 2026-08-24) —
        mapping them would file DC licenses under an H3 cell in Pennsylvania.
        Holds pre-spine (nothing mapped) and must hold after it."""
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        field_map = get_dataset(CityId.WASHINGTON_DC, FeedType.SLA).field_map
        for canonical, keys in field_map.items():
            assert "LATITUDE" not in keys, canonical
            assert "LONGITUDE" not in keys, canonical

    def test_deeds_declares_parcel_join_for_non_addressable_cama_rows(self):
        """US-74 finding: the CAMA sales layer publishes ZERO address-like
        fields (metadata + 300-newest-row field union, 2026-08-24), so no
        pure-address geocoding contract can be declared. The parcel-key SSL
        is joined to Parcel Lots before parsing instead."""
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        extra = get_dataset(CityId.WASHINGTON_DC, FeedType.DEEDS)
        assert extra.non_spatial is not True
        assert extra.parcel_join["join_key"] == "SSL"
        assert extra.parcel_join["geometry_source"] == "centroid"
        assert extra.needs_geocode is not True
        assert any(
            "ssl" in str(v).lower() for v in (extra.field_map or {}).values()
        )


# ---------------------------------------------------------------------------
# Parser fixtures — REAL attribute dicts pulled via REST on 2026-08-23
# (`query?f=json&where=1=1&outFields=*&orderByFields=<col> DESC`), exactly the
# flat dicts ArcGISClient._flatten_feature hands to producers.
# ---------------------------------------------------------------------------

DC_FIELD_MAPS = {
    FeedType.PERMITS: {
        "job_id": ["PERMIT_ID"],
        "latitude": ["LATITUDE"],
        "longitude": ["LONGITUDE"],
        "issuance_date": ["ISSUE_DATE"],
        "job_type": ["PERMIT_TYPE_NAME", "PERMIT_SUBTYPE_NAME"],
        "cost": ["FEES_PAID"],
        "borough": ["WARD"],
        "zipcode": ["ZIPCODE"],
    },
    FeedType.COMPLAINTS_311: {
        "incident_id": ["SERVICEREQUESTID"],
        "latitude": ["LATITUDE"],
        "longitude": ["LONGITUDE"],
        "complaint_type": ["SERVICECODEDESCRIPTION"],
        "created_date": ["ADDDATE"],
        "closed_date": ["RESOLUTIONDATE"],
        "status": ["SERVICEORDERSTATUS"],
        "incident_address": ["STREETADDRESS"],
        "borough": ["WARD"],
        "zipcode": ["ZIPCODE"],
    },
    FeedType.SLA: {
        "license_id": ["CUSTOMERNUMBER"],
        "license_type": ["LICENSETYPE"],
        "effective_date": ["LICENSESTARTDATE"],
        "expiration_date": ["LICENSEENDDATE"],
        "borough": ["WARD"],
        # US-74: premises address only. BILLINGADDRESS is a mailing address
        # and must never feed the geocoder; LATITUDE/LONGITUDE stay unmapped
        # (null/sentinel 39/-77 junk).
        "address_street": ["PREMISEADDRESS"],
    },
    FeedType.DEEDS: {
        "doc_id": ["ROW_NUMBER"],
        "bbl": ["SSL"],
        "document_amount": ["SALE_PRICE"],
        "recorded_date": ["SALE_DATE"],
        "doc_type": ["QUALIFIED"],
    },
}


class DcParsingBase:
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
        # Live newest-by-ISSUE_DATE row from FEEDS/DCRA/FeatureServer/18
        # (2026-08-23). Epoch-ms dates; uppercase coordinate attributes.
        return {
            "DCRAINTERNALNUMBER": 112606425.0,
            # ArcGISClient._flatten_feature converts epoch-ms date fields to
            # isoformat strings before producers see them — fixtures mirror
            # that post-client shape.
            "ISSUE_DATE": "2026-08-17T04:00:00+00:00",
            "PERMIT_ID": "B2606425",
            "PERMIT_TYPE_NAME": "CONSTRUCTION",
            "PERMIT_SUBTYPE_NAME": "ALTERATION AND REPAIR",
            "PERMIT_CATEGORY_NAME": "NA",
            "APPLICATION_STATUS_NAME": "PERMIT ISSUED",
            "FULL_ADDRESS": "3836 FULTON ST NW, WASHINGTON, DC 20007",
            "DESC_OF_WORK": "Removal of partition walls, new beams and posts.",
            "SSL": "1812    0032",
            "ZONING": "R-2",
            "FEES_PAID": 655,
            "OWNER_NAME": "PAULSON, ELIZABETH M",
            "LATITUDE": 38.92595847,
            "LONGITUDE": -77.07651245,
            "XCOORD": 393365.43,
            "YCOORD": 139789.65,
            "ZIPCODE": None,
            "WARD": "3",
            "OBJECTID": 1139527956,
        }

    @pytest.fixture
    def complaint_row(self):
        # Live newest-by-ADDDATE row from ServiceRequests/FeatureServer/21
        # (2026-08-23).
        return {
            "SERVICEREQUESTID": "26-00503166",
            "STREETADDRESS": "3547 CHESAPEAKE STREET NW",
            "ZIPCODE": 20008,
            "SERVICECODEDESCRIPTION": "Dockless Vehicle Parking Complaint",
            "ORGANIZATIONACRONYM": "DDOT",
            "ADDDATE": "2026-08-23T23:41:34+00:00",
            "RESOLUTIONDATE": None,
            "SERVICEORDERSTATUS": "Open",
            "PRIORITY": "Standard",
            "WARD": "Ward 3",
            "LATITUDE": 38.9509324,
            "LONGITUDE": -77.06956514,
            "OBJECTID": 12746894,
        }

    @pytest.fixture
    def sla_row(self):
        # Live newest-by-INITIALISSUEDATE row with NULL coordinates from
        # FEEDS/DCRA/FeatureServer/0 (2026-08-23). Note PREMISEINDC="No" —
        # out-of-state license rows exist and upstream filtering should use it.
        return {
            "CUSTOMERNUMBER": "410526000684",
            "LICENSESTATUS": "Active",
            "LICENSETYPE": "Business License",
            "LICENSESTATUSDATE": "2026-08-06T04:00:00+00:00",
            "LICENSESTARTDATE": "2026-08-06T04:00:00+00:00",
            "LICENSEENDDATE": "2028-08-31T04:00:00+00:00",
            "INITIALISSUEDATE": "2026-08-06T04:00:00+00:00",
            "BUSINESSACTIVITY": "General Contractor/Construction Manager (A, B, C, ",
            "PREMISEADDRESS": "4210 Deer Park RD, Randallstown, MD, 21133, USA",
            "PREMISEINDC": "No",
            "ENTITYNAME": "PREMIUM HOME PRO LLC",
            "CATEGORYSERVICETYPE": "Contractor and Construction Services",
            "LATITUDE": None,
            "LONGITUDE": None,
            "SSL": None,
            "OBJECTID": 3001457,
        }

    @pytest.fixture
    def deed_row(self):
        # Live newest-by-SALE_DATE row from Property_and_Land_WebMercator/
        # FeatureServer/57 (2026-08-23). NO coordinate fields at all.
        return {
            "OBJECTID": 483608734,
            "ROW_NUMBER": 414660,
            "SSL": "6093    0808",
            "SALE_DATE": "2026-08-12T04:00:00+00:00",
            "SALE_PRICE": 496000.0,
            "QUALIFIED": "Q",
            "SALE_CODE": "01",
            "SALE_CURR_OWNER": "1",
            "GIS_LAST_MOD_DTTM": 1787303797000,
        }


class TestDcChainsToday(DcParsingBase):
    """Bare fallback chains, no registry map (rows arriving before the spine).
    UPPERCASE coordinate/id spellings match nothing in the lowercase chains —
    pins what breaks without field_map entries."""

    def test_permit_rows_are_dropped_by_bare_chains(self, permits, permit_row):
        """PERMIT_ID matches NO id chain term — the whole row is dropped by
        the id guard before the spine's field_map lands."""
        assert permits.parse_socrata_row(permit_row, city_id="austin") is None

    def test_311_rows_are_dropped_by_bare_chains(self, complaints, complaint_row):
        assert complaints.parse_socrata_row(complaint_row, city_id="austin") is None


class TestDcWithProposedFieldMap(DcParsingBase):
    """Patches resolve_field_map to hand back the EXACT maps proposed in
    .streams/city-dc.md, proving they resolve every DC spelling before the
    spine lands."""

    @pytest.fixture(autouse=True)
    def _proposed_maps(self, monkeypatch):
        import src.producers.field_maps as fm

        monkeypatch.setattr(
            fm,
            "resolve_field_map",
            lambda city_value, feed: DC_FIELD_MAPS.get(feed, {}),
            raising=True,
        )

    # -- PERMITS -------------------------------------------------------------

    def test_permit_reads_uppercase_coordinate_attributes(self, permits, permit_row):
        """PINNED QUIRK: coords are LATITUDE/LONGITUDE (uppercase); only the
        proposed field_map entries bridge them to the lowercase chains."""
        ev = permits.parse_socrata_row(permit_row, city_id="washington_dc")
        assert ev.latitude == pytest.approx(38.92595847)
        assert ev.longitude == pytest.approx(-77.07651245)

    def test_permit_epoch_dates_convert(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="washington_dc")
        assert str(ev.issuance_date).startswith("2026-08-17")

    def test_permit_id_type_and_cost_from_proposed_map(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="washington_dc")
        assert ev.job_id == "B2606425"
        # job_type normalizes to the JobType enum — "CONSTRUCTION" falls to
        # the OT bucket, but must not be None.
        assert ev.job_type is not None
        assert ev.estimated_cost == 655.0

    def test_permit_resolves_inside_the_dc_bbox(self, permits, permit_row):
        from src.spatial.cities.washington_dc import is_in_dc_metro

        ev = permits.parse_socrata_row(permit_row, city_id="washington_dc")
        assert is_in_dc_metro(ev.latitude, ev.longitude)

    # -- 311 ------------------------------------------------------------------

    def test_311_reads_uppercase_attributes(self, complaints, complaint_row):
        ev = complaints.parse_socrata_row(complaint_row, city_id="washington_dc")
        assert ev.latitude == pytest.approx(38.9509324)
        assert ev.longitude == pytest.approx(-77.06956514)

    def test_311_type_created_status_through_map(self, complaints, complaint_row):
        ev = complaints.parse_socrata_row(complaint_row, city_id="washington_dc")
        assert ev.incident_id == "26-00503166"
        assert ev.complaint_type == "Dockless Vehicle Parking Complaint"
        assert str(ev.created_date).startswith("2026-08-23")
        assert ev.status == "Open"

    def test_311_open_request_has_no_closed_date(self, complaints, complaint_row):
        ev = complaints.parse_socrata_row(complaint_row, city_id="washington_dc")
        assert ev.closed_date is None

    def test_311_rejects_null_island_placeholder(self, complaints, complaint_row):
        complaint_row["LATITUDE"] = 0.0
        complaint_row["LONGITUDE"] = 0.0
        assert complaints.parse_socrata_row(complaint_row, city_id="washington_dc") is None

    # -- DEEDS (parcel-joined) ---------------------------------------------------

    def test_deed_events_carry_null_coordinates_and_h3(self, deeds, deed_row):
        """Property Sales CAMA carries NO coordinate fields AND no address
        fields (US-74 verified the field union over 300 newest rows) — SSL
        parcel key only. Events parse with null lat/lng/H3; DeedEvent's Avro
        lat/lng are nullable unions so these serialize and reach the topic
        (no DLQ). Direct parser calls without enrichment retain null geometry."""
        ev = deeds.parse_socrata_row(deed_row, city_id="washington_dc")
        assert ev.doc_id == "414660"
        assert ev.bbl == "6093    0808"
        assert ev.document_amount == 496000.0
        assert ev.latitude is None
        assert ev.longitude is None
        assert ev.h3_res9 is None

    def test_deed_sale_date_parses_from_epoch_ms(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="washington_dc")
        assert str(ev.recorded_date).startswith("2026-08-12")

    def test_deeds_declares_ssl_parcel_centroid_join(self):
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        extra = get_dataset(CityId.WASHINGTON_DC, FeedType.DEEDS)
        assert extra.non_spatial is not True
        assert extra.parcel_join == {
            "parcel_layer": f"{DCGIS}/DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/33",
            "join_key": "SSL",
            "geometry_source": "centroid",
        }


GEOCODED_ANSWERS = {
    # Live premises strings -> census-quality coordinates captured 2026-08-24
    # through the real Census backend (conf 1.0).
    "915 ELDER ST NW, Washington, DC, 20012, USA": (38.977339493805, -77.025759511774),
    "4210 Deer Park RD, Randallstown, MD, 21133, USA": (39.38644, -76.827902),
}


class TestDcGeocodedSlaParsing(DcParsingBase):
    """US-74: SLA rows resolve PREMISEADDRESS at parse time for specs
    declaring needs_geocode (ADR 0004), mirroring Norfolk's 311 contract.

    The geocoder stub bypasses the registry's declaration gate, so these
    parser pins run green before the spine lands; the registration-side
    counterpart lives in TestWashingtonDcRegistration."""

    @pytest.fixture(autouse=True)
    def _geocoded_contract(self, monkeypatch):
        import src.producers.field_maps as fm

        monkeypatch.setattr(
            fm,
            "resolve_field_map",
            lambda city_value, feed: DC_FIELD_MAPS.get(feed, {}),
            raising=True,
        )
        self.calls = []

        def fake_resolve(city_id, feed_value, address, context=None):
            self.calls.append((city_id, feed_value, address, context))
            return GEOCODED_ANSWERS.get(address)

        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared", fake_resolve
        )

    @pytest.fixture
    def in_dc_license_row(self):
        # Live newest-by-OBJECTID row from FEEDS/DCRA/FeatureServer/0
        # (2026-08-24): in-DC premises, VA mailing billing address, sentinel
        # LATITUDE/LONGITUDE junk — the exact shape the geocode path must
        # handle. Dates mirror ArcGISClient._flatten_feature isoformat output.
        return {
            "CUSTOMERNUMBER": "500521801716",
            "LICENSESTATUS": "Expired - Enforcement",
            "LICENSETYPE": "Business License",
            "LICENSESTATUSDATE": "2025-10-02T04:00:00+00:00",
            "LICENSESTARTDATE": "2020-12-01T05:00:00+00:00",
            "LICENSEENDDATE": "2022-11-30T05:00:00+00:00",
            "INITIALISSUEDATE": "2020-12-02T05:00:00+00:00",
            "BUSINESSACTIVITY": "One Family Rental",
            "PREMISEADDRESS": "915 ELDER ST NW, Washington, DC, 20012, USA",
            "PREMISEINDC": "Yes",
            "ENTITYNAME": "FENGYONG LIN",
            "ENTITYTRADENAME": None,
            "CATEGORYSERVICETYPE": "Housing and Lodging Services",
            "BILLINGADDRESS": "1350 Beverly Road #115-345, MCLEAN, VA, 22101, USA",
            "WARD": "Ward 4",
            "MAR_ID": 314089.0,
            "SSL": "2964    0061,2964    2059,2964    2058,2964    2060",
            "LATITUDE": 39,
            "LONGITUDE": -77,
            "OBJECTID": 3608719,
        }

    def test_in_dc_premises_geocodes_at_parse_with_h3(self, sla, in_dc_license_row):
        ev = sla.parse_socrata_row(in_dc_license_row, city_id="washington_dc")
        assert ev is not None
        assert ev.license_id == "500521801716"
        assert ev.latitude == pytest.approx(38.977339493805)
        assert ev.longitude == pytest.approx(-77.025759511774)
        assert ev.h3_res7 is not None
        assert ev.h3_res8 is not None
        assert ev.h3_res9 is not None
        assert self.calls == [
            ("washington_dc", "sla", "915 ELDER ST NW, Washington, DC, 20012, USA", None)
        ]

    def test_billing_address_is_never_geocoded(self, sla, in_dc_license_row):
        """BILLINGADDRESS is a mailing address (this live row bills to
        McLean, VA) — only PREMISEADDRESS may feed the geocoder."""
        sla.parse_socrata_row(in_dc_license_row, city_id="washington_dc")
        assert all("MCLEAN" not in str(call[2]) for call in self.calls)

    def test_dates_still_map_on_geocoded_rows(self, sla, in_dc_license_row):
        ev = sla.parse_socrata_row(in_dc_license_row, city_id="washington_dc")
        assert str(ev.effective_date).startswith("2020-12-01")
        assert str(ev.expiration_date).startswith("2022-11-30")
        assert ev.license_type == "Business License"

    def test_sentinel_coordinate_columns_never_leak_into_events(
        self, sla, in_dc_license_row
    ):
        """The layer's own LATITUDE=39/LONGITUDE=-77 junk must lose to the
        geocoded premises point — events carry resolved coords, not sentinels."""
        ev = sla.parse_socrata_row(in_dc_license_row, city_id="washington_dc")
        assert ev.latitude != 39
        assert ev.longitude != -77
        assert ev.h3_res9 is not None

    def test_out_of_state_premises_flows_to_geocoder_verbatim(
        self, sla, sla_row, monkeypatch
    ):
        """PREMISEINDC='No' rows (~24% of the watermark window) license
        premises OUTSIDE DC. The premises string is still the site address,
        so it geocodes to its true location; whether to filter those rows
        upstream is a separate spine decision."""
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (
                GEOCODED_ANSWERS.get(address) if address else None
            ),
        )
        ev = sla.parse_socrata_row(sla_row, city_id="washington_dc")
        assert ev is not None
        assert ev.latitude == pytest.approx(39.38644)
        assert ev.longitude == pytest.approx(-76.827902)

    def test_missing_address_yields_null_coord_event(self, sla, sla_row):
        """Rows without any address candidate parse through the producer's
        coordinate-less tolerance as null-lat/lng/null-H3 events — but SLA's
        Avro doubles are NON-null, so they DLQ at produce time. Every point
        of address completeness is G5' headroom."""
        sla_row["PREMISEADDRESS"] = None
        ev = sla.parse_socrata_row(sla_row, city_id="washington_dc")
        assert ev is not None
        assert ev.latitude is None
        assert ev.longitude is None
        assert ev.h3_res7 is None
        assert ev.h3_res9 is None

    def test_geocode_failure_falls_back_to_null_coord_event(
        self, sla, in_dc_license_row, monkeypatch
    ):
        """An unresolvable premises string must degrade to the null-coord
        event, never kill parsing or fabricate coordinates."""
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        ev = sla.parse_socrata_row(in_dc_license_row, city_id="washington_dc")
        assert ev is not None
        assert ev.latitude is None
        assert ev.longitude is None
        assert ev.h3_res7 is None
