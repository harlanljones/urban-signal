# Hex coverage benchmark protocol and baselines (HX-A5)

Instrument: `bash autoresearch.sh` (offline, deterministic replay; client CPU
only — not network, GPU, or Core Web Vitals). Workload: 157 metros, 53,799
unique res-9 cells, 785 viewport/LOD steps; tile workload SHA-256
`d8052e4a05b73106987293093087d2666a02bb04e54ab2b7fe4855c8b9be7fc9`.

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
