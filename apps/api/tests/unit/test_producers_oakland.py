"""Unit tests for the Oakland, CA leaf (US-223): spatial module + field
maps + producer parse wiring.

Oakland is a TWO-FEED PARTIAL metro on the official Socrata domain
``data.oaklandca.gov``: COMPLAINTS_311 (``quth-gb8e``, OAK 311 Call
Center, 1,185,559 rows) and CRIME (``ppgh-7dqv``, OPD CrimeWatch Data,
1,281,231 rows — coordinates AND address, clearing the ADR-0004 gate).
PERMITS (no dataset on the domain; Accela interactive-only), SLA (no
registry published), and DEEDS (Alameda County LANDATA unreachable) stay
unregistered.

Tests pass WITHOUT a spine registration (no CityId.OAKLAND, no REGISTRY
assertions — "oakland" stays a plain string). Spine-stable per the
wave-7 leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from the Socrata resource API:
311 rows ordered by ``$order=datetimeinit DESC`` (newest watermark
2026-08-28T04:59:31.000) plus a CLOSED row and a coordinate-less row;
crime rows from the CrimeWatch Data archive (newest case 26-036393 at
2026-08-25T22:57:00.000, one 1999 row, one 2004 row). Fixtures are RAW
Socrata JSON rows passed to the real ``parse_socrata_row`` path exactly
as ``SocrataClient.paginate`` yields them (no client-side flatten).

The srx/sry trap is pinned here: on quth-gb8e the columns carry WGS84
degrees (srx = longitude, sry = latitude) despite echoing St. Louis's
projected x/y names, while the ``reqaddress`` container is poisoned
(lat 30.0099 / lng -141.219 on SeeClickFix rows) and is never a map
candidate.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_oakland import (
    DROPPED_NONADDRESS_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    OAKLAND_311_FIELD_MAP,
    OAKLAND_CRIME_FIELD_MAP,
)
from src.spatial.cities.oakland import (
    OAKLAND_311_ENDPOINT,
    OAKLAND_CITY_ID,
    OAKLAND_CRIME_ENDPOINT,
    OAKLAND_DIVISION_BBOXES,
    OAKLAND_DIVISIONS,
    OAKLAND_FEED_SPECS,
    OAKLAND_GEOCODE_CONTEXT,
    OAKLAND_METRO_BBOX,
    OAKLAND_SUBMARKETS,
    REGISTRATION,
    get_oakland_dataset,
    is_in_greater_oakland_metro,
    is_in_oakland_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    """Pin the leaf field map until the spine registers OAKLAND in
    REGISTRY (afterwards ``resolve_field_map`` resolves it on its own)."""
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


# ---------------------------------------------------------------------------
# Live 311 fixtures (byte-verbatim, quth-gb8e, probe 2026-08-28 UTC).
# ---------------------------------------------------------------------------

# Newest row at probe time — SeeClickFix source. srx/sry are WGS84
# degrees (srx = longitude, sry = latitude); reqaddress carries the
# poisoned SeeClickFix placeholder (lat 30.0099 / lng -141.219).
_SR_1661517 = {
    "requestid": "1661517",
    "datetimeinit": "2026-08-28T04:59:31.000",
    "source": "SeeClickFix",
    "description": "Park - Sign",
    "reqcategory": "BLDGMAINT",
    "reqaddress": {
        "latitude": "30.009927006088322",
        "longitude": "-141.21915062082073",
    },
    "status": "PENDING",
    "srx": "-122.28556105813014",
    "sry": "37.81142799277458",
    "councildistrict": "CCD3",
    "beat": "05X",
    "probaddress": "1651 ADELINE ST",
    "city": "Oakland",
    "state": "CA",
    "zipcode": "94607",
}

# Newest CLOSED row at probe time — Phone source, closed 2h13m after init.
_SR_1661273 = {
    "requestid": "1661273",
    "datetimeinit": "2026-08-27T12:47:25.000",
    "source": "Phone",
    "description": "Tree - Broken/Hanging Limb",
    "reqcategory": "TREES",
    "reqaddress": {
        "latitude": "30.00992696972717",
        "longitude": "-141.21915037126644",
    },
    "status": "CLOSED",
    "datetimeclosed": "2026-08-27T15:00:18.000",
    "srx": "-122.21075172862535",
    "sry": "37.780915622920716",
    "councildistrict": "CCD5",
    "beat": "24X",
    "probaddress": "2199 40TH AV",
    "city": "Oakland",
    "state": "CA",
    "zipcode": "94601",
}

# CLOSED row with NO srx/sry keys at all (2% of the dataset) — exercises
# the ADR-0004 geocode supplement on probaddress.
_SR_1661212 = {
    "requestid": "1661212",
    "datetimeinit": "2026-08-27T11:06:40.000",
    "source": "Phone or Email",
    "description": "Watershed and Creeks - Other/Complex",
    "reqcategory": "WATERSHED",
    "status": "CLOSED",
    "datetimeclosed": "2026-08-27T11:10:28.000",
    "probaddress": "4120 redwood road",
    "city": "Oakland",
    "state": "CA",
    "zipcode": "94612",
}

# ---------------------------------------------------------------------------
# Live crime fixtures (byte-verbatim, ppgh-7dqv, probe 2026-08-28 UTC).
# ---------------------------------------------------------------------------

# Newest case at probe time (2026-08-25T22:57) — one of THREE descriptions
# sharing casenumber 26-036393 (multi-offense case; casenumber alone is
# not an id).
_CRIME_26_036393A = {
    "crimetype": "FELONY ASSAULT",
    "datetime": "2026-08-25T22:57:00.000",
    "casenumber": "26-036393",
    "description": "ASSAULT WITH FIREARM ON PERSON",
    "policebeat": "17Y",
    "address": "1100 E 28TH ST",
    "city": "Oakland",
    "state": "CA",
    "location": {"type": "Point", "coordinates": [-122.23658, 37.79991]},
}

# Same case, second description — the composite-id evidence row.
_CRIME_26_036393B = {
    "crimetype": "FELONY ASSAULT",
    "datetime": "2026-08-25T22:57:00.000",
    "casenumber": "26-036393",
    "description": "SHOOT AT UNOCCUPIED DWELLING/VEHICLE/ETC",
    "policebeat": "17Y",
    "address": "1100 E 28TH ST",
    "city": "Oakland",
    "state": "CA",
    "location": {"type": "Point", "coordinates": [-122.23658, 37.79991]},
}

# 1999 archive row with location but NO policebeat and NO address.
_CRIME_99_102329 = {
    "crimetype": "FORCIBLE RAPE",
    "datetime": "1999-10-11T00:00:00.000",
    "casenumber": "99-102329",
    "description": "RAPE BY FORCE/FEAR/ETC",
    "city": "Oakland",
    "state": "CA",
    "location": {"type": "Point", "coordinates": [-122.27307, 37.80508]},
}

# 2004 archive row — ordinary beat + address + location.
_CRIME_04_123489 = {
    "crimetype": "BURGLARY",
    "datetime": "2004-11-11T00:00:00.000",
    "casenumber": "04-123489",
    "description": "BURGLARY-AUTO",
    "policebeat": "13Y",
    "address": "5700 MERRIEWOOD DR",
    "city": "Oakland",
    "state": "CA",
    "location": {"type": "Point", "coordinates": [-122.21383, 37.83573]},
}


class TestOaklandSpatial:
    def test_metro_bbox_sanity(self):
        assert OAKLAND_METRO_BBOX["min_lat"] < OAKLAND_METRO_BBOX["max_lat"]
        assert OAKLAND_METRO_BBOX["min_lng"] < OAKLAND_METRO_BBOX["max_lng"]

    def test_is_in_oakland_metro_rejects_missing_coordinates(self):
        assert is_in_oakland_metro(None, None) is False
        assert is_in_oakland_metro(37.8040, None) is False
        assert is_in_oakland_metro(None, -122.2712) is False

    def test_is_in_oakland_metro_rejects_other_cities(self):
        assert is_in_oakland_metro(37.7749, -122.4194) is False   # San Francisco
        assert is_in_oakland_metro(37.3352, -121.8915) is False   # San Jose
        assert is_in_oakland_metro(37.8044, -122.2712 + 1.0) is False  # far bay
        assert is_in_oakland_metro(36.9741, -122.0308) is False   # Santa Cruz

    def test_downtown_anchors_are_contained(self):
        assert is_in_oakland_metro(37.8040, -122.2712)  # Frank Ogawa Plaza
        assert is_in_oakland_metro(37.7970, -122.2560)  # Lake Merritt shore
        assert is_in_oakland_metro(37.8410, -122.2530)  # Rockridge College Ave
        assert is_in_oakland_metro(37.7750, -122.2150)  # Fruitvale BART
        assert is_in_oakland_metro(37.7320, -122.1900)  # Eastmont Town Center
        assert is_in_oakland_metro(37.7126, -122.2212)  # OAK airport

    def test_live_fixture_coordinates_are_contained(self):
        points = [
            (_SR_1661517, _SR_1661273, _CRIME_26_036393A, _CRIME_04_123489),
        ]
        for sr, sr2, crime, crime2 in points:
            assert is_in_oakland_metro(float(sr["sry"]), float(sr["srx"]))
            assert is_in_oakland_metro(float(sr2["sry"]), float(sr2["srx"]))
            assert is_in_oakland_metro(
                crime["location"]["coordinates"][1],
                crime["location"]["coordinates"][0],
            )
            assert is_in_oakland_metro(
                crime2["location"]["coordinates"][1],
                crime2["location"]["coordinates"][0],
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in OAKLAND_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= OAKLAND_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= OAKLAND_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= OAKLAND_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= OAKLAND_METRO_BBOX["max_lng"], name

    def test_division_bboxes_are_pairwise_disjoint(self):
        names = list(OAKLAND_DIVISION_BBOXES)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                ba, bb = OAKLAND_DIVISION_BBOXES[a], OAKLAND_DIVISION_BBOXES[b]
                overlaps_lat = ba["min_lat"] < bb["max_lat"] and bb["min_lat"] < ba["max_lat"]
                overlaps_lng = ba["min_lng"] < bb["max_lng"] and bb["min_lng"] < ba["max_lng"]
                assert not (overlaps_lat and overlaps_lng), (a, b)

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in OAKLAND_SUBMARKETS.items():
            bbox = OAKLAND_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in OAKLAND_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(OAKLAND_SUBMARKETS)

    def test_submarkets_carry_the_oakland_city_id(self):
        assert {m.city_id for m in OAKLAND_SUBMARKETS.values()} == {"oakland"}

    def test_city_id_and_registration_shape(self):
        assert OAKLAND_CITY_ID == "oakland"
        assert REGISTRATION.metro_bbox is OAKLAND_METRO_BBOX
        assert REGISTRATION.submarkets is OAKLAND_SUBMARKETS
        assert REGISTRATION.division_bboxes is OAKLAND_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_oakland_metro
        assert len(REGISTRATION.divisions) == 7
        assert len(OAKLAND_SUBMARKETS) == 13

    def test_required_real_neighborhoods_present(self):
        assert set(OAKLAND_SUBMARKETS) == {
            "West Oakland",
            "Downtown Oakland",
            "Uptown",
            "Lake Merritt",
            "Grand Lake",
            "Temescal",
            "Rockridge",
            "Montclair",
            "Skyline Hills",
            "Fruitvale",
            "San Antonio",
            "Eastmont",
            "Elmhurst",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_oakland_metro is is_in_oakland_metro


class TestOaklandFieldMaps:
    def test_311_map_reads_live_columns(self):
        assert OAKLAND_311_FIELD_MAP["incident_id"] == ["requestid"]
        assert OAKLAND_311_FIELD_MAP["latitude"] == ["sry"]
        assert OAKLAND_311_FIELD_MAP["longitude"] == ["srx"]
        assert OAKLAND_311_FIELD_MAP["created_date"] == ["datetimeinit"]
        assert OAKLAND_311_FIELD_MAP["closed_date"] == ["datetimeclosed"]
        assert OAKLAND_311_FIELD_MAP["complaint_type"] == ["reqcategory"]
        assert OAKLAND_311_FIELD_MAP["borough"] == ["councildistrict"]
        assert OAKLAND_311_FIELD_MAP["incident_address"] == ["probaddress"]
        assert OAKLAND_311_FIELD_MAP["zipcode"] == ["zipcode"]

    def test_crime_map_reads_live_columns(self):
        assert OAKLAND_CRIME_FIELD_MAP["incident_id"] == ["casenumber"]
        assert OAKLAND_CRIME_FIELD_MAP["offense_type"] == ["crimetype"]
        assert OAKLAND_CRIME_FIELD_MAP["occurred_date"] == ["datetime"]
        assert OAKLAND_CRIME_FIELD_MAP["borough"] == ["policebeat"]
        assert OAKLAND_CRIME_FIELD_MAP["address"] == ["address"]

    def test_crime_coordinates_stay_unmapped_point_container_fallback(self):
        """The point container is read by the crime parser's GeoJSON
        fallback; a latitude/longitude candidate would feed it the
        coordinates LIST instead of floats."""
        assert "latitude" not in OAKLAND_CRIME_FIELD_MAP
        assert "longitude" not in OAKLAND_CRIME_FIELD_MAP
        coords = first_mapped(
            _CRIME_04_123489, OAKLAND_CRIME_FIELD_MAP, "latitude", "longitude"
        )
        assert coords is None

    def test_poisoned_reqaddress_container_is_never_a_candidate(self):
        mapped = {c for values in FIELD_MAP.values() for c in values}
        assert mapped
        assert "reqaddress" not in mapped
        assert "reqaddress" in DROPPED_NONADDRESS_COLUMNS
        # The poison value would never resolve to Oakland degrees.
        assert abs(float(_SR_1661517["reqaddress"]["latitude"])) <= 90
        assert float(_SR_1661517["reqaddress"]["latitude"]) == pytest.approx(30.009927006088322)
        assert float(_SR_1661517["sry"]) == pytest.approx(37.81142799277458)

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {
            "311": OAKLAND_311_FIELD_MAP,
            "crime": OAKLAND_CRIME_FIELD_MAP,
        }
        assert GEOCODE_CONTEXT == "Oakland, CA"
        assert OAKLAND_GEOCODE_CONTEXT == "Oakland, CA"


class TestOakland311Parsing:
    @pytest.fixture
    def producer(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_newest_fixture_parses_srx_sry_as_degrees(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = producer.parse_socrata_row(_SR_1661517, city_id="oakland")
        assert event is not None
        assert event.city_id == "oakland"
        assert event.incident_id == "1661517"
        assert event.latitude == pytest.approx(37.81142799277458)
        assert event.longitude == pytest.approx(-122.28556105813014)
        assert event.complaint_type == "BLDGMAINT"
        assert event.descriptor is None
        assert event.zipcode == "94607"
        assert event.created_date.isoformat().startswith("2026-08-28T04:59:31")
        assert event.closed_date is None
        assert event.source_neighborhood == "CCD3"
        assert event.h3_res7 is not None
        assert event.h3_res9 is not None
        assert is_in_oakland_metro(event.latitude, event.longitude)

    def test_closed_fixture_carries_closed_date(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = producer.parse_socrata_row(_SR_1661273, city_id="oakland")
        assert event is not None
        assert event.incident_id == "1661273"
        assert event.complaint_type == "TREES"
        assert event.closed_date is not None
        assert event.closed_date.isoformat().startswith("2026-08-27T15:00:18")
        assert event.latitude == pytest.approx(37.780915622920716)
        assert event.source_neighborhood == "CCD5"

    def test_row_without_srx_sry_resolves_through_the_geocode_fallback(
        self, producer, monkeypatch
    ):
        """2% of live rows carry no srx/sry. Call-args/counts are
        spine-volatile and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch, "311")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (37.8022, -122.2645),
        )
        event = producer.parse_socrata_row(_SR_1661212, city_id="oakland")
        assert event is not None
        assert event.incident_id == "1661212"
        assert event.latitude == pytest.approx(37.8022)
        assert event.longitude == pytest.approx(-122.2645)
        assert event.h3_res7 is not None

    def test_coordinate_less_row_dropped_when_geocode_fails(
        self, producer, monkeypatch
    ):
        _patch_resolve(monkeypatch, "311")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert producer.parse_socrata_row(_SR_1661212, city_id="oakland") is None

    def test_projected_feet_in_srx_sry_never_emit_as_degrees(
        self, producer, monkeypatch
    ):
        """If the city ever flips srx/sry to projected feet (the St. Louis
        namesake), the producer's projected-coordinate guard nulls them and
        the row falls to geocode — never fake degrees."""
        _patch_resolve(monkeypatch, "311")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        record = dict(_SR_1661517)
        record["srx"] = "-2428800.0"   # state-plane-feet-shaped garbage
        record["sry"] = "704000.0"
        assert producer.parse_socrata_row(record, city_id="oakland") is None

    def test_row_without_any_id_is_dropped(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = dict(_SR_1661517)
        record.pop("requestid")
        assert producer.parse_socrata_row(record, city_id="oakland") is None


class TestOaklandCrimeParsing:
    @pytest.fixture
    def producer(self):
        with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
            from src.producers.crime_incidents_producer import CrimeIncidentsProducer

            return CrimeIncidentsProducer()

    def test_newest_fixture_parses_through_the_point_container(
        self, producer, monkeypatch
    ):
        _patch_resolve(monkeypatch, "crime")
        event = producer.parse_socrata_row(_CRIME_26_036393A, city_id="oakland")
        assert event is not None
        assert event.city_id == "oakland"
        assert event.incident_id == "26-036393"
        assert event.offense_type == "FELONY ASSAULT"
        assert event.description == "ASSAULT WITH FIREARM ON PERSON"
        assert event.offense_class == "PART1"
        assert event.occurred_date is not None
        assert event.occurred_date.isoformat().startswith("2026-08-25T22:57:00")
        assert event.latitude == pytest.approx(37.79991)
        assert event.longitude == pytest.approx(-122.23658)
        assert event.source_neighborhood == "17Y"
        assert event.h3_res7 is not None
        assert is_in_oakland_metro(event.latitude, event.longitude)

    def test_casenumber_repeats_across_multi_offense_case(
        self, producer, monkeypatch
    ):
        """Live case 26-036393 carries three descriptions: both rows parse
        with the same incident_id — the spec's id_keys pair casenumber with
        description so acquisition dedup stays row-exact."""
        _patch_resolve(monkeypatch, "crime")
        a = producer.parse_socrata_row(_CRIME_26_036393A, city_id="oakland")
        b = producer.parse_socrata_row(_CRIME_26_036393B, city_id="oakland")
        assert a is not None and b is not None
        assert a.incident_id == b.incident_id == "26-036393"
        assert a.description != b.description

    def test_archive_row_without_beat_or_address_still_parses(
        self, producer, monkeypatch
    ):
        _patch_resolve(monkeypatch, "crime")
        event = producer.parse_socrata_row(_CRIME_99_102329, city_id="oakland")
        assert event is not None
        assert event.incident_id == "99-102329"
        assert event.offense_type == "FORCIBLE RAPE"
        assert event.offense_class == "PART1"
        assert event.latitude == pytest.approx(37.80508)
        assert event.longitude == pytest.approx(-122.27307)
        assert event.source_neighborhood is None
        assert is_in_oakland_metro(event.latitude, event.longitude)

    def test_null_location_resolves_through_the_geocode_fallback(
        self, producer, monkeypatch
    ):
        """4.6% of live rows carry a null location container; the ADR-0004
        supplement geocodes the address text. Call-args/counts are
        spine-volatile and not asserted."""
        _patch_resolve(monkeypatch, "crime")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (37.83573, -122.21383),
        )
        record = dict(_CRIME_04_123489)
        record.pop("location")
        event = producer.parse_socrata_row(record, city_id="oakland")
        assert event is not None
        assert event.incident_id == "04-123489"
        assert event.offense_type == "BURGLARY"
        assert event.offense_class == "PART1"
        assert event.latitude == pytest.approx(37.83573)
        assert event.longitude == pytest.approx(-122.21383)
        assert event.h3_res9 is not None

    def test_null_location_dropped_when_geocode_fails(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        record = dict(_CRIME_04_123489)
        record.pop("location")
        assert producer.parse_socrata_row(record, city_id="oakland") is None

    def test_row_without_any_id_is_dropped(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        record = dict(_CRIME_04_123489)
        record.pop("casenumber")
        assert producer.parse_socrata_row(record, city_id="oakland") is None


class TestOaklandFeedSpec:
    def test_311_spec_matches_live_dataset(self):
        spec = get_oakland_dataset(FeedType.COMPLAINTS_311)
        assert spec.platform == "socrata"
        assert spec.endpoint == OAKLAND_311_ENDPOINT
        assert spec.watermark_col == "datetimeinit"
        assert spec.id_keys == ["requestid"]
        assert spec.topic == "raw.municipal.311"
        assert spec.interval_seconds == 180.0
        assert spec.producer_key == "311"
        assert spec.expected_cadence_days == 1
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Oakland, CA"
        assert spec.field_map == OAKLAND_311_FIELD_MAP

    def test_crime_spec_matches_live_dataset(self):
        spec = get_oakland_dataset(FeedType.CRIME)
        assert spec.platform == "socrata"
        assert spec.endpoint == OAKLAND_CRIME_ENDPOINT
        assert spec.watermark_col == "datetime"
        assert spec.id_keys == ["casenumber", "description"]
        assert spec.topic == "raw.municipal.crime"
        assert spec.interval_seconds == 1800.0
        assert spec.producer_key == "crime"
        assert spec.expected_cadence_days == 1
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Oakland, CA"
        assert spec.field_map == OAKLAND_CRIME_FIELD_MAP

    def test_registered_feed_set_is_311_and_crime_only(self):
        assert set(OAKLAND_FEED_SPECS) == {"311", "crime"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_oakland_dataset(FeedType.PERMITS)
        assert "oakland" in str(exc.value)
        assert "311" in str(exc.value)
        assert "crime" in str(exc.value)

    def test_endpoints_are_the_probed_socrata_datasets(self):
        assert "data.oaklandca.gov" in OAKLAND_311_ENDPOINT
        assert "quth-gb8e" in OAKLAND_311_ENDPOINT
        assert "data.oaklandca.gov" in OAKLAND_CRIME_ENDPOINT
        assert "ppgh-7dqv" in OAKLAND_CRIME_ENDPOINT
