"""Unit tests for the Bridgeport, CT leaf (US-419): spatial module + field maps
+ SLA and DEEDS producer parse wiring.

Bridgeport is a TWO-FEED PARTIAL metro on Connecticut's statewide Socrata portal
(``data.ct.gov``): SLA (State Licenses and Credentials, ``ngch-56tr``, filtered
to ``city = 'BRIDGEPORT'`` and liquor permit types) and DEEDS (Real Estate Sales,
``5mzw-sjtu``, filtered ``town = 'Bridgeport'``). Both are address-only — no native WGS84 lat/lng read
by the shared producers — so both declare ``needs_geocode=True``.

Tests pass WITHOUT a spine registration (no CityId.BRIDGEPORT, no REGISTRY
assertions — "bridgeport" stays a plain string). Division/borough resolution
and geocode-hook call counts are deliberately NOT asserted: both change when
the spine lands.

Live fixtures captured from data.ct.gov ($order=recordrefreshedon DESC /
$order=daterecorded DESC). SLA rows 2026-09-30 under the liquor filter, with
the permittee's own name replaced on the individually held permit; DEEDS rows
2026-08-30, watermark 2025-09-30 (listyear 2024, an annual grand-list
publication).
"""

from unittest.mock import patch

import pytest

from src.producers.ct_liquor_specs import CT_LIQUOR_SLA_FIELD_MAP, ct_liquor_where
from src.producers.field_maps import first_mapped
from src.spatial.cities.bridgeport import (
    BRIDGEPORT_CITY_ID,
    BRIDGEPORT_DEEDS_ENDPOINT,
    BRIDGEPORT_DIVISION_BBOXES,
    BRIDGEPORT_DIVISIONS,
    BRIDGEPORT_FEED_SPECS,
    BRIDGEPORT_METRO_BBOX,
    BRIDGEPORT_SLA_ENDPOINT,
    BRIDGEPORT_SUBMARKETS,
    DEEDS_FIELD_MAP,
    FIELD_MAP,
    REGISTRATION,
    SLA_FIELD_MAP,
    get_bridgeport_dataset,
    is_in_bridgeport_metro,
)

# Newest liquor permit (credentialid 2016279): a business permittee, so
# ``businessname`` is the holding company and ``dba`` the bar's name.
_SLA_FIXTURE_BERTOS = {
    "credentialid": "2016279",
    "name": "AYALA'S LLC",
    "type": "BUSINESS",
    "businessname": "AYALA'S LLC",
    "dba": "BERTO\u2019S SPORTS BAR & GRILL",
    "fullcredentialcode": "LIR.0020362",
    "credentialtype": "LIR",
    "credentialnumber": "20362",
    "credential": "RESTAURANT LIQUOR",
    "status": "ACTIVE UNDER REVIEW",
    "statusreason": "DIVISION APPROVAL NEEDED",
    "active": "1",
    "issuedate": "2021-10-01T00:00:00.000",
    "effectivedate": "2026-10-01T00:00:00.000",
    "expirationdate": "2027-09-30T00:00:00.000",
    "address": "709 BEECHWOOD AVE",
    "city": "BRIDGEPORT",
    "state": "CT",
    "zip": "066051606",
    "recordrefreshedon": "2026-09-28T00:00:00.000",
}

# An individually held permit (credentialid 427231): ``name`` is the permittee,
# a person (replaced here), there is no ``businessname``, and ``dba`` names the
# store.
_SLA_FIXTURE_DANNYS = {
    "credentialid": "427231",
    "name": "PERMITTEE NAME REDACTED",
    "type": "INDIVIDUAL",
    "dba": "DANNY'S VARIETY",
    "fullcredentialcode": "LGB.0014025",
    "credentialtype": "LGB",
    "credentialnumber": "14025",
    "credential": "GROCERY BEER",
    "status": "INACTIVE",
    "active": "0",
    "issuedate": "2006-05-15T00:00:00.000",
    "effectivedate": "2009-05-15T00:00:00.000",
    "expirationdate": "2010-05-14T00:00:00.000",
    "address": "856 FAIRFIELD AVE",
    "city": "BRIDGEPORT",
    "state": "CT",
    "zip": "06604",
    "recordrefreshedon": "2026-03-27T00:00:00.000",
}

# A new application (credentialid 2951919): PENDING with no issue or effective
# date yet, the earliest sign of a new store.
_SLA_FIXTURE_MADERA = {
    "credentialid": "2951919",
    "name": "MADERA MARKET LLC",
    "type": "LIMITED LIABILITY COMPANY",
    "businessname": "MADERA MARKET LLC",
    "dba": "MADERA MARKET",
    "fullcredentialcode": "LGB.0016030.P-CW",
    "credentialtype": "LGB",
    "credentialnumber": "16030",
    "credential": "GROCERY BEER",
    "status": "PENDING",
    "statusreason": "APPROVED FOR PROVISIONAL WITH REQUIREMENTS",
    "active": "0",
    "address": "818 NOBLE AV",
    "city": "BRIDGEPORT",
    "state": "CT",
    "zip": "06608",
    "recordrefreshedon": "2026-09-17T00:00:00.000",
}

