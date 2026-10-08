"""Tests for release-generation pruning (hex-coverage Stage B bounded retention)."""

from __future__ import annotations

import json

import httpx
import pytest
from scripts.prune_snapshot_releases import (
    PruneError,
    delete_keys,
    keep_ids,
    list_release_keys,
    main,
    prune,
    read_pointer_from_bulk,
    release_id,
    stale_release_keys,
)

KEEP = {"r-20261007-aaaaaaaa", "r-20261006-bbbbbbbb"}
STALE = "r-20261005-cccccccc"


def _client(keys: list[str], posts: list[list[str]]) -> httpx.Client:
    """A KV mock: paginates key lists two at a time and records delete bodies."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            cursor = int(dict(request.url.params).get("cursor", "0") or 0)
            page = keys[cursor : cursor + 2]
            next_cursor = str(cursor + 2) if cursor + 2 < len(keys) else ""
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": [{"name": name} for name in page],
                    "result_info": {"cursor": next_cursor},
                },
            )
        body = json.loads(request.content)
        posts.append(body)
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {"successful_key_count": len(body), "unsuccessful_keys": []},
            },
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_read_pointer_from_bulk(tmp_path):
    bulk = tmp_path / "kv-bulk.json"
    bulk.write_text(
        json.dumps(
            [
                {"key": "grid/nyc", "value": "{}"},
                {
                    "key": "snapshot/current",
                    "value": json.dumps({"current": "r-1", "previous": "r-0"}),
                },
            ]
        )
    )
    pointer = read_pointer_from_bulk(bulk)
    assert pointer == {"current": "r-1", "previous": "r-0"}


def test_read_pointer_missing_raises(tmp_path):
    bulk = tmp_path / "kv-bulk.json"
    bulk.write_text(json.dumps([{"key": "grid/nyc", "value": "{}"}]))
    with pytest.raises(PruneError):
        read_pointer_from_bulk(bulk)


def test_keep_ids_drops_null_previous():
    assert keep_ids({"current": "r-1", "previous": None}) == {"r-1"}
    with pytest.raises(PruneError):
        keep_ids({"current": None, "previous": None})


def test_release_id_parsing():
    assert release_id("releases/r-1/grid/nyc") == "r-1"
    assert release_id("releases/") is None
    assert release_id("releases/r-1") is None
    assert release_id("grid/nyc") is None


def test_stale_release_keys_keeps_current_and_previous():
    keys = [
        f"releases/{KEEP_id}/grid/nyc" for KEEP_id in sorted(KEEP)
    ] + [
        f"releases/{STALE}/grid/nyc",
        f"releases/{STALE}/cells/abc",
        "releases/",  # unparseable -> never deleted
        "grid/nyc",  # legacy logical key -> not under the prefix
    ]
    stale = stale_release_keys(keys, KEEP)
    assert sorted(stale) == sorted([f"releases/{STALE}/grid/nyc", f"releases/{STALE}/cells/abc"])


def test_prune_deletes_only_stale_generations():
    keys = [f"releases/{KEEP_id}/grid/nyc" for KEEP_id in sorted(KEEP)]
    keys += [f"releases/{STALE}/grid/nyc", f"releases/{STALE}/cells/abc"]
    posts: list[list[str]] = []
    summary = prune(_client(keys, posts), "acct", "ns", KEEP)
    assert summary["scanned"] == 4
    assert summary["kept"] == 2
    assert summary["stale"] == 2
    assert summary["deleted"] == 2
    assert posts == [[f"releases/{STALE}/grid/nyc", f"releases/{STALE}/cells/abc"]]


def test_prune_dry_run_deletes_nothing():
    keys = [f"releases/{STALE}/grid/nyc"]
    posts: list[list[str]] = []
    summary = prune(_client(keys, posts), "acct", "ns", KEEP, dry_run=True)
    assert summary["stale"] == 1
    assert summary["deleted"] == 0
    assert posts == []


def test_delete_keys_batches():
    posts: list[list[str]] = []
    client = _client([], posts)
    outcome = delete_keys(client, "acct", "ns", ["a", "b", "c"], batch=2)
    assert [len(p) for p in posts] == [2, 1]
    assert outcome["successful"] == 3


def test_list_release_keys_follows_cursor():
    keys = ["releases/a/x", "releases/b/x", "releases/c/x"]
    assert list_release_keys(_client(keys, []), "acct", "ns") == keys


def test_main_without_token_fails(tmp_path, monkeypatch):
    bulk = tmp_path / "kv-bulk.json"
    bulk.write_text(json.dumps([{"key": "snapshot/current", "value": '{"current":"r-1"}'}]))
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    code = main(
        ["--account-id", "acct", "--namespace-id", "ns", "--pointer", str(bulk)]
    )
    assert code == 1
