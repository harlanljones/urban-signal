"""Unit tests for the New Haven, CT leaf (US-419): spatial module + field maps
+ SLA and DEEDS producer parse wiring.

New Haven is a TWO-FEED metro on Connecticut's statewide Socrata portal
(``data.ct.gov``): State Licenses and Credentials (``ngch-56tr``, Tier 1 SLA)
and Real Estate Conveyance Tax / property sales (``5mzw-sjtu``, Tier 1 DEEDS)
— the SAME statewide feeds Hartford already carries, filtered to New Haven.

Tests pass WITHOUT a spine registration (no CityId.NEW_HAVEN, no REGISTRY
assertions — "new_haven" stays a plain string). Division/borough resolution
and geocode-hook call counts are deliberately NOT asserted: both change when
the spine lands. Both feeds are address-only from the producer's view, so
parse events are coordinate-less pre-spine (the geocode hook is only reached
once a registered spec declares ``needs_geocode``; the DEEDS ``geo_coordinates``
Point is not yet read by the shared deeds producer's nested-loc fallback).

Live fixtures captured from data.ct.gov/resource/ngch-56tr.json (2026-09-30,
under the liquor filter, $order=recordrefreshedon DESC; the permittee's own
name replaced on the individually held permit) and
data.ct.gov/resource/5mzw-sjtu.json (2026-08-30, $where=town = 'New Haven',
$order=daterecorded DESC; DEEDS watermark 2025-09-30).
"""

from unittest.mock import patch

import pytest

from src.producers.ct_liquor_specs import CT_LIQUOR_SLA_FIELD_MAP, ct_liquor_where
from src.producers.field_maps import first_mapped
from src.spatial.cities.new_haven import (
    DEEDS_FIELD_MAP,
    DEEDS_NEVER_CANDIDATE_COLUMNS,
    FIELD_MAP,
    SLA_FIELD_MAP,
    SLA_NEVER_CANDIDATE_COLUMNS,
)
from src.spatial.cities.new_haven import (
    NEW_HAVEN_CITY_ID,
    NEW_HAVEN_DEEDS_ENDPOINT,
    NEW_HAVEN_DIVISION_BBOXES,
    NEW_HAVEN_DIVISIONS,
    NEW_HAVEN_FEED_SPECS,
    NEW_HAVEN_METRO_BBOX,
    NEW_HAVEN_SLA_ENDPOINT,
    NEW_HAVEN_SUBMARKETS,
    REGISTRATION,
    get_new_haven_dataset,
    is_in_new_haven_metro,
)

# ---------------------------------------------------------------------------
# SLA fixtures — liquor permits (2026-09-30). Individual, business and
# corporation permittees all appear; the feed is address-only (no native
# lat/lng columns).
# ---------------------------------------------------------------------------
# An individually held permit: ``name`` is the permittee, a person (replaced
# here), there is no ``businessname``, and ``dba`` names the cafe.
_SLA_FIXTURE_MOLIENDA = {
    "credentialid": "910592",
    "name": "PERMITTEE NAME REDACTED",
    "type": "INDIVIDUAL",
    "dba": "LA MOLIENDA CAFE",
    "fullcredentialcode": "LCA.0007160",
    "credentialtype": "LCA",
    "credentialnumber": "7160",
    "credential": "CAFE LIQUOR",
    "status": "ACTIVE",
    "statusreason": "CURRENT",
    "active": "1",
    "issuedate": "2010-03-11T00:00:00.000",
    "effectivedate": "2026-07-11T00:00:00.000",
    "expirationdate": "2027-07-10T00:00:00.000",
    "address": "113 GRAND AVE",
    "city": "NEW HAVEN",
    "state": "CT",
    "zip": "065133907",
    "recordrefreshedon": "2026-07-20T00:00:00.000",
}

