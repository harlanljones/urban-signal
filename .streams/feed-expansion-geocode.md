# Stream log — feed-expansion-geocode — 2026-08-27

Leaf discovery stream for Linear US-196: unlock already-identified
address-only feeds on *registered* metros via ADR 0004. Do not edit
registered city modules or spine in this stream.

## Claim

- **Stream id:** `feed-expansion-geocode`
- **Leaf files I will create/edit:**
  - `.streams/feed-expansion-geocode.md` (this file)
  - `docs/research/wave-3-feed-expansion.md` (NEW — probe results + DatasetSpec drafts)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (add DatasetSpecs on existing REGISTRY entries)
  - `apps/api/src/config.py` (new endpoint settings)
  - `apps/api/src/producers/scheduler.py` (confirm STREET_CUT job for nyc)
  - `apps/api/src/producers/dob_permits_producer.py` (only if Sacramento dual-schema)
  - per-city modules already registered (sacramento, norfolk, washington_dc, denver, chicago, nyc) — **do not edit**
  - leaf (not spine): `street_cut_permits_producer.py` geocode hook at application time

## Intent

Re-probe the US-196 feed list live. For each: newest-row watermark,
geocoding fields, recent-window count, proposed `needs_geocode=True`
DatasetSpec + field_map. Write drafts only. Applying them is a later
serial interlock hold so registered cities are not mutated concurrently.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed Linear US-196 and dispatched
  this research/draft stream. No in-place edits to registered cities.
- 2026-08-27 12:45 PT — Live re-probe complete. Ticket text is stale vs
  REGISTRY for Norfolk 311+SLA and DC SLA+DEEDS (already registered, still
  live). Denver SLA/DEEDS remain US-73 NO-GO (no address). Chicago
  `pubx-yq2d` now has native lat/lng (93.4% recent) — old "no coordinates"
  reading is obsolete. `hr8i-6s6s` is a current/future subset of the same
  family (NO-GO as second primary). NYC `tqtj-sjs8` live same-day;
  house-number fill 34.5% → G5 risk unless intersection geocode recovers.
  Sacramento city table is monthly (newest Status_Date still 2026-07-30;
  lastEdit 2026-08-01); GO as companion, do not replace county points.

## Current step

Research file written. Findings comment on US-196. Ticket left In Progress
(application hold still pending). Stream not unassigned.

## Next step

Orchestrator serial hold: apply GO specs (Sacramento companion, Chicago
`pubx-yq2d`, NYC `tqtj-sjs8`) + street-cut geocode hook; skip Denver and
`hr8i-6s6s` primary; `pytest -m interlock`. Re-probe Sacramento before
hold if after 2026-09-15 and Status_Date has not moved.
