from datetime import UTC, datetime
from unittest.mock import MagicMock

from src.producers.fdic_bankbranch_producer import FdicBankBranchProducer


def row(branch="100", service="11", established="01/02/2020"):
    return {
        "UNINUM": branch, "SERVTYPE": service, "LATITUDE": "40.7", "LONGITUDE": "-74.0",
        "ESTYMD": established, "CERT": "12", "NAME": "Example Bank",
        "ADDRESS": "1 Main St", "CITY": "New York", "STNAME": "NY", "ZIP": "10001",
    }


def producer(tmp_path, pages):
    client = MagicMock()
    calls = {"sod": 0, "locations": 0}

    def paginate(endpoint, **_):
        index = calls[endpoint]
        calls[endpoint] += 1
        if endpoint == "sod":
            return iter([[]])
        return iter([pages[min(index, len(pages) - 1)]])

    client.paginate.side_effect = paginate
    indexer = MagicMock()
    indexer.get_multi_res_hierarchy.return_value = {"h3_res7": "7", "h3_res8": "8", "h3_res9": "9"}
    result = FdicBankBranchProducer(client=client, indexer=indexer, state_dir=tmp_path)
    result.producer = MagicMock()
    return result


def test_build_event_uses_established_date_and_sod_context(tmp_path):
    branch = producer(tmp_path, [[], []])
    branch._sod = {"100": {"YEAR": "2025", "DEPSUMBR": "135353"}}
    event = branch.build_event(row(), "opened")
    assert event.branch_id == "100"
    assert event.event_date == datetime(2020, 1, 2, tzinfo=UTC)
    assert event.deposits_year == 2025
    assert event.deposits_thousands == 135353.0
    assert event.date_is_detection is False


def test_snapshot_diff_emits_once_and_persists_state(tmp_path):
    branch = producer(tmp_path, [[row(), row("200", "1")], [row()], [row()]])
    assert branch.run_stream() == 1
    assert (tmp_path / "branches.json").exists()
    assert branch.run_stream() == 0  # no second emission after reloading state


def test_limited_snapshot_does_not_persist_partial_state(tmp_path):
    branch = producer(tmp_path, [[row(), row("200")], []])
    assert branch.run_stream(limit=1) == 1
    assert not (tmp_path / "branches.json").exists()
