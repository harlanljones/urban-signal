# ADR 0007: Multi-Source Metro vs Separate Registration

**Status:** Accepted
**Date:** 2026-08-24
**Scope:** urban-signal
**Supersedes:** —
**Companion:** US-68; US-80 (Pierce County, WA); `docs/research/metro-expansion-and-new-signals.md` §1

## Context

Each registered metro is one hand-authored `CityRegistration`: a single
`METRO_BBOX`, `DIVISION_BBOXES` nested inside it, submarket points inside
divisions, and `datasets: Dict[FeedType, DatasetSpec]` — exactly **one
endpoint per feed type per `CityId`** (`src/spatial/city_registry.py`). The
interlock gate (`pytest -m interlock`) enforces the containment invariant
(division bboxes inside the metro bbox, submarkets inside divisions) and the
one-endpoint-per-feed invariants (`test_dataset_specs_complete`,
`test_feed_topics_map_to_configured_topics`, `test_job_names_unique`,
`test_get_dataset_readable_error`, `test_platform_clients_exposed`).

A `DatasetSpec` endpoint is per-jurisdiction. That makes a county bolted onto
a metro ambiguous: "add Pierce County as a Seattle division" silently requires
either per-division endpoints (a spine schema change) or feeding Pierce hexes
from Seattle's endpoint (wrong data). Three shapes exist, cheapest first:

1. **New divisions under the existing metro** — works only when the county's
   data already flows through a feed the metro registers (rare outside King
   County, where the King County parcel-sales feed is registered as Seattle's
   deeds endpoint).
2. **Separate registration (new `CityId`)** — the honest shape today; each
   jurisdiction is its own partial registration with its own endpoints.
   Pierce County is specced this way (US-80).
3. **Multi-source metro** — keep one metro identity, make `DatasetSpec`
   per-division or per-source lists. A real schema change to spine files and
   the scheduler, not additive.

Shape 2 is accumulating: Montgomery County, DC, and (proposed) Prince George's
County are three separate registrations covering one metropolitan area, and
Oakland 311 — a live feed inside the SF registration's EAST_BAY division —
cannot be expressed by shape 2 at all. The registry is modelling jurisdictions
while the product sells metros.

## Decision

**Separate registration (shape 2) remains the ingestion model. Multi-source
metro (shape 3) is rejected for now. The product-lens mismatch is addressed by
a registry-level metro grouping, not by a `DatasetSpec` schema change.**

Concretely:

- Pierce County, WA registers as its own `CityId` (permits-only ArcGIS, US-80),
  unblocked by this decision.
- Multi-source `DatasetSpec` (per-division or per-source endpoint lists) is
  **deferred** until a funded feed actually needs it. The trigger is a concrete
  division-level feed inside an existing metro (the Oakland-311 class); when one
  is funded, the change is raised through the **interlock-refactor path** as a
  spine refactor — never worked around.
- The "registry models jurisdictions while the product sells metros" pain is
  treated as a **product-presentation problem**, not an ingestion one. The
  follow-up is an additive `metro_group` concept on the registry (a grouping of
  `CityId`s surfaced as one product metro / dashboard selector), which does not
  change `DatasetSpec`, the scheduler, or any interlock invariant.

The immediate geography consequence: **geography follows data source, not
adjacency.** A county is worth adding only if its feeds justify a separate
registration.

## Alternatives Considered

- **Multi-source metro now (shape 3).** Rejected: it is a spine schema change
  touching every `reg.datasets` invariant plus the scheduler, and its only
  concrete motivation today (Pierce) is served honestly by shape 2. Adopting
  it pre-emptively prices a refactor for a hypothetical feed. It remains
  available and is explicitly triggered by the next funded division-level feed.
- **New divisions under an existing metro (shape 1) for Pierce.** Rejected:
  Pierce's data comes from Pierce County's own ArcGIS FeatureServer; there is
  no Seattle feed it flows through. Feeding Pierce hexes from Seattle's
  endpoint would be wrong data.
- **Product-layer metro grouping as the only change, silently dropping the
  separate registrations.** Rejected: the grouping is additive and leaves the
  registrations intact; it does not change how ingestion is scheduled.
- **Do nothing / accept accumulation.** Rejected: the DC-metro spread and the
  unexpressible Oakland-311 feed make the decision explicit, and US-80 is
  blocked on it.

## Consequences

- **US-80 unblocks**: Pierce County proceeds as a separate registration.
- **US-68's AC met**: this ADR records the decision and its consequences.
- Shape 2 continues to cost "one enum member, aliases, registry entry, endpoint
  fields, field-mapping fallbacks" per jurisdiction — the recurring tax already
  priced in the survey; the grouping follow-up does not remove it.
- Oakland-311-class feeds remain unexpressible until the multi-source refactor
  is triggered; the SF registration's EAST_BAY division stays a geographic
  division fed by SF's endpoints.
- Interlock gate is unchanged and stays green: no `DatasetSpec` schema change.
  The future `metro_group` concept, when added, must extend the gate's coverage
  (a grouping resolving to registered `CityId`s) in the same spine hold.