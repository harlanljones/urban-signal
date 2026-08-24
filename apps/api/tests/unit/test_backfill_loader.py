"""Offline tests for the bulk backfill loader (mocked scheduler machinery)."""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from scripts.backfill_loader import backfill_job, build_query_shape, main, select_jobs


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
