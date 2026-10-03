"""Bend deeds from Deschutes County's sales table (2026-09-30).

The county's ``GIS_SALES`` table holds each taxlot's two latest sales, with
no geometry and no city column. Bend reads the sales dated in the 90 days
before each poll on the four township-ranges under its metro box (1,048 of
the county's 2,105 on 2026-09-30), places each on its taxlot polygon, and
keeps the 1,019 inside the box (``metro_clip``).
"""

from unittest.mock import patch

import pytest

from src.spatial.city_registry import CityId, FeedType, get_dataset

FIELD_MAP = {
    "doc_id": ["Book_Page_1", "Taxlot"],
    "recorded_date": ["Sales_Date_1"],
    "document_amount": ["Total_Sales_Price_1"],
    "bbl": ["Taxlot"],
    "doc_type": ["Reject_Description_1"],
}


def test_bend_reads_the_countys_sales_table():
    from src.config import settings

    spec = get_dataset(CityId.BEND, FeedType.DEEDS)
    assert spec.endpoint == settings.arcgis_bend_deeds_url
    assert spec.endpoint.endswith("/Taxlots/FeatureServer/8")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "Sales_Date_1"
    # Every taxlot that touches the metro box starts with one of these four
    # township-range prefixes (50,356 of them on 2026-09-30); the upper bound
    # keeps out sales keyed in the future (2044, 4004).
    assert spec.where == (
        "(Taxlot LIKE '1711%' OR Taxlot LIKE '1712%' OR Taxlot LIKE '1811%' OR Taxlot LIKE '1812%') "
        "AND Sales_Date_1 >= CURRENT_DATE - INTERVAL '90' DAY AND Sales_Date_1 <= CURRENT_TIMESTAMP"
    )
    assert spec.order_by == "Sales_Date_1 DESC, OBJECTID DESC"
    # A sale can cover several taxlots, and a taxlot's next sale replaces
    # its row.
    assert spec.id_keys == ["Taxlot", "Sales_Date_1", "Book_Page_1"]
    assert spec.composite_id is True
    # Seller_1, Buyer_1, Seller_2 and Buyer_2 stay on the server.
    assert spec.select == "OBJECTID,Taxlot,Book_Page_1,Sales_Date_1,Total_Sales_Price_1,Reject_Description_1"
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    assert (spec.oid_field, spec.max_record_count, spec.batch_limit) == ("OBJECTID", 2000, 2500)
    assert spec.interval_seconds == 21600.0
    # The table reloads overnight; the newest sale trails by days.
    assert spec.expected_cadence_days == 7


def test_each_sale_takes_its_taxlots_centroid_and_bends_box_keeps_it():
    from src.config import settings

    spec = get_dataset(CityId.BEND, FeedType.DEEDS)
    assert spec.parcel_join == {
        "parcel_layer": settings.arcgis_deschutes_taxlots_url,
        "join_key": "TAXLOT",
        "geometry_source": "centroid",
        "row_key": "Taxlot",
    }
    assert spec.parcel_join["parcel_layer"].endswith("/Taxlots/FeatureServer/0")
    # The table is county-wide: Redmond, Sisters, La Pine and Sunriver sell
    # too, and some sales on Bend's township-ranges fall outside its box.
    assert spec.metro_clip is True


class TestBendDeedParsing:
    """A synthetic sale, flattened and placed as a poll places it."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @staticmethod
    def _row(**changes):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {
            "OBJECTID": 900001,
            "Taxlot": "181208AB09999",
            "Book_Page_1": "2026-99999",
            "Sales_Date_1": 1789430400000,  # 2026-09-15 00:00 UTC
            "Total_Sales_Price_1": 612000.0,
            "Reject_Description_1": "CONFIRMED SALE",
            **changes,
        }
        row = ArcGISClient()._flatten_feature({"attributes": attributes}, date_fields={"Sales_Date_1"})
        # The parcel join's centroid for the taxlot.
        return {**row, "latitude": 44.0480, "longitude": -121.3120}

    def test_a_sale_is_published_at_its_taxlot(self, deeds):
        event = deeds.parse_socrata_row(self._row(), city_id="bend")
        assert event is not None
        assert (event.doc_id, event.bbl) == ("2026-99999", "181208AB09999")
        assert event.recorded_date.date().isoformat() == "2026-09-15"
        assert event.document_amount == 612000.0
        # The assessor's verdict on the sale, as Hartford's sale code is.
        assert event.doc_type == "CONFIRMED SALE"
        assert (event.latitude, event.longitude) == (44.0480, -121.3120)
        assert event.h3_res9 is not None

    def test_a_transfer_without_a_price_still_publishes(self, deeds):
        event = deeds.parse_socrata_row(
            self._row(Total_Sales_Price_1=0.0, Reject_Description_1="GRANTOR/GRANTEE ARE THE SAME"), city_id="bend"
        )
        assert event is not None
        assert (event.document_amount, event.doc_type) == (0.0, "GRANTOR/GRANTEE ARE THE SAME")
