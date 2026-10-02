"""Offline tests for the bulk backfill loader (mocked scheduler machinery)."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from scripts.backfill_loader import (
    backfill_job,
    build_query_shape,
    main,
    select_jobs,
)

from src.producers.csv_client import CSVClient
from src.producers.scheduler import MunicipalIngestionScheduler


def _meta(watermark_col="IssuedDate", platform="socrata", producer_key="permits", **extra):
    meta = {
        "endpoint": "https://data.example/resource/x.json",
        "topic": "raw.municipal.permits",
        "watermark_col": watermark_col,
        "id_keys": ["permitnumber", "_id"],
        "city_id": "baltimore",
        "producer_key": producer_key,
        "platform": platform,
        "watermark_type": None,
        "watermark_format": None,
        "watermark_exclude": [],
    }
    meta.update(extra)
    return meta


class _FakeScheduler:
    def __init__(self, jobs):
        # jobs: name -> meta
        self.job_metadata = jobs
        self.configs = {name: MagicMock() for name in jobs}
        self.producers = {}
        self._seen: set[str] = set()
        self.dedup = MagicMock()

        def _check_and_add(key: str) -> bool:
            if key in self._seen:
                return True
            self._seen.add(key)
            return False

        self.dedup.check_and_add.side_effect = _check_and_add
        self.dlq_producer = MagicMock()

    def _extract_record_id(self, job_name, row):
        return f"{job_name}:{row.get('permitnumber', row.get('_id', 'x'))}"

    def _metro_clip(self, job_name):
        return None

    def _paginating_client_for(self, job_name):
        return self.clients[job_name]


def _fake_event(ts=datetime(2026, 8, 20, tzinfo=UTC), city="baltimore", key="P1"):
    ev = MagicMock()
    ev.job_id, ev.incident_id, ev.license_id, ev.doc_id = key, None, None, None
    ev.city_id = city
    ev.issuance_date, ev.created_date, ev.effective_date, ev.recorded_date = ts, None, None, None
    return ev


def _wire(fake, client, producer_wrapper):
    fake.clients = {"permits_baltimore": client}
    fake.producers["permits"] = producer_wrapper


def test_build_query_shape_windowed_with_sentinel_guard():
    meta = _meta(watermark_exclude=["3200-01-01"])
    where, kwargs = build_query_shape(meta, datetime(2026, 5, 26, tzinfo=UTC))
    assert "IssuedDate >= '2026-05-26" in where
    assert "NOT IN" in where  # sentinel guard appended (ADR 0005)
    assert kwargs == {"order_by": "IssuedDate DESC"}


def test_build_query_shape_snapshot_feed_has_no_where():
    where, kwargs = build_query_shape(_meta(watermark_col=""), None)
    assert where is None
    assert kwargs == {}


def test_build_query_shape_snapshot_feed_keeps_the_registry_where():
    # A snapshot on a shared layer is scoped by its registry filter alone
    # (here a SNAP state and bbox); dropping it would backfill the national
    # table under one city.
    snap_where = (
        "State = 'FL' AND Latitude BETWEEN 30.29 AND 30.63"
        " AND Longitude BETWEEN -84.7 AND -84.05"
    )
    where, kwargs = build_query_shape(_meta(watermark_col="", base_where=snap_where), None)
    assert where == f"({snap_where})"
    assert kwargs == {}


def test_build_query_shape_windowed_feed_keeps_the_registry_where():
    meta = _meta(base_where="prem_county = 'ALAMEDA'", watermark_exclude=["3200-01-01"])
    where, kwargs = build_query_shape(meta, datetime(2026, 5, 26, tzinfo=UTC))
    assert where.startswith("(prem_county = 'ALAMEDA') AND IssuedDate >= '2026-05-26")
    assert "NOT IN" in where
    assert kwargs == {"order_by": "IssuedDate DESC"}


def test_every_registered_filter_survives_into_the_backfill_query():
    """Backfills scope rows the way poll_job does: every spec's own ``where``
    is part of the backfill query, windowed or not."""
    from src.spatial.city_registry import REGISTRY

    checked = 0
    for city_id, reg in REGISTRY.items():
        for feed, ds in reg.datasets.items():
            if not ds.where:
                continue
            meta = _meta(
                watermark_col=ds.watermark_col,
                platform=ds.platform,
                endpoint=ds.endpoint,
                base_where=ds.where,
                watermark_exclude=ds.watermark_exclude or [],
            )
            for since in (None, datetime(2026, 5, 26, tzinfo=UTC)):
                where, _ = build_query_shape(meta, since)
                assert where.startswith(f"({ds.where})"), (city_id.value, feed.value)
            checked += 1
    assert checked > 54  # the SNAP slices alone are 54


def test_build_query_shape_dc_arcgis_uses_an_ansi_literal_and_no_order_by():
    # US-109: the DC server (maps2.dcgis.dc.gov) rejects ISO-string date
    # comparisons and the where+orderByFields combination; the loader must
    # emit an ANSI literal and page by OID.
    meta = _meta(
        watermark_col="ISSUE_DATE",
        platform="arcgis",
        endpoint="https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/18",
    )
    where, kwargs = build_query_shape(meta, datetime(2026, 5, 26, tzinfo=UTC))
    assert "ISSUE_DATE >= timestamp '2026-05-26 00:00:00'" in where
    assert "2026-05-26T" not in where
    assert kwargs == {}


def test_build_query_shape_non_dc_arcgis_keeps_iso_and_order():
    meta = _meta(
        watermark_col="ISSUED_DT",
        platform="arcgis",
        endpoint="https://services1.arcgis.com/9yy6msODkIBzkUXU/arcgis/rest/services/Building_Permits/FeatureServer/0",
    )
    where, kwargs = build_query_shape(meta, datetime(2026, 5, 26, tzinfo=UTC))
    assert "ISSUED_DT >= '2026-05-26T00:00:00'" in where
    assert kwargs == {"order_by": "ISSUED_DT DESC"}


def test_a_backfill_selects_the_columns_its_poll_selects():
    # A deeds select keeps grantor and grantee names on the server; without
    # it a backfill read every column.
    meta = _meta(
        watermark_col="SALEDATE",
        platform="arcgis",
        endpoint="https://services.example/arcgis/rest/services/Sales/FeatureServer/0",
        select="PARCELID,SALEDATE,SALEPRICE",
    )
    _, kwargs = build_query_shape(meta, datetime(2026, 5, 26, tzinfo=UTC))
    assert kwargs == {"select": "PARCELID,SALEDATE,SALEPRICE", "order_by": "SALEDATE DESC"}


def test_a_backfill_reads_coded_values_as_their_names_as_its_poll_does():
    # Allentown's 311 form stores "130245" for "Report a Pothole".
    meta = _meta(
        watermark_col="CreationDate",
        platform="arcgis",
        endpoint="https://services.example/arcgis/rest/services/Requests/FeatureServer/0",
        select="objectid,globalid,issue,status,CreationDate",
        decode_domains=True,
    )
    _, kwargs = build_query_shape(meta, datetime(2026, 5, 26, tzinfo=UTC))
    assert kwargs == {
        "select": "objectid,globalid,issue,status,CreationDate",
        "decode_domains": True,
        "order_by": "CreationDate DESC",
    }


def test_a_snapshot_backfill_keeps_its_own_order():
    meta = _meta(watermark_col="", platform="arcgis", order_by="SALE_DATE DESC, OBJECTID DESC")
    _, kwargs = build_query_shape(meta, None)
    assert kwargs == {"order_by": "SALE_DATE DESC, OBJECTID DESC"}


def test_a_text_watermark_window_starts_in_its_own_format():
    # ADR 0005: the column holds text, so the literal is compared as text.
    # '20260115' sorts above '2026-05-26T00:00:00', so the ISO window read
    # every sale from the first of January.
    meta = _meta(
        watermark_col="DOCDATE",
        platform="arcgis",
        endpoint="https://services.example/arcgis/rest/services/Sales/FeatureServer/0",
        watermark_type="text",
        watermark_format="%Y%m%d",
    )
    where, kwargs = build_query_shape(meta, datetime(2026, 5, 26, tzinfo=UTC))
    assert where == "DOCDATE >= '20260526'"
    assert kwargs == {"order_by": "DOCDATE DESC"}


def _text_dated_sales(order_by=None):
    return _meta(
        watermark_col="SALE_DATE",
        platform="arcgis",
        endpoint="https://services.example/arcgis/rest/services/Sales/FeatureServer/0",
        watermark_type="text",
        watermark_format="%m/%d/%Y",
        **({"order_by": order_by} if order_by else {}),
    )


def test_text_the_server_can_compare_keeps_its_comparison():
    csv = _meta(
        watermark_col="sale_date",
        platform="csv",
        endpoint="https://data.example/sales.csv",
        watermark_type="text",
        watermark_format="%m/%d/%Y",
    )
    untyped = _meta(watermark_col="ISSUEDATE", platform="arcgis", watermark_format="%m/%d/%Y")
    since = datetime(2026, 7, 2, tzinfo=UTC)
    assert build_query_shape(csv, since)[0] == "sale_date >= '07/02/2026'"
    assert build_query_shape(untyped, since)[0] == "ISSUEDATE >= '2026-07-02T00:00:00'"


def test_a_window_on_text_that_does_not_sort_names_its_dates():
    # As text, '12/31/2018' sorts above '07/02/2026': from that literal,
    # Reno's newest-first read began with sales made on December 31 of 2018
    # to 2025. The window names July's days from the 2nd, then whole months.
    meta = _text_dated_sales(order_by="SALE_DATE DESC")
    where, kwargs = build_query_shape(meta, datetime(2026, 7, 2, tzinfo=UTC))
    assert where.startswith("(SALE_DATE IN ('07/02/2026', '7/2/2026', '07/03/2026', '7/3/2026'")
    assert "SALE_DATE LIKE '08/%/2026' OR SALE_DATE LIKE '8/%/2026'" in where
    # The column has no newest-first order, so the spec's own stands.
    assert kwargs == {"order_by": "SALE_DATE DESC"}


def test_a_full_load_keeps_every_text_dated_row():
    meta = _text_dated_sales()
    fake = _FakeScheduler({"permits_baltimore": meta})
    client = MagicMock()
    client.paginate.return_value = [[{"permitnumber": "old", "SALE_DATE": "10/02/2018"}]]
    pw = MagicMock()
    pw.parse_socrata_row.side_effect = lambda row, city_id=None: _fake_event(key=row["permitnumber"])
    _wire(fake, client, pw)

    report = backfill_job(
        fake, "permits_baltimore", since_dt=None, max_rows=None, page_size=None, batch_delay_seconds=0
    )

    assert report["published"] == 1
    assert client.paginate.call_args.kwargs["where_clause"] is None


def test_a_text_dated_csv_backfills_its_window():
    body = "Sale Date,Parcel\n12/15/2025,A\n10/01/2025,B\n02/03/2026,C\n09/15/2024,D\n"
    client = CSVClient(httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body))))
    meta = _meta(
        watermark_col="sale_date",
        platform="csv",
        endpoint="https://data.example/sales.csv",
        watermark_type="text",
        watermark_format="%m/%d/%Y",
    )

    where, kwargs = build_query_shape(meta, datetime(2025, 11, 1, tzinfo=UTC))
    rows = [row for batch in client.paginate(endpoint_url=meta["endpoint"], where_clause=where, **kwargs) for row in batch]

    # With the format the CSV client compares and sorts the column as dates;
    # as text, '02/03/2026' sorts below '11/01/2025' and above '12/15/2025'.
    assert where == "sale_date >= '11/01/2025'"
    assert [row["parcel"] for row in rows] == ["C", "A"]


def test_san_jose_text_window_casts_both_sides():
    meta = _meta(
        watermark_col="ISSUEDATE",
        platform="ckan",
        endpoint="ckan://data.sanjoseca.gov/045b3678-e923-4002-b696-300955bc6d06",
        watermark_type="text",
        watermark_format="%m/%d/%Y %I:%M:%S %p",
    )
    where, kwargs = build_query_shape(meta, datetime(2026, 5, 26, tzinfo=UTC))
    assert where == (
        "to_timestamp(\"ISSUEDATE\", 'MM/DD/YYYY HH12:MI:SS AM') >= "
        "to_timestamp('05/26/2026 12:00:00 AM', 'MM/DD/YYYY HH12:MI:SS AM')"
    )
    # The column itself still sorts as text ('9/9/2026' above '9/29/2026'),
    # so no newest-first order is sent.
    assert kwargs == {}


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


def test_every_backfill_hands_its_client_what_the_poll_hands_it(scheduler):
    """A spec's ``select``, workbook link, zip member, delimiter, keyset column
    and CSV watermark arguments reach a backfill as they reach ``poll_job``.
    Only the order differs: a window pages newest-first on its watermark."""
    shared = {"endpoint_url", "where_clause", "batch_size", "max_records"}
    checked = 0
    for job, meta in scheduler.job_metadata.items():
        if meta.get("platform") == "gbfs" or meta.get("national_feed"):
            continue
        client = scheduler._paginating_client_for(job)
        client.paginate = MagicMock(return_value=[])
        scheduler.poll_job(job, limit=10)
        polled = {k: v for k, v in client.paginate.call_args.kwargs.items() if k not in shared}

        _, backfilled = build_query_shape(meta, None)
        if meta.get("watermark_col"):
            polled.pop("order_by", None)
            backfilled.pop("order_by", None)
        assert backfilled == polled, job
        checked += 1
    assert checked > 300


def test_a_richmond_backfill_finds_the_workbook_and_places_each_sale(scheduler):
    producer = scheduler.producers["deeds"]
    rows = [
        {"pin": "W0001234005", "transfer_date": "2026-09-22T00:00:00", "consideration": 285000,
         "deed_book": "ID2026", "deed_page": 21877, "deed_type": "Deed"},
    ]
    producer.excel.paginate = MagicMock(return_value=[rows])
    producer.arcgis.fetch_centroid_index = MagicMock(return_value={"W0001234005": (37.553, -77.462)})

    report = backfill_job(
        scheduler, "deeds_richmond",
        since_dt=datetime(2026, 7, 2, tzinfo=UTC), max_rows=None,
        page_size=None, batch_delay_seconds=0,
    )

    assert report["published"] == 1
    kwargs = producer.excel.paginate.call_args.kwargs
    assert kwargs["link_pattern"] == r"Assessor_Transfers_[0-9-]+\.xlsx$"
    assert not set(kwargs["select"].split(",")) & {"grantee", "grantor"}
    lookup = producer.arcgis.fetch_centroid_index.call_args.kwargs
    assert (lookup["join_key"], lookup["join_values"]) == ("PIN", ["W0001234005"])
    event = producer.producer.produce.call_args.kwargs["payload"]
    assert (event.latitude, event.longitude) == (37.553, -77.462)


def test_a_bend_backfill_keeps_the_sales_its_metro_box_holds(scheduler):
    """A backfill clips Deschutes County's sales to Bend's box as the poll does."""
    producer = scheduler.producers["deeds"]
    rows = [
        {"OBJECTID": 1, "Taxlot": "181208AB09999", "Book_Page_1": "2026-99999",
         "Sales_Date_1": "2026-09-15T00:00:00+00:00", "Total_Sales_Price_1": 612000.0,
         "Reject_Description_1": "CONFIRMED SALE"},
        {"OBJECTID": 2, "Taxlot": "171229DD09999", "Book_Page_1": "2026-99998",
         "Sales_Date_1": "2026-09-14T00:00:00+00:00", "Total_Sales_Price_1": 0.0,
         "Reject_Description_1": "GRANTOR/GRANTEE ARE THE SAME"},
    ]
    producer.arcgis.paginate = MagicMock(return_value=[rows])
    producer.arcgis.fetch_centroid_index = MagicMock(
        return_value={"181208AB09999": (44.0480, -121.3120), "171229DD09999": (44.1500, -121.3300)}
    )

    report = backfill_job(
        scheduler, "deeds_bend", since_dt=None, max_rows=None, page_size=None, batch_delay_seconds=0,
    )

    assert (report["fetched"], report["published"], report["outside_metro"]) == (2, 1, 1)
    scheduler.dlq_producer.route_to_dlq.assert_not_called()
    event = producer.producer.produce.call_args.kwargs["payload"]
    assert (event.bbl, event.latitude, event.longitude) == ("181208AB09999", 44.0480, -121.3120)


def test_a_worcester_backfill_places_each_request_from_its_state_plane_columns(scheduler):
    """A backfill converts a table's State Plane coordinates as the poll does."""
    producer = scheduler.producers["311"]
    rows = [
        {"ObjectId": 382001, "Service_Request_ID": 9900001, "Date_Logged": "2026-09-30", "Request_Type": "Pothole",
         "Division": "DPW&P Streets", "Status": "Open", "Closed_Date": None,
         "X_Coordinate": 574340.05, "Y_coordinate": 2920859.95},
    ]
    producer.arcgis.paginate = MagicMock(return_value=[rows])
    producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

    report = backfill_job(
        scheduler, "311_worcester", since_dt=datetime(2026, 9, 1, tzinfo=UTC), max_rows=None,
        page_size=None, batch_delay_seconds=0,
    )

    assert report["published"] == 1
    scheduler.dlq_producer.route_to_dlq.assert_not_called()
    event = producer.producer.produce.call_args.kwargs["payload"]
    assert (round(event.latitude, 5), round(event.longitude, 5)) == (42.26259, -71.80229)


