# Hex coverage benchmark protocol and baselines (HX-A5)

Instrument: `bash autoresearch.sh` (offline, deterministic replay; client CPU
only — not network, GPU, or Core Web Vitals). Workload: 157 metros, 53,799
unique res-9 cells, 785 viewport/LOD steps; tile workload SHA-256
`e089578aa13d884f220904269783c721e6442cfbe06d10dda6c85852b5c86fb6`
(Stage B fixture; the Stage A tables below used
`d8052e4a05b73106987293093087d2666a02bb04e54ab2b7fe4855c8b9be7fc9`).

## Stage A baseline (main @ 50522d5, 2026-10-12, three consecutive runs)

| Run | tile_load_cpu_ms | tile_requests | tile_response_bytes | manifest_bytes | bulk_bytes | snapshot_ms |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 147.565 | 472 | 99,686,392 | 2,479,735 | 571,140,879 | 12,319.8 |
| 2 | 163.109 | 472 | 99,686,392 | 2,479,735 | 571,140,111 | 12,494.2 |
| 3 | 137.284 | 472 | 99,686,392 | 2,479,735 | 571,137,143 | 11,938.4 |
| **median** | **147.565** | 472 | 99,686,392 | 2,479,735 | ~571.1 M | 12,319.8 |

Deterministic metrics (requests, bytes, manifest bytes) are identical across
runs; only CPU time and `bulk_bytes` (inference-latency digit width) vary.

## Rebaseline rule (DG-8)

- Compare **medians of three runs** on the same fixture; never a single run.
- Observed run-to-run spread on unchanged code is **±8 % (137.3–163.1 ms)**,
  wider than DG-8's proposed +5 %. Threshold applied: a change regresses only
  if its three-run median exceeds baseline median by more than **max(5 %,
  observed spread of the baseline runs)** — currently 10.5 % (163.1 / 147.6 − 1).
  Deterministic metrics (requests, bytes) use exact equality unless the change
  is designed to alter them, in which case the delta is recorded here.
- The fixture (`scripts/autoresearch_coverage.json`,
  `scripts/autoresearch_semantic.sha256`) may change only in HX-B7, with the
  old fixture on new code and the new fixture on new code both recorded below.

## Stage A delta (HX-A1..A6 + worker pin fix; three runs)

| Run | tile_load_cpu_ms | tile_requests | tile_response_bytes | manifest_bytes |
|---:|---:|---:|---:|---:|
| 1 | 136.978 | 472 | 99,686,392 | 2,479,896 |
| 2 | 150.997 | 472 | 99,686,392 | 2,479,896 |
| 3 | 157.754 | 472 | 99,686,392 | 2,479,896 |
| **median** | **150.997** | 472 | 99,686,392 | 2,479,896 |

Median +2.3 % vs baseline 147.565 (threshold 10.5 %). Requests, bytes, the tile
workload SHA-256 and the publication semantic SHA-256 are unchanged, so k-ring
coverage is byte-identical (INV-6). `manifest_bytes` +161 is the additive
`coverage.tiers` block. The bridge band's res-6 requests are outside this
offline fixture, which replays metro tiles only.

## Harness boundary for the regional cutover

The existing harness is reused, not replaced. It builds a real dense snapshot
with fixed model seeds and a fixed publication timestamp, denies Python network
connections, then executes the shipped loader against local serialized tiles.
The client replay freezes inference-latency telemetry so response bytes are
identical across runs. Coverage and publication semantics must match their pins.
Current semantic SHA-256:
`90ca443630cef09c464d4056b5262d5639429cf71d2e9bbd9bcded790d0b2602`.

`tile_load_cpu_ms` remains the primary metric; `snapshot_ms`, manifest size,
response bytes and request counts are secondary. This measures full snapshot
construction and metro LOD loading, **not** incremental region skipping,
generation-aware cache retention, national underlay loading, live KV latency,
network transfer or GPU rendering. Those paths need separate behavioral proof
as the Stage C readers and writers land; unchanged replay hashes alone do not
prove a regional cutover.

## Regional-cutover harness checkpoint (2026-10-12)

Three consecutive runs after the pre-flight completed; no production code
changes. Each invocation exited 0 and matched both Stage B hashes above.

| Run | tile_load_cpu_ms | snapshot_ms | tile_requests | tile_response_bytes | manifest_bytes |
|---:|---:|---:|---:|---:|---:|
| 1 | 247.925 | 16,156.930 | 472 | 102,670,152 | 2,479,916 |
| 2 | 206.135 | 17,342.292 | 472 | 102,670,152 | 2,479,916 |
| 3 | 234.385 | 17,047.120 | 472 | 102,670,152 | 2,479,916 |
| **median** | **234.385** | **17,047.120** | 472 | 102,670,152 | 2,479,916 |

All runs covered 157 metros, 53,799 cells, 785 viewport steps and 628 source
submissions. A separate initial validation overlapped the CI/CD pre-flight;
its 238.281 ms sample is excluded from this table. Current timings differ from
historical measurements despite unchanged workload hashes; the cause is not
established. Do not present that difference as a code regression or improvement.
Bulk and raw tile sizes vary with inference-latency telemetry; canonical
semantics and serialized replay response bytes remain fixed.

## Stage C & D exit benchmark (2026-10-12, three consecutive runs)

Three consecutive isolated runs on branch `autoresearch/adaptive-hex-regional-backfill`
(commit `9d2198e`). Every invocation exited 0 and matched both Stage B workload
and semantic hashes.

| Run | tile_load_cpu_ms | snapshot_ms | tile_requests | tile_response_bytes | manifest_bytes |
|---:|---:|---:|---:|---:|---:|
| 1 | 196.942 | 18,589.164 | 472 | 102,670,152 | 2,493,346 |
| 2 | 178.464 | 18,933.478 | 472 | 102,670,152 | 2,493,346 |
| 3 | 175.255 | 19,589.460 | 472 | 102,670,152 | 2,493,346 |
| **median** | **178.464** | **18,933.478** | 472 | 102,670,152 | 2,493,346 |

Median client loading CPU time is **178.464 ms** vs checkpoint baseline median
234.385 ms (-23.9% improvement) and run #41 baseline 218.062 ms (-18.2% improvement).
Requests (472), response bytes (102,670,152), viewport steps (785), source
submissions (628), metros (157), and unique cells (53,799) are strictly unchanged.
Manifest bytes increased by +13,430 bytes (+0.54%) reflecting additive `regions`
generation pointers and `rank_epoch` breakpoint fields, well within the 8 MiB
manifest budget.

## Region-pointer cutover (2026-10-13, `693b688`)

Same fixture, one run after Region chunk maps began deriving their shas from the
publish's own object table: `tile_load_cpu_ms` 140.458, `tile_requests` 472,
`tile_response_bytes` 102,670,152, `manifest_bytes` 2,496,329, and both pinned
hashes unchanged — the change is build-side only, so the replayed client
workload is untouched.

`peak_rss_mib` rose 2,890 → 3,068 (+178 MiB): the object table is now
materialized before Region staging (it has to be, so Region chunks can reference
published objects) instead of at the end of the build. `snapshot_ms` is
unchanged; the build still canonicalizes each payload once.
