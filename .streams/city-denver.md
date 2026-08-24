# Stream log — city-denver — 2026-08-24

## Claim

- **Stream id:** city-denver
- **Leaf files I will create/edit:** `src/spatial/cities/denver.py`, `tests/unit/test_producers_denver.py`
- **Spine files I expect to need:** `src/config.py`, `src/spatial/city_registry.py`, `src/spatial/cities/__init__.py`, `src/serving/dashboard.py`, `apps/product/public/index.html`, `README.md`, `src/export/snapshot_builder.py`, `tests/unit/test_export_snapshot.py`

## Intent

Register Denver's verified ArcGIS construction-permit and ODC 311 feeds, explicitly omit ungeocoded sales and issue-date-less licenses, pin uppercase coordinate and numeric-date quirks, and wire the city through the dashboard and export surfaces with the interlock gate green.

## Decisions

- 2026-08-24 — Use `denver` as the job suffix and register only permits plus 311; licenses and sales remain excluded because they cannot satisfy the current spatial contract.
- 2026-08-24 — Use one Denver Core division for the ArcGIS city-and-county extent; no authoritative submarket roster was supplied by the verified feed contract.
- 2026-08-24 — Preserve `RECEPTION_DATE` as the ArcGIS watermark and filter `$0` transfers only if the sales feed is ever revisited; no sales feed is registered now.

## Current step

Spine wiring is complete; Denver parser fixtures, snapshot/export, dashboard, and interlock checks are green.

## Next step

Post the HAR-24 verification comment and close the issue.