def test_backfill_job_counts_and_watermark():
    fake = _FakeScheduler({"permits_baltimore": _meta()})
    client = MagicMock()
    client.paginate.return_value = [
        [
            {"permitnumber": "A1", "IssuedDate": "2026-08-20T10:00:00"},
            {"permitnumber": "A2", "IssuedDate": "2026-08-21T10:00:00"},
        ],
        [{"permitnumber": "A1", "IssuedDate": "2026-08-19T10:00:00"}],  # dup id
    ]
    pw = MagicMock()
    pw.parse_socrata_row.side_effect = lambda row, city_id=None: (
        _fake_event(datetime(2026, 8, 21, tzinfo=UTC)) if row["permitnumber"] != "bad" else None
    )
    _wire(fake, client, pw)

    report = backfill_job(
        fake, "permits_baltimore",
        since_dt=datetime(2026, 5, 26, tzinfo=UTC), max_rows=None,
        page_size=None, batch_delay_seconds=0,
    )

    assert report["fetched"] == 3
    assert report["published"] == 2
    assert report["duplicates"] == 1
    assert report["max_watermark_seen"] == "2026-08-21T00:00:00"
    assert report["error"] is None
    # newest-first windowed query shape reached the client
    _, kwargs = client.paginate.call_args
    assert kwargs["where_clause"].startswith("IssuedDate >= '2026-05-26")
    assert kwargs["order_by"] == "IssuedDate DESC"
    # published through the producer, drops routed to DLQ
    assert pw.producer.produce.call_count == 2
    pw.producer.flush.assert_called_once()