# Newest DEEDS row (serialnumber 241376, 2370 NORTH AVE UNIT #05E — a Condo).
# daterecorded 2025-09-30 (listyear 2024).
_DEEDS_FIXTURE_2370 = {
    "serialnumber": "241376",
    "listyear": "2024",
    "daterecorded": "2025-09-30T00:00:00.000",
    "town": "Bridgeport",
    "address": "2370 NORTH AVE UNIT #05E",
    "assessedvalue": "46590",
    "saleamount": "192000",
    "salesratio": "0.24265625",
    "propertytype": "Residential",
    "residentialtype": "Condo",
    "geo_coordinates": {"type": "Point", "coordinates": [-73.21643, 41.17868]},
}

# Second co-newest DEEDS row (serialnumber 241374, 171 WAKE ST #177 — carries
# nonusecode/opm_remarks).
_DEEDS_FIXTURE_171 = {
    "serialnumber": "241374",
    "listyear": "2024",
    "daterecorded": "2025-09-30T00:00:00.000",
    "town": "Bridgeport",
    "address": "171 WAKE ST #177",
    "assessedvalue": "147150",
    "saleamount": "550000",
    "salesratio": "0.2675454545454545",
    "propertytype": "Residential",
    "residentialtype": "Two Family",
    "nonusecode": "07 - Change in Property",
    "opm_remarks": "TOTAL RENOVATION PER MLS",
    "geo_coordinates": {"type": "Point", "coordinates": [-73.15983, 41.20185]},
}

# Third co-newest DEEDS row (serialnumber 241379, 1421 KOSSUTH ST).
_DEEDS_FIXTURE_1421 = {
    "serialnumber": "241379",
    "listyear": "2024",
    "daterecorded": "2025-09-30T00:00:00.000",
    "town": "Bridgeport",
    "address": "1421 KOSSUTH ST",
    "assessedvalue": "154530",
    "saleamount": "510000",
    "salesratio": "0.303",
    "propertytype": "Residential",
    "residentialtype": "Two Family",
    "geo_coordinates": {"type": "Point", "coordinates": [-73.1817, 41.19789]},
}


def _patch_resolve(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed.value],
    )


class TestBridgeportSpatial:
    def test_metro_bbox_sanity(self):
        assert BRIDGEPORT_METRO_BBOX["min_lat"] < BRIDGEPORT_METRO_BBOX["max_lat"]
        assert BRIDGEPORT_METRO_BBOX["min_lng"] < BRIDGEPORT_METRO_BBOX["max_lng"]

    def test_is_in_bridgeport_metro_rejects_missing_coordinates(self):
        assert is_in_bridgeport_metro(None, None) is False

    def test_is_in_bridgeport_metro_rejects_other_cities(self):
        assert is_in_bridgeport_metro(41.7637, -72.6734) is False  # Hartford
        assert is_in_bridgeport_metro(40.7128, -74.0060) is False  # NYC
        assert is_in_bridgeport_metro(41.3083, -72.9279) is False  # New Haven
        assert is_in_bridgeport_metro(41.14, -73.35) is False     # west of Black Rock (Fairfield line)
        assert is_in_bridgeport_metro(41.17, -73.10) is False     # east of East End (Stratford line)

    def test_live_deeds_geo_coordinates_are_contained(self):
        for row in (_DEEDS_FIXTURE_2370, _DEEDS_FIXTURE_171, _DEEDS_FIXTURE_1421):
            lng, lat = row["geo_coordinates"]["coordinates"]
            assert is_in_bridgeport_metro(lat, lng)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in BRIDGEPORT_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= BRIDGEPORT_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= BRIDGEPORT_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= BRIDGEPORT_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= BRIDGEPORT_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in BRIDGEPORT_SUBMARKETS.items():
            bbox = BRIDGEPORT_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in BRIDGEPORT_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(BRIDGEPORT_SUBMARKETS)

    def test_submarkets_carry_the_bridgeport_city_id(self):
        assert {m.city_id for m in BRIDGEPORT_SUBMARKETS.values()} == {"bridgeport"}

    def test_city_id_and_registration_shape(self):
        assert BRIDGEPORT_CITY_ID == "bridgeport"
        assert REGISTRATION.metro_bbox is BRIDGEPORT_METRO_BBOX
        assert REGISTRATION.submarkets is BRIDGEPORT_SUBMARKETS
        assert len(REGISTRATION.divisions) == 6
        assert len(BRIDGEPORT_SUBMARKETS) == 8

    def test_required_real_neighborhoods_present(self):
        assert set(BRIDGEPORT_SUBMARKETS) == {
            "Downtown",
            "South End",
            "West Side",
            "The Hollow",
            "Black Rock",
            "East Side",
            "East End",
            "North End",
        }


