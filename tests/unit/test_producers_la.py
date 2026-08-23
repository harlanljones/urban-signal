"""Unit tests for the Los Angeles Metro registration and its producer wiring.

Los Angeles is the first city registered with an incomplete feed set: the city
retired its open 311 endpoint and LA County publishes no open recorded-deeds
feed, so only permits and business registrations exist. These tests pin that
partial registration down and cover the LA-specific field names the shared
Socrata row parsers had to learn.
"""

from unittest.mock import patch

import pytest

from src.spatial.cities.los_angeles import (
    LA_DIVISION_BBOXES,
    LA_DIVISIONS,
    LA_METRO_BBOX,
    LA_SUBMARKETS,
    is_in_la_metro,
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


class TestLosAngelesRegistration:
    def test_registered(self):
        assert CityId.LOS_ANGELES in REGISTRY

    @pytest.mark.parametrize(
        "alias",
        ["los_angeles", "Los Angeles", "LA", "la county", "pasadena", "long beach", "socal"],
    )
    def test_aliases_resolve(self, alias):
        assert normalize_city(alias) is CityId.LOS_ANGELES

    def test_registration_shape(self):
        reg = REGISTRY[CityId.LOS_ANGELES]
        assert reg.state == "CA"
        assert reg.job_suffix == "la"
        assert reg.submarkets is LA_SUBMARKETS
        assert reg.divisions is LA_DIVISIONS
        assert len(reg.divisions) == 6

    def test_center_inside_metro_bbox(self):
        reg = REGISTRY[CityId.LOS_ANGELES]
        assert is_in_la_metro(reg.center["lat"], reg.center["lng"])

    def test_is_in_la_metro_rejects_missing_coordinates(self):
        assert is_in_la_metro(None, None) is False

    def test_is_in_la_metro_rejects_other_cities(self):
        assert is_in_la_metro(47.6062, -122.3321) is False   # Seattle
        assert is_in_la_metro(37.7749, -122.4194) is False   # San Francisco

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LA_SUBMARKETS.items():
            bbox = LA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LA_SUBMARKETS)

    def test_submarkets_carry_the_la_city_id(self):
        assert {m.city_id for m in LA_SUBMARKETS.values()} == {"los_angeles"}

    def test_job_names_are_namespaced(self):
        assert get_job_name(FeedType.PERMITS, CityId.LOS_ANGELES) == "permits_la"


class TestPartialFeedRegistration:
    """LA registers only two of the four feed types, on purpose."""

    def test_only_permits_and_sla_are_registered(self):
        assert set(REGISTRY[CityId.LOS_ANGELES].datasets) == {FeedType.PERMITS, FeedType.SLA}

    def test_watermarks_match_published_schemas(self):
        assert get_dataset(CityId.LOS_ANGELES, FeedType.PERMITS).watermark_col == "issue_date"
        assert get_dataset(CityId.LOS_ANGELES, FeedType.SLA).watermark_col == "location_start_date"

    @pytest.mark.parametrize("feed", [FeedType.COMPLAINTS_311, FeedType.DEEDS])
    def test_absent_feeds_raise_a_readable_error(self, feed):
        """A bare KeyError names neither the city nor the feed; this must."""
        with pytest.raises(KeyError) as exc:
            get_dataset(CityId.LOS_ANGELES, feed)
        message = str(exc.value)
        assert "los_angeles" in message
        assert feed.value in message
        assert "permits" in message and "sla" in message

    def test_unregistered_city_raises_readable_error(self):
        class Fake:
            value = "atlantis"

        with pytest.raises(KeyError, match="atlantis"):
            get_dataset(Fake(), FeedType.PERMITS)

    def test_scheduler_iterates_partial_feed_sets_without_error(self):
        """The scheduler walks datasets.items(), so a partial set must be safe."""
        for cid, reg in REGISTRY.items():
            assert list(reg.datasets.items()) is not None, cid

    def test_every_alias_target_is_registered(self):
        for alias, cid in ALIASES.items():
            assert cid in REGISTRY, f"alias {alias!r} resolves to unregistered {cid}"