def test_backfill_job_raw_column_watermark_and_violation_key():
    # A violation event carries no issuance/created/effective/recorded date:
    # the seed watermark comes from the raw watermark column, and the key from
    # violation_id, matching poll_job and ViolationsProducer.run_stream.
    fake = _FakeScheduler(
        {"violations_austin": _meta(watermark_col="opened_date", producer_key="violations", city_id="austin")}
    )
    client = MagicMock()
    client.paginate.return_value = [
        [
            {"_id": "C-1", "opened_date": "2026-08-20T10:00:00.000"},
            {"_id": "C-2", "opened_date": "2026-08-22T11:30:00.000"},
        ]
    ]
    pw = MagicMock()
    pw.parse_socrata_row.side_effect = lambda row, city_id=None: SimpleNamespace(
        violation_id=row["_id"], city_id="austin"
    )
    fake.clients = {"violations_austin": client}
    fake.producers["violations"] = pw

    report = backfill_job(
        fake, "violations_austin",
        since_dt=None, max_rows=None, page_size=None, batch_delay_seconds=0,
    )

    assert report["published"] == 2
    assert report["max_watermark_seen"] == "2026-08-22T11:30:00"
    keys = [c.kwargs["key"] for c in pw.producer.produce.call_args_list]
    assert keys == ["austin:C-1", "austin:C-2"]


