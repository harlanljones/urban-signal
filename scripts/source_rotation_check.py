"""Standing calendar: rotating source IDs (Norfolk FY, Alameda, King Co, Snohomish).

US-77. The weekly staleness probe watches registered feeds and the quarterly
rejection re-probe watches feeds we turned down; this covers the third gap —
feeds whose *identifier* rotates on a calendar, so the endpoint does not go
stale, it gets *replaced*.

Each check is a dated, owned recurring item in the ``CHECKS`` manifest below.
A single scheduled run (daily cron, alongside the staleness probe) dispatches
only the checks whose ``next_due`` has arrived, so every check fires on its
own cadence:

- ``norfolk_deeds_fy``   every July — rotate the FY sales dataset ID
- ``alameda_transfer``   annually    — revalue the transfer list if refreshed
- ``kingco_parcel_sales`` quarterly   — confirm slow cadence, not retirement
- ``snohomish_recent_sales`` annually — revalue the parked sales corpus

Run on the host:

    python scripts/source_rotation_check.py --status            # calendar view
    python scripts/source_rotation_check.py --force norfolk_deeds_fy
    python scripts/source_rotation_check.py --write-report      # fire due checks
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "docs" / "research" / "source-rotation-report.json"
STATE_PATH = REPO_ROOT / "docs" / "research" / "source-rotation-state.json"


def _iso_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _epoch_ms(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value) / 1000.0, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


_MONTH_STRING = re.compile(r"^([A-Za-z]{3})-(\d{4})$")
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def _month_string(value: Any) -> datetime | None:
    match = _MONTH_STRING.match(str(value or "").strip())
    if not match:
        return None
    try:
        return datetime(int(match.group(2)), _MONTHS[match.group(1)], 1, tzinfo=UTC)
    except KeyError:
        return None


# The dated, owned recurring checks. ``next_due`` seeds the first run; the
# state file carries the advancing schedule. ``source`` cites where the
# rotating-identifier contract is recorded so each check stays auditable.
CHECKS: list[dict[str, Any]] = [
    {
        "id": "norfolk_deeds_fy",
        "cadence": "every July",
        "next_due": "2027-07-01",
        "owner": "reliability",
        "source": "docs/expansion-roadmap.md §4 (Norfolk quirks); src/spatial/city_registry.py:901",
        "note": "Norfolk publishes one Property Assessment and Sales dataset per fiscal year; the old ID keeps answering with frozen data. Rotate the registered endpoint to the new FY resource when it appears.",
        "probe": {
            "kind": "socrata_rotation",
            "domain": "data.norfolk.gov",
            "id": "qva7-tzrf",
            "current_fy": "FY27",
            "catalog_queries": ["property assessment", "sales"],
            "family_prefix": "Property Assessment and Sales",
        },
    },
    {
        "id": "alameda_transfer",
        "cadence": "annually",
        "next_due": "2027-08-23",
        "owner": "reliability",
        "source": "docs/research/metro-expansion-and-new-signals.md §1 (Alameda)",
        "note": "Assessor Office Ownership Transfer List (APN, transfer_dt, value_from_trans_tax) was stale (newest 2023-04, layer untouched since 2025-07-07). If it ever refreshes it is the best deeds-shaped dataset of any surveyed county.",
        "probe": {
            "kind": "arcgis_layer",
            "url": "https://services5.arcgis.com/ROBnTHSNjoZ2Wm1P/arcgis/rest/services/Assessor_Office_Ownership_Transfer_List/FeatureServer/0",
            "date_col": "transfer_dt",
            "epoch_ms": True,
            "baseline": "2025-07-07",
        },
    },
    {
        "id": "kingco_parcel_sales",
        "cadence": "quarterly",
        "next_due": "2026-11-23",
        "owner": "reliability",
        "source": "docs/research/current-city-feed-gaps.md; docs/research/deeds-watermark-audit.md",
        "note": "Seattle DEEDS depends on this layer. Flagged 2026-08-23 as not refreshed since 2025-11-28 — confirm it is a slow cadence, not a quiet retirement.",
        "probe": {
            "kind": "arcgis_layer",
            "url": "https://gismaps.kingcounty.gov/arcgis/rest/services/Property/KingCo_PropertyInfo/MapServer/3",
            "date_col": "SaleDate",
            "epoch_ms": True,
            "baseline": "2025-11-20",
        },
    },
    {
        "id": "snohomish_recent_sales",
        "cadence": "annually",
        "next_due": "2027-08-23",
        "owner": "reliability",
        "source": "docs/research/metro-expansion-and-new-signals.md §1 (Snohomish)",
        "note": "Parked, not rejected: quarterly snapshots with month-level date strings (\"Jun-2026\"). Revalue as a future backfill/validation corpus rather than a live feed.",
        "probe": {
            "kind": "arcgis_layer",
            "url": "https://services6.arcgis.com/z6WYi9VRHfgwgtyW/arcgis/rest/services/Recent_Property_Sales/FeatureServer/0",
            "date_col": "TRNSF_DATE",
            "epoch_ms": False,
            "month_string": True,
            "baseline": "2026-08-19",
        },
    },
]


def _newest_date(probe: dict[str, Any], value: Any) -> datetime | None:
    if probe.get("epoch_ms"):
        return _epoch_ms(value)
    if probe.get("month_string"):
        return _month_string(value)
    return _iso_date(value)


def probe_socrata_rotation(probe: dict[str, Any], client: httpx.Client) -> tuple[str, str, dict[str, Any]]:
    base = f"https://{probe['domain']}/resource/{probe['id']}.json"
    count = client.get(base, params={"$select": "count(*)"}, timeout=30.0).json()
    rows = count[0].get("count") if isinstance(count, list) and count else None
    newest = None
    top = client.get(
        base,
        params={
            "$where": "transfer_date is not null",
            "$order": "transfer_date DESC",
            "$limit": 1,
        },
        timeout=30.0,
    ).json()
    if isinstance(top, list) and top:
        newest = top[0].get("transfer_date")

    hits = []
    for query in probe.get("catalog_queries", []):
        payload = client.get(
            "https://api.us.socrata.com/api/catalog/v1",
            params={"domains": probe["domain"], "q": query, "limit": 10},
            timeout=30.0,
        ).json()
        for item in (payload or {}).get("results", []):
            res = item.get("resource", {})
            name = res.get("name") or ""
            if probe.get("family_prefix", "").lower() in name.lower():
                hits.append({"id": res.get("id"), "name": name})

    current_fy = probe.get("current_fy", "")
    fy_match = re.search(r"FY(\d{2})", current_fy or "")
    current_num = int(fy_match.group(1)) if fy_match else None
    successors = []
    for hit in hits:
        m = re.search(r"FY(\d{2})", hit["name"])
        if m and current_num is not None and int(m.group(1)) > current_num:
            successors.append(hit)
    family_ids = sorted({h["id"] for h in hits})

    if successors:
        status = "ROTATION_DUE"
        reason = f"newer FY dataset(s) on {probe['domain']}: {', '.join(h['name'] for h in successors)}"
    else:
        status = "CURRENT"
        reason = f"current {current_fy} id alive ({rows} rows, newest transfer_date={newest}); no newer FY in family ({', '.join(family_ids) or 'none'})"
    evidence = {"id": probe["id"], "rows": rows, "newest_transfer_date": newest, "family": family_ids, "successors": successors}
    return status, reason, evidence


def probe_arcgis_layer(probe: dict[str, Any], client: httpx.Client) -> tuple[str, str, dict[str, Any]]:
    url = probe["url"]
    try:
        count_payload = client.get(
            url + "/query",
            params={"where": "1=1", "returnCountOnly": True, "f": "json"},
            timeout=30.0,
        ).json()
        rows = count_payload.get("count")
        params: dict[str, Any] = {
            "where": "1=1",
            "outFields": probe["date_col"],
            "resultRecordCount": 1,
            "f": "json",
        }
        # Month-string columns ("Sep-2025") sort lexicographically on the
        # server, so scan a bounded OBJECTID-DESC sample and take the max
        # client-side instead of trusting orderByFields on the date string.
        if probe.get("month_string"):
            params["orderByFields"] = "OBJECTID DESC"
            params["resultRecordCount"] = 500
        else:
            params["orderByFields"] = f"{probe['date_col']} DESC"
        top = client.get(url + "/query", params=params, timeout=30.0).json()
        features = top.get("features", [])
        raw_values = [f.get("attributes", {}).get(probe["date_col"]) for f in features]
        if probe.get("month_string"):
            parsed = [_month_string(v) for v in raw_values]
            parsed = [p for p in parsed if p]
            newest = max(parsed) if parsed else None
            raw = next((v for v, p in zip(raw_values, [_month_string(v) for v in raw_values]) if p == newest), None)
        else:
            raw = raw_values[0] if raw_values else None
            newest = _newest_date(probe, raw)
    except httpx.HTTPStatusError as exc:
        return "UNREACHABLE", f"HTTP {exc.response.status_code}", {"reachable": False}
    except Exception as exc:  # noqa: BLE001
        return "UNREACHABLE", str(exc)[:120], {"reachable": False}

    baseline = _iso_date(probe.get("baseline"))
    if newest and baseline:
        if newest > baseline:
            status = "MOVED"
            reason = f"newest {probe['date_col']} {newest.date()} > baseline {baseline.date()} — revalue"
        else:
            status = "UNCHANGED"
            reason = f"newest {probe['date_col']} {newest.date()} still <= baseline {baseline.date()}"
    else:
        status = "UNKNOWN"
        reason = f"could not parse newest {probe['date_col']}={raw!r}"
    evidence = {"reachable": True, "rows": rows, "newest_raw": raw, "newest_iso": newest.isoformat() if newest else None}
    return status, reason, evidence


PROBES = {
    "socrata_rotation": probe_socrata_rotation,
    "arcgis_layer": probe_arcgis_layer,
}


def advance_next_due(check: dict[str, Any], today: date) -> str:
    cadence = check["cadence"]
    if cadence == "every July":
        year = today.year if today.month <= 6 else today.year + 1
        return f"{year}-07-01"
    if cadence == "quarterly":
        return (datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=91)).date().isoformat()
    if cadence == "annually":
        return (datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=365)).date().isoformat()
    return check["next_due"]


def load_state() -> dict[str, dict[str, str]]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict[str, dict[str, str]]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(STATE_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATE_PATH)


def run(client: httpx.Client, state: dict[str, dict[str, str]], force: list[str], today: date) -> dict[str, Any]:
    reports = []
    for check in CHECKS:
        next_due = state.get(check["id"], {}).get("next_due") or check["next_due"]
        due = today.isoformat() >= next_due or check["id"] in force
        if not due:
            continue
        probe = PROBES[check["probe"]["kind"]]
        try:
            status, reason, evidence = probe(check["probe"], client)
            error = None
        except Exception as exc:  # noqa: BLE001  # one broken probe must not kill the run
            status, reason, evidence, error = "ERROR", str(exc)[:160], {}, str(exc)[:160]
        new_next_due = advance_next_due(check, today) if status != "ERROR" else next_due
        state[check["id"]] = {"next_due": new_next_due}
        reports.append({
            "id": check["id"],
            "cadence": check["cadence"],
            "owner": check["owner"],
            "next_due": new_next_due,
            "due": due,
            "status": status,
            "reason": reason,
            "evidence": evidence,
            "probed_at": datetime.now(UTC).isoformat(),
            **({"error": error} if error else {}),
        })
        print(f"{check['id']:22} {status:14} {reason}", flush=True)
    return {"generated_at": datetime.now(UTC).isoformat(), "checks": reports}


def calendar_rows() -> list[dict[str, Any]]:
    state = load_state()
    today = date.today().isoformat()
    rows = []
    for check in CHECKS:
        next_due = state.get(check["id"], {}).get("next_due") or check["next_due"]
        rows.append({
            "id": check["id"],
            "cadence": check["cadence"],
            "next_due": next_due,
            "owner": check["owner"],
            "source": check["source"],
            "note": check["note"],
            "due": today >= next_due,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true", help="print the calendar (no probes)")
    ap.add_argument("--force", action="append", help="run a check now regardless of due date (repeatable)")
    ap.add_argument("--write-report", action="store_true", help="persist report + advance state")
    args = ap.parse_args(argv)

    if args.status:
        for row in calendar_rows():
            flag = "  DUE NOW" if row["due"] else ""
            print(f"{row['id']:22} {row['cadence']:14} next {row['next_due']}  owner={row['owner']}{flag}")
            print(f"    {row['note']}")
        return 0

    today = date.today()
    state = load_state()
    try:
        with httpx.Client() as client:
            summary = run(client, state, args.force or [], today)
    except Exception as exc:  # noqa: BLE001
        print(f"source-rotation run failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2, default=str))
    if not summary["checks"]:
        print("no checks due today; use --force <id> to run a check now")
    if args.write_report and summary["checks"]:
        REPORT_PATH.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
        save_state(state)
        print(f"report written: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())