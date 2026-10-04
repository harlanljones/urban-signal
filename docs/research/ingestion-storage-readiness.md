# Shadow ingestion storage readiness

**Status: blocked for live ingestion.** The selected target is a dedicated
Cloudflare R2 bucket, but its account owner, bucket, credentials, approved
prefix, retention policy, and provider-level conditional-write verification are
not available yet. No cloud writes or bucket provisioning were performed.

The implementation provides `LocalObjectStore(root)` for durable local
development and tests, and an injected-client `S3ObjectStore(client, bucket,
prefix)` adapter. Both expose immutable object writes and verified reads, plus
checkpoint reads and compare-and-swap. Local writes use an OS file lock,
same-directory atomic replacement, file and directory fsync, and opaque
checkpoint versions. A new local root is created with mode `0700`; existing
roots must be directories owned by the current user and not group- or
other-writable. The root and contents must only be modified through the store
or by its trusted owner. `flock` coordinates cooperating processes, not
malicious processes running as the same user. The S3-compatible adapter sends
`IfNoneMatch="*"` for immutable objects and absent-checkpoint creation, and
`IfMatch=<read ETag>` for checkpoint advancement. It never falls back to
read-then-unconditional-put.
Successful writes are read back and checked before returning. HTTP 409/412
conditional conflicts become `CheckpointConflict`; authorization and other
provider errors propagate.

## Provider evidence

The intended provider reference is Cloudflare's [R2 S3 API
extensions](https://developers.cloudflare.com/r2/api/s3/extensions/). The
documentation could not be retrieved from this execution environment (HTTP
403), so support and exact behavior for conditional `PutObject` with
`If-None-Match: *` and `If-Match: <ETag>` remain **unverified** here. An
S3-compatible client accepting these request fields does not prove that the R2
endpoint enforces them. The adapter is fail-closed: endpoint rejection raises
an error and leaves the checkpoint unchanged; do not add an unconditional
retry.

## Required readiness work

Before live scheduling, the storage owner must establish the dedicated bucket
and shadow-only credentials, choose and approve a namespace and retention
period, and run an isolated-prefix provider probe using the exact configured
R2 endpoint and client version. The probe must demonstrate all of the
following against R2 itself:

1. `IfNoneMatch="*"` creates an absent object once, and a second create is
   rejected with a recognized 409/412 response.
2. Competing absent-checkpoint writers yield exactly one success.
3. `IfMatch=<ETag>` accepts the observed current ETag and rejects a stale ETag.
4. The conditional failures leave the previous object bytes and ETag intact.
5. An acknowledged object can be read from a fresh client and its byte length
   and SHA-256 match; an acknowledged checkpoint body and ETag read back as
   written.
6. The configured role cannot access production KV or unrelated buckets, and
   authorization failures do not trigger retries without conditions.

Record the account owner, bucket, endpoint/region setting, prefix, client
version, probe timestamp and results, least-privilege policy, rotation owner,
and retention/restore decision in the runbook. Do not store credential values
in the repository. A fresh-runner restore drill and measured bootstrap, delta,
and reconciliation storage/request costs are also outstanding.

If R2 does not enforce both conditional request forms, keep live ingestion
disabled and select a store whose provider documentation and isolated probe
confirm those semantics (for example, an appropriately governed AWS S3 bucket),
or use a transactional conditional-write service. A read followed by an
unconditional object write is not a safe substitute.
