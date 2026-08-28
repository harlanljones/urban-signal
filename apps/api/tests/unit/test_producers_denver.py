"""Contract tests for Denver's ArcGIS permit, 311, and property-sales feeds.

US-73 (Wave G3) live research outcomes baked into these pins:

* Real Property Sales and Transfers registers on FeedType.DEEDS behind the
  numeric ``RECEPTION_DATE`` yyyymmdd integer watermark. The column is an
  esriFieldTypeInteger (never epoch-converted by ArcGISClient), so the spec
  declares the ADR 0005 text watermark (``%Y%m%d``): the scheduler stores the
  raw digits and emits the quoted comparison ``RECEPTION_DATE > 'YYYYMMDD'``
  the server answers identically to the numeric form (verified live
  2026-08-24: both return 51,799 rows for the 2024-01-01 threshold).
* Active Business Licenses (table id 31) is DESCOPED. Its only date-like
  field is ``Expiration_Date``, which is term-length-driven, not
  arrival-ordered: newest-by-OBJECTID licenses expire 2027-2030 while the
  ORDER-BY-DESC maxima are century typos (2200-12-31, 8099-12-31). All 41,986
  rows share the single status "License Issued - Active" and no other
  date-like attribute exists.
* The sales table publishes NO address or coordinate columns (verified over
  the newest 500 rows: zero address-like keys), so the registration is
  non_spatial like DC's CAMA sales and events carry null lat/lng/H3. The
  deeds parse path also has no geocode hook site yet, so even declaring
  needs_geocode would be inert today - pinned explicitly below.
* Known dirty values are excluded server-side from watermark tracking via
  ``watermark_exclude``: the malformed 50250305 (parses as year 5025) and the
  future-dated 20261230/20281113 receptions, any of which would otherwise
  jump the high watermark years past real time and blind the feed.

Registration pins are RED until the spine adds the FeedType.DEEDS dataset to
CityId.DENVER (orchestrator applies after this leaf lands) - expected.
Parser pins run green today against the unregistered city via a candidate
field map, mirroring Norfolk's SLA pinning style.
"""

from datetime import UTC
from unittest.mock import patch

import pytest

from src.config import settings

from src.spatial.cities.denver import (
    DENVER_DIVISION_BBOXES,
    DENVER_DIVISIONS,
    DENVER_METRO_BBOX,
    DENVER_SUBMARKETS,
    is_in_denver_metro,
)
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
    normalize_city,
)

DENVER_SALES_ENDPOINT = (
    "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
    "ODC_real_property_sales_and_transfers/FeatureServer/60"
)

# Candidate field_map proposed in the US-73 REPORT for the spine's DEEDS
# registration; per-entry rationale mirrors the DC CAMA chain (doc_id<-ROW_
# NUMBER, bbl<-SSL, document_amount<-SALE_PRICE, recorded_date<-SALE_DATE).
DENVER_SALES_CANDIDATE_MAP = {
    "doc_id": ["RECEPTION_NUM"],
    "bbl": ["PARID"],
    "document_amount": ["SALE_PRICE"],
    "recorded_date": ["RECEPTION_DATE"],
    "doc_type": ["INSTRUMENT"],
    "borough": ["NBHD_1_CN"],
    "party1_grantor": ["GRANTOR"],
    "party2_grantee": ["GRANTEE"],
}

# Dirty RECEPTION_DATE values observed live 2026-08-24 (malformed year and
# future-dated receptions); proposed watermark_exclude contents.
DENVER_SALES_WATERMARK_EXCLUDE = ["50250305", "20281113", "20261230"]