def test_select_jobs_filters_city_and_feed():
    fake = _FakeScheduler({})
    fake.job_metadata = {
        "permits": _meta(),
        "permits_baltimore": _meta(),
        "311_baltimore": _meta(producer_key="311"),
        "sla_montgomery": _meta(producer_key="sla", city_id="montgomery"),
    }
    fake.job_metadata["permits"]["city_id"] = "nyc"

    assert select_jobs(fake, ["baltimore"], None) == ["311_baltimore", "permits_baltimore"]
    assert select_jobs(fake, ["baltimore"], ["311"]) == ["311_baltimore"]
    assert select_jobs(fake, None, ["sla"]) == ["sla_montgomery"]
    assert len(select_jobs(fake, None, None)) == 4


def test_main_runs_all_matching_jobs():
    fake = _FakeScheduler({
        "permits_baltimore": _meta(),
        "311_baltimore": _meta(producer_key="311"),
    })
    client = MagicMock()
    client.paginate.return_value = [[{"permitnumber": "A1", "IssuedDate": "2026-08-20"}]]
    pw = MagicMock()
    pw.parse_socrata_row.return_value = _fake_event()
    fake.clients = {"permits_baltimore": client, "311_baltimore": client}
    fake.producers = {"permits": pw, "311": pw}

    rc = main(["--city", "baltimore", "--since-days", "90", "--batch-delay-seconds", "0"], scheduler=fake)
    assert rc == 0
    assert pw.producer.produce.call_count == 2