class TestBridgeportFeedSpecs:
    def test_sla_spec_shape(self):
        spec = BRIDGEPORT_FEED_SPECS["sla"]
        assert spec["endpoint"] == BRIDGEPORT_SLA_ENDPOINT
        assert BRIDGEPORT_SLA_ENDPOINT == "https://data.ct.gov/resource/ngch-56tr.json"
        assert spec["platform"] == "socrata"
        assert spec["watermark_col"] == "recordrefreshedon"
        assert spec["id_keys"] == ["credentialid"]
        assert spec["producer_key"] == "sla"
        assert spec["topic_key"] == "topic_sla"

    def test_deeds_spec_shape(self):
        spec = BRIDGEPORT_FEED_SPECS["deeds"]
        assert spec["endpoint"] == BRIDGEPORT_DEEDS_ENDPOINT
        assert BRIDGEPORT_DEEDS_ENDPOINT == "https://data.ct.gov/resource/5mzw-sjtu.json"
        assert spec["platform"] == "socrata"
        assert spec["watermark_col"] == "daterecorded"
        assert spec["id_keys"] == ["serialnumber", "listyear"]
        assert spec["producer_key"] == "deeds"
        assert spec["topic_key"] == "topic_deeds"

    def test_where_order_and_geocode_are_pinned(self):
        sla_extra = BRIDGEPORT_FEED_SPECS["sla"]["extra"]
        deeds_extra = BRIDGEPORT_FEED_SPECS["deeds"]["extra"]
        assert sla_extra["where"] == ct_liquor_where("BRIDGEPORT")
        assert sla_extra["order_by"] == "recordrefreshedon DESC"
        assert sla_extra["needs_geocode"] is True
        assert sla_extra["geocode_context"] == "Bridgeport, CT"
        assert deeds_extra["where"] == "town = 'Bridgeport'"
        assert deeds_extra["order_by"] == "daterecorded DESC"
        assert deeds_extra["needs_geocode"] is True
        assert deeds_extra["geocode_context"] == "Bridgeport, CT"

    def test_get_bridgeport_dataset_resolves_sla(self, monkeypatch):
        _patch_resolve(monkeypatch)
        from src.spatial.city_registry import FeedType

        spec = get_bridgeport_dataset(FeedType.SLA)
        assert spec.endpoint == BRIDGEPORT_SLA_ENDPOINT
        assert spec.platform == "socrata"
        assert spec.watermark_col == "recordrefreshedon"
        assert spec.where == ct_liquor_where("BRIDGEPORT")
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.needs_geocode is True

    def test_get_bridgeport_dataset_resolves_deeds(self, monkeypatch):
        _patch_resolve(monkeypatch)
        from src.spatial.city_registry import FeedType

        spec = get_bridgeport_dataset(FeedType.DEEDS)
        assert spec.endpoint == BRIDGEPORT_DEEDS_ENDPOINT
        assert spec.platform == "socrata"
        assert spec.watermark_col == "daterecorded"
        assert spec.where == "town = 'Bridgeport'"
        assert spec.field_map == DEEDS_FIELD_MAP
        assert spec.id_keys == ["serialnumber", "listyear"]
        assert spec.needs_geocode is True

    def test_get_bridgeport_dataset_rejects_unregistered_feeds(self):
        class _Feed:
            value = "permits"

        with pytest.raises(KeyError, match="bridgeport"):
            get_bridgeport_dataset(_Feed())