# BUSINESS row: businessname is the holding company, dba the restaurant;
# effectivedate is the current term (2026-09-12), issuedate the first permit
# (2023-09-12).
_SLA_FIXTURE_GIOIA = {
    "credentialid": "2494984",
    "name": "150 WOOSTER ST LLC",
    "type": "BUSINESS",
    "businessname": "150 WOOSTER ST LLC",
    "dba": "GIOIA",
    "fullcredentialcode": "LIR.0021164",
    "credentialtype": "LIR",
    "credentialnumber": "21164",
    "credential": "RESTAURANT LIQUOR",
    "status": "ACTIVE",
    "statusreason": "CURRENT",
    "active": "1",
    "issuedate": "2023-09-12T00:00:00.000",
    "effectivedate": "2026-09-12T00:00:00.000",
    "expirationdate": "2027-09-11T00:00:00.000",
    "address": "150 WOOSTER ST",
    "city": "NEW HAVEN",
    "state": "CT",
    "zip": "065115710",
    "recordrefreshedon": "2026-09-25T00:00:00.000",
}

# CORPORATION row: a non-profit theater permit.
_SLA_FIXTURE_MUSIC_HALL = {
    "credentialid": "1273063",
    "name": "NEW HAVEN CENTER FOR PERFORMING ARTS INC",
    "type": "CORPORATION",
    "businessname": "NEW HAVEN CENTER FOR PERFORMING ARTS INC",
    "dba": "COLLEGE STREET MUSIC HALL",
    "fullcredentialcode": "LTH.0000091",
    "credentialtype": "LTH",
    "credentialnumber": "91",
    "credential": "NON PROFIT THEATER LIQUOR",
    "status": "ACTIVE",
    "statusreason": "CURRENT",
    "active": "1",
    "issuedate": "2015-05-04T00:00:00.000",
    "effectivedate": "2026-09-04T00:00:00.000",
    "expirationdate": "2027-09-03T00:00:00.000",
    "address": "238 COLLEGE ST",
    "city": "NEW HAVEN",
    "state": "CT",
    "zip": "065102404",
    "recordrefreshedon": "2026-07-20T00:00:00.000",
}

# ---------------------------------------------------------------------------
# DEEDS fixtures — newest rows by daterecorded (2025-09-30). Each carries a
# nested Socrata geo_coordinates Point the shared deeds producer does NOT yet
# read (see module docstring caveat). assessedvalue (underscore-free) does not
# shadow the document_amount chain; saleamount is the sale price.
# ---------------------------------------------------------------------------
_DEEDS_FIXTURE_HARRISON = {
    "serialnumber": "241120",
    "listyear": "2024",
    "daterecorded": "2025-09-30T00:00:00.000",
    "town": "New Haven",
    "address": "23 HARRISON ST",
    "assessedvalue": "135170",
    "saleamount": "270000",
    "salesratio": "0.5006",
    "propertytype": "Residential",
    "residentialtype": "Single Family",
    "geo_coordinates": {"type": "Point", "coordinates": [-72.96246, 41.32726]},
}

_DEEDS_FIXTURE_POPE = {
    "serialnumber": "241121",
    "listyear": "2024",
    "daterecorded": "2025-09-30T00:00:00.000",
    "town": "New Haven",
    "address": "5 POPE ST",
    "assessedvalue": "206920",
    "saleamount": "459000",
    "salesratio": "0.4508",
    "propertytype": "Residential",
    "residentialtype": "Single Family",
    "geo_coordinates": {"type": "Point", "coordinates": [-72.90047, 41.2707]},
}

_DEEDS_FIXTURE_BROOKLAWN = {
    "serialnumber": "241119",
    "listyear": "2024",
    "daterecorded": "2025-09-30T00:00:00.000",
    "town": "New Haven",
    "address": "109 BROOKLAWN CIR",
    "assessedvalue": "141960",
    "saleamount": "415000",
    "salesratio": "0.342",
    "propertytype": "Residential",
    "residentialtype": "Single Family",
    "geo_coordinates": {"type": "Point", "coordinates": [-72.98114, 41.3257]},
}


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
def deeds():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        return DeedsACRISProducer()


