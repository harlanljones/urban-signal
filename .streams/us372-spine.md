# Stream log — us372-spine — 2026-08-28

## Claim

- **Stream id:** `us372-spine` (spine hold for the us372-state-licenses leaf delta, scoped by Harlan)
- **Scope (3 registrations only, per Harlan's dispatch):**
  1. CO liquor `ier5-5ms2` → Denver `FeedType.SLA` (replaces `snap_sla_spec("CO")`)
  2. TX TABC `7hf9-qc9f` → Houston/Dallas/San Antonio `FeedType.SLA` (replaces `snap_sla_spec("TX")`; Austin migrates to the namespaced map for cross-city uniformity)
  3. OR CCB `g77e-6bhs` → Portland `FeedType.SLA` — **Harlan's call: SWAP, OLCC qad4-bnxp retired** (ADR 0007 one-endpoint-per-feedtype; second-feedtype route rejected as new machinery)
- **Spine files:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`. scheduler.py NO-OP (all three ride FeedType.SLA / producer_key="sla"; snapshot+watermark handled generically).
- **Leaf sources consumed:** `apps/api/src/producers/state_license_specs.py`, `apps/api/src/producers/field_maps_state_licenses.py` (untracked leaf work by us372-state-licenses — NOT edited by this hold).

## Decisions

- 2026-08-28 — Portland fork raised to Harlan (ADR 0007 "never worked around"): options were swap / additive second-dataset refactor / defer. Answer: **swap OLCC → CCB**.
- 2026-08-28 — Endpoints must be settings-declared (`test_endpoints_declared_in_settings` collects str defaults starting with platform schemes; URL-with-$select defaults qualify). Three new config fields.
- 2026-08-28 — Registry entries are inline DatasetSpec copies of the leaf spec dicts with endpoints re-pointed at the new settings fields (house style), field maps imported from the leaf module.
- 2026-08-28 — Austin migration included: same namespaced endpoint, TABC_ACTIVE_FIELD_MAP, watermark current_issued_date → status_change_date (fresher cursor, captures renewals). Stored high_watermark stays epoch-compatible.
- 2026-08-28 — The OR CCB dataset's `related_key` verified as a real (hidden) view column; dedup falls through to `license_number` for row payloads that omit it.
- 2026-08-28 — Edit #3 initially landed the Dallas slice in El Paso's block (shared "frozen 2018-2021" permits context); caught by the SNAP extended-set test, reverted El Paso, applied to the real Dallas block. All seven blocks re-verified per-city.

## Outcome

- **CO liquor `ier5-5ms2` → Denver** — replaced `snap_sla_spec("CO")`; snapshot (`watermark_col=""`), geocoded points (`needs_geocode=False`), where `city = 'Denver'` (3,121 rows verified live).
- **TABC `7hf9-qc9f` → Houston/Dallas/Austin/San Antonio** — county slices Harris 20,003 / Dallas 9,667 / Bexar 7,520 (verified live); Austin migrated to the shared namespaced map + `status_change_date` watermark. All four TX slices share one endpoint/field-map/watermark contract; address-only rows geocode via ADR 0004.
- **OR CCB `g77e-6bhs` → Portland** — SWAP: OLCC retired, CCB takes the SLA slot. Snapshot mode, where `city = 'PORTLAND' AND state = 'OR'` (6,067 rows verified live), address-only (needs_geocode, Portland OR context).
- El Paso / Fort Worth SNAP SLA slices untouched (out of scope).
- **Config:** `socrata_tabc_active_endpoint`, `socrata_co_liquor_endpoint`, `socrata_or_ccb_endpoint`, each carrying `$select=*, '<ns>:' || ... as license_type_ns` (leaf-verified httpx merge).
- **Tests:** interlock gate 24/24 green; affected files green (snap lists shrunk 27→23; dallas/denver/houston/san_antonio left SNAP; portland/denver/austin updated; parse tests stub the ADR-0004 geocoder per the boise precedent). Full suite: pre-existing `test_city_leaf_naming` failure (101 vs 97 leaf modules — southeast-wave debt, NOT this hold).

## Next step

Dispatch log updated; US-372 comment for the record. Follow-ups per Harlan's queue completed separately: Maricopa CSV probe (`docs/research/probe-maricopa-sales-affidavits.md`), FRED key wiring (`.env.example` `FRED_API_KEY`), Tier 2 ETL plan (`docs/research/tier-2-etl-plan.md`).
