# Stream log — us120-evictions-content — 2026-08-24

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** us120-evictions-content
- **Leaf files I will create/edit:** `apps/product/pages/system.html`,
  `apps/product/pages/evidence.html`, `apps/product/pages/cities.html`,
  `apps/product/pages/cities.json` (only if its metadata needs it),
  `scripts/export_site_facts.py` (repo root, ONLY if FEED_ORDER decision says so),
  and `.streams/us120-evictions-content.md` (this log)
- **Spine files I expect to need:** none (all target files absent from
  docs/agents/spine-manifest.txt; US-120 is the only stream touching
  facts export per dispatch log)

## Intent

Add the NYC evictions stream to the product site where feeds are enumerated
(system/evidence/cities pages) with its ACTUAL platform/cadence sourced from
`apps/api/src/spatial/city_registry.py` + `apps/api/src/producers/*`. Decide
whether EVICTIONS belongs in `scripts/export_site_facts.py` `FEED_ORDER` (first-
class product fact for all metros) or stays hand-authored prose; pick the
least-invasive correct option and document the tradeoff. Do NOT hand-edit
`apps/product/public/facts.json`; regenerate via `bun run facts:export` if
FEED_ORDER changes. Do not commit anything (local git policy).

## Decisions

- **Verified stream facts (F5):** NYC evictions registry entry at
  `apps/api/src/spatial/city_registry.py:543-563` — `FeedType.EVICTIONS`
  DatasetSpec: platform=`socrata`, endpoint=`settings.socrata_nyc_evictions_endpoint`
  (`https://data.cityofnewyork.us/resource/6z8x-wfk4.json`, config.py:181-184),
  watermark_col=`executed_date`, topic=`raw.municipal.evictions`
  (config.py:56), interval_seconds=`900.0` (15 min), producer_key=`evictions`,
  extra: `expected_cadence_days=7` + field_map. Producer:
  `apps/api/src/producers/evictions_producer.py` — NYC-only context/validation
  signal, NEVER a LIMS input (single-metro asymmetry rule); scheduler registers
  `"evictions": EvictionsProducer(...)` (scheduler.py:225). Feed carries
  lat/lon directly; id_keys `court_index_number`/`docket_number`.

- **KEY DECISION — FEED_ORDER: DO NOT add EVICTIONS.** Evidence:
  (1) `scripts/export_site_facts.py:48` FEED_ORDER = [PERMITS, COMPLAINTS_311,
  SLA, DEEDS] drives `feed_labels` + per-metro `feeds`/`platforms` arrays +
  city-detail `feeds` map. (2) `scripts/verify-site-content.mjs:33` HARD-ASSERTS
  `metro.feeds.length !== 4` for EVERY metro — adding EVICTIONS makes all
  metros 5 slots and breaks the gate (and that verifier is NOT a leaf I can
  edit). (3) `apps/product/src/main.js:4` hardcodes `layers = ["Permits","311",
  "Licenses","Deeds"]` and is not a leaf file — a 5th slot would render with
  undefined labels. (4) `llms-full.txt:61` documents feed key schema
  (`permits`,`311`,`sla`,`deeds`). (5) EVICTIONS is NYC-only and NOT a LIMS
  ingredient — making it a first-class fact for all 28 metros (empty column)
  would misrepresent coverage. CONCLUSION: EVICTIONS stays hand-authored prose
  on system/evidence/cities pages with its real platform/cadence. NO change to
  scripts/export_site_facts.py; facts.json NOT regenerated (no FEED_ORDER
  change, and facts:export would anyway be unchanged).

## Current step

COMPLETE. Step 2 leaf edits applied; Step 3 PROPOSED SHARED EDITS appended;
Step 4 verification done. `bun run facts:check` → FACTS_FRESH (27 metros).
No JS touched by this stream; HTML fragments tag-balanced.

## Next step

None — hand back to orchestrator for serial shared-edit application
(CHANGELOG + llms.txt/llms-full.txt), full `bun run build`/`lint`, and commit.## PROPOSED SHARED EDITS (do NOT apply — orchestrator applies serially)

These are the shared-file edits US-120 requires. Since EVICTIONS was NOT added
to FEED_ORDER, `apps/product/public/facts.json` was NOT regenerated (facts:export
would produce byte-identical output — no FEED_ORDER change). No change to
`scripts/export_site_facts.py`.

### 1. `apps/product/CHANGELOG.md` — Unreleased > Added

Append under the existing `## Unreleased` / `### Added` list:

```md
- Documented the NYC Marshal's executed evictions stream (`6z8x-wfk4`) across the
  system, evidence, and cities pages as a context-only validation signal — Socrata,
  15-minute poll, `executed_date` watermark — explicitly not a LIMS input.
```

### 2. `apps/product/public/llms.txt` — summary line

Line 3 currently:
`> Urban Signal is an open-source spatial-intelligence system that turns municipal permits, 311 requests, licenses, deeds, and related records into explainable H3-based signals.`

No change required (it already says "and related records"). OPTIONAL only if the
orchestrator wants evictions surfaced in the top-level summary:
```md
> ... permits, 311 requests, licenses, deeds, executed evictions, and related records ...
```

### 3. `apps/product/public/llms-full.txt` — `/system/` section (line 20)

Line 20 currently:
`The ingestion and normalization pipeline: how Socrata, ArcGIS, Carto, CKAN, and static-CSV feeds are contracted per city, normalized onto an H3 grid, and served as actionable momentum.`

Append one sentence (matches the new system.html copy):
```md
New York additionally registers a context-only executed-evictions stream (`6z8x-wfk4`, Socrata, 15-minute poll) that never feeds the LIMS score.
```

### 4. `apps/product/public/llms-full.txt` — Per-city brief schema (line 61)

No change required: the brief `feeds` schema stays `permits`/`311`/`sla`/`deeds`
(evictions is not a first-class brief feed). Leave as-is.

---

### Notes for the orchestrator

- `apps/product/pages/system.html`, `evidence.html`, `cities.html`, and
  `cities.json` were edited (leaf files) — all mention the NYC evictions stream
  with platform=socrata, cadence=15 min, NYC-only context/validation.
- No FEED_ORDER change → `scripts/export_site_facts.py` untouched and
  `public/facts.json` NOT regenerated. `facts:check` is expected to stay green.
- No JS files were touched by this stream (`node --check` N/A here).
- `dist/` build + full `bun run lint` gate deferred to orchestrator close-out.
