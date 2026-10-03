# M6 — Retire redundant backend services

Date: 2026-10-03. Status: proposed. Dependencies: replacement behavior verified for each consumer; M5 for replaced dashboard paths. Streaming alerts have their own readiness gate.

## Purpose

Remove verified redundant runtime costs while preserving data, active users, alerts and rollback. Repository Docker/Kubernetes definitions do not prove deployed services or unused capacity. Actual infrastructure, billing and alert consumers remain unknown from the audit.

## Inventory and replacement ledger

Use authenticated read-only provider inventory and billing evidence to identify service/account/region, owner, image/version, schedule, secrets dependencies, consumers, inbound/outbound traffic, Kafka topics/groups/lag/retention, PostGIS tables/row counts/backups, object volumes and observed cost. Do not expose secret values. Record unsupported access explicitly and block retirement of unidentified resources.

For every consumer list its current input/output contract, freshness requirement, replacement, parity evidence, retention/export obligation and rollback procedure. Candidate components include scheduler, Kafka/schema registry, enrichment/aggregation, PostGIS sync/database, MinIO, inference API and alert dispatcher. Each has an independent keep/migrate/retire decision; no all-or-nothing shutdown.

Daily dashboard freshness does not establish daily alert freshness. Confirm recipients and acceptable alert cadence. Keep the streaming path when its real-time contract remains needed; any migration to daily alerts requires explicit product/recipient requirements and duplicate/suppression behavior. A permit-only pilot does not replace four-feed aggregation or calibrations.

## Reversible sequence

1. Verify and export required history, checkpoint/calibration state and schema/configuration; test restoration into an isolated target.
2. Run the replacement in shadow at the agreed consumer contract; reconcile outputs and observe retries, deduplication and failures.
3. Cut over one consumer at a time with recorded owner acceptance, monitoring and a tested route back.
4. Stop a redundant writer/service reversibly; retain durable state and restore capability through an owner-agreed observation/rollback window. Set that duration in the service ledger before cutover.
5. Confirm the stopped service receives no required traffic and replacements meet freshness/parity. Delete resources or data only under a separately authorized irreversible action after retention obligations are satisfied.

If a dependency is shared, retain it until every dependent consumer is migrated or explicitly remains supported. Re-enable prior routes/services on parity, freshness, alert or data-loss failures; avoid resuming from obsolete checkpoints without reconciliation.

## Acceptance and savings evidence

- Authenticated deployment inventory, owner and dependency ledger complete for every proposed retirement.
- Backup/export and restore drills pass; retention and rollback windows recorded.
- Replacement meets each consumer's actual contract, including alerts/calibration where applicable.
- Reversible stop and observation complete without required traffic or functionality loss.
- Billing/resource evidence shows actual recurring spend avoided, net of replacement storage/compute. Configured resource requests and hypothetical list prices do not count as realized savings.
- Final report states retained services, retired resources, outstanding obligations and rollback status.

No production shutdown, alert-recipient messaging, destructive deletion or retention reduction occurs as part of generating this specification.
