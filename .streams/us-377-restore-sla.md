# Stream log — us-377-restore-sla — 2026-09-25

## Claim

- **Stream id:** us-377-restore-sla
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/data/{austin,dallas,fort_worth,el_paso,buffalo,rochester,syracuse,nyc,washington_dc}.yaml`
  - `apps/api/tests/unit/test_producers_{austin,dc,snap}.py`
  - `apps/api/tests/unit/test_childcare_specs.py`
  - `apps/product/public/facts.json`, `apps/product/public/cities/*.json`
  - `.streams/us-377-restore-sla.md`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py` (additive `FeedType.CHILDCARE`)
  - `apps/api/src/producers/sla_licenses_producer.py` (thread feed type into field-map resolution)
  - `apps/api/src/config.py` (only if the restored endpoints lack Settings fields)

## Intent

US-377 (`96d7580`, PR #49) wired four childcare licensing registries into nine
metros "under FeedType.SLA" by *replacing* each city's existing `datasets.sla`
block rather than adding alongside it. NYC lost its DBPR business-licensing
feed, Austin its TABC feed, Buffalo and Syracuse their NY liquor feeds, DC its
DCRA feed, and Dallas/Fort Worth/El Paso/Rochester their USDA SNAP Retailer
Locator layers. Done means: the nine displaced feeds are restored, the four
childcare registries register under a new additive `FeedType.CHILDCARE`
alongside them, no city's signals are lost, and `pytest -m interlock` plus the
full suite are green with no pinning test weakened.

## Decisions

- 2026-09-25 — Confirmed with the ticket owner: restore the displaced feeds and
  give childcare its own FeedType. Accepting the displacement was rejected
  because it permanently drops nine metros' business-licensing and SNAP
  household-formation signals.
- 2026-09-25 — `FeedType.SLA` is already a bucket, not strictly business
  licensing: USDA SNAP Retailer Locator (US-364) and several state licensing
  families already register under it as household-formation proxies. So
  "childcare under SLA" matched local convention; the defect was the
  *replacement*, not the bucket choice. A new FeedType is still required
  because `datasets` holds one DatasetSpec per feed type per city.
- 2026-09-25 — First design (one `sla` producer serving both feeds, feed type
  threaded through `parse_socrata_row`) was **rejected by the interlock gate**:
  `test_dataset_specs_complete` requires `producer_key == feed.value`, and
  `test_feed_topics_map_to_configured_topics` requires a topic per feed type.
  The gate is the house rule, so the design changed to a dedicated
  `ChildcareLicensingProducer` subclass rather than weakening two invariants.
  Childcare shares the SLA *topic*, which the gate explicitly permits for
  identical event shapes (`ENERGY_BENCHMARK`/`BIKE_PED` precedent).
- 2026-09-25 — `FEED` is a `FeedType` *value held as a string* and resolved per
  call. A module-level `from src.spatial.city_registry import FeedType` in a
  producer is a circular import: city_registry → registry_derivation → city
  modules → producers. This is why the module's registry imports are
  function-local; the new producer follows the same rule.
- 2026-09-25 — Nine tests were red from this displacement before this stream
  started: `test_producers_austin` (1), `test_producers_dc` (4),
  `test_producers_snap` (2), `test_scheduler` (2). Restoring the feeds fixed
  all nine. Two further failures were unrelated latent rot found while
  verifying: a magic feed *count* in `test_feed_staleness_probe.py` (now pins
  the feed *set*, so a change names itself) and a hardcoded two-value
  `ingestion_mode` assertion in `test_scheduler.py` when five modes are in use.
  The modes are now `INGESTION_MODES` in the registry and the interlock gate
  asserts every registered spec declares one of them.
- 2026-09-25 — `scripts/export_site_facts.py`'s `FEED_ORDER` deliberately left
  at the four headline families. It is a marketing list, and the restored
  business-licensing feed is what belongs there; advertising childcare is a
  product decision, not a consequence of this fix. `facts:check` is green.

## Current step

Complete and verified. All nine displaced feeds restored, childcare registered
alongside them, spine edits held and released clean.

## Next step

Nothing outstanding for this stream. If childcare should be advertised on the
product site, that is a separate product decision: add `FeedType.CHILDCARE` to
`FEED_ORDER` in `scripts/export_site_facts.py` and re-export.
