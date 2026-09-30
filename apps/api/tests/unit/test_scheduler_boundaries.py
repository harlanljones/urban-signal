"""The incremental filter's boundary, source column and zone, and the row ids
and parcel joins poll_job applies before parsing.

A date-only column stores one time for a whole day, so a strict ``>`` on its
watermark never read the rows a city published later that day; an ArcGIS
layer that declares a zone reads the stored UTC watermark as local time; and a
sale keyed by parcel alone collided with the parcel's next sale.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers.scheduler import MunicipalIngestionScheduler


@pytest.fixture
def scheduler():
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        sched = MunicipalIngestionScheduler(
            dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0, dedup_capacity=1000
        )
    for producer in sched.producers.values():
        producer.producer = MagicMock()
    sched.state_file = None
    return sched


def _permit(job, issued, **extra):
    return {
        "job__": job,
        "latitude": "40.725",
        "longitude": "-73.997",
        "job_type": "A1",
        "initial_cost": "100000",
        "issuance_date": issued,
        **extra,
    }


def _where(producer, client="socrata"):
    return getattr(producer, client).paginate.call_args.kwargs["where_clause"]


class TestBoundary:
    def test_a_whole_hour_watermark_keeps_its_day(self, scheduler):
        producer = scheduler.producers["permits"]
        producer.socrata.paginate = MagicMock(return_value=[])
        scheduler.metrics["permits"].high_watermark = "2026-09-29T00:00:00"

        scheduler.poll_job("permits", limit=10)

        assert _where(producer) == "issuance_date >= '2026-09-29T00:00:00'"

    def test_a_timestamp_watermark_stays_strict(self, scheduler):
        producer = scheduler.producers["permits"]
        producer.socrata.paginate = MagicMock(return_value=[])
        scheduler.metrics["permits"].high_watermark = "2026-09-29T10:15:07"

        scheduler.poll_job("permits", limit=10)

        assert _where(producer) == "issuance_date > '2026-09-29T10:15:07'"

    def test_a_full_poll_stuck_on_its_boundary_steps_past_it(self, scheduler):
        producer = scheduler.producers["permits"]
        met = scheduler.metrics["permits"]
        met.high_watermark = "2026-09-29T00:00:00"
        boundary = [_permit(f"M{i}", "2026-09-29T00:00:00.000") for i in range(3)]
        producer.socrata.paginate = MagicMock(return_value=[boundary])

        scheduler.poll_job("permits", limit=3)

        assert met.high_watermark == "2026-09-29T00:00:00"
        assert met.boundary_stalled is True

        # The same rows again would stall forever: the next filter is strict.
        producer.socrata.paginate = MagicMock(return_value=[[_permit("M9", "2026-09-30T00:00:00.000")]])
        scheduler.poll_job("permits", limit=3)
        assert _where(producer) == "issuance_date > '2026-09-29T00:00:00'"

        # The watermark moved, so the boundary rule applies again.
        assert met.high_watermark == "2026-09-30T00:00:00"
        assert met.boundary_stalled is False
        producer.socrata.paginate = MagicMock(return_value=[])
        scheduler.poll_job("permits", limit=3)
        assert _where(producer) == "issuance_date >= '2026-09-30T00:00:00'"

    def test_a_stalled_timestamp_steps_to_the_next_second(self, scheduler):
        """Milwaukee's licence layer returns its refresh time as 01:23:59 but
        stores a finer one, so ``> 01:23:59`` kept matching every row."""
        producer = scheduler.producers["permits"]
        producer.socrata.paginate = MagicMock(return_value=[])
        met = scheduler.metrics["permits"]
        met.high_watermark = "2026-09-30T01:23:59"
        met.boundary_stalled = True

        scheduler.poll_job("permits", limit=3)

        assert _where(producer) == "issuance_date >= '2026-09-30T01:24:00'"

    def test_a_short_poll_is_not_a_stall(self, scheduler):
        producer = scheduler.producers["permits"]
        met = scheduler.metrics["permits"]
        met.high_watermark = "2026-09-29T00:00:00"
        producer.socrata.paginate = MagicMock(return_value=[[_permit("M1", "2026-09-29T00:00:00.000")]])

        scheduler.poll_job("permits", limit=3)

        assert met.boundary_stalled is False

    def test_a_newest_first_poll_never_steps_past(self, scheduler):
        """Newer rows would have come first, so a full page that left the
        watermark alone holds nothing newer to reach."""
        producer = scheduler.producers["permits"]
        met = scheduler.metrics["permits"]
        scheduler.job_metadata["permits"]["order_by"] = "issuance_date DESC"
        met.high_watermark = "2026-09-29T00:00:00"
        boundary = [_permit(f"M{i}", "2026-09-29T00:00:00.000") for i in range(3)]
        producer.socrata.paginate = MagicMock(return_value=[boundary])

        scheduler.poll_job("permits", limit=3)

        assert met.boundary_stalled is False


class TestWatermarkSource:
    def test_the_watermark_follows_the_filter_column(self, scheduler):
        """Connecticut's licences filter on a refresh date but date each event
        by its effective date: advancing from the event date re-read the whole
        refresh on every poll."""
        producer = scheduler.producers["permits"]
        scheduler.job_metadata["permits"]["watermark_col"] = "refreshed_at"
        producer.socrata.paginate = MagicMock(
            return_value=[[_permit("M1", "2026-01-05T00:00:00.000", refreshed_at="2026-09-29T08:00:00.000")]]
        )

        result = scheduler.poll_job("permits", limit=10)

        assert result["high_watermark"] == "2026-09-29T08:00:00"

    def test_the_event_date_stands_in_for_an_empty_column(self, scheduler):
        producer = scheduler.producers["permits"]
        scheduler.job_metadata["permits"]["watermark_col"] = "refreshed_at"
        producer.socrata.paginate = MagicMock(
            return_value=[[_permit("M1", "2026-09-28T09:30:00.000", refreshed_at=None)]]
        )

        result = scheduler.poll_job("permits", limit=10)

        assert result["high_watermark"] == "2026-09-28T09:30:00"

    def test_a_csv_with_a_declared_format_reads_past_its_iso_watermark(self, scheduler):
        """St. Louis's export writes ``2026-09-28 09:30:00.0`` and the spec
        declares that format, which the CSV client compares the column in,
        while the watermark it stores is ISO. The literal has to parse too:
        read only in the declared format it matched no row, and every poll
        after the first read nothing."""
        producer = scheduler.producers["permits"]
        producer.parse_socrata_row = lambda row, city_id=None: SimpleNamespace(
            job_id=row["address"],
            city_id="st_louis",
            issuance_date=datetime.fromisoformat(row["issuedate"]),
        )
        export = (
            "ADDRESS,ISSUEDATE,APPLICATIONDESCRIPTION\n"
            "100 MARKET ST,2026-09-20 10:00:00.0,Alteration\n"
            "200 OLIVE ST,2026-09-28 09:30:00.0,New building\n"
        )

        def serve(text):
            producer.csv.http = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=text)))

        serve(export)
        scheduler.poll_job("permits_stl", limit=100)
        assert scheduler.metrics["permits_stl"].high_watermark == "2026-09-28T09:30:00"

        serve(export + "300 PINE ST,2026-09-29 12:00:00.0,Alteration\n")
        result = scheduler.poll_job("permits_stl", limit=100)

        assert (result["records_fetched"], result["records_published"]) == (1, 1)


class TestLayerZone:
    def test_an_arcgis_filter_reads_in_the_layers_zone(self, scheduler):
        """DC's 311 layer declares Eastern time: 01:30 UTC is 21:30 the evening
        before, exact to the second."""
        producer = scheduler.producers["311"]
        producer.arcgis.paginate = MagicMock(return_value=[])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": "America/New_York"})
        scheduler.metrics["311_dc"].high_watermark = "2026-09-30T01:30:00"

        result = scheduler.poll_job("311_dc", limit=10)

        assert result["status"] == "SUCCESS"
        assert _where(producer, "arcgis") == "ADDDATE > timestamp '2026-09-29 21:30:00'"

    def test_an_unreadable_layer_fails_the_poll_not_the_scheduler(self, scheduler):
        producer = scheduler.producers["311"]
        producer.arcgis.paginate = MagicMock(return_value=[])
        producer.arcgis.get_layer_metadata = MagicMock(side_effect=RuntimeError("ArcGIS error 499"))
        scheduler.metrics["311_dc"].high_watermark = "2026-09-30T01:30:00"

        result = scheduler.poll_job("311_dc", limit=10)

        assert result["status"] == "ERROR"
        assert "499" in result["error"]
        producer.arcgis.paginate.assert_not_called()


class TestSaleRows:
    def test_a_composite_id_joins_every_key(self, scheduler):
        """Lynchburg's DocumentNo repeats across an instrument's parcels and
        LRSN across a parcel's sales: a row is the pair."""
        assert scheduler._extract_record_id(
            "deeds_lynchburg", {"LRSN": 8921, "DocumentNo": "260000257      "}
        ) == "deeds_lynchburg:8921|260000257"
        assert scheduler._extract_record_id(
            "deeds_lynchburg", {"LRSN": 17439, "DocumentNo": "260000257"}
        ) == "deeds_lynchburg:17439|260000257"
        assert scheduler._extract_record_id("deeds_lynchburg", {"LRSN": 8921}) == "deeds_lynchburg:8921|"

    def test_a_parcel_keeps_each_sale_and_drops_repeated_shapes(self, scheduler):
        """Stark County repeats a parcel's sale row for each of its shapes, and
        keying by parcel alone dropped the parcel's next sale."""
        first = {"PARID": "9999001", "INSTRUMENT_NUMBER": "202609290000001", "OBJECTID": 11}
        shape = {**first, "OBJECTID": 12}
        resale = {**first, "INSTRUMENT_NUMBER": "202610150000007", "OBJECTID": 13}

        ids = [scheduler._extract_record_id("deeds_canton", row) for row in (first, shape, resale)]

        assert ids == [
            "deeds_canton:9999001|202609290000001",
            "deeds_canton:9999001|202609290000001",
            "deeds_canton:9999001|202610150000007",
        ]
        # Object ids do not follow the transfer date, so the feed reads newest first.
        assert scheduler.job_metadata["deeds_canton"]["order_by"] == "TRANSFER_DATE DESC, OBJECTID DESC"

    def test_a_poll_places_sales_at_their_parcel_centroid(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            {"LRSN": 14196, "DocumentNo": "260005545", "SaleDate": "2026-09-25T00:00:00+00:00",
             "SaleAmount": 180000.0, "ESRI_OID": 29},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"14196": (37.4136, -79.1422)})

        result = scheduler.poll_job("deeds_lynchburg", limit=10)

        assert result["records_published"] == 1
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert kwargs["join_key"] == "LRSN"
        assert kwargs["join_values"] == [14196]
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.latitude, event.longitude) == (37.4136, -79.1422)
        assert event.h3_res9 is not None

    def test_a_poll_hands_the_join_its_via_table(self, scheduler):
        """DC's condominium units reach their lot through CONDORELATE."""
        producer = scheduler.producers["deeds"]
        rows = [
            {"SSL": "0016    2033", "SALE_DATE": "2026-09-22T04:00:00+00:00", "SALE_PRICE": 455000,
             "QUALIFIED": "Q", "ROW_NUMBER": 7, "OBJECTID": 41},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"0016 2033": (38.9105, -77.0431)})

        result = scheduler.poll_job("deeds_dc", limit=10)

        assert result["records_published"] == 1
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert kwargs["endpoint_url"].endswith("/FeatureServer/40")
        assert kwargs["via"] == {
            "table": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/"
            "Property_and_Land_WebMercator/FeatureServer/52",
            "key": "SSL",
            "to": "MAT_SSL",
        }
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.latitude, event.longitude) == (38.9105, -77.0431)

    def test_a_hartford_sale_joins_its_parcel_by_the_tables_parcel_number(self, scheduler):
        """Hartford's CAMA table has no geometry; its ParcelNumber is the
        parcel layer's PARCELNUMBER. A snapshot reads its own window only."""
        producer = scheduler.producers["deeds"]
        rows = [
            {"OBJECTID": 90003, "ParcelNumber": "900000001", "LastSaleDate": "2026-09-22T00:00:00+00:00",
             "LastSalePrice": 310000.0, "LastSalecode": "Valid Sale", "LegalRef": "99999 0001"},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"900000001": (41.7637, -72.6851)})

        result = scheduler.poll_job("deeds_hartford", limit=10)

        assert result["records_published"] == 1
        assert _where(producer, "arcgis") == (
            "(LastSaleDate >= CURRENT_DATE - INTERVAL '90' DAY AND LastSaleDate <= CURRENT_TIMESTAMP)"
        )
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert kwargs["endpoint_url"].endswith("/OpenData_Housing_Development/MapServer/11")
        assert (kwargs["join_key"], kwargs["join_values"]) == ("PARCELNUMBER", ["900000001"])
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.latitude, event.longitude) == (41.7637, -72.6851)

    def test_a_parcels_next_transfer_is_new_to_its_snapshot(self, scheduler):
        """Nashville's parcel layer holds each parcel's last transfer. The
        window re-reads an unchanged row as a duplicate; a resale replaces the
        parcel's row and publishes."""
        producer = scheduler.producers["deeds"]
        sale = {"OBJECTID": 90001, "STANPAR": "09999000100", "OwnDate": "2026-09-15T05:00:00+00:00",
                "SalePrice": 425000.0, "OwnInstr": "DB-20260917 0099999", "Lat": 36.1627, "Lon": -86.7816}
        resale = {**sale, "OwnDate": "2026-09-29T05:00:00+00:00", "SalePrice": 440000.0,
                  "OwnInstr": "DB-20260930 0099998"}

        producer.arcgis.paginate = MagicMock(return_value=[[sale]])
        first = scheduler.poll_job("deeds_bna", limit=10)
        again = scheduler.poll_job("deeds_bna", limit=10)
        producer.arcgis.paginate = MagicMock(return_value=[[resale]])
        after_resale = scheduler.poll_job("deeds_bna", limit=10)

        assert [r["records_published"] for r in (first, again, after_resale)] == [1, 0, 1]
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.doc_id, event.bbl, event.document_amount) == ("DB-20260930 0099998", "09999000100", 440000.0)
        assert (event.latitude, event.longitude) == (36.1627, -86.7816)

    def test_a_maricopa_deed_poll_reads_its_citys_jurisdiction(self, scheduler):
        """Five cities read one county parcel layer; each poll asks for its
        own JURISDICTION's window and places a deed at the parcel's own
        coordinates. A deed on two parcels publishes once for each."""
        producer = scheduler.producers["deeds"]
        rows = [
            {"OBJECTID": 900001, "APN": "13299999", "DEED_NUMBER": "20269999999",
             "DEED_DATE": "2026-09-15T00:00:00+00:00", "SALE_PRICE": "485000",
             "LATITUDE": 33.4148, "LONGITUDE": -111.9093},
            {"OBJECTID": 900002, "APN": "13299998", "DEED_NUMBER": "20269999999",
             "DEED_DATE": "2026-09-15T00:00:00+00:00", "SALE_PRICE": "485000",
             "LATITUDE": 33.4150, "LONGITUDE": -111.9095},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock()

        result = scheduler.poll_job("deeds_tempe", limit=10)

        assert result["records_published"] == 2
        assert _where(producer, "arcgis") == (
            "(JURISDICTION = 'TEMPE' AND DEED_DATE >= CURRENT_DATE - INTERVAL '90' DAY "
            "AND DEED_DATE <= CURRENT_TIMESTAMP)"
        )
        producer.arcgis.fetch_centroid_index.assert_not_called()
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(e.bbl, e.latitude, e.longitude) for e in events] == [
            ("13299999", 33.4148, -111.9093),
            ("13299998", 33.4150, -111.9095),
        ]

    def test_a_medford_poll_reads_the_sales_in_the_city(self, scheduler):
        """Jackson County's sales layer is county-wide. Medford's poll asks for
        the city's window and publishes each account's sale where the client
        placed it, once for each account a sale covers."""
        producer = scheduler.producers["deeds"]
        rows = [
            {"OBJECTID": 900001, "AccountId": 99999999, "maptaxlot": "372W13CD99901",
             "SalesDate": "2026-09-25T00:00:00+00:00", "SalesPrice": 540000.0,
             "DocumentNumber": "2026-99999", "DocumentTypeDescription": "WARRANTY DEED",
             "latitude": 42.3431, "longitude": -122.8601},
            {"OBJECTID": 900002, "AccountId": 99999998, "maptaxlot": "372W13CD99900",
             "SalesDate": "2026-09-25T00:00:00+00:00", "SalesPrice": 540000.0,
             "DocumentNumber": "2026-99999", "DocumentTypeDescription": "WARRANTY DEED",
             "latitude": 42.3433, "longitude": -122.8603},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock()

        result = scheduler.poll_job("deeds_medford", limit=10)

        assert (result["records_published"], result["outside_metro"]) == (2, 0)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        assert _where(producer, "arcgis") == (
            "(SiteCity = 'MEDFORD' AND SalesDate >= CURRENT_DATE - INTERVAL '90' DAY "
            "AND SalesDate <= CURRENT_TIMESTAMP)"
        )
        producer.arcgis.fetch_centroid_index.assert_not_called()
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(e.doc_id, e.bbl, e.doc_type, e.latitude) for e in events] == [
            ("2026-99999", "372W13CD99901", "WARRANTY DEED", 42.3431),
            ("2026-99999", "372W13CD99900", "WARRANTY DEED", 42.3433),
        ]

    def test_a_bend_poll_keeps_the_sales_its_metro_box_holds(self, scheduler):
        """Deschutes County's sales table covers the county. Each sale takes
        its taxlot's centroid, and a poll keeps the ones inside Bend's metro
        box; a sale outside it, or on a taxlot the join cannot find, is
        skipped and counted, never dead-lettered."""
        producer = scheduler.producers["deeds"]
        rows = [
            {"OBJECTID": 1, "Taxlot": "181208AB09999", "Book_Page_1": "2026-99999",
             "Sales_Date_1": "2026-09-15T00:00:00+00:00", "Total_Sales_Price_1": 612000.0,
             "Reject_Description_1": "CONFIRMED SALE"},
            {"OBJECTID": 2, "Taxlot": "171229DD09999", "Book_Page_1": "2026-99998",
             "Sales_Date_1": "2026-09-14T00:00:00+00:00", "Total_Sales_Price_1": 0.0,
             "Reject_Description_1": "GRANTOR/GRANTEE ARE THE SAME"},
            {"OBJECTID": 3, "Taxlot": "181211CC09999", "Book_Page_1": "2026-99997",
             "Sales_Date_1": "2026-09-14T00:00:00+00:00", "Total_Sales_Price_1": 390000.0,
             "Reject_Description_1": "UNCONFIRMED SALE"},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(
            return_value={"181208AB09999": (44.0480, -121.3120), "171229DD09999": (44.1500, -121.3300)}
        )

        result = scheduler.poll_job("deeds_bend", limit=10)

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 1, 2)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        assert _where(producer, "arcgis") == (
            "((Taxlot LIKE '1711%' OR Taxlot LIKE '1712%' OR Taxlot LIKE '1811%' OR Taxlot LIKE '1812%') "
            "AND Sales_Date_1 >= CURRENT_DATE - INTERVAL '90' DAY AND Sales_Date_1 <= CURRENT_TIMESTAMP)"
        )
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert kwargs["endpoint_url"].endswith("/Taxlots/FeatureServer/0")
        assert (kwargs["join_key"], kwargs["join_values"]) == (
            "TAXLOT", ["181208AB09999", "171229DD09999", "181211CC09999"]
        )
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.doc_id, event.bbl, event.doc_type) == ("2026-99999", "181208AB09999", "CONFIRMED SALE")
        assert (event.latitude, event.longitude, event.document_amount) == (44.0480, -121.3120, 612000.0)

    def test_a_sale_the_join_cannot_place_yet_publishes_once_it_can(self, scheduler):
        """A skipped row is not marked seen, so it publishes on the poll that
        places it."""
        producer = scheduler.producers["deeds"]
        sale = {"OBJECTID": 1, "Taxlot": "181208AB09999", "Book_Page_1": "2026-99999",
                "Sales_Date_1": "2026-09-15T00:00:00+00:00", "Total_Sales_Price_1": 612000.0,
                "Reject_Description_1": "CONFIRMED SALE"}
        producer.arcgis.paginate = MagicMock(return_value=[[sale]])

        producer.arcgis.fetch_centroid_index = MagicMock(return_value={})
        unplaced = scheduler.poll_job("deeds_bend", limit=10)
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"181208AB09999": (44.0480, -121.3120)})
        placed = scheduler.poll_job("deeds_bend", limit=10)

        assert [(r["records_published"], r["outside_metro"]) for r in (unplaced, placed)] == [(0, 1), (1, 0)]

    def test_a_feed_without_the_clip_publishes_outside_its_box(self, scheduler):
        """Phoenix's city limits reach north of its metro box along I-17, and
        its deeds keep those sales."""
        producer = scheduler.producers["deeds"]
        rows = [
            {"OBJECTID": 900003, "APN": "20299999", "DEED_NUMBER": "20269999997",
             "DEED_DATE": "2026-09-15T00:00:00+00:00", "SALE_PRICE": "610000",
             "LATITUDE": 33.8800, "LONGITUDE": -112.1600},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_phoenix", limit=10)

        assert (result["records_published"], result["outside_metro"]) == (1, 0)

    def test_the_clip_reads_a_rows_mapped_coordinates_first(self, scheduler):
        """A row is placed where its event will be: by the columns its field
        map names, else by ``latitude``/``longitude``."""
        assert scheduler._metro_clip("deeds_hartford") is None
        scheduler.job_metadata["deeds_tempe"]["metro_clip"] = True
        inside = scheduler._metro_clip("deeds_tempe")

        in_tempe, north_of_it = (33.4148, -111.9093), (33.6000, -111.7000)
        assert inside({"LATITUDE": in_tempe[0], "LONGITUDE": in_tempe[1],
                       "latitude": north_of_it[0], "longitude": north_of_it[1]})
        assert not inside({"LATITUDE": north_of_it[0], "LONGITUDE": north_of_it[1],
                           "latitude": in_tempe[0], "longitude": in_tempe[1]})
        assert inside({"latitude": in_tempe[0], "longitude": in_tempe[1]})
        assert not inside({"APN": "13299999"})

    def test_a_license_joins_its_parcel_by_the_tables_column_name(self, scheduler, monkeypatch):
        """Lynchburg's licence table spells the key ParcelID and its parcel
        polygons Parcel_ID; the licence takes the centroid, never a geocode."""
        geocoded = []

        class _Geocoder:
            def geocode(self, query):
                geocoded.append(query)
                return None

        monkeypatch.setattr("src.spatial.geocoder.get_geocoder", lambda: _Geocoder())
        producer = scheduler.producers["sla"]
        rows = [
            {"OBJECTID": 4609, "LicenseNumber": "031386", "Company": "NEEDLE NINJA LLC", "TradeName": "",
             "ParcelID": "02449010", "Status": "ACTIVE", "LicenseIssued": "2026-08-21T00:00:00+00:00",
             "LicenseExpires": "2027-05-01T00:00:00+00:00", "BusinessType": "01 Retail Merchant"},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"02449010": (37.414, -79.143)})

        result = scheduler.poll_job("sla_lynchburg", limit=10)

        assert result["records_published"] == 1
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert kwargs["endpoint_url"].endswith("/ODPDynamic/MapServer/41")
        assert (kwargs["join_key"], kwargs["join_values"]) == ("Parcel_ID", ["02449010"])
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.latitude, event.longitude) == (37.414, -79.143)
        assert geocoded == []

    def test_a_workbook_sale_joins_by_its_own_column_name(self, scheduler):
        """Richmond's workbook headers arrive lower-cased (``pin``) while its
        Parcels layer spells the field ``PIN``."""
        producer = scheduler.producers["deeds"]
        rows = [
            {"pin": "W0001234005", "transfer_date": "2026-09-22T00:00:00", "consideration": 285000,
             "deed_book": "ID2026", "deed_page": 21877, "deed_type": "Deed"},
        ]
        producer.excel.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"W0001234005": (37.553, -77.462)})

        result = scheduler.poll_job("deeds_richmond", limit=10)

        assert result["records_published"] == 1
        assert producer.excel.paginate.call_args.kwargs["link_pattern"] == r"Assessor_Transfers_[0-9-]+\.xlsx$"
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert (kwargs["join_key"], kwargs["join_values"]) == ("PIN", ["W0001234005"])
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.latitude, event.longitude) == (37.553, -77.462)
        assert scheduler._extract_record_id("deeds_richmond", rows[0]) == (
            "deeds_richmond:W0001234005|2026-09-22T00:00:00|ID2026|21877"
        )