class TestLosAngelesRowParsing:
    """LADBS and LA Office of Finance use field names the shared parsers did not know."""

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
    def permit_row(self):
        return {
            "permit_nbr": "26016-90000-21692",
            "issue_date": "2026-08-15T00:00:00.000",
            "submitted_date": "2026-08-06T00:00:00.000",
            "permit_type": "Bldg-Alter/Repair",
            "valuation": "3600",
            "lat": "34.07097",
            "lon": "-118.36744",
            "primary_address": "123 EXAMPLE ST",
            "zip_code": "90019",
        }

    @pytest.fixture
    def sla_row(self):
        return {
            "location_account": "0002214058-0001-9",
            "business_name": "EXAMPLE LLC",
            "dba_name": "EXAMPLE",
            "primary_naics_description": "Retail",
            "location_start_date": "2005-01-01T00:00:00.000",
            "location_1": {"latitude": "34.1436", "longitude": "-118.0314"},
        }

    def test_permit_parses(self, permits, permit_row):
        assert permits.parse_socrata_row(permit_row, city_id="los_angeles") is not None

    def test_permit_id_comes_from_permit_nbr(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="los_angeles")
        assert ev.job_id == "26016-90000-21692"

    def test_permit_longitude_reads_the_lon_column(self, permits, permit_row):
        """LADBS spells it `lon`; every other city spells it `longitude` or `lng`."""
        ev = permits.parse_socrata_row(permit_row, city_id="los_angeles")
        assert ev.longitude == pytest.approx(-118.36744)
        assert ev.latitude == pytest.approx(34.07097)

    def test_permit_cost_comes_from_valuation(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="los_angeles")
        assert ev.estimated_cost == 3600.0

    def test_permit_dates_map(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="los_angeles")
        assert str(ev.issuance_date).startswith("2026-08-15")
        assert str(ev.filing_date).startswith("2026-08-06")

    def test_permit_resolves_to_a_division(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="los_angeles")
        assert ev.borough == "CENTRAL_LA"

    def test_permit_city_autodetects(self, permits, permit_row):
        assert permits.parse_socrata_row(permit_row).city_id == "los_angeles"

    def test_sla_parses_and_maps_location_account(self, sla, sla_row):
        ev = sla.parse_socrata_row(sla_row, city_id="los_angeles")
        assert ev is not None
        assert ev.license_id == "0002214058-0001-9"

    def test_sla_reads_the_location_1_container(self, sla, sla_row):
        ev = sla.parse_socrata_row(sla_row, city_id="los_angeles")
        assert ev.latitude == pytest.approx(34.1436)
        assert ev.longitude == pytest.approx(-118.0314)

    def test_sla_rejects_null_island_placeholder(self, sla, sla_row):
        """~7% of LA rows carry 0.0/0.0; indexing those would file them under an
        H3 cell in the Gulf of Guinea."""
        sla_row["location_1"] = {"latitude": "0.0", "longitude": "0.0"}
        assert sla.parse_socrata_row(sla_row, city_id="los_angeles") is None

    def test_sla_autodetect_beats_the_san_francisco_branch(self, sla, sla_row):
        """LA shares dba_name and location_start_date with SF's registry, so the
        LA check must run first or every LA row is mislabelled san_francisco."""
        assert sla.parse_socrata_row(sla_row).city_id == "los_angeles"

    def test_sla_san_francisco_rows_still_autodetect_correctly(self, sla):
        sf_row = {
            "location_id": "SF-1",
            "dba_name": "SF EXAMPLE",
            "location_start_date": "2020-01-01T00:00:00.000",
            "naics_code_description": "Retail",
            "location": {"latitude": "37.7749", "longitude": "-122.4194"},
        }
        ev = sla.parse_socrata_row(sf_row)
        assert ev is not None
        assert ev.city_id == "san_francisco"
