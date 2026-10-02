# Stream log — texas-south-feeds — 2026-10-02

## Claim

- **Stream id:** `texas-south-feeds`
- **Leaf files created/edited:**
  - corpus files `midland.yaml`, `longview.yaml` and `charleston_sc.yaml` (a
    `permits` spec each) and `odessa.yaml`, `waco.yaml` and
    `lexington.yaml` (a `311` spec each), and their `cities/*.py` modules
    (the notes)
  - tests: `test_midland_permits.py`, `test_longview_permits.py`,
    `test_charleston_sc_permits.py`, `test_odessa_311.py`,
    `test_waco_311.py` and `test_lexington_311.py` (new);
    `test_snapshot_reach.py`
  - notes in `docs/research/one-family-depth-2026-10-02.md` (new) and
    `snapshot-reach-2026-09-30.md`, this file, `.streams/dispatch-log.md`,
    and dated lines in `.streams/city-midland.md`, `city-longview.md`,
    `city-odessa.md` and `city-waco.md`
- **Spine files touched:** `config.py` (the six sources). `pytest -m
  interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and the six
  `cities/*.json`. The dashboard lists metros by name, so it is unchanged.

## Intent

Register the feeds the Texas and southern groups of the one-family probe
verified: permits for Midland, Longview and Charleston SC, and `311` for
Odessa, Waco and Lexington.

## Decisions

- 2026-10-02 — Window Midland's permits on the application date, not the
  issue date: rows keep the issue date they had when loaded, so the layer
  dates 10 residential building permits issued in September 2026 against 73
  to 101 a month before, while applications held steady.
- 2026-10-02 — Keep `PERIOD_NUMBER <= 1` for Longview: the layer holds a row
  per permit and review period, and the first period is one row per permit.
- 2026-10-02 — Leave out the permits that are not building work by type in
  all three permit specs (Midland's driveways, utilities, oil and gas and
  events; Longview's contractor registrations, right-of-way work and
  reviews; Charleston's engineering, short-term rental renewals, rental
  registration and events), spelling Midland's three names with a trailing
  space as the layer does.
- 2026-10-02 — Run Charleston's permits as a 90-day window on the server:
  its issue dates are midnight on most rows and carry a time on the rest.
  `expected_cadence_days` 4, since the layer ran 46 hours behind on a
  Friday.
- 2026-10-02 — Read Odessa's and Waco's public requests only (`private =
  '0'`, `IsPrivate = 0`), and keep the readable status ahead of Waco's
  open-or-closed flag.
- 2026-10-02 — Keep Lexington's Code Enforcement requests: they are
  residents' requests routed to the division, not inspectors' cases.
- 2026-10-02 — Accept the clip of north Odessa (about one request in
  seven): widening the metro box would change its grid tiles, which belongs
  in its own change.
- 2026-10-02 — Hold Charleston County's sales on its terms, Charleston's
  missed-collection layer as one kind of request, and Tyler's, Beaumont's,
  Texarkana's and Abilene's permits (stale, partial, text-dated and monthly).
- 2026-10-02 — Caps from the busiest 90 days found (Midland 3,786,
  Longview 1,136, Charleston 2,445); request feeds keep the default 1,000.

## Current step

Done.

## Next step

None for these six metros' new families. The held sources wait on the
re-checks in the research note; the north-eastern and western groups'
registrations follow in their own stream.
