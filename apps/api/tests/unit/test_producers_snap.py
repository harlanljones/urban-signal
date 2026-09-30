"""US-364: USDA FNS SNAP Retailer Locator registered as FeedType.SLA.

The SNAP registration reuses the existing SLALicenseEvent machinery — no new
producer code. One national ArcGIS FeatureServer (usda-fns org, item
8b260f9a10b0459aa441ad8588c2251c) is sliced per metro with a where clause on
its state and its metro bbox, so every spec comes from the shared
``snap_sla_spec`` helper (six-metro starter set in 965b312, then extended to
every remaining SLA-less registered metro in the US-364 follow-up). The bbox
term arrived on 2026-09-30: a state-only slice handed every metro in a state
the same first 1,000 retailers by ObjectId.

Probed live 2026-08-27:

* Layer fields: Record_ID / Store_Name / Store_Street_Address /
  Additonal_Address (sic) / City / State / Zip_Code / Zip4 / County /
  Store_Type / Latitude / Longitude / Incentive_Program / Grantee_Name /
  ObjectId. Record_ID is unique across all 252,080 rows (groupBy outStatistics
  max group size 1) and is the retailer/record number -> license_id.
* The live layer carries NO authorization-date fields (auth start/end exist
  only in FNS's static 2005-2025 historical zip, frozen at 2025-12-31), so
  events carry null issued/expiry and the feed ingests as a snapshot: a full
  registry pull per cycle whose cross-run id-dedup diff is the open/close
  signal (KC SLA precedent, US-134).
* Cadence: FNS states "The data is updated every 2 weeks" (item description);
  editingInfo.lastEditDate was 2026-08-19 at probe -> expected_cadence_days=14.

Fixture rows below are live captures per starter metro (Dallas, Denver,
Wichita) in raw ArcGIS feature shape, flattened through the production
``_flatten_feature`` so parser tests see exactly what the paginating client
delivers: attributes plus geometry lifted onto lowercase latitude/longitude.
"""

import pytest

from src.spatial.city_registry import SNAP_SLA_FIELD_MAP

SNAP_ENDPOINT_FRAG = (
    "services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/"
    "snap_retailer_location_data/FeatureServer/0"
)

# US-364 starter set: geographically spread SLA-less metros (one per state).
# dallas/denver left the set in the US-372 spine hold: their SLA slots were
# taken by the real TABC / CO liquor registries.
SNAP_STARTER_METROS = [
    ("columbus", "OH"),
    ("raleigh", "NC"),
    ("boise", "ID"),
    ("wichita", "KS"),
]

# US-364 extension: every remaining SLA-less registered metro at edit time.
# Metros sharing a state each carry their own spec with the same filter
# (dallas/fort_worth both TX in the starter shape) — duplication accepted.
# houston/san_antonio left the set in the US-372 spine hold (TABC slices).
SNAP_EXTENDED_METROS = [
    ("albuquerque", "NM"),
    ("charlotte", "NC"),
    ("chattanooga", "TN"),
    ("cleveland", "OH"),
    ("dayton", "OH"),
    ("durham", "NC"),
    ("el_paso", "TX"),
    ("fort_worth", "TX"),
    ("honolulu", "HI"),
    ("indianapolis", "IN"),
    ("las_vegas", "NV"),
    ("memphis", "TN"),
    ("pierce", "WA"),
    ("pittsburgh", "PA"),
    ("prince_georges", "MD"),
    ("reno", "NV"),
    ("sacramento", "CA"),
    ("san_jose", "CA"),
    ("tulsa", "OK"),
]

