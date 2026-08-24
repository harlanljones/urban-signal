# ADR 0004: Address Geocoding with a Postgres Replay Cache

**Status:** Accepted
**Date:** 2026-08-24
**Scope:** urban-signal
**Supersedes:** —
**Companion:** US-28 (Wave G1); `docs/expansion-roadmap-wave-2.md` §3 D6

## Context

Eleven verified, currently-publishing feeds locate their rows with an address
string instead of coordinates — seven inside cities already registered. They
are excluded from the product solely for lack of a coordinate to index into
H3. Wave G exists to add them, and everything downstream (G2 Norfolk, G3 DC +
Denver completions, G4 Montgomery evaluation) consumes this capability.

The requirements are unforgiving in one specific way: backfill parity gate G6
re-runs historical ingestion months later and compares row counts per cell.
Any geocoding whose answer drifts between passes makes parity unverifiable.

## Decision

`src/spatial/geocoder.py` — a leaf module with one sanctioned spine touch in
`SpatialEnrichmentWorker.process_record`, invoked only when a normalized event
arrives with an address field but no coordinate.

1. **The Postgres cache is the replay guarantee, not an optimization.**
   `geocode_cache(address_hash → lat, lon, confidence, source)` freezes the
   first definitive provider answer per version-stamped hash of the
   normalized address. Definitive misses are frozen too (`lat IS NULL`), so a
   provider that later "finds" an address cannot make a replay diverge from
   the original backfill. Verified live: 500 newest Norfolk 311 rows geocoded
   twice across a `DELETE FROM geocode_cache` — 350 distinct addresses,
   350/350 byte-identical resolutions including the 23 misses.

2. **Normalization is versioned.** `normalize_address` is deterministic
   (uppercase, punctuation folded, whitespace collapsed, unit-designator
   tails dropped) and hashed as `sha256("v1|" + normalized)`. Changing the
   normalizer invalidates every cached coordinate by construction rather than
   silently mixing two eras of answers under one key.

3. **Confidence gating at read time.** Below `settings.geocode_confidence_
   floor` (default 0.9) a cached raw value resolves to `None`, so events emit
   null H3 rather than a wrong cell; raising or lowering policy never
   requires re-hitting providers because raw values are immutable. Census
   statuses map conservatively (Exact→1.0, Tie→0.5, Non_Exact→0.7);
   Nominatim exposes no score, so confidence is corroboration-based (house
   number present in the matched display → 0.95, else 0.5).

4. **Backends are pluggable and self-hostable.** `CensusBatchBackend`
   (TIGER/Line addressbatch, ≤1000/call, zero marginal cost) ships as the
   plan's named substrate; `NominatimBackend` (self-hostable URL; the public
   instance is usable for verification at its 1 req/s policy) served this
   ticket's acceptance runs because Census egress was unreachable from the
   verification environment. The cache makes backend choice invisible to
   replays.

5. **Provenance flag.** Enrichment stamps `coord_source` on every record it
   touches: `"native"` when the feed supplied geometry, otherwise the
   geocoder source string. Persistence of the flag into feature-store tables
   is deliberately deferred to the first-retrain prep delta (risk W7): the
   model-provenance check needs it at training time, and adding columns to
   four sinks is that delta's scope, not Wave G's.

## Alternatives Considered

- **Per-call paid providers** (commercial APIs): rejected — millions of
  backfill geocodes at nonzero marginal cost, rate limits per city, and
  results that drift without notice.
- **Geocode-at-registration only** (bake coordinates into registry specs):
  rejected — new rows arrive continuously; geocoding is a stream concern,
  not a schema constant.
- **Parcel-join geocoding** (DC `SSL`, Denver `PARID`): explicitly out of
  scope; if the address path proves insufficient there, that is a new ADR.
- **Trust Nominatim importance as confidence**: rejected — importance ranks
  a place's general prominence, not whether THIS house number matched;
  corroboration of the query's leading token is the honest signal available
  without a scoring endpoint.

## Consequences

- G2/G3/G4 can register address-only feeds behind a declared field_map plus
  `needs_geocode: true`-style expectation; no new geography hand-authoring.
- Wrong-cell risk is bounded by the floor: a miss thins a cell's features,
  it cannot poison them.
- Provider outages degrade enrichment to today's behavior (records skip)
  without caching garbage: exceptions are never frozen as answers.
- The public Nominatim instance is verification-grade only; production
  backfills must point `nominatim_base_url` at a self-hosted instance (its
  usage policy forbids bulk loads against the shared service).