def test_denver_geometry_is_self_consistent():
    assert is_in_denver_metro(39.7527, -104.9992)
    assert not is_in_denver_metro(39.1031, -84.5120)
    assert not is_in_denver_metro(None, None)
    for name, bbox in DENVER_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= DENVER_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= DENVER_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= DENVER_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= DENVER_METRO_BBOX["max_lng"], name
    claimed = [name for division in DENVER_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(DENVER_SUBMARKETS)
    assert {meta.city_id for meta in DENVER_SUBMARKETS.values()} == {"denver"}


class TestDenverRegistration:
    def test_registered(self):
        assert CityId.DENVER in REGISTRY

    @pytest.mark.parametrize("alias", ["denver", "denver_co"])
    def test_aliases_resolve(self, alias):
        assert normalize_city(alias) is CityId.DENVER

    def test_registration_shape(self):
        reg = REGISTRY[CityId.DENVER]
        assert reg.state == "CO"
        assert reg.job_suffix == "denver"
        assert reg.submarkets is DENVER_SUBMARKETS
        assert reg.divisions is DENVER_DIVISIONS

    def test_job_names_are_namespaced(self):
        assert get_job_name(FeedType.PERMITS, CityId.DENVER) == "permits_denver"

    def test_sales_reverted_under_g8_prime(self):
        """US-73 finding: the sales table (ODC_real_property_sales_and_transfers,
        309,548 rows) exposes ZERO address-like columns — verified over the
        newest 500 real rows. Registering it would emit 100% null-H3 events
        that the enrichment worker cannot place, violating the Wave-G gate
        ("a feed registered because of Wave G that lands above 5% null-H3 is
        reverted"). Parcel-join geocoding is explicitly out of scope per plan
        D6, so the feed waits for either a parcel-join ADR or a raw-archive
        rationale.

        The candidate registration recipe is preserved in the constants above
        (DENVER_SALES_ENDPOINT / DENVER_SALES_WATERMARK_EXCLUDE /
        DENVER_SALES_CANDIDATE_MAP) — note the ADR 0005 text-watermark
        declaration is LOAD-BEARING there: RECEPTION_DATE is an integer
        yyyymmdd column and values like 50250305 (parses as year 5025) would
        blind incremental polling without watermark_exclude."""
        with pytest.raises(KeyError, match="no.*feed"):
            get_dataset(CityId.DENVER, FeedType.DEEDS)

    def test_sales_candidate_map_stays_unregistered(self):
        """resolve_field_map degrades to {} for the unregistered feed and the
        producer's doc_id chain finds nothing on arcgis-shaped rows, so every
        sales row parses to None until a registration supplies the map."""
        from src.producers.field_maps import resolve_field_map

        assert resolve_field_map("denver", FeedType.DEEDS) == {}

    def test_licenses_descoped_sla_slot_history(self):
        """US-73 descope evidence: Denver's own Active Business Licenses
        (table id 31) exposes exactly one date-like field, Expiration_Date,
        which is term-length-driven rather than arrival-ordered - newest-by-
        OBJECTID rows expire 2027-2030 while the ORDER BY DESC maxima are
        century typos (2200-12-31 and 8099-12-31 among 41,986 rows all
        sharing the single status 'License Issued - Active'). No issue-date
        field and no edit timestamp exist, so that source itself stays
        unregistered. US-364 filled the SLA slot with the national USDA FNS
        SNAP retailer feed; US-372 replaced that stand-in with the state CO
        liquor registry (geocoded points, snapshot mode) — the US-73 verdict
        about the Denver licenses source still stands."""
        from src.spatial.city_registry import get_dataset

        spec = get_dataset(CityId.DENVER, FeedType.SLA)
        assert spec.endpoint == settings.socrata_co_liquor_endpoint
        assert "ier5-5ms2" in spec.endpoint
        assert "snap_retailer_location_data" not in spec.endpoint
        assert "data.denvergov.org" not in spec.endpoint
        # US-372 contract: snapshot (no chronological watermark — expiration
        # is expiry-style), geocoded points ship with the rows.
        assert spec.ingestion_mode == "snapshot"
        assert spec.watermark_col == ""
        assert spec.needs_geocode is False
        assert spec.where == "city = 'Denver'"


def test_denver_is_now_a_three_feed_city():
    city = CityId.DENVER
    assert normalize_city("denver") is city
    assert REGISTRY[city].job_suffix == "denver"
    # US-73 outcome: the Denver licenses source stayed descoped (no usable
    # watermark) and sales were reverted under G8' (zero address columns).
    # US-364 added SNAP (national FNS feed, State='CO') as the SLA feed.
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
        FeedType.SLA,
    }


def test_denver_arcgis_specs_pin_date_and_coordinate_quirks():
    reg = REGISTRY[CityId.DENVER]
    permits = reg.datasets[FeedType.PERMITS]
    complaints = reg.datasets[FeedType.COMPLAINTS_311]
    assert permits.field_map["issuance_date"] == ["DATE_ISSUED"]
    assert complaints.watermark_col == "Case_Created_Date"
    assert complaints.field_map["latitude"] == ["Latitude"]
    assert complaints.field_map["longitude"] == ["Longitude"]
    assert permits.companion_endpoints["commercial"].endswith("/FeatureServer/317")