# Every SNAP metro's state and the retailers inside its state and metro bbox,
# counted live 2026-09-30 with the spec's own where clause (returnCountOnly).
# A snapshot poll reads at most its job's batch_limit rows (1000 unless the
# spec declares more), so each cap must clear its metro's count with room to
# grow. docs/research/snap-metro-scope-2026-09-30.md has the statewide counts.
SNAP_METRO_RETAILERS = {
    "albuquerque": ("NM", 412),
    "alexandria": ("LA", 85),
    "anchorage": ("AK", 111),
    "asheville": ("NC", 175),
    "augusta": ("GA", 305),
    "boise": ("ID", 231),
    "canton": ("OH", 248),
    "cape_coral": ("FL", 429),
    "charleston_sc": ("SC", 433),
    "charlotte": ("NC", 1036),
    "chattanooga": ("TN", 386),
    "cleveland": ("OH", 948),
    "columbus": ("OH", 1080),
    "columbus_ga": ("GA", 193),
    "dallas": ("TX", 1970),
    "dayton": ("OH", 774),
    "denver": ("CO", 1202),
    "durham": ("NC", 208),
    "el_paso": ("TX", 600),
    "evansville": ("IN", 188),
    "fort_smith": ("AR", 114),
    "fort_worth": ("TX", 1806),
    "gainesville": ("FL", 149),
    "greenville": ("SC", 219),
    "honolulu": ("HI", 505),
    "houston": ("TX", 4205),
    "huntsville": ("AL", 261),
    "indianapolis": ("IN", 946),
    "jackson_ms": ("MS", 316),
    "jonesboro": ("AR", 88),
    "lake_charles": ("LA", 148),
    "lakeland": ("FL", 210),
    "las_vegas": ("NV", 1317),
    "lexington": ("KY", 254),
    "macon_bibb": ("GA", 209),
    "madison": ("WI", 303),
    "melbourne": ("FL", 422),
    "memphis": ("TN", 825),
    "monroe": ("LA", 129),
    "ocala": ("FL", 310),
    "omaha": ("NE", 387),
    "pierce": ("WA", 896),
    "pittsburgh": ("PA", 526),
    "port_st_lucie": ("FL", 177),
    "prince_georges": ("MD", 1078),
    "raleigh": ("NC", 1466),
    "reno": ("NV", 316),
    "rochester": ("NY", 400),
    "sacramento": ("CA", 1965),
    "san_antonio": ("TX", 1536),
    "san_jose": ("CA", 755),
    "seattle": ("WA", 1103),
    "tallahassee": ("FL", 242),
    "toledo": ("OH", 439),
    "tulsa": ("OK", 670),
    "wichita": ("KS", 378),
    "wilmington_nc": ("NC", 262),
}


def _flatten_feature(attributes: dict, geometry: dict) -> dict:
    """Run a raw ArcGIS feature through the production flattener so parser
    tests see exactly what SLALicensesProducer.paginate delivers."""
    from src.producers.arcgis_client import ArcGISClient

    # The live layer declares zero esriFieldTypeDate columns.
    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry}, date_fields=set()
    )


# Live row captured 2026-08-27 (where="State = 'TX' AND City = 'DALLAS'").
DALLAS_SNAP_FEATURE = {
    "attributes": {
        "Record_ID": 1448096,
        "Store_Name": "Park Lane Mart",
        "Store_Street_Address": "8209 Park Ln",
        "Additonal_Address": None,
        "City": "Dallas",
        "State": "TX",
        "Zip_Code": "75231",
        "Zip4": "6022",
        "County": "DALLAS",
        "Store_Type": "Convenience Store",
        "Latitude": 32.87183,
        "Longitude": -96.76413,
        "Incentive_Program": None,
        "Grantee_Name": None,
        "ObjectId": 196,
    },
    "geometry": {"x": -96.76413000000001, "y": 32.87183},
}

# Live row captured 2026-08-27 (where="State = 'CO' AND City = 'DENVER'").
DENVER_SNAP_FEATURE = {
    "attributes": {
        "Record_ID": 1698883,
        "Store_Name": "QuikTrip 4204",
        "Store_Street_Address": "17410 Green Valley Ranch Blvd",
        "Additonal_Address": None,
        "City": "Denver",
        "State": "CO",
        "Zip_Code": "80249",
        "Zip4": "9041",
        "County": "DENVER",
        "Store_Type": "Convenience Store",
        "Latitude": 39.783176,
        "Longitude": -104.78581,
        "Incentive_Program": None,
        "Grantee_Name": None,
        "ObjectId": 94,
    },
    "geometry": {"x": -104.78581, "y": 39.783176000000005},
}

# Live row captured 2026-08-27 (where="State = 'KS' AND City = 'WICHITA'").
WICHITA_SNAP_FEATURE = {
    "attributes": {
        "Record_ID": 1690538,
        "Store_Name": "Amigos Market",
        "Store_Street_Address": "840 S Oliver Ave",
        "Additonal_Address": None,
        "City": "Wichita",
        "State": "KS",
        "Zip_Code": "67218",
        "Zip4": "2329",
        "County": "SEDGWICK",
        "Store_Type": "Convenience Store",
        "Latitude": 37.672279,
        "Longitude": -97.279945,
        "Incentive_Program": None,
        "Grantee_Name": None,
        "ObjectId": 385,
    },
    "geometry": {"x": -97.27994499999998, "y": 37.672278999999996},
}


