"""Medford deeds from Jackson County's sales layer (2026-09-30).

Jackson County's ``PropertySales`` layer (ArcGIS Server 10.91) holds each
account's latest sale on its taxlot polygon, county-wide, with the site city.
Medford reads the sales in the city (``SiteCity`` is MEDFORD, not
MEDFORD/COUNTY) dated in the 90 days before each poll: 304 on 2026-09-30,
each placed at its polygon's centroid. The server's responses carry a header
line httpx rejects, so the ArcGIS client reaches it through
``src.producers.tolerant_http``.
"""

from unittest.mock import patch

import httpx
import pytest

from src.spatial.city_registry import CityId, FeedType, get_dataset

FIELD_MAP = {
    "doc_id": ["DocumentNumber", "maptaxlot"],
    "recorded_date": ["SalesDate"],
    "document_amount": ["SalesPrice"],
    "bbl": ["maptaxlot"],
    "doc_type": ["DocumentTypeDescription"],
}


def test_medford_reads_the_sales_in_the_city():
    from src.config import settings

    spec = get_dataset(CityId.MEDFORD, FeedType.DEEDS)
    assert spec.endpoint == settings.arcgis_medford_deeds_endpoint
    assert spec.endpoint.endswith("/Demog/PropertySales/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "SalesDate"
    # The upper bound keeps out sales keyed in the future (one reads 2621).
    assert spec.where == (
        "SiteCity = 'MEDFORD' AND SalesDate >= CURRENT_DATE - INTERVAL '90' DAY AND SalesDate <= CURRENT_TIMESTAMP"
    )
    assert spec.order_by == "SalesDate DESC, OBJECTID DESC"
    # A sale can cover several accounts (304 rows carried 291 document
    # numbers), and an account's next sale replaces its row.
    assert spec.id_keys == ["AccountId", "SalesDate", "DocumentNumber"]
    assert spec.composite_id is True
    assert spec.select == "OBJECTID,AccountId,maptaxlot,SalesDate,SalesPrice,DocumentNumber,DocumentTypeDescription"
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    # The layer places each sale on its own polygon: no join, and the city
    # filter already keeps the county's other sales out.
    assert spec.parcel_join == {}
    assert spec.metro_clip is False
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.interval_seconds == 21600.0
    assert spec.expected_cadence_days == 7


def test_the_host_takes_ansi_date_literals():
    from src.producers.watermarks import ANSI_DATE_LITERAL_HOSTS, watermark_comparison

    assert "spatial.jacksoncountyor.gov" in ANSI_DATE_LITERAL_HOSTS
    spec = get_dataset(CityId.MEDFORD, FeedType.DEEDS)
    clause = watermark_comparison("SalesDate", ">=", "2026-09-01T00:00:00", spec.endpoint)
    assert clause == "SalesDate >= timestamp '2026-09-01 00:00:00'"


def test_the_client_reaches_the_county_through_the_tolerant_transport(monkeypatch):
    from src.producers import tolerant_http
    from src.producers.arcgis_client import ArcGISClient

    hosts = []

    def answer(self, request):
        hosts.append(request.url.host)
        return httpx.Response(200, json={"count": 304}, request=request)

    monkeypatch.setattr(tolerant_http.TolerantTransport, "handle_request", answer)
    spec = get_dataset(CityId.MEDFORD, FeedType.DEEDS)

    payload = ArcGISClient()._request_json(
        f"{spec.endpoint}/query", {"where": spec.where, "returnCountOnly": "true", "f": "json"}
    )

    assert payload == {"count": 304}
    assert hosts == ["spatial.jacksoncountyor.gov"]


# A synthetic sale on a synthetic taxlot in east Medford, as the layer serves
# it with ``outSR=4326``.
SALE = {
    "OBJECTID": 900001,
    "AccountId": 99999999,
    "maptaxlot": "372W25DD99999",
    "SalesDate": 1789430400000,  # 2026-09-15 00:00 UTC
    "SalesPrice": 389000.0,
    "DocumentNumber": "2026-99999",
    "DocumentTypeDescription": "WARRANTY DEED",
}
TAXLOT_OUTLINE = {
    "rings": [[[-122.8412, 42.3301], [-122.8404, 42.3301], [-122.8404, 42.3307],
               [-122.8412, 42.3307], [-122.8412, 42.3301]]]
}


class TestMedfordDeedParsing:
    """The synthetic sale through the ArcGIS flattener and the deeds producer."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @staticmethod
    def _row(**changes):
        from src.producers.arcgis_client import ArcGISClient

        return ArcGISClient()._flatten_feature(
            {"attributes": {**SALE, **changes}, "geometry": TAXLOT_OUTLINE}, date_fields={"SalesDate"}
        )

    def test_a_sale_is_published_at_its_taxlots_centroid(self, deeds):
        event = deeds.parse_socrata_row(self._row(), city_id="medford")
        assert event is not None
        assert (event.doc_id, event.bbl) == ("2026-99999", "372W25DD99999")
        assert event.recorded_date.date().isoformat() == "2026-09-15"
        assert event.document_amount == 389000.0
        assert event.doc_type == "WARRANTY DEED"
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (42.3304, -122.8408)
        assert event.h3_res9 is not None

    def test_a_sale_without_a_document_type_still_publishes(self, deeds):
        event = deeds.parse_socrata_row(self._row(DocumentTypeDescription=None), city_id="medford")
        assert event is not None
        assert event.doc_id == "2026-99999"