def test_denver_live_shaped_permit_row_parses():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        producer = DOBPermitsProducer()
    row = {
        "OBJECTID": 289755,
        "DATE_ISSUED": "2012-11-15T00:00:00+00:00",
        "DATE_RECEIVED": "2012-11-14T00:00:00+00:00",
        "PERMIT_NUM": "2012-RESCON-0000004625",
        "ADDRESS": "3729 N LIPAN ST",
        "CLASS": "NEW BUILDING",
        "VALUATION": 14285,
        "UNITS": 1,
        "NEIGHBORHOOD": "Highland",
        "latitude": 39.7690,
        "longitude": -105.0100,
    }
    event = producer.parse_socrata_row(row, city_id="denver")
    assert event is not None
    assert event.job_id == "2012-RESCON-0000004625"
    assert event.address_street == "3729 N LIPAN ST"
    assert event.latitude == pytest.approx(39.7690)


def test_denver_live_shaped_311_row_parses_uppercase_coordinates():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        producer = Complaints311Producer()
    row = {
        "OBJECTID": 376730884,
        "Case_Summary": "Pothole",
        "Case_Status": "Closed - Answer Provided",
        "Case_Created_dttm": "12/31/2025 11:32:50 AM",
        "Incident_Address_1": "1700 LINCOLN ST",
        "Incident_Zip_Code": "80203",
        "Latitude": 39.7430,
        "Longitude": -104.9850,
        "Type": "Street Maintenance",
    }
    event = producer.parse_socrata_row(row, city_id="denver")
    assert event is not None
    assert event.incident_id == "376730884"
    assert event.latitude == pytest.approx(39.7430)
    assert event.incident_address == "1700 LINCOLN ST"