@pytest.fixture
def snap_producer():
    from unittest.mock import patch

    from src.producers.sla_licenses_producer import SLALicensesProducer

    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        return SLALicensesProducer(bootstrap_servers="localhost:9092")


class TestSnapRegistrationShape:
    def test_starter_set_registers_sla_specs(self):
        from src.spatial.city_registry import (
            REGISTRY,
            CityId,
            FeedType,
            get_dataset,
            snap_sla_where,
        )

        expected = {
            CityId.COLUMBUS: "OH",
            CityId.RALEIGH: "NC",
            CityId.BOISE: "ID",
            CityId.WICHITA: "KS",
        }
        for city, state in expected.items():
            spec = get_dataset(city, FeedType.SLA)
            assert spec.platform == "arcgis"
            assert SNAP_ENDPOINT_FRAG in spec.endpoint, city
            assert spec.where == snap_sla_where(state, REGISTRY[city].metro_bbox), city

    def test_starter_set_pinned_by_state_and_bbox_where_clauses(self):
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        expected = {
            CityId.COLUMBUS: (
                "State = 'OH' AND Latitude BETWEEN 39.75 AND 40.2"
                " AND Longitude BETWEEN -83.3 AND -82.7"
            ),
            CityId.RALEIGH: (
                "State = 'NC' AND Latitude BETWEEN 35.4 AND 36.15"
                " AND Longitude BETWEEN -79.5 AND -78.0"
            ),
            CityId.BOISE: (
                "State = 'ID' AND Latitude BETWEEN 43.43 AND 43.74"
                " AND Longitude BETWEEN -116.42 AND -116.03"
            ),
            CityId.WICHITA: (
                "State = 'KS' AND Latitude BETWEEN 37.4 AND 37.95"
                " AND Longitude BETWEEN -97.85 AND -97.05"
            ),
        }
        for city, where in expected.items():
            assert get_dataset(city, FeedType.SLA).where == where

    def test_specs_share_the_snap_snapshot_contract(self):
        """All 23 registrations share one endpoint/field-map helper and
        declare the verified-live acquisition contract: snapshot mode (no
        per-row date field exists), Record_ID/ObjectId ids, ObjectId OID,
        14-day cadence per FNS's published refresh statement."""
        from src.spatial.city_registry import FeedType, get_dataset, normalize_city

        specs = [
            get_dataset(normalize_city(city_value), FeedType.SLA)
            for city_value, _state in SNAP_STARTER_METROS + SNAP_EXTENDED_METROS
        ]
        for spec in specs:
            assert spec.ingestion_mode == "snapshot"
            assert spec.watermark_col == ""
            assert spec.id_keys == ["Record_ID", "ObjectId"]
            assert spec.oid_field == "ObjectId"
            assert spec.max_record_count == 1000
            assert spec.expected_cadence_days == 14
            assert spec.interval_seconds == 1800.0
            assert spec.producer_key == "sla"
            assert spec.needs_geocode is False
            # Each spec carries the shared SNAP map by value (the registry is
            # derived from the corpus, so spec.field_map == not object-identical
            # to the snapshot-contract helper anymore US-428).
            assert spec.field_map == SNAP_SLA_FIELD_MAP

    def test_snap_field_map_keys(self):
        assert SNAP_SLA_FIELD_MAP == {
            "license_id": ["Record_ID"],
            "license_type": ["Store_Type"],
            "dba": ["Store_Name"],
            "latitude": ["Latitude"],
            "longitude": ["Longitude"],
            "address_street": ["Store_Street_Address"],
            "borough": ["City"],
            "zipcode": ["Zip_Code"],
        }

    def test_field_map_resolves_for_starter_city(self):
        from src.producers.field_maps import resolve_field_map
        from src.spatial.city_registry import FeedType

        assert resolve_field_map("columbus", FeedType.SLA) == SNAP_SLA_FIELD_MAP
        assert resolve_field_map("wichita", FeedType.SLA) == SNAP_SLA_FIELD_MAP

    def test_extended_set_registers_sla_specs(self):
        """The US-364 extension: every remaining SLA-less registered metro
        gets its own SNAP spec with the same snapshot contract, sliced to its
        state's two-letter code inside its metro bbox (verified live)."""
        from src.spatial.city_registry import (
            REGISTRY,
            FeedType,
            get_dataset,
            normalize_city,
            snap_sla_where,
        )

        for city_value, state in SNAP_EXTENDED_METROS:
            city = normalize_city(city_value)
            spec = get_dataset(city, FeedType.SLA)
            assert SNAP_ENDPOINT_FRAG in spec.endpoint, city_value
            assert spec.where == snap_sla_where(state, REGISTRY[city].metro_bbox), city_value
            assert spec.ingestion_mode == "snapshot"
            assert spec.watermark_col == ""
            assert spec.expected_cadence_days == 14
            assert spec.field_map == SNAP_SLA_FIELD_MAP
            assert spec.needs_geocode is False

    def test_every_registered_metro_has_sla(self):
        """The extension closed the set; later waves registered metros whose
        probes found no SLA-grade feed (the 2026-09-06 mid-Atlantic wave
        registered deeds-only), and grand_rapids is geometry-only.
        Every other registered metro carries an SLA spec."""
        from src.spatial.city_registry import REGISTRY, FeedType, get_dataset

        sla_less = {
            "albany",
            "allentown",
            "billings",
            "bowling_green",
            "bozeman",
            "burlington",
            "chandler",
            "charleston_wv",
            "dover",
            "fort_collins",
            "frederick",
            "grand_rapids",
            "harrisburg",
            "huntington_wv",
            "laredo",
            "lincoln",
            "manchester",
            "missoula",
            "montgomery_al",
            "nampa",
            "peoria",
            "portland_maine",
            "providence",
            "richmond",
            "roanoke",
            "santa_fe",
            "savannah",
            "sioux_falls",
            "tempe",
            "topeka",
            "wilmington_de",
            "yakima",
        }
        for city_id in REGISTRY:
            if city_id.value in sla_less:
                with pytest.raises(KeyError):
                    get_dataset(city_id, FeedType.SLA)
                continue
            spec = get_dataset(city_id, FeedType.SLA)
            assert spec is not None, city_id