class TestBridgeportFieldMaps:
    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["credentialid", "fullcredentialcode"]
        assert SLA_FIELD_MAP["license_type"] == ["credential", "credentialtype"]
        assert SLA_FIELD_MAP["effective_date"] == ["effectivedate", "issuedate"]
        assert SLA_FIELD_MAP["expiration_date"] == ["expirationdate"]
        assert SLA_FIELD_MAP["address_street"] == ["address"]
        assert SLA_FIELD_MAP["zipcode"] == ["zip"]
        assert SLA_FIELD_MAP["status"] == ["status"]
        assert SLA_FIELD_MAP["premises_name"] == ["businessname", "dba"]
        assert SLA_FIELD_MAP["dba"] == ["dba", "businessname"]
        assert SLA_FIELD_MAP is CT_LIQUOR_SLA_FIELD_MAP

    def test_deeds_map_reads_live_columns(self):
        assert DEEDS_FIELD_MAP["doc_id"] == ["serialnumber"]
        assert DEEDS_FIELD_MAP["recorded_date"] == ["daterecorded"]
        assert DEEDS_FIELD_MAP["document_amount"] == ["saleamount"]
        assert DEEDS_FIELD_MAP["address_street"] == ["address"]
        assert DEEDS_FIELD_MAP["borough"] == ["town"]
        assert DEEDS_FIELD_MAP["doc_type"] == ["propertytype"]

    def test_source_city_column_maps_to_borough_slot(self):
        assert SLA_FIELD_MAP["borough"] == ["city"]
        assert first_mapped(_SLA_FIXTURE_BERTOS, SLA_FIELD_MAP, "borough") == "BRIDGEPORT"
        assert first_mapped(_DEEDS_FIXTURE_2370, DEEDS_FIELD_MAP, "borough") == "Bridgeport"

    def test_license_id_falls_through_to_fullcredentialcode(self):
        row = dict(_SLA_FIXTURE_BERTOS)
        row.pop("credentialid")
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "LIR.0020362"

    def test_individual_permit_is_named_by_its_dba_not_the_permittee(self):
        row = dict(_SLA_FIXTURE_DANNYS)
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "DANNY'S VARIETY"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "DANNY'S VARIETY"

    def test_no_coordinate_columns_are_candidates(self):
        """Both feeds are address-only: no latitude/longitude slots, and the
        native deeds geo_coordinates Point is deliberately NOT mapped."""
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP
        assert "latitude" not in DEEDS_FIELD_MAP
        assert "longitude" not in DEEDS_FIELD_MAP
        assert first_mapped(_DEEDS_FIXTURE_2370, DEEDS_FIELD_MAP, "latitude") is None
        assert first_mapped(_DEEDS_FIXTURE_2370, DEEDS_FIELD_MAP, "longitude") is None


class TestBridgeportSLAParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_newest_fixture_parses_through_real_producer_path(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_BERTOS, city_id="bridgeport")
        assert event is not None
        assert event.city_id == "bridgeport"
        assert event.license_id == "2016279"
        assert event.license_type == "RESTAURANT LIQUOR"
        assert event.premises_name == "AYALA'S LLC"
        assert event.dba == "BERTO\u2019S SPORTS BAR & GRILL"
        assert event.license_status == "ACTIVE UNDER REVIEW"
        assert event.address == "709 BEECHWOOD AVE"
        assert event.source_neighborhood == "BRIDGEPORT"

    def test_effective_and_expiration_dates_parse(self, sla, monkeypatch):
        """effective_date is the current term (effectivedate), not the first
        issue in 2021."""
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_BERTOS, city_id="bridgeport")
        assert event is not None
        assert str(event.effective_date).startswith("2026-10-01")
        assert str(event.expiration_date).startswith("2027-09-30")

    def test_individual_permit_never_publishes_the_permittee(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_DANNYS, city_id="bridgeport")
        assert event is not None
        assert event.license_id == "427231"
        assert event.license_type == "GROCERY BEER"
        assert event.premises_name == "DANNY'S VARIETY"
        assert event.dba == "DANNY'S VARIETY"
        assert "PERMITTEE NAME REDACTED" not in event.model_dump_json()

    def test_pending_application_without_dates_parses(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_MADERA, city_id="bridgeport")
        assert event is not None
        assert event.license_id == "2951919"
        assert event.license_status == "PENDING"
        assert event.effective_date is None
        assert event.dba == "MADERA MARKET"


class TestBridgeportDeedsParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_newest_deed_parses_through_real_producer_path(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch)
        event = deeds.parse_socrata_row(_DEEDS_FIXTURE_2370, city_id="bridgeport")
        assert event is not None
        assert event.city_id == "bridgeport"
        assert event.doc_id == "241376"
        assert event.document_amount == pytest.approx(192000.0)
        assert event.doc_type == "RESIDENTIAL"
        assert event.source_neighborhood == "Bridgeport"

    def test_recorded_date_parses_from_daterecorded(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch)
        event = deeds.parse_socrata_row(_DEEDS_FIXTURE_2370, city_id="bridgeport")
        assert event is not None
        assert (event.recorded_date.year, event.recorded_date.month, event.recorded_date.day) == (
            2025,
            9,
            30,
        )

    def test_document_amount_comes_from_saleamount_not_assessedvalue(self, deeds, monkeypatch):
        """The deeds doc_amount chain reads saleamount via the field map; the
        live assessedvalue column is a separate assessed value, not the sale."""
        _patch_resolve(monkeypatch)
        event = deeds.parse_socrata_row(_DEEDS_FIXTURE_171, city_id="bridgeport")
        assert event is not None
        assert event.document_amount == pytest.approx(550000.0)

    def test_deed_with_remarks_columns_parses(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch)
        event = deeds.parse_socrata_row(_DEEDS_FIXTURE_1421, city_id="bridgeport")
        assert event is not None
        assert event.doc_id == "241379"
        assert event.document_amount == pytest.approx(510000.0)