class TestNewHavenSpatial:
    def test_metro_bbox_sanity(self):
        assert NEW_HAVEN_METRO_BBOX["min_lat"] < NEW_HAVEN_METRO_BBOX["max_lat"]
        assert NEW_HAVEN_METRO_BBOX["min_lng"] < NEW_HAVEN_METRO_BBOX["max_lng"]

    def test_is_in_new_haven_metro_rejects_missing_coordinates(self):
        assert is_in_new_haven_metro(None, None) is False

    def test_is_in_new_haven_metro_rejects_other_cities(self):
        assert is_in_new_haven_metro(41.7637, -72.6734) is False  # Hartford
        assert is_in_new_haven_metro(41.0534, -73.5387) is False  # Stamford
        assert is_in_new_haven_metro(40.7128, -74.0060) is False  # NYC
        assert is_in_new_haven_metro(42.3601, -71.0589) is False  # Boston

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in NEW_HAVEN_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= NEW_HAVEN_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= NEW_HAVEN_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= NEW_HAVEN_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= NEW_HAVEN_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in NEW_HAVEN_SUBMARKETS.items():
            bbox = NEW_HAVEN_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in NEW_HAVEN_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(NEW_HAVEN_SUBMARKETS)

    def test_submarkets_carry_the_new_haven_city_id(self):
        assert {m.city_id for m in NEW_HAVEN_SUBMARKETS.values()} == {"new_haven"}

    def test_city_id_and_registration_shape(self):
        assert NEW_HAVEN_CITY_ID == "new_haven"
        assert REGISTRATION.metro_bbox is NEW_HAVEN_METRO_BBOX
        assert REGISTRATION.submarkets is NEW_HAVEN_SUBMARKETS
        assert len(REGISTRATION.divisions) == 6
        assert len(NEW_HAVEN_SUBMARKETS) == 8

    def test_required_real_neighborhoods_present(self):
        assert set(NEW_HAVEN_SUBMARKETS) == {
            "Downtown",
            "Wooster Square",
            "East Rock",
            "Westville",
            "Fair Haven",
            "Dixwell",
            "Newhallville",
            "The Hill",
        }


