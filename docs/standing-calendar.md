# Standing calendar: rotating source IDs

US-77. A dated, owned schedule of checks for feeds whose **identifier rotates on
a calendar** — the endpoint does not go stale, it gets *replaced*. These are the
checks that fall between the two existing monitors:

- weekly staleness probe (`scripts/feed_staleness_probe.py`) — watches registered feeds;
- quarterly rejection re-probe (`scripts/rejection_recheck.py`) — watches feeds we turned down.

This calendar is **not prose in a roadmap**; it is the executable schedule in
`scripts/source_rotation_check.py` (manifest = the four rows below) plus the
advancing state in `docs/research/source-rotation-state.json`. A single daily
cron run of the script fires only the checks whose `next_due` has arrived, so
each check fires on its own cadence.

## Calendar

| Check | Cadence | Next due | Owner | Source |
|---|---|---|---|---|
| `norfolk_deeds_fy` | every July | `2027-07-01` | reliability | roadmap §4 Norfolk quirks; `src/spatial/city_registry.py:901` |
| `alameda_transfer` | annually | `2027-08-24` | reliability | `docs/research/metro-expansion-and-new-signals.md` §1 |
| `kingco_parcel_sales` | quarterly | `2026-11-23` | reliability | `docs/research/current-city-feed-gaps.md`; `deeds-watermark-audit.md` |
| `snohomish_recent_sales` | annually | `2027-08-24` | reliability | `docs/research/metro-expansion-and-new-signals.md` §1 |

## Checks

### `norfolk_deeds_fy` — every July
Norfolk publishes one "Property Assessment and Sales" dataset per fiscal year;
the old ID keeps answering with frozen data, so staleness alarms fire late or
not at all. Current registered ID is `qva7-tzrf` (**FY27**,
`apps/api/src/config.py:192`). The probe counts the current dataset and
catalog-searches the `data.norfolk.gov` family; it reports **`ROTATION_DUE`**
when a newer `FY##` resource appears. Rotation is a spine change (endpoint in
`config.py`).

### `alameda_transfer` — annually
Alameda's "Assessor Office Ownership Transfer List"
(`services5.arcgis.com/ROBnTHSNjoZ2Wm1P/.../Assessor_Office_Ownership_Transfer_List/FeatureServer/0`)
is a true transfer feed (APN, `transfer_dt`, `value_from_trans_tax`) but was
stale (newest row 2023-04, layer untouched since 2025-07-07). **If it ever
refreshes it is the best deeds-shaped dataset of any surveyed county.** The probe
reports **`MOVED`** when `transfer_dt` advances past the survey baseline.

### `kingco_parcel_sales` — quarterly
Seattle DEEDS depends on this layer
(`gismaps.kingcounty.gov/arcgis/rest/services/Property/KingCo_PropertyInfo/MapServer/3`).
Flagged 2026-08-23 as not refreshed since 2025-11-28 — this check confirms it is
a slow cadence, not a quiet retirement. The probe reports the newest `SaleDate`.

### `snohomish_recent_sales` — annually
Parked, not rejected: quarterly snapshots with month-level date strings
(`"Jun-2026"`). Revalue as a future backfill/validation corpus rather than a
live feed. The probe scans a bounded `OBJECTID DESC` sample (month-string dates
do not sort server-side) and reports the newest `TRNSF_DATE`.

## Baseline run (2026-08-24)

`scripts/source_rotation_check.py --force <id> --write-report` → report in
`docs/research/source-rotation-report.json`:

| Check | Status | Evidence |
|---|---|---|
| `norfolk_deeds_fy` | CURRENT | FY27 `qva7-tzrf` alive (74,331 rows, newest transfer_date 2026-08-21); no newer FY in family |
| `alameda_transfer` | UNCHANGED | newest `transfer_dt` 2025-03-31 ≤ baseline 2025-07-07 |
| `kingco_parcel_sales` | UNCHANGED | newest `SaleDate` 2025-11-20 = baseline (still frozen) |
| `snohomish_recent_sales` | UNCHANGED | newest `TRNSF_DATE` Aug-2026 (quarterly cadence continues) |

## Running it

```bash
python scripts/source_rotation_check.py --status          # calendar view (no probes)
python scripts/source_rotation_check.py --write-report    # fire checks whose next_due has arrived
python scripts/source_rotation_check.py --force <id>      # run one check now
```

Wire `--write-report` into the same cron slot as the weekly staleness probe; the
script dispatches per-check cadences itself.