def test_main_reports_fetch_error_and_exits_nonzero(capsys):
    fake = _FakeScheduler({"permits_baltimore": _meta()})
    client = MagicMock()
    client.paginate.side_effect = RuntimeError("portal down")
    pw = MagicMock()
    fake.clients = {"permits_baltimore": client}
    fake.producers = {"permits": pw}

    rc = main(["--city", "baltimore", "--batch-delay-seconds", "0"], scheduler=fake)
    assert rc == 1
    out = capsys.readouterr().out
    assert '"error": "fetch/publish aborted: portal down"' in out
    assert '"published": 0' in out


def test_seed_state_writes_and_keeps_max(tmp_path, capsys):
    fake = _FakeScheduler({"permits_baltimore": _meta()})
    client = MagicMock()
    client.paginate.return_value = [[{"permitnumber": "A1", "IssuedDate": "2026-08-20"}]]
    pw = MagicMock()
    pw.parse_socrata_row.return_value = _fake_event()
    fake.clients = {"permits_baltimore": client}
    fake.producers = {"permits": pw}

    state = tmp_path / "wm.json"
    rc = main(
        ["--city", "baltimore", "--batch-delay-seconds", "0", "--seed-state", str(state)],
        scheduler=fake,
    )
    assert rc == 0
    first = json.loads(state.read_text())
    assert first["permits_baltimore"]["high_watermark"] == "2026-08-20T00:00:00"
    assert first["permits_baltimore"]["seeded_by"] == "backfill_loader"

    # A second, lower watermark must not lower the stored one.
    client.paginate.return_value = [[{"permitnumber": "A2", "IssuedDate": "2026-07-01"}]]
    pw.parse_socrata_row.return_value = _fake_event(datetime(2026, 7, 1, tzinfo=UTC))
    main(["--city", "baltimore", "--batch-delay-seconds", "0", "--seed-state", str(state)], scheduler=fake)
    assert json.loads(state.read_text())["permits_baltimore"]["high_watermark"] == "2026-08-20T00:00:00"
