# ADR 0005: Typed Text Watermarks with Declared Sentinel Exclusion

**Status:** Accepted
**Date:** 2026-08-24
**Scope:** urban-signal
**Supersedes:** —
**Companion:** HJ-114 (D7); `docs/expansion-roadmap-wave-2.md` §3 D7;
HJ-125 (PG County registration, unblocked by this decision)

## Context

Incremental ingestion assumes watermark columns compare correctly both
server-side (`ORDER BY col DESC`, `col > high_watermark`) and client-side
(max over fetched values). Two registered-adjacent sources break that
assumption:

1. **Sentinel values.** PG County's deed transfers (`qzrv-2tnv`) fill
   `transfer_date` with `ZZZZZZZZ` — and, as verified live on 2026-08-24,
   a second spelling `XXXXXXXX`. Sentinels sort above every real date, so
   they win `DESC` ordering, match every incremental `>` filter forever,
   and would be stored as the high watermark, permanently pinning the feed
   to its oldest rows.
2. **Mixed formats.** NYC's permit `issuance_date` carries ISO timestamps
   alongside `MM/DD/YYYY` in one column. Lexical comparison orders by
   string, not by date.

Wave 1 already shipped the client-side fix for (2): multi-format parsing in
`src/producers/watermarks.py` (ISO, `MM/DD/YYYY`, `YYYYMMDD`, epoch), used
by the staleness probe. But nothing expressed these per-feed facts in the
registry, so each new text-typed city re-fights the problem ad hoc — and
nothing stops sentinels from entering the scheduler's stored watermark.

## Decision

A dataset declares its watermark's type through `DatasetSpec.extra`; the
scheduler resolves declarations into behavior. No client changes.

```python
extra={
    "watermark_type": "text",          # opt-in; absent ⇒ legacy event-attr path
    "watermark_format": "%Y%m%d",      # strptime format of every non-sentinel value
    "watermark_exclude": ["ZZZZZZZZ", "XXXXXXXX"],
}
```

Three consequences, all behind the interlock gate:

1. **Server-side exclusion guard.** For any feed with declared exclusions,
   the scheduler appends `col NOT IN ('ZZZZZZZZ', ...)` to the fetch WHERE,
   and the probe passes the same guard as `where_clause`. Sentinels cannot
   crowd out real newest rows inside the bounded sample or the fetch page.
   The clause is built by `watermark_exclude_clause` (single-quote escaping,
   `None` when empty) and works across Socrata `$where`, ArcGIS `where`,
   and Carto WHERE.
2. **Typed raw-string high watermark.** Text-typed feeds track recency from
   the RAW column value before row parsing: each value is validated by
   `typed_watermark_entry` (declared-format parse + exclusion + emptiness),
   invalid values are dropped, and the stored high watermark is the raw
   string of the calendar-max entry. Because every surviving value shares
   one declared format, lexical `>` stays sound server-side across runs.
   Tracking pre-parse means a sentinel-free row advances ingestion recency
   even when event parsing routes it to the DLQ.
3. **Legacy path untouched.** Feeds without `watermark_type: "text"` keep
   the existing event-attribute watermark (`issuance_date` → `created_date`
   → …) with ISO storage. NYC needs no registry change: its problem was
   mixed formats, already solved by multi-format parse.

The probe gains no staleness semantics change — it already treated
unparseable watermarks as missing — but its bounded newest-row sample now
spends its budget on real data instead of sentinel rows.

## Alternatives Considered

- **Client-side filtering only** (drop sentinels after fetch): rejected —
  sentinels still win server-side `ORDER BY DESC`, so the newest REAL rows
  may not appear in the page at all; the guard must reach the query.
- **Normalize on ingest** (rewrite sentinel rows' dates): rejected —
  fabricating dates for garbage rows corrupts provenance; exclusion is
  honest about what the source published.
- **Per-client sentinel hardcoding** (`ZZZ...` constants in clients):
  rejected — spellings vary per source (`XXXXXXXX` proved this within one
  week of noticing `ZZZZZZZZ`); declaration beats convention.
- **Epoch-normalized stored watermark for text feeds**: rejected — storing
  ISO-reformatted strings under a `YYYYMMDD` column breaks the `>`
  filter against future raw comparisons; raw storage keeps one format.

## Consequences

- PG County registration (HJ-125) declares both observed sentinels; the
  mechanism is verified live against `qzrv-2tnv`: guarded top-of-order
  returns real `YYYYMMDD` dates (`20260529`…), typed newest = 2026-05-29.
- New text-typed cities cost three `extra` keys, zero scheduler edits.
- Sentinel discovery remains operational: the probe flags stale feeds, and
  an unknown sentinel spelling still fails parse (→ dropped, feed reads
  stale) rather than poisoning state — degradation, not corruption.
- `watermark_exclude` lists live in the registry and inherit review there;
  wrong declarations surface as the same stale-feed signal.