class TestNewHavenFeedSpecs:
    def test_the_leaf_mirror_carries_sla_and_deeds_only(self):
        # The registry also holds 311 from SeeClickFix's public view, which
        # the corpus registers itself (test_new_haven_311.py).
        assert set(NEW_HAVEN_FEED_SPECS) == {"sla", "deeds"}

    def test_sla_spec_shape(self):
        spec = NEW_HAVEN_FEED_SPECS["sla"]
        assert spec["endpoint"] == NEW_HAVEN_SLA_ENDPOINT
        assert NEW_HAVEN_SLA_ENDPOINT == "https://data.ct.gov/resource/ngch-56tr.json"
        assert spec["platform"] == "socrata"
        assert spec["watermark_col"] == "recordrefreshedon"
        assert spec["id_keys"] == ["credentialid"]
        assert spec["producer_key"] == "sla"
        assert spec["topic_key"] == "topic_sla"

    def test_deeds_spec_shape(self):
        spec = NEW_HAVEN_FEED_SPECS["deeds"]
        assert spec["endpoint"] == NEW_HAVEN_DEEDS_ENDPOINT
        assert NEW_HAVEN_DEEDS_ENDPOINT == "https://data.ct.gov/resource/5mzw-sjtu.json"
        assert spec["platform"] == "socrata"
        assert spec["watermark_col"] == "daterecorded"
        assert spec["id_keys"] == ["serialnumber", "listyear"]
        assert spec["producer_key"] == "deeds"
        assert spec["topic_key"] == "topic_deeds"

    def test_null_guards_orders_and_geocode_are_pinned(self):
        sla_extra = NEW_HAVEN_FEED_SPECS["sla"]["extra"]
        # recordrefreshedon has 0 nulls (no IS NOT NULL guard needed).
        assert sla_extra["where"] == ct_liquor_where("NEW HAVEN")
        assert sla_extra["order_by"] == "recordrefreshedon DESC"
        assert sla_extra["needs_geocode"] is True
        assert sla_extra["geocode_context"] == "New Haven, CT"

        deeds_extra = NEW_HAVEN_FEED_SPECS["deeds"]["extra"]
        assert deeds_extra["where"] == "town = 'New Haven'"
        assert deeds_extra["order_by"] == "daterecorded DESC"
        assert deeds_extra["needs_geocode"] is True
        assert deeds_extra["geocode_context"] == "New Haven, CT"

    def test_deeds_composite_id_keys_are_documented(self):
        # serialnumber resets across the 22 assessment years (probe caveat);
        # the scope string must name the composite key so the spine keeps it.
        scope = NEW_HAVEN_FEED_SPECS["deeds"]["extra"]["scope"]
        assert "serialnumber" in scope
        assert "listyear" in scope

    def test_get_new_haven_dataset_resolves_sla(self, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        from src.spatial.city_registry import FeedType

        spec = get_new_haven_dataset(FeedType.SLA)
        assert spec.endpoint == NEW_HAVEN_SLA_ENDPOINT
        assert spec.platform == "socrata"
        assert spec.watermark_col == "recordrefreshedon"
        assert spec.where == ct_liquor_where("NEW HAVEN")
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.needs_geocode is True
        assert spec.geocode_context == "New Haven, CT"
        assert spec.id_keys == ["credentialid"]

    def test_get_new_haven_dataset_resolves_deeds(self, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        from src.spatial.city_registry import FeedType

        spec = get_new_haven_dataset(FeedType.DEEDS)
        assert spec.endpoint == NEW_HAVEN_DEEDS_ENDPOINT
        assert spec.platform == "socrata"
        assert spec.watermark_col == "daterecorded"
        assert spec.where == "town = 'New Haven'"
        assert spec.field_map == DEEDS_FIELD_MAP
        assert spec.needs_geocode is True
        assert spec.geocode_context == "New Haven, CT"
        assert spec.id_keys == ["serialnumber", "listyear"]

    def test_get_new_haven_dataset_rejects_unregistered_feeds(self):
        class _Feed:
            value = "permits"

        with pytest.raises(KeyError, match="new_haven"):
            get_new_haven_dataset(_Feed())


class TestNewHavenFieldMaps:
    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["credentialid", "fullcredentialcode"]
        assert SLA_FIELD_MAP["license_type"] == ["credential", "credentialtype"]
        assert SLA_FIELD_MAP["effective_date"] == ["effectivedate", "issuedate"]
        assert SLA_FIELD_MAP["expiration_date"] == ["expirationdate"]
        assert SLA_FIELD_MAP["address_street"] == ["address"]
        assert SLA_FIELD_MAP["zipcode"] == ["zip"]
        assert SLA_FIELD_MAP["borough"] == ["city"]
        assert SLA_FIELD_MAP["premises_name"] == ["businessname", "dba"]
        assert SLA_FIELD_MAP["dba"] == ["dba", "businessname"]
        assert SLA_FIELD_MAP["status"] == ["status"]
        assert SLA_FIELD_MAP is CT_LIQUOR_SLA_FIELD_MAP

    def test_deeds_map_reads_live_columns(self):
        assert DEEDS_FIELD_MAP["doc_id"] == ["serialnumber"]
        assert DEEDS_FIELD_MAP["recorded_date"] == ["daterecorded"]
        assert DEEDS_FIELD_MAP["document_amount"] == ["saleamount"]
        assert DEEDS_FIELD_MAP["address_street"] == ["address"]
        assert DEEDS_FIELD_MAP["borough"] == ["town"]
        assert DEEDS_FIELD_MAP["doc_type"] == ["propertytype"]

    def test_city_column_maps_to_sla_borough_slot(self):
        assert first_mapped(_SLA_FIXTURE_MOLIENDA, SLA_FIELD_MAP, "borough") == "NEW HAVEN"
        assert first_mapped(_DEEDS_FIXTURE_HARRISON, DEEDS_FIELD_MAP, "borough") == "New Haven"

    def test_sla_names_come_from_businessname_and_dba(self):
        # INDIVIDUAL rows carry no businessname and name the permittee, so the
        # dba names the premises.
        assert first_mapped(_SLA_FIXTURE_MOLIENDA, SLA_FIELD_MAP, "premises_name") == "LA MOLIENDA CAFE"
        assert first_mapped(_SLA_FIXTURE_GIOIA, SLA_FIELD_MAP, "premises_name") == "150 WOOSTER ST LLC"
        assert first_mapped(_SLA_FIXTURE_GIOIA, SLA_FIELD_MAP, "dba") == "GIOIA"

    def test_never_candidate_columns_are_never_map_candidates(self):
        for feed_map, never in (
            (SLA_FIELD_MAP, SLA_NEVER_CANDIDATE_COLUMNS),
            (DEEDS_FIELD_MAP, DEEDS_NEVER_CANDIDATE_COLUMNS),
        ):
            for values in feed_map.values():
                for col in values:
                    assert col not in never, (col, never)

    def test_never_candidate_columns_are_present_on_live_fixtures(self):
        for col in SLA_NEVER_CANDIDATE_COLUMNS:
            assert col in _SLA_FIXTURE_GIOIA, col
        # remarks is "some rows" on the live feed, so assert only the columns
        # every DEEDS fixture actually carries.
        for col in ("listyear", "assessedvalue", "salesratio", "residentialtype", "geo_coordinates"):
            assert col in _DEEDS_FIXTURE_HARRISON, col


class TestNewHavenSLAParsing:
    def test_individual_permit_parses_without_the_permittee(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_FIXTURE_MOLIENDA, city_id="new_haven")
        assert event is not None
        assert event.city_id == "new_haven"
        assert event.license_id == "910592"
        assert event.dba == "LA MOLIENDA CAFE"
        assert event.premises_name == "LA MOLIENDA CAFE"
        assert event.license_type == "CAFE LIQUOR"
        assert event.license_status == "ACTIVE"
        assert event.address == "113 GRAND AVE"
        assert event.source_neighborhood == "NEW HAVEN"
        assert "PERMITTEE NAME REDACTED" not in event.model_dump_json()

    def test_business_fixture_reads_businessname_and_dates(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_FIXTURE_GIOIA, city_id="new_haven")
        assert event is not None
        assert event.license_id == "2494984"
        assert event.premises_name == "150 WOOSTER ST LLC"
        assert event.dba == "GIOIA"
        assert event.license_type == "RESTAURANT LIQUOR"
        # effective_date is effectivedate (2026-09-12), NOT issuedate (2023-09-12).
        assert str(event.effective_date).startswith("2026-09-12")
        assert str(event.expiration_date).startswith("2027-09-11")

    def test_corporation_fixture_parses(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_FIXTURE_MUSIC_HALL, city_id="new_haven")
        assert event is not None
        assert event.license_id == "1273063"
        assert event.dba == "COLLEGE STREET MUSIC HALL"
        assert event.license_type == "NON PROFIT THEATER LIQUOR"
        assert event.address == "238 COLLEGE ST"

    def test_license_id_falls_through_to_fullcredentialcode(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        row = dict(_SLA_FIXTURE_MOLIENDA)
        row["credentialid"] = ""
        event = sla.parse_socrata_row(row, city_id="new_haven")
        assert event is not None
        assert event.license_id == "LCA.0007160"


class TestNewHavenDeedsParsing:
    def test_newest_fixture_parses_through_real_producer_path(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(_DEEDS_FIXTURE_HARRISON, city_id="new_haven")
        assert event is not None
        assert event.city_id == "new_haven"
        assert event.doc_id == "241120"
        assert event.document_amount == pytest.approx(270000.0)
        assert event.doc_type == "RESIDENTIAL"
        assert str(event.recorded_date).startswith("2025-09-30")
        assert event.source_neighborhood == "New Haven"

    def test_document_amount_reads_saleamount_not_assessedvalue(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(_DEEDS_FIXTURE_POPE, city_id="new_haven")
        assert event is not None
        assert event.document_amount == pytest.approx(459000.0)
        assert event.doc_id == "241121"

    def test_doc_type_is_property_classification_not_deed_instrument(self, deeds, monkeypatch):
        """propertytype ("Residential"/"Condo") is a property classification,
        not a deed instrument type — there is no deed-type column on this feed."""
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(_DEEDS_FIXTURE_BROOKLAWN, city_id="new_haven")
        assert event is not None
        assert event.doc_type == "RESIDENTIAL"
        assert event.document_amount == pytest.approx(415000.0)

    def test_geo_coordinates_point_is_present_on_live_fixture(self):
        # The nested Point is on the wire; the shared producer's nested-loc
        # fallback does not yet read geo_coordinates (spine TODO). We pin the
        # fixture shape, not the event's resolved coordinates.
        gc = _DEEDS_FIXTURE_HARRISON["geo_coordinates"]
        assert gc["type"] == "Point"
        assert gc["coordinates"] == [-72.96246, 41.32726]
