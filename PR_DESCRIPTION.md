# US-423: Ingest FDIC Summary of Deposits, FMCSA carrier fleet data, and SBA 7(a)/504 loan volumes

## Summary

The Linear ticket description (US-423) bundles five federal feeds from
`docs/research/federal-mobility-energy-financial-signals-2026-08-30.md`:
FDIC Summary of Deposits, FMCSA SAFER/MCMIS, SBA 7(a)/504 loans, EIA Form 861
retail electricity rates, and CFPB HMDA LAR.

Investigation found that **FDIC SOD, FMCSA carrier registration, and SBA
7(a)/504 loans already have full producers wired into the platform** from
prior work (`fdic_bankbranch_producer.py`, `carrier_license_producer.py` +
`fmcsa_specs.py`, `sba_loan_producer.py`, all registered in
`src/spatial/national_feeds.py`). This PR adds the genuinely missing pieces:

1. **FMCSA fleet power-unit / hazmat freight-density** — the existing FMCSA
   integration (US-373) rides the SLA license-event path (registration
   status only); it does not carry `TOTAL_POWER_UNITS` or `HAZMAT_FLAG`, so
   the "freight & logistics density index" the ticket asks for did not
   exist. Added as a leaf module.
2. **EIA Form 861 / retail electricity rates** — no ingestion existed at
   all. Added a REST client + normalization for the EIA API v2
   retail-sales endpoint (commercial/industrial $/kWh).
3. **CFPB HMDA LAR ingestion** — `hmda_metrics.py` (US-165) already proved
   tract-level HMDA rollups to H3 are feasible, but took pre-aggregated
   counts as input; nothing turned raw LAR rows into those counts. Added
   the missing row-parsing/aggregation step plus an HMDA Data Browser CSV
   client.

All three follow this repo's established convention for this wave of
federal context feeds (`epa_echo.py`, `hpms_context.py`, `hmda_metrics.py`,
`national_feeds.py`'s own module docstring): **leaf modules, no spine
edits**. None of them import `config`, `city_registry`, `geo_utils`,
`submarkets`, or `producers`. Registering any of them as a live scheduled
national feed (`NationalFeedSpec` entry, scheduled producer, macro/feature-
store table) is an explicit follow-up spine change, deliberately out of
scope here — matching how FDIC/SBA graduated from leaf-only to spine-wired
in separate, later PRs.

## Changes

- `apps/api/src/spatial/eia_electricity.py` (new) — `EiaElectricityClient`
  (offset-paginated REST client over `/v2/electricity/retail-sales/data`),
  row normalization (`parse_retail_sales_row(s)`, c/kWh -> $/kWh via
  `cents_to_dollars_per_kwh`), and `commercial_industrial_rate_index` (latest
  commercial/industrial $/kWh per state — the ticket's operating-cost axis).
- `apps/api/src/spatial/cfpb_hmda.py` (new) — `HmdaLarClient` (FFIEC Data
  Browser API v2 CSV client), `aggregate_lar_rows` (raw LAR rows ->
  per-tract `TractHmdaAggregate` counts: purchase/investor-purchase,
  home-improvement volume, decided/denied, government-backed share, loan
  amount total), and `tract_metrics_for_rollup` which hands off directly to
  the existing `hmda_metrics.rollup_tract_to_h3` (verified in tests).
- `apps/api/src/spatial/fmcsa_fleet_density.py` (new) — `CarrierFleetRecord`,
  `carrier_freight_weight` (power-unit count with a hazmat multiplier and a
  mega-fleet clamp), `map_carrier_to_h3` / `accumulate_fleet_density`
  (mirrors `epa_echo.py`'s event->H3 accumulation pattern), and
  `hazmat_share` for a hex's hazmat-carrier concentration.
- `apps/api/tests/unit/test_eia_electricity.py` (new) — parsing, rate-index,
  and client pagination/param tests (fake `httpx`-shaped client, no network).
- `apps/api/tests/unit/test_cfpb_hmda.py` (new) — tract normalization,
  aggregation semantics (action/purpose/occupancy/loan-type codes), and an
  end-to-end aggregate -> `rollup_tract_to_h3` wiring test.
- `apps/api/tests/unit/test_fmcsa_fleet_density.py` (new) — weighting,
  clamping, H3 mapping, and accumulation tests.

## Testing

- `python -m pytest apps/api/tests/unit/test_eia_electricity.py
  apps/api/tests/unit/test_cfpb_hmda.py
  apps/api/tests/unit/test_fmcsa_fleet_density.py -q` — all new tests pass
  (38 tests).
- Full `apps/api/tests/unit` suite run to confirm no regressions from the
  new leaf modules (they touch no shared/spine files).

## Notes

- **FDIC SOD, FMCSA license events, and SBA 7(a)/504** were already fully
  implemented (producers + `NationalFeedSpec` entries) before this ticket
  was picked up; no changes were made to those files. If the ticket intent
  was instead to re-verify or extend those specific producers (e.g. an
  explicit branch-opening/closure-velocity aggregate table, or a
  job-creation-by-NAICS rollup for SBA), that is a distinct scope from what
  was missing and not covered here — flagged for follow-up if still wanted.
- EIA and HMDA (and the new FMCSA fleet-density helper) are intentionally
  **not** wired into `national_feeds.py` / the scheduler / `config.py`, per
  this repo's documented pattern of landing federal context feeds as
  spine-free leaf modules first and registering them in a later, explicitly
  scoped spine PR. A comment was left on the Linear ticket noting this
  scoping call in case the reviewer wants full spine registration in this
  same PR instead.
- EIA's utility-service-territory polygon overlay (mapping a commercial
  rate onto H3 by utility boundary rather than by state) is out of scope
  per the research doc's own phasing ("Wave 1 Series / Wave 2 Spatial");
  this PR covers the Wave 1 series retrieval only.