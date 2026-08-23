"""Unit tests for the Seattle / King County registration and the ArcGIS client.

Seattle is the first city whose deeds feed is an ArcGIS FeatureServer rather than
a Socrata dataset, so these tests cover both the registry wiring and the paging,
date, and geometry behaviour that differ from Socrata. All HTTP is mocked; the
fixtures below mirror the real King County parcel-sales layer.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.arcgis_client import ArcGISClient
from src.spatial.cities.seattle import (
    SEATTLE_DIVISION_BBOXES,
    SEATTLE_DIVISIONS,
    SEATTLE_METRO_BBOX,
    SEATTLE_SUBMARKETS,
    is_in_seattle_metro,
)
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_job_name,
    normalize_city,
)

LAYER_URL = "https://example.com/arcgis/rest/services/PARCEL_SALES/FeatureServer/0"

LAYER_META = {
    "name": "Parcel sales history - last 3 years",
    "objectIdField": "OBJECTID",
    "maxRecordCount": 1000,
    "fields": [
        {"name": "PIN", "type": "esriFieldTypeString"},
        {"name": "ExciseTaxNum", "type": "esriFieldTypeInteger"},
        {"name": "SaleDate", "type": "esriFieldTypeDate"},
        {"name": "SalePrice", "type": "esriFieldTypeInteger"},
        {"name": "OBJECTID", "type": "esriFieldTypeOID"},
    ],
}

# A square parcel in north Seattle; centroid lands at roughly (47.7152, -122.3031).
RING = [
    [-122.302812218542, 47.7152886116842],
    [-122.302809330938, 47.7151233982326],
    [-122.303458702412, 47.7151292165643],
    [-122.303461546700, 47.7152944278857],
    [-122.302812218542, 47.7152886116842],
]


def _feature(oid: int) -> dict:
    return {
        "attributes": {
            "OBJECTID": oid,
            "PIN": f"990400{oid:04d}",
            "ExciseTaxNum": 3250340 + oid,
            # 2023-08-16T00:00:00Z as ArcGIS epoch milliseconds.
            "SaleDate": 1692144000000,
            "SalePrice": 760000,
        },
        "geometry": {"rings": [RING]},
    }


def _mock_response(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def _patch_http(pages):
    """Patch httpx.Client so the first GET returns layer metadata, then `pages`."""
    payloads = [LAYER_META, *pages]
    calls = {"n": 0}

    def _get(url, params=None, headers=None):
        payload = payloads[min(calls["n"], len(payloads) - 1)]
        calls["n"] += 1
        return _mock_response(payload)

    client = MagicMock()
    client.__enter__.return_value.get.side_effect = _get
    client.__exit__.return_value = False
    return patch("httpx.Client", return_value=client), calls


class TestSeattleRegistration:
    """The registry entry that ties seattle.py into the multi-city machinery."""

    def test_seattle_is_registered(self):
        assert CityId.SEATTLE in REGISTRY, "CityId.SEATTLE must have a REGISTRY entry"

    @pytest.mark.parametrize(
        "alias",
        ["seattle", "SEATTLE", "sea", "king_county", "king county", "puget sound", "bellevue"],
    )
    def test_aliases_resolve(self, alias):
        assert normalize_city(alias) is CityId.SEATTLE

    def test_every_alias_target_is_registered(self):
        """Guards the exact break this test file was added for: an alias that
        resolves to a CityId with no REGISTRY entry raises KeyError downstream."""
        from src.spatial.city_registry import ALIASES

        for alias, cid in ALIASES.items():
            assert cid in REGISTRY, f"alias {alias!r} resolves to unregistered {cid}"

    def test_registration_shape(self):
        reg = REGISTRY[CityId.SEATTLE]
        assert reg.state == "WA"
        assert reg.job_suffix == "seattle"
        assert reg.metro_bbox is SEATTLE_METRO_BBOX
        assert reg.division_bboxes is SEATTLE_DIVISION_BBOXES
        assert reg.submarkets is SEATTLE_SUBMARKETS
        assert reg.divisions is SEATTLE_DIVISIONS
        assert set(reg.datasets) == set(FeedType)

    def test_center_is_inside_metro_bbox(self):
        reg = REGISTRY[CityId.SEATTLE]
        assert is_in_seattle_metro(reg.center["lat"], reg.center["lng"])

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in SEATTLE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SEATTLE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SEATTLE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SEATTLE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SEATTLE_METRO_BBOX["max_lng"], name

    def test_job_names_are_namespaced(self):
        assert get_job_name(FeedType.PERMITS, CityId.SEATTLE) == "permits_seattle"
        assert get_job_name(FeedType.DEEDS, CityId.SEATTLE) == "deeds_seattle"

    def test_deeds_feed_is_arcgis_and_others_are_socrata(self):
        datasets = REGISTRY[CityId.SEATTLE].datasets
        assert datasets[FeedType.DEEDS].platform == "arcgis"
        for feed in (FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.SLA):
            assert datasets[feed].platform == "socrata"

    def test_watermark_columns_match_published_schemas(self):
        """Field names verified against the live dataset schemas."""
        datasets = REGISTRY[CityId.SEATTLE].datasets
        assert datasets[FeedType.PERMITS].watermark_col == "issueddate"
        assert datasets[FeedType.COMPLAINTS_311].watermark_col == "createddate"
        assert datasets[FeedType.SLA].watermark_col == "applicationdate"
        assert datasets[FeedType.DEEDS].watermark_col == "SaleDate"


class TestArcGISClient:
    """Paging, date coercion, and geometry reduction specific to ArcGIS."""

    @pytest.mark.parametrize(
        "given",
        [LAYER_URL, LAYER_URL + "/", LAYER_URL + "/query", LAYER_URL + "/query/"],
    )
    def test_layer_url_normalization(self, given):
        assert ArcGISClient._normalize_layer_url(given) == LAYER_URL

    def test_flattens_features_to_socrata_shaped_rows(self):
        ctx, _ = _patch_http([{"features": [_feature(1)], "exceededTransferLimit": False}])
        with ctx:
            rows = ArcGISClient().fetch_records(LAYER_URL, limit=10)
        assert len(rows) == 1
        assert rows[0]["PIN"] == "9904000001"
        assert "attributes" not in rows[0]

    def test_date_fields_become_iso_strings(self):
        ctx, _ = _patch_http([{"features": [_feature(1)], "exceededTransferLimit": False}])
        with ctx:
            rows = ArcGISClient().fetch_records(LAYER_URL, limit=10)
        assert rows[0]["SaleDate"].startswith("2023-08-16T")

    def test_non_date_numeric_fields_are_left_alone(self):
        ctx, _ = _patch_http([{"features": [_feature(1)], "exceededTransferLimit": False}])
        with ctx:
            rows = ArcGISClient().fetch_records(LAYER_URL, limit=10)
        assert rows[0]["SalePrice"] == 760000
        assert rows[0]["ExciseTaxNum"] == 3250341

    def test_polygon_rings_reduce_to_a_centroid(self):
        """Parcel layers serve polygons; without this the row has no coordinate
        and every downstream H3 index would be null."""
        ctx, _ = _patch_http([{"features": [_feature(1)], "exceededTransferLimit": False}])
        with ctx:
            rows = ArcGISClient().fetch_records(LAYER_URL, limit=10)
        assert rows[0]["latitude"] == pytest.approx(47.7152, abs=1e-3)
        assert rows[0]["longitude"] == pytest.approx(-122.3031, abs=1e-3)
        assert is_in_seattle_metro(rows[0]["latitude"], rows[0]["longitude"])

    def test_point_geometry_is_used_directly(self):
        feat = _feature(1)
        feat["geometry"] = {"x": -122.3321, "y": 47.6062}
        ctx, _ = _patch_http([{"features": [feat], "exceededTransferLimit": False}])
        with ctx:
            rows = ArcGISClient().fetch_records(LAYER_URL, limit=10)
        assert rows[0]["latitude"] == pytest.approx(47.6062)
        assert rows[0]["longitude"] == pytest.approx(-122.3321)

    def test_missing_geometry_yields_no_coordinates(self):
        feat = _feature(1)
        feat.pop("geometry")
        ctx, _ = _patch_http([{"features": [feat], "exceededTransferLimit": False}])
        with ctx:
            rows = ArcGISClient().fetch_records(LAYER_URL, limit=10)
        assert "latitude" not in rows[0]

    def test_paginate_continues_while_transfer_limit_exceeded(self):
        """A short page is not proof of exhaustion on ArcGIS: the server caps the
        page and flags it, so paging must follow the flag, not the row count."""
        pages = [
            {"features": [_feature(1), _feature(2)], "exceededTransferLimit": True},
            {"features": [_feature(3)], "exceededTransferLimit": False},
        ]
        ctx, _ = _patch_http(pages)
        with ctx:
            batches = list(ArcGISClient().paginate(LAYER_URL, batch_size=10))
        assert [len(b) for b in batches] == [2, 1]

    def test_paginate_stops_on_empty_page(self):
        pages = [
            {"features": [_feature(1)], "exceededTransferLimit": True},
            {"features": [], "exceededTransferLimit": False},
        ]
        ctx, _ = _patch_http(pages)
        with ctx:
            batches = list(ArcGISClient().paginate(LAYER_URL, batch_size=10))
        assert [len(b) for b in batches] == [1]

    def test_paginate_honours_max_records(self):
        pages = [{"features": [_feature(i) for i in range(3)], "exceededTransferLimit": True}] * 5
        ctx, _ = _patch_http(pages)
        with ctx:
            batches = list(ArcGISClient().paginate(LAYER_URL, batch_size=3, max_records=6))
        assert sum(len(b) for b in batches) == 6

    def test_page_size_is_clamped_to_server_max_record_count(self):
        seen = {}

        def _get(url, params=None, headers=None):
            if params and params.get("f") == "json" and "where" not in params:
                return _mock_response(LAYER_META)
            seen.update(params or {})
            return _mock_response({"features": [], "exceededTransferLimit": False})

        client = MagicMock()
        client.__enter__.return_value.get.side_effect = _get
        client.__exit__.return_value = False
        with patch("httpx.Client", return_value=client):
            ArcGISClient().fetch_records(LAYER_URL, limit=999_999)
        assert seen["resultRecordCount"] == LAYER_META["maxRecordCount"]

    def test_default_where_clause_matches_everything(self):
        seen = {}

        def _get(url, params=None, headers=None):
            if params and params.get("f") == "json" and "where" not in params:
                return _mock_response(LAYER_META)
            seen.update(params or {})
            return _mock_response({"features": [], "exceededTransferLimit": False})

        client = MagicMock()
        client.__enter__.return_value.get.side_effect = _get
        client.__exit__.return_value = False
        with patch("httpx.Client", return_value=client):
            ArcGISClient().fetch_records(LAYER_URL)
        assert seen["where"] == "1=1"
        assert seen["orderByFields"] == "OBJECTID"

    def test_arcgis_error_body_raises_despite_http_200(self):
        """ArcGIS reports failures inside a 200 response, so status alone is not enough."""
        payload = {"error": {"code": 400, "message": "Invalid where clause", "details": []}}
        ctx, _ = _patch_http([payload])
        with ctx, pytest.raises(RuntimeError, match="Invalid where clause"):
            ArcGISClient().fetch_records(LAYER_URL, where_clause="bogus =")

    def test_layer_metadata_is_cached_across_calls(self):
        ctx, calls = _patch_http([{"features": [], "exceededTransferLimit": False}] * 4)
        with ctx:
            c = ArcGISClient()
            c.fetch_records(LAYER_URL)
            before = calls["n"]
            c.fetch_records(LAYER_URL)
            after = calls["n"]
        # Second call issues only the query, not another metadata fetch.
        assert after - before == 1

    def test_satisfies_paginating_client_protocol(self):
        from src.spatial.city_registry import PaginatingClient

        assert isinstance(ArcGISClient(), PaginatingClient)


class TestSeattleDeedParsing:
    """King County's ArcGIS layer uses PascalCase attribute names, so the deed
    parser's lowercase Socrata fallback chains had to learn them. Without this
    every Seattle row parsed to an empty doc_id and was silently dropped."""

    @pytest.fixture
    def producer(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @pytest.fixture
    def row(self):
        return {
            "PIN": "9904000063",
            "ExciseTaxNum": 3250340,
            "SaleDate": "2023-08-16T00:00:00+00:00",
            "SalePrice": 760000,
            "Property_Type": "Improved",
            "Sellername": "GLEIBERMAN ZACKARY",
            "buyername": "PRESTON HEATHER",
            "latitude": 47.71521,
            "longitude": -122.30314,
        }

    def test_row_parses_instead_of_being_dropped(self, producer, row):
        assert producer.parse_socrata_row(row, city_id="seattle") is not None

    def test_core_fields_map_from_pascalcase(self, producer, row):
        ev = producer.parse_socrata_row(row, city_id="seattle")
        assert ev.city_id == "seattle"
        assert ev.doc_id == "3250340"          # ExciseTaxNum
        assert ev.bbl == "9904000063"          # PIN
        assert ev.document_amount == 760000.0  # SalePrice
        assert str(ev.recorded_date).startswith("2023-08-16")
        assert ev.party1_grantor == "GLEIBERMAN ZACKARY"
        assert ev.party2_grantee == "PRESTON HEATHER"

    def test_coordinates_produce_h3_indexes(self, producer, row):
        ev = producer.parse_socrata_row(row, city_id="seattle")
        assert ev.h3_res7 and ev.h3_res8 and ev.h3_res9

    def test_city_autodetects_from_king_county_fields(self, producer, row):
        """No explicit city_id: the ArcGIS-only columns must not fall through to nyc."""
        assert producer.parse_socrata_row(row).city_id == "seattle"

    def test_zero_price_sale_still_parses(self, producer, row):
        """Non-arms-length transfers record a $0 price and must not be dropped."""
        row["SalePrice"] = 0
        ev = producer.parse_socrata_row(row, city_id="seattle")
        assert ev is not None
        assert ev.document_amount == 0.0

    def test_deeds_producer_selects_arcgis_client_for_seattle(self, producer):
        from src.producers.arcgis_client import ArcGISClient
        from src.producers.socrata_client import SocrataClient

        assert isinstance(producer._client_for("arcgis"), ArcGISClient)
        assert isinstance(producer._client_for("socrata"), SocrataClient)

    def test_existing_socrata_cities_still_parse(self, producer):
        """Regression guard: the new fallbacks must not shadow the NYC path."""
        ev = producer.parse_socrata_row(
            {"doc_id": "NYC123", "recorded_datetime": "2024-01-05T00:00:00", "doc_amount": "1500000"},
            city_id="nyc",
        )
        assert ev is not None
        assert ev.city_id == "nyc"
        assert ev.doc_id == "NYC123"