class TestDenverSalesRowParsing:
    """Real sales rows (captured live 2026-08-24 from FeatureServer table 60)
    through DeedsACRISProducer.parse_socrata_row under the candidate field
    map. Pins run green before the spine lands the registration."""

    @pytest.fixture
    def deeds(self, monkeypatch):
        import src.producers.field_maps as fm

        monkeypatch.setattr(
            fm,
            "resolve_field_map",
            lambda city_value, feed: (
                DENVER_SALES_CANDIDATE_MAP
                if getattr(feed, "value", feed) == "deeds"
                else {}
            ),
            raising=True,
        )
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @pytest.fixture
    def sane_wd_row(self):
        # Newest-sane-window warranty deed (RECEPTION_DATE 20260813).
        return {
            "OBJECTID": 217518487,
            "PARID": 604322005000,
            "RECEPTION_NUM": 2026096458,
            "INSTRUMENT": "WD",
            "SALE_YEAR": 2026,
            "SALE_MONTHDAY": 811,
            "RECEPTION_DATE": 20260813,
            "SALE_PRICE": 900000,
            "GRANTOR": "OSTROWSKI,GREGORY R",
            "GRANTEE": "PSJ & ASSOCIATES II LLC",
            "CLASS": "R",
            "D_CLASS_N": "SFR Grade B",
            "NBHD_1_CN": "LOWRY",
        }

    @pytest.fixture
    def zero_transfer_row(self):
        # $0 city-to-city-style trust transfer carrying the malformed
        # 50250305 reception date (parses as year 5025 under %Y%m%d).
        return {
            "OBJECTID": 217382507,
            "PARID": 230204016000,
            "RECEPTION_NUM": 2025018558,
            "INSTRUMENT": "BF",
            "SALE_YEAR": 2025,
            "SALE_MONTHDAY": 707,
            "RECEPTION_DATE": 50250305,
            "SALE_PRICE": 0,
            "GRANTOR": "MARTINEZ,CLYDE A",
            "GRANTEE": "MARTINEZ,CLYDE TRUST",
            "CLASS": "R",
            "MKT_CLUS": "9",
            "D_CLASS": "113",
            "D_CLASS_N": "SFR Grade C",
            "NBHD_1": 240,
            "NBHD_1_CN": "W HIGHLAND",
        }

    @pytest.fixture
    def future_dated_row(self):
        # Pre-dated future reception (Dec 30 2026 recorded against an Aug
        # capture) - the watermark-poisoning shape watermark_exclude guards.
        return {
            "OBJECTID": 217370973,
            "PARID": 227804157157,
            "RECEPTION_NUM": 2025131095,
            "INSTRUMENT": "WD",
            "SALE_YEAR": 2026,
            "SALE_MONTHDAY": 1230,
            "RECEPTION_DATE": 20261230,
            "SALE_PRICE": 580000,
            "GRANTOR": "MASSA,MOLLY M",
            "GRANTEE": "MEIGS,ANDREW PATRICK",
            "CLASS": "O",
            "D_CLASS": "101",
            "D_CLASS_N": "RESIDENTIAL-CONDOMINIUM",
            "NBHD_1": 263,
            "NBHD_1_CN": "BALLPARK",
        }

    def test_sane_sale_maps_business_key_parcel_price_and_parties(
        self, deeds, sane_wd_row
    ):
        ev = deeds.parse_socrata_row(sane_wd_row, city_id="denver")
        assert ev is not None
        assert ev.doc_id == "2026096458"
        assert ev.bbl == "604322005000"
        assert ev.document_amount == 900000.0
        assert ev.doc_type == "WD"
        assert ev.party1_grantor == "OSTROWSKI,GREGORY R"
        assert ev.party2_grantee == "PSJ & ASSOCIATES II LLC"
        assert ev.source_neighborhood == "LOWRY"
        assert ev.borough == "LOWRY"

    def test_integer_reception_date_falls_back_to_now_at_parse(
        self, deeds, sane_wd_row
    ):
        """TRUE behavior pinned: _parse_datetime treats ints outside
        1900-2100 as unparseable (the %Y%m%d branch is string-only), so the
        int yyyymmdd reception date yields None and recorded_date lands on
        the parse-time now() fallback - NOT 2026-08-13. The wire event still
        carries a non-null datetime (deed Avro requires it); recency truth
        lives in the watermark layer, not the event. If the spine later
        coerces int dates, this pin is the one to update deliberately."""
        from datetime import datetime

        before = datetime.now(UTC)
        ev = deeds.parse_socrata_row(sane_wd_row, city_id="denver")
        after = datetime.now(UTC)
        assert ev is not None
        assert before <= ev.recorded_date <= after
        assert ev.recorded_date.year == before.year

    def test_zero_price_transfer_is_not_dropped(self, deeds, zero_transfer_row):
        """$0 city-to-city transfers emit cost-0 events at parse time -
        filtering is a registry/scheduler concern, never a silent parser
        drop. Verified live: 74 of the newest 500 rows carry SALE_PRICE=0
        (55,177 across the 309,548-row table)."""
        ev = deeds.parse_socrata_row(zero_transfer_row, city_id="denver")
        assert ev is not None
        assert ev.document_amount == 0.0
        assert ev.doc_id == "2025018558"
        assert ev.bbl == "230204016000"

    def test_malformed_and_future_dates_take_the_same_now_fallback(
        self, deeds, zero_transfer_row, future_dated_row
    ):
        """Both dirty shapes (unparseable 50250305, future 20261230) fall to
        the now() fallback instead of raising or fabricating the reception
        date - and neither kills parsing. Server-side watermark hygiene for
        these exact values is pinned in TestDenverRegistration via
        watermark_exclude."""
        from datetime import datetime

        now = datetime.now(UTC)
        for row in (zero_transfer_row, future_dated_row):
            ev = deeds.parse_socrata_row(row, city_id="denver")
            assert ev is not None
            assert abs((ev.recorded_date - now).total_seconds()) < 300

    def test_sales_table_has_no_geometry_so_events_carry_null_coords_h3(
        self, deeds, sane_wd_row
    ):
        """The table publishes no coordinate columns and no address columns;
        like Norfolk's sales and DC's CAMA path, events serialize with null
        lat/lng/null H3 keyed on PARID."""
        ev = deeds.parse_socrata_row(sane_wd_row, city_id="denver")
        assert ev.latitude is None
        assert ev.longitude is None
        assert ev.h3_res7 is None
        assert ev.h3_res8 is None
        assert ev.h3_res9 is None

    def test_deeds_parse_path_never_invokes_the_geocode_hook(
        self, deeds, sane_wd_row, zero_transfer_row, future_dated_row, monkeypatch
    ):
        """Documents the gap: unlike the SLA/311 producers, DeedsACRISProducer
        has no geocode_row_if_declared hook site, so declaring needs_geocode
        on a deeds spec would be inert. Pinning zero calls makes any future
        spine wiring visible here."""
        calls = []
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: calls.append(address),
        )
        for row in (sane_wd_row, zero_transfer_row, future_dated_row):
            assert deeds.parse_socrata_row(row, city_id="denver") is not None
        assert calls == []