def _snap_specs():
    """Every registered SLA spec that reads the SNAP layer, by city."""
    from src.spatial.city_registry import REGISTRY, FeedType

    return {
        city_id.value: reg.datasets[FeedType.SLA]
        for city_id, reg in REGISTRY.items()
        if FeedType.SLA in reg.datasets
        and SNAP_ENDPOINT_FRAG in reg.datasets[FeedType.SLA].endpoint
    }


class TestSnapMetroScope:
    """A statewide SNAP filter handed every metro in a state the same first
    1,000 retailers by ObjectId (Tallahassee got 19 of its 242). Each spec is
    now its state inside its metro bbox, with a cap that covers the bbox."""

    def test_where_narrows_the_state_to_the_bbox(self):
        from src.spatial.city_registry import snap_sla_where

        bbox = {"min_lat": 30.29, "max_lat": 30.63, "min_lng": -84.7, "max_lng": -84.05}
        assert snap_sla_where("FL", bbox) == (
            "State = 'FL' AND Latitude BETWEEN 30.29 AND 30.63"
            " AND Longitude BETWEEN -84.7 AND -84.05"
        )

    def test_every_snap_spec_is_the_helper_for_its_metro(self):
        """Each corpus block is exactly what ``snap_sla_spec`` builds from the
        metro's state and bbox, so no block drifts back to a statewide slice."""
        from src.spatial.city_registry import REGISTRY, normalize_city, snap_sla_spec

        specs = _snap_specs()
        assert set(specs) == set(SNAP_METRO_RETAILERS)
        for city_value, spec in specs.items():
            state, _retailers = SNAP_METRO_RETAILERS[city_value]
            bbox = REGISTRY[normalize_city(city_value)].metro_bbox
            assert spec == snap_sla_spec(state, bbox, spec.batch_limit), city_value

    def test_every_cap_covers_its_metro_with_room_to_grow(self):
        """A snapshot poll that fills its cap never reads the rest, so each
        metro's cap clears its measured retailers by half again."""
        for city_value, spec in _snap_specs().items():
            _state, retailers = SNAP_METRO_RETAILERS[city_value]
            cap = spec.batch_limit or 1000
            assert cap >= 1.5 * retailers, (city_value, retailers, cap)
            # A cap is declared only where the default falls short.
            assert spec.batch_limit is None or 1.5 * retailers > 1000, city_value


