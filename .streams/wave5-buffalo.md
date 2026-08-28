# Wave 5 — Buffalo, NY claim

Ticket: US-349. Agent: LEAF-IMPLEMENTATION. Claimed: 2026-08-27.

## Scope (leaf only)

- `apps/api/src/spatial/cities/buffalo.py` (new)
- `apps/api/src/producers/field_maps_buffalo.py` (new, if needed)
- `apps/api/tests/unit/test_producers_buffalo.py` (new)

Forbidden: `city_registry.py`, `config.py`, `serving/dashboard.py`,
`cities/__init__.py`, existing tests, `apps/product/**`. No commits.

## Feed registered by this leaf

- SLA/licenses — Restaurant Licenses, Socrata `data.buffalony.gov/resource/4pp3-qkuj.json`
  (Tier 1 per `docs/research/probe-buffalo.md`, stamp 2026-08-27).

## Status: DONE (leaf, 2026-08-27)

Changeset: `apps/api/src/spatial/cities/buffalo.py` (1 feed: SLA Restaurant
Licenses, Socrata `4pp3-qkuj`; 6 divisions / 8 submarkets),
`apps/api/src/producers/field_maps_buffalo.py` (SLA map; gpsx/gpsy never
candidates — mixed CRS live),
`apps/api/tests/unit/test_producers_buffalo.py` (28 tests, spine-stable).

Gates: `test_producers_buffalo.py` 28/28 green; `test_city_leaf_naming.py -k
buffalo` green; `pytest -m interlock` 24 passed / 0 failed (unregistered leaf
holds closure); full suite 1876 passed / 3 skipped / 1 failed = spine-owned
leaf-count pin (`== 62`, concurrent wave-5 leaves make 67).

Live re-probe 2026-08-27: watermark `issdttm` = 2026-08-20 (re-stamped),
7d window = 23, 2/1,429 null `issdttm`, NEW vs probe doc: `neighborhood`
column exists (source-neighborhood passthrough) and `gpsx`/`gpsy` are MIXED
CRS (WGS84 on some rows, State Plane feet on others — native
`latitude`/`longitude` authoritative). 3 fixtures captured byte-verbatim.

Spine delta handoff: below / final message.
