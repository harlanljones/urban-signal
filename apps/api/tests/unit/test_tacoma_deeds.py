"""Tacoma deeds from Pierce County's weekly sales extract (2026-09-30).

The Assessor-Treasurer's ``sale.zip`` holds ``sale.txt``: every sale in the
county since 1997, a line for each parcel a sale covers, pipe-delimited with
no header row (646,457 lines in the 2026-09-25 extract). Tacoma reads the
lines dated in the 90 days before each poll (2,432 county-wide on
2026-09-30), places each on its parcel in the county's tax parcel layer, only
where the parcel lies in one of the City of Tacoma's seven tax code areas,
and keeps the placed sales inside its metro box (``metro_clip``): 452 of them.
"""

import io
import zipfile
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import httpx
import pytest

from src.producers.csv_client import CSVClient
from src.spatial.city_registry import CityId, FeedType, get_dataset

# The extract's columns in file order, from the Assessor-Treasurer's layout.
COLUMNS = [
    "etn", "parcel_count", "parcel_number", "sale_date", "sale_price", "deed_type", "grantor", "grantee",
    "valid_invalid", "confirmed_unconfirmed", "exclude_reason", "improved_vacant", "appraisal_account_type",
]

FIELD_MAP = {
    "doc_id": ["etn", "parcel_number"],
    "recorded_date": ["sale_date"],
    "document_amount": ["sale_price"],
    "bbl": ["parcel_number"],
    "doc_type": ["deed_type"],
}

# The tax code areas of 75,859 of the 75,908 parcels inside the city limits
# on 2026-09-30 (47 of the rest carry code 0). The four parcels in them that
# lie outside the limits are each within 80 metres of the boundary.
TACOMA_TAX_CODE_AREAS = "Tax_Area_Code IN ('005', '006', '010', '011', '015', '025', '026')"


def test_tacoma_reads_the_countys_weekly_sales_extract():
    from src.config import settings

    spec = get_dataset(CityId.TACOMA, FeedType.DEEDS)
    assert spec.endpoint == settings.csv_tacoma_deeds_endpoint
    assert spec.endpoint == "https://online.co.pierce.wa.us/datamart/sale.zip"
    assert (spec.platform, spec.ingestion_mode) == ("csv", "snapshot")
    assert (spec.zip_member, spec.delimiter) == ("sale.txt", "|")
    # Dates are written 09/11/2026; the window compares them as dates.
    assert (spec.watermark_col, spec.watermark_format, spec.watermark_type) == ("sale_date", "%m/%d/%Y", None)
    assert spec.where == "sale_date >= CURRENT_DATE - INTERVAL '90' DAY"
    assert spec.order_by == "sale_date DESC"
    # A sale covers one or more parcels (up to 22 in the window): the layout's
    # primary key is the excise tax number with the parcel.
    assert spec.id_keys == ["etn", "parcel_number"]
    assert spec.composite_id is True
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    # A full read of the county's window, with half again to spare.
    assert spec.batch_limit == 5000
    # The extract is rebuilt every Friday: one download a day.
    assert spec.interval_seconds == 86400.0
    assert spec.expected_cadence_days == 7


def test_the_extract_names_its_columns_and_the_parties_stay_out_of_every_row():
    spec = get_dataset(CityId.TACOMA, FeedType.DEEDS)
    assert spec.columns == COLUMNS
    selected = spec.select.split(",")
    assert selected == ["etn", "parcel_number", "sale_date", "sale_price", "deed_type"]
    assert set(selected) <= set(COLUMNS)
    assert not set(selected) & {"grantor", "grantee"}