@pytest.fixture
def snap_field_map(monkeypatch):
    """Pin the SNAP map for dallas/denver: both cities left the SNAP registry
    set in the US-372 spine hold (TABC / CO liquor took their SLA slots), so
    the live resolve_field_map no longer returns SNAP's map for them. The
    parser contract below is map-shaped, not registry-shaped."""

    def fake(city, feed):
        if city in ("dallas", "denver", "wichita"):
            return SNAP_SLA_FIELD_MAP
        return {}

    monkeypatch.setattr("src.producers.field_maps.resolve_field_map", fake)
    return fake


class TestSnapParsing:
    def test_dallas_row_parses_through_field_map(self, snap_field_map, snap_producer):
        row = _flatten_feature(
            DALLAS_SNAP_FEATURE["attributes"], DALLAS_SNAP_FEATURE["geometry"]
        )
        event = snap_producer.parse_socrata_row(row, city_id="dallas")
        assert event is not None
        assert event.city_id == "dallas"
        assert event.license_id == "1448096"  # field_map license_id <- Record_ID
        assert event.license_type == "Convenience Store"  # <- Store_Type
        assert event.dba == "Park Lane Mart"  # <- Store_Name
        assert event.address == "8209 Park Ln"  # <- Store_Street_Address
        assert event.borough == "NORTH_DALLAS_PRESTON"  # coordinate -> division
        assert event.source_neighborhood == "Dallas"  # <- City (field map)
        assert event.latitude == pytest.approx(32.87183)
        assert event.longitude == pytest.approx(-96.76413)
        # The live layer carries no date fields: null issued/expiry is the
        # honest wire shape (historical-zip backfill is a follow-up).
        assert event.effective_date is None
        assert event.expiration_date is None
        # No status column -> registry default ACTIVE.
        assert event.license_status == "ACTIVE"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None

    def test_denver_row_parses_with_global_h3_outside_bbox_check(self, snap_field_map, snap_producer):
        row = _flatten_feature(
            DENVER_SNAP_FEATURE["attributes"], DENVER_SNAP_FEATURE["geometry"]
        )
        event = snap_producer.parse_socrata_row(row, city_id="denver")
        assert event is not None
        assert event.city_id == "denver"
        assert event.license_id == "1698883"
        assert event.dba == "QuikTrip 4204"
        assert event.latitude == pytest.approx(39.783176)
        assert event.longitude == pytest.approx(-104.78581)
        assert event.h3_res7 is not None

    def test_wichita_row_parses_geometry_lift_matches_attributes(self, snap_producer):
        row = _flatten_feature(
            WICHITA_SNAP_FEATURE["attributes"], WICHITA_SNAP_FEATURE["geometry"]
        )
        # _flatten_feature lifts point geometry onto lowercase latitude/
        # longitude via setdefault; the attributes also carry Latitude/
        # Longitude. The field map reads the attribute spellings.
        assert row["Latitude"] == pytest.approx(row["latitude"])
        event = snap_producer.parse_socrata_row(row, city_id="wichita")
        assert event is not None
        assert event.city_id == "wichita"
        assert event.license_id == "1690538"
        assert event.license_type == "Convenience Store"
        assert event.address == "840 S Oliver Ave"
        assert event.latitude == pytest.approx(37.672279)
        assert event.longitude == pytest.approx(-97.279945)

    def test_missing_record_id_drops_the_row(self, snap_field_map, snap_producer):
        row = _flatten_feature(
            DALLAS_SNAP_FEATURE["attributes"], DALLAS_SNAP_FEATURE["geometry"]
        )
        row.pop("Record_ID")
        # No chain fallback spells SNAP's license id (the generic chains look
        # for location_id/location_account/certificate_number/...), so without
        # the field-map hit the row is unrepresentable and must drop.
        assert snap_producer.parse_socrata_row(row, city_id="dallas") is None

    def test_coordinate_less_row_emits_null_coord_event(self, snap_field_map, snap_producer):
        """Null-coord tolerance (DC Basic Business Licenses precedent): a row
        with a valid id but no lat/lng still emits with null H3 rather than
        being dropped — and, critically, files under no H3 cell."""
        attrs = dict(DALLAS_SNAP_FEATURE["attributes"])
        attrs["Latitude"] = None
        attrs["Longitude"] = None
        row = _flatten_feature(attrs, {})  # geometry-less capture too
        event = snap_producer.parse_socrata_row(row, city_id="dallas")
        assert event is not None
        assert event.license_id == "1448096"
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None
        assert event.h3_res8 is None
        assert event.h3_res9 is None
