# Stream log — us397-tx-trec-tdlr — 2026-08-30

## Claim

- **Stream id:** `us397-tx-trec-tdlr`
- **Leaf files I will create/edit:** `apps/api/src/producers/tx_trec_specs.py` +
  `apps/api/src/producers/field_maps_tx_trec.py` +
  `apps/api/tests/unit/test_tx_trec_specs.py` + `.streams/us397-tx-trec-tdlr.md`
- **Spine files I expect to need:** `apps/api/src/config.py`,
  `apps/api/src/spatial/city_registry.py` (NOT edited in this phase — the
  orchestrator applies the spine delta serially)

## Intent

Register three TX state license registries as SLA supplements for the nine
feedless TX metros (Abilene, Amarillo, Beaumont, Longview, Midland, Odessa,
Texarkana, Tyler, Waco) plus upgrades for Austin/Dallas/Fort Worth/Houston/San
Antonio/El Paso: TX TREC Broker & Sales Agent License Holders
(`s7ft-44qi`, stock, `trec_broker:`), TX TREC Applications for Initial License
Issuance (`bf5n-799f`, flow/leading indicator, `trec_app:`), and TX TDLR All
Licenses (`7358-krk7`, `tdlr:`, with the `MMDDCCYY` text watermark trap on
`license_expiration_date_mmddccyy`). Leaf-only deliverable this phase: three
`DatasetSpec`-shaped plain dicts in `tx_trec_specs.py` that construct via
`DatasetSpec(**spec)` with zero massaging, field maps in
`field_maps_tx_trec.py` keyed to the `sla` FeedType semantics of
`field_maps.resolve_field_map`, and unit tests proving shape/keys/watermark and
parse-through-the-real-producer. Done means the tests pass, ruff is clean, and
the spine has a copy-pasteable contract to wire these under SLA during the
interlock hold. County-name-only sources resolve to county-level covariates via
the `geography_crosswalk`, not H3 point events — labeled honestly in the docs.

## Decisions

- 2026-08-30 — Live-verified all three endpoints (data.texas.gov): `s7ft-44qi`
  (TREC broker stock, native `updated` watermark, county slice `county='Travis'`
  works), `bf5n-799f` (TREC app flow, native `updated`, county slice works),
  `7358-krk7` (TDLR, 983,494 rows). TDLR has NO native `updated` column — the
  only system timestamp is Socrata `:updated_at`, composed into `$select` like
  the childcare TX precedent (US-377). **Ticket said `updated` watermark for
  all three, but the TDLR dataset cannot honor that** — watermark is
  `:updated_at` for `tx_tdlr`; the two TREC feeds keep native `updated`.
- 2026-08-30 — `license_expiration_date_mmddccyy` verified as `MM/DD/YYYY`
  text (5,000-row format scan: 100% `NN/NN/NNNN`, 0 rows without slashes);
  the producer's `_parse_datetime` handles `%m/%d/%Y`, no producer change
  needed. The column NAME implies MMDDCCYY but the data is slash-delimited.
- 2026-08-30 — County-name-only sources declared `needs_geocode=False` with
  no lat/lng in the field maps; the county name rides `borough` (`county` /
  `business_county`) and resolves to county-level covariates via
  `geography_crosswalk`, NOT H3 point events (documented honestly in both
  leaf modules). Null-coordinate events follow the DC Basic Business Licenses
  precedent (US-134).
- 2026-08-30 — Namespacing rides the endpoint `$select` (SoQL
  `'trec_broker:'/'trec_app:'/'tdlr:' || license_type as license_type_ns`),
  the state-license/childcare pattern. TDLR's `$select` additionally composes
  `:updated_at` for the watermark column. No `namespaced` dict key — the
  ticket's "namespaced" key is expressed via the endpoint, matching
  `state_license_specs.py`/`childcare_specs.py` exactly (a bare `namespaced`
  key would not construct as `DatasetSpec(**spec)`).
- 2026-08-30 — Specs are county-sliced factory functions
  (`tx_trec_broker_spec(county)`, `tx_trec_app_spec(county)`,
  `tx_tdlr_spec(county)`), mirroring `tabc_active_spec(county)` /
  `tx_hhsc_ccl_spec(county)`. TDLR's `where` filters `business_county`
  (uppercase on the source, e.g. `'TRAVIS'`), TREC feeds filter `county`
  (Title case, e.g. `'Travis'`).
- 2026-08-30 — `tx_tdlr` cadence `interval_seconds=86400` (daily; 983,494-row
  full registry, expensive to poll hourly), TREC feeds hourly (3600) — daily
  refresh both.

## Current step

Leaf phase complete: all three leaf files written, tests green (18/18),
ruff clean. Work left uncommitted per dispatch.

## Next step

Hand the stream to the orchestrator for the spine hold (config.py
endpoint fields + city_registry.py registrations for the 9 feedless TX metros
and the 6 upgraded metros). Update dispatch log and the US-397 Linear ticket.
