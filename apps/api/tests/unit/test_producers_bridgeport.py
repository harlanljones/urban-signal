"""Unit tests for the Bridgeport, CT leaf (US-419): spatial module + field maps
+ SLA and DEEDS producer parse wiring.

Bridgeport is a TWO-FEED PARTIAL metro on Connecticut's statewide Socrata portal
(``data.ct.gov``): SLA (State Licenses and Credentials, ``ngch-56tr``, filtered
``city = 'BRIDGEPORT'``) and DEEDS (Real Estate Sales, ``5mzw-sjtu``, filtered
``town = 'Bridgeport'``). Both are address-only — no native WGS84 lat/lng read
by the shared producers — so both declare ``needs_geocode=True``.

Tests pass WITHOUT a spine registration (no CityId.BRIDGEPORT, no REGISTRY
assertions — "bridgeport" stays a plain string). Division/borough resolution
and geocode-hook call counts are deliberately NOT asserted: both change when
the spine lands.

Live fixtures captured byte-verbatim 2026-08-30 from data.ct.gov
($order=recordrefreshedon DESC / $order=daterecorded DESC) — newest rows by
watermark. SLA watermark 2026-08-30; DEEDS watermark 2025-09-30 (listyear 2024,
an annual grand-list publication).
"""

from unittest.mock import patch

import pytest

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

# Newest SLA row (credentialid 923910, BUZZ'S MOBIL, 2394 E MAIN ST —
# RETAIL GASOLINE DEALER, RGD.0003314). Broad statewide credentials feed;
# watermark recordrefreshedon 2026-08-30.
_SLA_FIXTURE_BUZZ = {
    "credentialid": "923910",
    "name": "BUZZ'S MOBIL",
    "type": "CORPORATION",
    "businessname": "BUZZ'S MOBIL",
    "fullcredentialcode": "RGD.0003314",
    "credentialtype": "RGD",
    "credentialnumber": "3314",
    "credential": "RETAIL GASOLINE DEALER",
    "status": "INACTIVE",
    "statusreason": "EXPIRED MORE THAN 3 YEARS - MUST REAPPLY",
    "active": "0",
    "issuedate": "2010-04-22T00:00:00.000",
    "effectivedate": "2012-12-21T00:00:00.000",
    "expirationdate": "2013-10-31T00:00:00.000",
    "address": "2394 E MAIN ST",
    "city": "BRIDGEPORT",
    "state": "CT",
    "zip": "066101803",
    "recordrefreshedon": "2026-08-30T00:00:00.000",
}

# Second co-newest SLA row (credentialid 7634, ROBERT RUFF — INDIVIDUAL with a
# ``dba`` column and NO ``businessname``/``issuedate``; exercises the
# name/businessname and effectivedate/issuedate fallthroughs).
_SLA_FIXTURE_RUFF = {
    "credentialid": "7634",
    "name": "ROBERT RUFF",
    "type": "INDIVIDUAL",
    "dba": "HOBART SALES AND SERVICE",
    "fullcredentialcode": "RPR.0000972",
    "credentialtype": "RPR",
    "credentialnumber": "972",
    "credential": "REPAIRER OF WEIGHING & MEASURING DEVICES",
    "status": "INACTIVE",
    "statusreason": "EXPIRED MORE THAN 3 YEARS - MUST REAPPLY",
    "active": "0",
    "effectivedate": "1998-03-17T00:00:00.000",
    "expirationdate": "1998-12-31T00:00:00.000",
    "address": "HOBART SALES & SERVICE",
    "city": "BRIDGEPORT",
    "state": "CT",
    "zip": "066053225",
    "recordrefreshedon": "2026-08-30T00:00:00.000",
}

# Third co-newest SLA row (credentialid 76672, CAPITOL SUNOCO — no issuedate,
# so effective_date resolves from effectivedate).
_SLA_FIXTURE_SUNOCO = {
    "credentialid": "76672",
    "name": "CAPITOL SUNOCO",
    "type": "LIMITED LIABILITY COMPANY",
    "businessname": "CAPITOL SUNOCO",
    "fullcredentialcode": "RGD.0000075",
    "credentialtype": "RGD",
    "credentialnumber": "75",
    "credential": "RETAIL GASOLINE DEALER",
    "status": "INACTIVE",
    "statusreason": "EXPIRED MORE THAN 3 YEARS - MUST REAPPLY",
    "active": "0",
    "effectivedate": "2011-11-01T00:00:00.000",
    "expirationdate": "2012-10-31T00:00:00.000",
    "address": "565 LINDLEY ST",
    "city": "BRIDGEPORT",
    "state": "CT",
    "zip": "066065451",
    "recordrefreshedon": "2026-08-30T00:00:00.000",
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
        assert sla_extra["where"] == "city = 'BRIDGEPORT'"
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
        assert spec.where == "city = 'BRIDGEPORT'"
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
        assert SLA_FIELD_MAP["premises_name"] == ["businessname", "name"]
        assert SLA_FIELD_MAP["dba"] == ["businessname", "name"]

    def test_deeds_map_reads_live_columns(self):
        assert DEEDS_FIELD_MAP["doc_id"] == ["serialnumber"]
        assert DEEDS_FIELD_MAP["recorded_date"] == ["daterecorded"]
        assert DEEDS_FIELD_MAP["document_amount"] == ["saleamount"]
        assert DEEDS_FIELD_MAP["address_street"] == ["address"]
        assert DEEDS_FIELD_MAP["borough"] == ["town"]
        assert DEEDS_FIELD_MAP["doc_type"] == ["propertytype"]

    def test_source_city_column_maps_to_borough_slot(self):
        assert SLA_FIELD_MAP["borough"] == ["city"]
        assert first_mapped(_SLA_FIXTURE_BUZZ, SLA_FIELD_MAP, "borough") == "BRIDGEPORT"
        assert first_mapped(_DEEDS_FIXTURE_2370, DEEDS_FIELD_MAP, "borough") == "Bridgeport"

    def test_license_id_falls_through_to_fullcredentialcode(self):
        row = dict(_SLA_FIXTURE_BUZZ)
        row.pop("credentialid")
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "RGD.0003314"

    def test_premises_name_falls_through_to_name(self):
        row = dict(_SLA_FIXTURE_RUFF)
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "ROBERT RUFF"

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
        event = sla.parse_socrata_row(_SLA_FIXTURE_BUZZ, city_id="bridgeport")
        assert event is not None
        assert event.city_id == "bridgeport"
        assert event.license_id == "923910"
        assert event.license_type == "RETAIL GASOLINE DEALER"
        assert event.premises_name == "BUZZ'S MOBIL"
        assert event.dba == "BUZZ'S MOBIL"
        assert event.license_status == "INACTIVE"
        assert event.address == "2394 E MAIN ST"
        assert event.source_neighborhood == "BRIDGEPORT"

    def test_effective_and_expiration_dates_parse(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_BUZZ, city_id="bridgeport")
        assert event is not None
        assert str(event.effective_date).startswith("2012-12-21")
        assert str(event.expiration_date).startswith("2013-10-31")

    def test_individual_credential_without_businessname_parses(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_RUFF, city_id="bridgeport")
        assert event is not None
        assert event.license_id == "7634"
        assert event.license_type == "REPAIRER OF WEIGHING & MEASURING DEVICES"
        assert event.premises_name == "ROBERT RUFF"
        assert event.dba == "ROBERT RUFF"

    def test_effective_date_falls_back_from_issuedate_to_effectivedate(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_SLA_FIXTURE_SUNOCO, city_id="bridgeport")
        assert event is not None
        assert str(event.effective_date).startswith("2011-11-01")


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
