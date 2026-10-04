# Backend development milestone specifications

Date: 2026-10-03. Status: proposed specifications; documentation only.

Goal: replace synthetic/default dashboard inputs with trustworthy daily municipal features while retaining Cloudflare web apps and using GitHub Actions unless measured workloads justify another executor. The existing zoom fix and snapshot optimization are deployed. No new infrastructure, source switch, notification recipient or service retirement is authorized by these documents alone.

| Milestone | Specification | Depends on | Exit evidence |
| --- | --- | --- | --- |
| M1 — Validate NYC source contract | [Source contract](2026-10-03-nyc-source-contract-design.md) | Existing audit | Proven identity, acquisition and reconciliation rules |
| M2 — Establish durable storage | [Storage](2026-10-03-ingestion-storage-design.md) | M1 sizing evidence; can investigate in parallel | Authorized target, verified conditional commits and restore |
| M3 — Build shadow ingestion | [Shadow ingestion](2026-10-03-shadow-ingestion-design.md) | M1 + M2 | Replayable daily acquisition and complete feature baseline |
| M4 — Validate shadow pilot | [Pilot validation](2026-10-03-shadow-validation-design.md) | M3 | Seven successful daily cycles plus correctness/cost evidence |
| M5 — Integrate real dashboard inputs | [Dashboard integration](2026-10-03-real-dashboard-inputs-design.md) | M4 + required feed/model readiness | Provenance-aware production rollout and tested rollback |
| M6 — Retire redundant services | [Retirement](2026-10-03-backend-retirement-design.md) | M5 for replaced dashboard dependencies; separate alert readiness | Owner-approved dependency removal, retained data and verified savings |

M1 and M2 evidence gathering can overlap. M3–M5 are sequential. Retirement inventory can begin early, but successful permit ingestion does not replace all Kafka, PostGIS or alert users.

Each spec describes required behavior and evidence, not a task-by-task implementation plan. Record unresolved decisions as gates with concrete evidence requirements. Start implementation planning for a milestone once its inputs are settled. The [existing pilot contract](daily-ingestion-pilot.md) remains the shared durability/replay contract; these specs refine it rather than replace it.

## Architecture choice

Recommended: daily Actions jobs plus durable object storage and Cloudflare serving. This matches approved freshness and keeps compute ephemeral. A container batch executor on GCP/AWS is an alternative for a measured bootstrap or reconciliation that cannot fit Actions limits. Keeping continuously running municipal services is appropriate where verified real-time alert users still depend on them. Railway/Fly scheduling is an executor option, not a substitute for durable acquisition and state correctness.

## Shared evidence rules

- Label source-event time, source-update time, acquisition time, feature as-of and snapshot publication time separately.
- Never infer completeness from an HTTP 200, green job, registry entry or newest event date.
- Version source, parser, feature and model contracts; reject incompatible combinations.
- Keep missing features explicit; zero and missing must not be interchangeable.
- Measure bootstrap, daily runs, retries, reconciliation, storage and remaining services separately. The existing estimate of 150 runner minutes/month covers the deployed snapshot workflow only.
- Production behavior changes and irreversible deletion have distinct release gates. Specs do not make unknown credentials, dataset guarantees, owners or bills known.

## Spec review

Scope covers all six pending milestones. M1 establishes identity and completeness; M2 owns storage commits; M3 owns acquisition/aggregation; M4 verifies them; M5 owns product/model publication; M6 owns dependency retirement. Their acceptance gates preserve the permit-only pilot boundary and the retained streaming-alert path.