def test_each_sale_takes_its_parcels_centroid_in_the_citys_tax_code_areas():
    from src.config import settings

    spec = get_dataset(CityId.TACOMA, FeedType.DEEDS)
    assert spec.parcel_join == {
        "parcel_layer": settings.arcgis_pierce_tax_parcels_url,
        "join_key": "TaxParcelNumber",
        "geometry_source": "centroid",
        "row_key": "parcel_number",
        "where": TACOMA_TAX_CODE_AREAS,
    }
    assert spec.parcel_join["parcel_layer"].endswith("/Tax_Parcels/FeatureServer/0")
    # A sale outside those areas stays unplaced and the clip skips it, as it
    # skips a city parcel past the box's east edge.
    assert spec.metro_clip is True


def test_the_csv_client_reads_the_window_as_the_spec_asks():
    """Two lines of one sale, one sale outside the window, and a grantee
    byte that is not UTF-8, as three lines of the 2026-09-25 extract carry."""
    spec = get_dataset(CityId.TACOMA, FeedType.DEEDS)
    today = datetime.now(UTC).date()
    recent = (today - timedelta(days=5)).strftime("%m/%d/%Y")
    older = (today - timedelta(days=40)).strftime("%m/%d/%Y")
    stale = (today - timedelta(days=200)).strftime("%m/%d/%Y")
    lines = [
        f"9999901|2|0000000001|{older}|780000.00|Statutory Warranty Deed|GRANTOR A|GRANTEE B|1|0||Improved|Residential",
        f"9999901|2|0000000002|{older}|780000.00|Statutory Warranty Deed|GRANTOR A|GRANTEE B|1|0||Improved|Residential",
        f"9999902|1|0000000003|{stale}|275000.00|Quit Claim Deed|GRANTOR C|GRANTEE D|0|0|Estate sale|Improved|Residential",
        f"9999903|1|0000000004|{recent}|451000.00|Bargain & Sale Deed|GRANTOR E|GRANTEE F|1|1||Vacant|Residential",
    ]
    text = ("\r\n".join(lines) + "\r\n").encode("ascii").replace(b"GRANTEE F", b"GRANTEE \x90F")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("sale.txt", text)
    payload = archive.getvalue()

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload))))
    rows = [
        row
        for batch in client.paginate(
            spec.endpoint,
            where_clause=spec.where,
            order_by=spec.order_by,
            select=spec.select,
            watermark_col=spec.watermark_col,
            watermark_format=spec.watermark_format,
            zip_member=spec.zip_member,
            delimiter=spec.delimiter,
            columns=spec.columns,
        )
        for row in batch
    ]

    assert [(row["etn"], row["parcel_number"]) for row in rows] == [
        ("9999903", "0000000004"), ("9999901", "0000000001"), ("9999901", "0000000002"),
    ]
    assert all(set(row) == set(spec.select.split(",")) for row in rows)
    assert rows[0]["deed_type"] == "Bargain & Sale Deed"


class TestTacomaDeedParsing:
    """A synthetic sale line, as the CSV client and the parcel join hand it on."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @staticmethod
    def _row(**changes):
        return {
            "etn": "9999901",
            "parcel_number": "0000000001",
            "sale_date": "09/11/2026",
            "sale_price": "451000.00",
            "deed_type": "Statutory Warranty Deed",
            # The parcel join's centroid, downtown.
            "latitude": 47.2529,
            "longitude": -122.4443,
            **changes,
        }

    def test_a_sale_is_published_at_its_parcel(self, deeds):
        event = deeds.parse_socrata_row(self._row(), city_id="tacoma")
        assert event is not None
        assert (event.doc_id, event.bbl) == ("9999901", "0000000001")
        assert event.recorded_date.date().isoformat() == "2026-09-11"
        assert event.document_amount == 451000.0
        assert event.doc_type == "STATUTORY WARRANTY DEED"
        assert (event.latitude, event.longitude) == (47.2529, -122.4443)
        assert event.h3_res9 is not None

    def test_a_foreclosure_publishes_with_its_deed_type(self, deeds):
        event = deeds.parse_socrata_row(self._row(deed_type="Trustee Deed (Foreclosure)"), city_id="tacoma")
        assert event is not None
        assert event.doc_type == "TRUSTEE DEED (FORECLOSURE)"
