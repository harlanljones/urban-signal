"""Quarterly re-probe of rejected feed candidates (Wave R2, US-86).

Research docs decay: the 2026-08-23 survey concluded Kansas City's 311 feed
was "effectively dead" one day before a different query found it alive with
816k rows. This script watches the candidates we walked away from so the next
wrong rejection corrects itself.

It probes every entry in REJECTIONS below — dataset counts, schema drift,
and catalog searches, depending on why the candidate was originally
rejected — and reports status diffs versus the recorded verdict:

- ``ALIVE_SINCE_REJECTION``  data moved after we walked away
- ``STILL_REJECTED``         nothing has changed; exclusion stands
- ``SUPERSEDED``             candidate has since been registered (closure)
- ``INACCESSIBLE``           endpoint unreachable/blocked (watch continues)

Reports diffs; never pages. Exit code is 0 on any report, nonzero only when
the run itself is broken (probe layer exception).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "docs" / "research" / "rejection-recheck-report.json"

# A candidate counts as ALIVE when its newest activity postdates its recorded
# rejection by this margin (a quarter of quiet is expected between runs).
LIVE_MARGIN_DAYS = 7

SOcrata = "socrata"


def _dt(epoch_seconds: float | None) -> datetime | None:
    if not epoch_seconds:
        return None
    return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc)


def _parse_yyyymmdd(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        try:
            return datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return _iso_or_none(text)


def probe_socrata_dataset(probe: dict[str, Any], client: httpx.Client) -> dict[str, Any]:
    """Row count + optional date-field max for one Socrata resource."""
    base = f"https://{probe['domain']}/resource/{probe['id']}.json"
    count = httpx_get_json(client, base, {"$select": "count(:id)"})
    total = count[0].get("count_id") if isinstance(count, list) and count else None
    out: dict[str, Any] = {"rows": total}
    date_field = probe.get("date_field")
    if date_field:
        newest = httpx_get_json(
            client, base, {"$limit": 1, "$order": f"{date_field} DESC"}
        )
        value = newest[0].get(date_field) if isinstance(newest, list) and newest else None
        out["newest"] = value
        parsed = (
            _dt(value) if isinstance(value, (int, float)) else None
        ) or _parse_yyyymmdd(value) or _iso_or_none(value)
        out["newest_dt"] = parsed.isoformat() if parsed else None
    schema = httpx_get_json(client, base, {"$limit": 0})
    if isinstance(schema, dict):
        out["columns"] = sorted(schema.keys())
    return out


def _iso_or_none(value: Any) -> datetime | None:
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def probe_socrata_catalog(probe: dict[str, Any], client: httpx.Client) -> dict[str, Any]:
    """Discovery-API search: any dataset in the domain matching a family
    keyword whose rowsUpdatedAt postdates the rejection."""
    results = []
    for query in probe.get("queries", []):
        try:
            payload = httpx_get_json(
                client,
                "https://api.us.socrata.com/api/catalog/v1",
                {"domains": probe["domain"], "q": query, "limit": 5},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                # Domain has left the Socrata discovery universe (platform
                # migration) — surfaced as drift, not crash.
                return {"freshest": None, "hits": 0, "domain_absent": True}
            raise
        for item in (payload or {}).get("results", []):
            res = item.get("resource", {})
            updated = _dt(res.get("rowsUpdatedAt"))
            results.append({
                "id": res.get("id"),
                "name": res.get("name"),
                "query": query,
                "rows_updated": updated.isoformat() if updated else None,
            })
    freshest = max(
        (r for r in results if r["rows_updated"]),
        key=lambda r: r["rows_updated"],
        default=None,
    )
    return {"freshest": freshest, "hits": len(results)}


def probe_socrata_schema(probe: dict[str, Any], client: httpx.Client) -> dict[str, Any]:
    """Column-name watch for rejections caused by a missing field (schema
    drift detection): fires when a watched pattern appears in the resource."""
    payload = httpx_get_json(client, f"https://{probe['domain']}/api/views/{probe['id']}.json", {})
    columns = [
        column.get("fieldName", "")
        for column in (payload or {}).get("columns", [])
    ]
    return {"columns": sorted(c for c in columns if c)}


def probe_arcgis_layer(probe: dict[str, Any], client: httpx.Client) -> dict[str, Any]:
    """Reachability + row count for an ArcGIS layer/table."""
    try:
        payload = httpx_get_json(
            client,
            f"{probe['url']}/query",
            {"where": "1=1", "returnCountOnly": True, "f": "json"},
        )
    except httpx.HTTPStatusError as exc:
        return {"reachable": False, "status": exc.response.status_code}
    if isinstance(payload, dict) and "count" in payload:
        return {"reachable": True, "rows": payload["count"]}
    return {"reachable": False, "error": str(payload)[:120]}


def httpx_get_json(client: httpx.Client, url: str, params: dict[str, Any]) -> Any:
    response = client.get(url, params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


PROBES = {
    "socrata_dataset": probe_socrata_dataset,
    "socrata_catalog": probe_socrata_catalog,
    "socrata_schema": probe_socrata_schema,
    "arcgis_layer": probe_arcgis_layer,
}

# The manifest of documented rejections. Each entry cites the research doc
# carrying the verdict so the report stays auditable back to prose.
REJECTIONS: list[dict[str, Any]] = [
    {
        # THE acceptance case: rejected 2026-08-23 as "effectively dead",
        # found alive 2026-08-24 under a different dataset name, registered
        # same day as HJ-120. Kept in the manifest as the mechanism proof.
        "id": "kc_311",
        "source": "wave-2-city-candidates.md §1 (2026-08-23 survey correction)",
        "rejected_on": "2026-08-23",
        "claim": "effectively dead from stale top hits",
        "superseded_by": "HJ-120",
        "probe": {
            "kind": "socrata_dataset",
            "domain": "data.kcmo.org",
            "id": "d4px-6rwg",
            "date_field": "open_date_time",
        },
    },
    {
        "id": "kc_permits",
        "source": "wave-2-city-candidates.md §Tier3 / socrata-sweep.md dead ends",
        "rejected_on": "2026-08-23",
        "claim": "decade-dead listings plus annual archive tables",
        "probe": {
            "kind": "socrata_catalog",
            "domain": "data.kcmo.org",
            "queries": ["building permits", "permits issued"],
        },
    },
    {
        # Superseded by US-134: the feed now carries a valid_license_for date
        # column and native GeoJSON point geometry, so this watch is a closure
        # until it flips to SUPERSEDED. The obsolete "no date column at all"
        # claim is corrected in data-coverage-sweep-2026-08-25.md §11.
        "id": "kc_sla",
        "source": "wave-2-city-candidates.md §Tier2 (corrected: data-coverage-sweep-2026-08-25.md §11)",
        "rejected_on": "2026-08-23",
        "claim": "location field only, no date column at all",
        "superseded_by": "US-134",
        "probe": {
            "kind": "socrata_schema",
            "domain": "data.kcmo.org",
            "id": "pnm4-68wg",
            "watch_patterns": ["date", "issued", "opened", "valid_license"],
        },
    },
    {
        # Flagged during US-75: hubNashville's Current-Year view began
        # carrying 2026 rows after the survey called it stuck at 2025.
        # Superseded by US-131: the hubNashville Current_Year 311 view is now
        # registered (ArcGIS, native coords, Latitude IS NOT NULL bucket).
        "id": "nashville_311",
        "source": "US-75 resolution note (survey said stuck at 2025)",
        "rejected_on": "2026-08-20",
        "claim": "latest hubNashville slice is 2025; no 2026 layer",
        "superseded_by": "US-131",
        "probe": {
            "kind": "socrata_catalog",
            "domain": "data.nashville.gov",
            "queries": ["311 service requests current year", "hubNashville"],
        },
    },
    {
        "id": "mc311",
        "source": "mc311-geocode-evaluation.md (US-94)",
        "rejected_on": "2026-08-24",
        "claim": "polygon attributes only; zip-only queries resolve nothing",
        "probe": {
            "kind": "socrata_schema",
            "domain": "data.montgomerycountymd.gov",
            "id": "xtyh-brr2",
            "watch_patterns": ["address", "street", "lat", "location"],
        },
    },
    {
        "id": "pg_parcel",
        "source": "HJ-125 resolution (deferred pending geometry hardening)",
        "rejected_on": "2026-08-24",
        "claim": "MultiPolygon-only geometry; no centroid columns",
        "probe": {
            "kind": "socrata_schema",
            "domain": "data.princegeorgescountymd.gov",
            "id": "qzrv-2tnv",
            "watch_patterns": ["centroid", "latitude", "longitude", "point"],
        },
    },
    {
        "id": "seattle_deeds",
        "source": "seattle-deeds-replacement.md (access-blocked)",
        "rejected_on": "2026-08-24",
        "claim": "rpsale_extr auth-gated; no anonymous official KC transaction API",
        "probe": {
            # King County publishes a Socrata open-data portal; if an
            # anonymous transaction-sales dataset ever appears there, this
            # watch fires without needing the gated AGO item.
            "kind": "socrata_catalog",
            "domain": "data.kingcounty.gov",
            "queries": ["real property sales", "rpsale", "sales transactions"],
        },
    },
    {
        "id": "providence_families",
        "source": "wave-2-city-candidates.md §Tier3",
        "rejected_on": "2026-08-23",
        "claim": "every feed-family hit years stale; 311 only",
        "probe": {
            "kind": "socrata_catalog",
            "domain": "data.providenceri.gov",
            "queries": ["building permits", "business licenses", "property sales", "311"],
        },
    },
    {
        "id": "miami_families",
        "source": "wave-2-city-candidates.md §Tier3",
        "rejected_on": "2026-08-23",
        "claim": "every feed-family hit stale; permits last moved 2022-06-01",
        "probe": {
            "kind": "socrata_catalog",
            "domain": "opendata.miamidade.gov",
            "queries": ["building permits", "business licenses", "property sales"],
        },
    },
    {
        "id": "buffalo_families",
        "source": "wave-2-city-candidates.md §Tier3",
        "rejected_on": "2026-08-23",
        "claim": "catalog answers; zero hits on all four families",
        "probe": {
            "kind": "socrata_catalog",
            "domain": "data.buffalony.gov",
            "queries": ["building permits", "business licenses", "property sales", "311"],
        },
    },
]


def classify(entry: dict[str, Any], evidence: dict[str, Any]) -> tuple[str, str]:
    """Map probe evidence to a status + one-line reason."""
    registered_now = entry_registered(entry["id"])
    kind = entry["probe"]["kind"]
    rejected_on = _parse_yyyymmdd(entry["rejected_on"])

    if kind == "socrata_dataset":
        newest = _iso_or_none(evidence.get("newest_dt"))
        if registered_now:
            return "SUPERSEDED", "registered (see superseded_by)"
        if newest and rejected_on and newest > rejected_on:
            return (
                "ALIVE_SINCE_REJECTION",
                f"newest activity {newest.date()} postdates the {entry['rejected_on']} verdict",
            )
        return "STILL_REJECTED", f"newest={evidence.get('newest')} rows={evidence.get('rows')}"
    if kind == "socrata_catalog":
        if evidence.get("domain_absent"):
            return (
                "INACCESSIBLE",
                "domain absent from Socrata discovery universe - manual re-probe required",
            )
        fresh = evidence.get("freshest") or {}
        updated = fresh.get("rows_updated")
        if registered_now:
            return "SUPERSEDED", "registered (see superseded_by)"
        if updated and rejected_on and _iso_or_none(updated) > rejected_on:
            return (
                "ALIVE_SINCE_REJECTION",
                f"{fresh.get('name')!r} ({fresh.get('id')}) moved {_iso_or_none(updated).date()}",
            )
        return (
            "STILL_REJECTED",
            f"freshest family hit: {(fresh.get('rows_updated') or 'none')[:10]}"
            if fresh
            else "no family hits at all",
        )
    if kind == "socrata_schema":
        columns = evidence.get("columns") or []
        lowered = [c.lower() for c in columns]
        matched = [
            pattern
            for pattern in entry["probe"].get("watch_patterns", [])
            if any(pattern in c for c in lowered)
        ]
        detail = f"matched patterns: {matched}" if matched else "no watched columns appeared"
        if registered_now:
            return "SUPERSEDED", "registered (see superseded_by)"
        if matched:
            return "ALIVE_SINCE_REJECTION", detail
        return "STILL_REJECTED", detail
    if kind == "arcgis_layer":
        if not evidence.get("reachable"):
            return "INACCESSIBLE", f"status/error: {evidence.get('status', evidence.get('error'))}"
        return "STILL_REJECTED", f"reachable, rows={evidence.get('rows')}"
    return "UNKNOWN", "unhandled probe kind"


_ENTRY_CITY = {
    "kc_311": ("kansas_city", "311"),
    "kc_permits": ("kansas_city", "permits"),
    "kc_sla": ("kansas_city", "sla"),
    "nashville_311": ("nashville", "311"),
    "mc311": ("montgomery", "311"),
    "pg_parcel": ("prince_georges", "deeds"),
}


def entry_registered(entry_id: str) -> bool:
    mapping = _ENTRY_CITY.get(entry_id)
    if not mapping:
        return False
    city_value, feed_value = mapping
    try:
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        cid = next(c for c in CityId if c.value == city_value)
        get_dataset(cid, FeedType(feed_value))
        return True
    except (KeyError, StopIteration):
        return False


def run(client: httpx.Client | None = None, entries: list[dict[str, Any]] | None = None) -> dict:
    own_client = client or httpx.Client()
    reports = []
    for entry in entries if entries is not None else REJECTIONS:
        probe = PROBES[entry["probe"]["kind"]]
        try:
            evidence = probe(entry["probe"], own_client)
            status, reason = classify(entry, evidence)
            error = None
        except Exception as exc:  # noqa: BLE001  # one broken probe must not kill the run
            evidence, status, reason, error = {}, "ERROR", str(exc)[:160], str(exc)[:160]
        reports.append({
            "id": entry["id"],
            "status": status,
            "reason": reason,
            "rejected_on": entry["rejected_on"],
            "claim": entry["claim"],
            "source": entry["source"],
            "superseded_by": entry.get("superseded_by"),
            "evidence": evidence,
            "probed_at": datetime.now(timezone.utc).isoformat(),
            **({"error": error} if error else {}),
        })
        print(f"{reports[-1]['id']:22} {status:22} {reason}", flush=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            status: sum(1 for r in reports if r["status"] == status)
            for status in {r["status"] for r in reports}
        },
        "results": reports,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true", help="Persist JSON report to docs/research/")
    args = parser.parse_args()
    try:
        with httpx.Client() as client:
            summary = run(client)
    except Exception as exc:  # noqa: BLE001
        print(f"recheck run failed: {exc}", file=sys.stderr)
        return 1
    flips = [r for r in summary["results"] if r["status"] == "ALIVE_SINCE_REJECTION"]
    print(json.dumps(summary["counts"], sort_keys=True))
    if flips:
        print("FLIPPED:", ", ".join(r["id"] for r in flips))
    if args.write_report:
        REPORT_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print(f"report written: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
