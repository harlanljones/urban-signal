# M1 — Validate the NYC permit source contract

Date: 2026-10-03. Status: proposed. Dependency: [ingestion audit](../../research/daily-ingestion-inventory.md).

## Purpose

Produce an implementable acquisition contract for `nyc / permits`, Socrata `ipu4-2q9a`, job `permits`. The existing issuance-date cursor and job-number identity cannot establish correction-safe, row-complete ingestion. Two observed permit rows share a job number, document, sequence and type. Approximately 3,990,806 rows exist; a capped poll cannot represent the whole dataset.

## Deliverable and interface

Commit a versioned source-contract document and small projected fixtures. Record endpoint/dataset identity, projected schema, business-key fields, source row ID, event/update timestamp types and precision, acquisition modes, deterministic ordering/continuation, replacement detection, correction overlap, reconciliation scope/cadence, request limits and timeout/retry behavior. Evidence includes query parameters, UTC observation time, row counts, hashes and links to publisher documentation. Exclude unrelated personal fields.

For each guarantee record `verified`, `unsupported`, or `unverified`, with evidence. A contract is implementation-ready only when every required guarantee is verified or has a tested fallback; observations from a few rows do not prove global uniqueness or ID persistence.

## Investigation and selection rules

1. Validate `permit_si_no` uniqueness/nullability across a complete, validated extraction or authoritative publisher guarantee. Investigate a documented composite if necessary. Do not use bare `job__` or assume Socrata row IDs survive replacement.
2. Test explicit `:updated_at` projection and filtering, equal-timestamp secondary ordering, adjacent-page continuation and inclusive/exclusive boundaries. Bound extraction at a source-supported upper watermark; verify behavior if records change while paginating.
3. Establish whether updates to old permits, geometry and status advance source update time. Use publisher guarantees and deterministic correction fixtures; record limits of live observational evidence.
4. Establish deletion/replacement visibility. Prefer a supported change feed if proven; otherwise require a consistent complete reconciliation or a documented, tested consistency strategy. Never infer deletion from an incomplete page set.
5. Verify quota/app-token requirements, 429 handling, safe page size and bounded bootstrap throughput. Existing ordered-query timeouts require an alternative or measured retry strategy, not an assumed working keyset query.

If update semantics are unsupported, select validated full acquisition/reconciliation and measure it. If neither complete acquisition nor identity can be established, mark the source unsuitable for this pilot and document an alternative source before M3. Do not silently narrow coverage to make a run pass.

## Acceptance

- Source contract resolves identity, completeness, correction, deletion and replacement rules with reproducible evidence.
- Fixtures demonstrate duplicates, equal timestamps across pages, late correction, moved geometry, missing IDs, deletion, publisher replacement and concurrent source changes.
- Event-time versus update-time behavior is explicit; issuance dates never stand in for update timestamps without a justified fallback.
- Bootstrap/delta/reconciliation sizing and quota evidence support M2/M3 planning.
- Missing cost is recorded: this feed cannot establish capex without an authoritative additional source/join.

Output is a source decision and contract, not a production registry or scheduler change. Rate/consistency guarantees and business-ID uniqueness remain unresolved until investigated.
