"""Unit tests for the Wave R2 rejection-recheck (US-86).

Classification logic is exercised with stubbed probe evidence; the manifest's
acceptance entry (KC 311 re-found from the 2026-08-23 rejection list) is
asserted structurally so the guarantee survives refactors.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from scripts.rejection_recheck import (
    REJECTIONS,
    classify,
    entry_registered,
    run,
)


def _entry(probe_kind: str, rejected_on: str = "2026-08-23", **probe_extra):
    return {
        "id": "test_entry",
        "source": "test",
        "rejected_on": rejected_on,
        "claim": "test claim",
        "superseded_by": None,
        "probe": {"kind": probe_kind, **probe_extra},
    }


def _dt(days_from_now: float) -> str:
    dt = datetime.now(UTC) + timedelta(days=days_from_now)
    return dt.isoformat()


class TestClassification:
    def test_dataset_alive_when_activity_postdates_rejection(self):
        entry = _entry("socrata_dataset", domain="d", id="x", date_field="created")
        evidence = {"rows": 816428, "newest_dt": _dt(-1)}  # yesterday
        status, reason = classify(entry, evidence)
        assert status == "ALIVE_SINCE_REJECTION"
        assert "postdates" in reason

    def test_dataset_still_rejected_when_quiet(self):
        entry = _entry("socrata_dataset", domain="d", id="x", date_field="created")
        evidence = {"rows": 12, "newest_dt": _dt(-400)}
        status, _ = classify(entry, evidence)
        assert status == "STILL_REJECTED"

    def test_catalog_domain_absent_is_inaccessible(self):
        entry = _entry(
            "socrata_catalog", domain="gone.example", queries=["permits"]
        )
        status, reason = classify(entry, {"freshest": None, "domain_absent": True})
        assert status == "INACCESSIBLE"
        assert "discovery universe" in reason

    def test_schema_watch_fires_on_new_columns(self):
        entry = _entry(
            "socrata_schema",
            domain="d",
            id="x",
            watch_patterns=["latitude", "address"],
        )
        status, reason = classify(
            entry, {"columns": ["objectid", "premise_address", "zip"]}
        )
        assert status == "ALIVE_SINCE_REJECTION"
        assert "address" in reason

    def test_arcgis_blocked_is_inaccessible(self):
        entry = _entry("arcgis_layer", url="https://blocked.example/0")
        status, _ = classify(entry, {"reachable": False, "status": 403})
        assert status == "INACCESSIBLE"


class TestManifestAcceptance:
    """The ticket's acceptance case, asserted structurally."""

    def test_kc_311_entry_carries_the_2026_08_23_rejection(self):
        entry = next(e for e in REJECTIONS if e["id"] == "kc_311")
        assert entry["rejected_on"] == "2026-08-23"
        assert entry["probe"]["id"] == "d4px-6rwg"
        assert entry["probe"]["domain"] == "data.kcmo.org"
        assert entry["superseded_by"] == "HJ-120"

    def test_every_entry_cites_a_source_doc_and_probe(self):
        for entry in REJECTIONS:
            assert entry["source"], entry["id"]
            assert entry["probe"]["kind"] in {
                "socrata_dataset",
                "socrata_catalog",
                "socrata_schema",
                "arcgis_layer",
            }, entry["id"]
            assert entry["rejected_on"], entry["id"]


class TestRun:
    def test_one_broken_probe_does_not_kill_the_run(self):
        good = dict(_entry("socrata_dataset", domain="ok.example", id="fine", date_field="created"), id="good")
        bad = dict(_entry("socrata_dataset", domain="bad.example", id="boom"), id="boom")

        class FlakyClient:
            def get(self, url, params=None, timeout=None):
                if "boom" in url:
                    raise RuntimeError("network split")
                response = MagicMock()
                response.raise_for_status = lambda: None
                if params and "$select" in params:
                    response.json.return_value = [{"count_id": 5}]
                elif params and "$order" in params:
                    response.json.return_value = [{"created": _dt(-1)}]
                else:
                    response.json.return_value = []
                return response

        summary = run(client=FlakyClient(), entries=[good, bad])
        statuses = {r["id"]: r["status"] for r in summary["results"]}
        assert statuses["good"] == "ALIVE_SINCE_REJECTION"
        assert statuses["boom"] == "ERROR"

    def test_registered_candidate_reports_superseded(self):
        entries = [dict(e) for e in REJECTIONS if e["id"] == "kc_311"]
        with patch("scripts.rejection_recheck.entry_registered", return_value=True):
            summary = run(client=MagicMock(), entries=entries)
        result = summary["results"][0]
        assert result["status"] == "SUPERSEDED"
        assert result["superseded_by"] == "HJ-120"

    def test_entry_registered_reflects_live_registry(self):
        # Kansas City 311 registered today (HJ-120); SLA never was.
        assert entry_registered("kc_311") is True
        assert entry_registered("kc_sla") is False


class TestLiveAcceptance:
    """The ticket's literal acceptance: the script re-finds KC 311 from the
    2026-08-23 rejection list. Networked — runs the real dataset probe only."""

    def test_kc_311_resolves_with_fresh_evidence(self):
        from scripts.rejection_recheck import probe_socrata_dataset

        entry = next(e for e in REJECTIONS if e["id"] == "kc_311")["probe"]
        with httpx_client() as client:
            evidence = probe_socrata_dataset(entry, client)
        assert int(evidence["rows"]) > 800_000  # 816k at the survey; still alive


def httpx_client():
    import httpx

    manager = httpx.Client()
    return manager
