"""Deeds for five Maricopa County cities from the Assessor's parcel layer.

The Assessor's parcel layer (``gis.mcassessor.maricopa.gov``, ArcGIS Server
11.5) carries each parcel's latest deed: its number and date, the sale price
where an affidavit was processed, and native LATITUDE/LONGITUDE. Phoenix,
Tempe, Chandler, Scottsdale and Glendale each read the deeds dated in the 90
days before each poll inside their own JURISDICTION: 9,224, 783, 1,573, 2,507
and 1,263 on 2026-09-30. Phoenix's Sales Affidavits file, which dead-lettered
every row, is no longer registered.
"""

from unittest.mock import patch

import pytest

from src.spatial.city_registry import CityId, FeedType, get_dataset

MARICOPA = {
    CityId.PHOENIX: ("PHOENIX", 15000),
    CityId.TEMPE: ("TEMPE", 2000),
    CityId.CHANDLER: ("CHANDLER", 3000),
    CityId.SCOTTSDALE: ("SCOTTSDALE", 5000),
    CityId.GLENDALE_AZ: ("GLENDALE", 2500),
}

FIELD_MAP = {
    "doc_id": ["DEED_NUMBER", "APN"],
    "recorded_date": ["DEED_DATE"],
    "document_amount": ["SALE_PRICE"],
    "bbl": ["APN"],
    "latitude": ["LATITUDE"],
    "longitude": ["LONGITUDE"],
}


@pytest.mark.parametrize("city", list(MARICOPA), ids=lambda city: city.value)
def test_each_city_reads_its_own_deeds_from_the_assessor_layer(city):
    from src.config import settings

    jurisdiction, cap = MARICOPA[city]
    spec = get_dataset(city, FeedType.DEEDS)
    assert spec.endpoint == settings.arcgis_maricopa_parcels_url
    assert spec.endpoint.endswith("/Parcels/MapServer/0")
    assert spec.platform == "arcgis"
    assert spec.ingestion_mode == "snapshot"
    assert spec.watermark_col == "DEED_DATE"
    assert spec.where == (
        f"JURISDICTION = '{jurisdiction}' AND DEED_DATE >= CURRENT_DATE - INTERVAL '90' DAY "
        "AND DEED_DATE <= CURRENT_TIMESTAMP"
    )
    assert spec.order_by == "DEED_DATE DESC, OBJECTID DESC"
    # A deed can convey several parcels (22 of Tempe's 783), and a parcel's
    # next deed replaces its row.
    assert spec.id_keys == ["APN", "DEED_DATE", "DEED_NUMBER"]
    assert spec.composite_id is True
    # OWNER_NAME, the MAIL_* block and INCAREOF stay on the server.
    assert spec.select == "OBJECTID,APN,DEED_NUMBER,DEED_DATE,SALE_PRICE,LATITUDE,LONGITUDE"
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    assert spec.oid_field == "OBJECTID"
    # The layer serves at most 1,000 rows a page.
    assert spec.max_record_count == 1000
    assert spec.batch_limit == cap
    assert spec.interval_seconds == 21600.0
    # The newest deed trails by one to two weeks and the layer loads about
    # weekly, so the alarm waits 28 days.
    assert spec.expected_cadence_days == 14


def test_phoenix_no_longer_reads_the_sales_affidavits_file():
    from src.config import settings

    spec = get_dataset(CityId.PHOENIX, FeedType.DEEDS)
    assert spec.endpoint != settings.csv_phoenix_deeds_endpoint
    assert (spec.zip_member, spec.delimiter, spec.geocode_context) == (None, None, None)
    assert spec.alarm_exempt is False


def test_the_host_takes_ansi_date_literals():
    from src.producers.watermarks import ANSI_DATE_LITERAL_HOSTS, watermark_comparison

    assert "gis.mcassessor.maricopa.gov" in ANSI_DATE_LITERAL_HOSTS
    spec = get_dataset(CityId.TEMPE, FeedType.DEEDS)
    clause = watermark_comparison("DEED_DATE", ">=", "2026-09-01T00:00:00", spec.endpoint)
    assert clause == "DEED_DATE >= timestamp '2026-09-01 00:00:00'"


def _flatten_feature(attributes: dict, geometry: dict) -> dict:
    """Run a raw feature through the production flattener, as paginate does."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry}, date_fields={"DEED_DATE"}
    )


PARCEL_ROW = {
    "OBJECTID": 900001,
    "APN": "13299999",
    "DEED_NUMBER": "20269999999",
    "DEED_DATE": 1789430400000,  # 2026-09-15 00:00 UTC
    "SALE_PRICE": "485000",
    "LATITUDE": 33.4148,
    "LONGITUDE": -111.9093,
}
PARCEL_OUTLINE = {
    "rings": [[[-111.9097, 33.4146], [-111.9089, 33.4146], [-111.9089, 33.4151],
               [-111.9097, 33.4151], [-111.9097, 33.4146]]]
}


class TestMaricopaDeedParsing:
    """A synthetic parcel-layer row through the flattener and the producer."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def _row(self, **changes):
        return _flatten_feature({**PARCEL_ROW, **changes}, PARCEL_OUTLINE)

    def test_a_deed_is_published_at_its_parcel(self, deeds):
        event = deeds.parse_socrata_row(self._row(), city_id="tempe")
        assert event is not None
        assert (event.doc_id, event.bbl) == ("20269999999", "13299999")
        assert event.recorded_date.date().isoformat() == "2026-09-15"
        # The price is text on this layer.
        assert event.document_amount == 485000.0
        # The layer's own coordinates, not the centroid the flattener adds.
        assert (event.latitude, event.longitude) == (33.4148, -111.9093)
        assert event.doc_type == "DEED"
        assert event.h3_res9 is not None

    def test_a_deed_without_an_affidavit_still_publishes(self, deeds):
        event = deeds.parse_socrata_row(self._row(SALE_PRICE=""), city_id="tempe")
        assert event is not None
        assert event.document_amount == 0.0
