# Stream log — us72-feedtype-taxonomy — 2026-08-24

## Claim

- **Stream id:** `us72-feedtype-taxonomy`
- **Leaf files I will create/edit:**
  - `apps/api/tests/unit/test_feedtype_taxonomy.py` (new)
  - `apps/api/tests/unit/test_interlock_gate.py` (FEED_TOPICS map)
  - `apps/api/src/consumers/feature_aggregation_worker.py` (enriched keying)
  - `.streams/us72-feedtype-taxonomy.md`
- **Spine files I expect to need:** `apps/api/src/spatial/city_registry.py`
  (FeedType members), `apps/api/src/config.py` (raw topics).

## Intent

US-72 (Signals S0): extend the feed taxonomy so signals beyond the original
four can be registered at all. Add FeedType members (crime, street_cut,
evictions, str), matching `raw.municipal.*` topics, and complete the
partition/keying review (plan §Scaling notes: key by `city_id+h3` to preserve
per-cell ordering). Deliberately NOT in scope: the features/model side and any
city registration — each signal ticket (US-71/81/92/93) carries its own
ablation requirement.

Done = enum + topics + routing ready (proven ingestible by tests), enriched
topic keyed `city_id:h3`, interlock + full suite green, US-72 resolved, then
US-71 (blocked by this) started.

## Decisions

- 2026-08-24 — New FeedType members: `CRIME`, `STREET_CUT`, `EVICTIONS`,
  `STR`. No city registers any of them yet — this ticket makes registration
  *possible*, downstream tickets register the feeds.
- 2026-08-24 — Topics mirror the existing `raw.municipal.*` convention:
  `raw.municipal.crime`, `.street_cut`, `.evictions`, `.str`. Scheduler
  routing and `get_job_name` are already generic over FeedType; no scheduler
  code change is needed for the taxonomy itself.
- 2026-08-24 — Keying review: raw topics key `city_id:record_id` (idempotent
  dedup, already the case). The enriched H3 topic keys by `h3_index` alone;
  per the scaling note we align it to `city_id:h3_index` and set the real
  `city_id` on `EnrichedH3Feature` (previously it defaulted to "nyc" for every
  cell — a latent mislabel). Downstream consumers (postgis_worker) ignore the
  key, so this is safe.
- 2026-08-24 — No producer/client/field-map work in this ticket: new feeds are
  not registered, so `test_platform_clients_exposed` and registry cadence are
  untouched.

## Current step

DONE. Enum + topics + enriched keying + tests all in place; interlock green;
full suite green (719 passed, 0 failures). Working tree NOT committed
(awaiting instruction; another stream's Pierce work is uncommitted alongside).

## Next step

Linear resolution on US-72, then claim + start US-71 (crime feeds), which US-72
unblocks.