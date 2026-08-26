# US-130 — Philadelphia deeds: filter to document_type='DEED'

Claimed. Linear: https://linear.app/harlanljones/issue/US-130/upgrade-philadelphia-deeds-filter-to-document-typedeed

Small additive change — one `DatasetSpec` edit (extra.where) + tests + docs. Do
NOT touch other cities' blocks; do NOT change `deeds_acris_producer.py`.

## Live probe (2026-08-25)

Query `https://phl.carto.com/api/v2/sql?q=...` against `rtt_summary` (endpoint
`carto://phl.carto.com/rtt_summary`, `config.py:435` — unchanged).

**Full `document_type` distribution (5,136,492 rows):** `DEED` = 1,100,426
rows with 1,048,899 carrying `total_consideration` = **95.3% price-bearing**
(exactly the ticket's numbers). Adjacent deed families live-probed:
- `MISCELLANEOUS DEED` = 164,359 @ 71.8% price-bearing
- `DEED SHERIFF` = 69,687 @ 91.5%
- `SHERIFF'S DEED` = 19,011 @ 95.0%
- `DEED MISCELLANEOUS` = 259,087 @ 0.1% (noise — NOT in the optional IN list)

Mortgage/satisfaction families are the price-poisoned majority:
`MORTGAGE` = 1.52M @ 21.9%, `SATISFACTION` = 858k @ 0.7%,
`ASSIGNMENT OF MORTGAGE` = 424k @ 17.1%, etc.

**WHERE-filter check:** `WHERE document_type = 'DEED'` → `n=1,100,426,
wp=1,048,899` — matches the ticket claim exactly.

**Decision:** use the simple `where = "document_type = 'DEED'"` (matches the
issue title and ticket's primary spec; it is the smallest defensible change and
kills the noise families). The optional `IN (...)` was considered but the extra
families (notably `DEED MISCELLANEOUS` @ 0.1% price-bearing) add noise without
clear benefit for this scope. Not chosen.

## Changes

- `apps/api/src/spatial/city_registry.py` — PHILADELPHIA `FeedType.DEEDS`
  `DatasetSpec.extra`: added `"where": "document_type = 'DEED'"` (CartoClient
  already applies `where` via scheduler `base_where`). Rewrote the enclosing
  comment to describe the where-filter scoping instead of the over-ingestion
  caveat. No other city touched. **No `config.py`, no producer, no schema
  change.**
- `apps/api/tests/unit/test_producers_philadelphia.py` — added
  `test_deeds_where_filter_scopes_to_price_bearing_document_type` asserting the
  registered spec's `extra["where"]` and that the fragment flows into the
  CartoClient WHERE via `_join_where`; updated the module docstring's DEEDS note.
- `README.md` — Philly deeds cell → "CARTO (RTT deeds; document_type='DEED')".
- `docs/expansion-roadmap.md` — Philly row deeds cell → "DEEDS `rtt_summary`
  (`document_type='DEED'`)" + note.

## Verify

- Focused: `test_producers_philadelphia.py` (registry spec + producer wiring).
- `ruff check` each touched file; zero net-new findings.

## Open questions / notes

- The optional `IN ('DEED','MISCELLANEOUS DEED','DEED SHERIFF','SHERIFF\'S
  DEED')` was NOT used; the simple `= 'DEED'` is the elected spec. The
  `'DEED'` string literal needs no escaping (no embedded quote).
