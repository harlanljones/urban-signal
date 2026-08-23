# Stream log — wave-b-field-maps — 2026-08-23

## Claim

- **Stream id:** `wave-b-field-maps`
- **Leaf files I will create/edit:** `src/producers/field_maps.py` (new helper,
  not on the spine), `tests/unit/test_field_maps.py`,
  `.streams/wave-b-field-maps.md` (this file)
- **Spine files I expect to need:** `src/spatial/city_registry.py`,
  `src/producers/dob_permits_producer.py`,
  `src/producers/complaints_311_producer.py`,
  `src/producers/sla_licenses_producer.py`,
  `src/producers/deeds_acris_producer.py`

Single stream holds the interlock for the whole wave. Scope follows step 1 of
the implementation sketch in
`docs/research/new-orleans-austin-verification.md`: the mapping-table mechanism
lands as its own spine stream BEFORE city leaves fan out in C1/C2.

## Intent

Cities declare their column spellings as data instead of growing shared
`or row.get(...)` chains forever. Concretely: `DatasetSpec.extra["field_map"]`
maps canonical event fields to candidate row keys (dotted paths index nested
containers); the four shared parsers consult the map for the resolved city
BEFORE falling back to their generic chains. Chains remain the defaults, so the
refactor is purely additive for every city that declares nothing. As the
end-to-end proof case, LA MyLA311's seven Wave-A spellings MIGRATE out of the
311 chains into `REGISTRY[LOS_ANGELES].datasets[COMPLAINTS_311]` — net-neutral
behavior, proven by the existing LA test suite staying green untouched. Also:
tighten the 311 `sr_number`⇒chicago sniff (Austin 311 trips it) to require a
second Chicago-only marker. Done looks like: interlock gate green, full suite
green, new mechanism tests green, NOLA/Austin implementable as mapping-table
entries plus geography modules with zero parser edits.

## Decisions

- 15:05 — Map lives in `DatasetSpec.extra["field_map"]` per the research
  recommendation ("extra already exists as the natural home"); no DatasetSpec
  schema change.
- 15:06 — `first_mapped` uses chain-parity truthiness (falsy values skip),
  so a map can never introduce behavior a same-position chain term wouldn't
  have; dotted `container.field` keys cover ArcGIS-style nested points
  (NOLA `location_1.latitude`, KC-style geometry) without a second lookup
  concept.
- 15:07 — `resolve_field_map` returns `{}` for unknown cities and for
  registered cities lacking the feed (LA DEEDS), so autodetected rows parse
  through bare chains exactly as before.
- 15:08 — Migration limited to LA 311 (Wave-A additions only — every one was
  LA-exclusive, so pulling them back out of shared chains cannot affect other
  cities); Seattle/LA/NYC/Chicago/SF legacy spellings stay in chains until a
  dedicated pass, keeping this wave reviewable.
- 15:09 — Sniff fix: chicago requires `sr_number` PLUS one of
  `sr_type`/`sr_short_code`/`ward`/`police_sector`/`community_area`. Austin's
  `sr_type_desc` is exact-key-distinct, so bare Austin rows fall to the nyc
  default instead of mislabelling chicago. Production call sites all pass
  `city_id` explicitly (verified: scheduler + all four produce() loops), so
  this hardens replay/testing paths only.

## Current step

Done.

## Next step

None. Gates: `pytest -m interlock` 17/17; full suite 251/251 (230 pre-wave +
21 new mechanism tests); ruff clean on new files, mypy clean, spine-file ruff
count down 4 vs HEAD baseline; the 3 pre-existing mypy findings in
deeds_acris_producer.py are unchanged (baselined). One mid-wave correction:
an edit briefly dropped the SF autodetect branch from the 311 parser — caught
by re-reading the diff before gating and restored; the final branch order is
SF → chicago(tightened) → LA → nyc, with all four branches verified present.
Artifacts left uncommitted per local git policy.

C1/C2 can now register NOLA/Austin (and any sweep city) as geography modules
plus `field_map` entries with zero parser edits: NOLA ~19 map entries,
Austin ~7, per the tables in docs/research/new-orleans-austin-verification.md.
