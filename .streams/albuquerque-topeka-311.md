# Stream log — albuquerque-topeka-311 — 2026-10-02

## Claim

- **Stream id:** `albuquerque-topeka-311`
- **Leaf files created/edited:**
  - corpus files `albuquerque.yaml` and `topeka.yaml` (a `311` spec each);
    `cities/albuquerque.py` and `cities/topeka.py` (the module notes);
    `producers/watermarks.py` (Topeka's request view takes ANSI literals)
  - tests: `test_albuquerque_311.py` and `test_topeka_311.py` (new);
    `test_producers_albuquerque.py` (a leaf-mirror test renamed)
  - notes in `docs/research/two-family-depth-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the two request layers). `pytest -m
  interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json`,
  `cities/albuquerque.json` and `cities/topeka.json`. The dashboard lists
  metros by name, so it is unchanged.

## Intent

Probe the 40 two-family metros with `permits` and `sla` for `311` and deeds,
and register what the interior group's probe verifies.

## Decisions

- 2026-10-02 — Register Albuquerque's CRM layer with a one-day floor:
  unbounded queries on it do not answer within 60 seconds, and a bounded one
  answers in seconds.
- 2026-10-02 — Accept Albuquerque's unreadable-row exposure: a window holding
  the one such row in the year to 2026-10-02 returns no rows, and the floor
  lets the poll move past a row like it a day later.
- 2026-10-02 — List Topeka's request view by its path in
  `ANSI_DATE_LITERAL_HOSTS`: the permits view on the same host takes ISO
  strings and rejects ANSI literals.
- 2026-10-02 — Hold Missoula's drainage reports (one issue type, about
  twelve a month) and Worcester's work orders (State Plane coordinates the
  `311` producer cannot convert yet).

## Current step

Done.

## Next step

Register what the Florida, south-eastern and western groups verify, and
consider a State Plane conversion in the `311` producer for Worcester.
