# Stream log — permit-types — 2026-10-02

## Claim

- **Stream id:** `permit-types`
- **Leaf files created/edited:**
  - `src/features/permit_taxonomy.py` (`building_permit_type` reads a
    building permit's class with its work type; "2 Family" and other counts
    of families name a building)
  - city leaves, each with a `compose_permit_type`: `chattanooga.py` and
    `philadelphia.py` (a building permit read with its work type),
    `laredo.py` (the group, its report tab and the kind), `augusta.py` (the
    trade its code names, before the type)
  - corpus: `chattanooga.yaml` selects `permittype`, `laredo.yaml` selects
    `Permit Group Tab`
  - tests: `test_permit_taxonomy.py`, `test_producers_chattanooga.py`,
    `test_producers_philadelphia.py`, `test_producers_laredo.py`,
    `test_producers_augusta.py`
  - this file and `.streams/dispatch-log.md`
- **Spine files touched:** `dob_permits_producer.py` (`_compose_permit_type`
  asks the city leaf for a permit's type before the field map is read).
  `pytest -m interlock` passes.
- **Generated surfaces:** none. Product facts and the dashboard count feeds,
  not the types a feed reads.

## Intent

In the four feeds whose sources split a permit's type across two columns, a
new house should read as new construction and a trade's permit as a trade's.

## Decisions

- 2026-10-02 — A city leaf composes the type (`compose_permit_type(row)`),
  as it composes an address: a field map lists alternatives, not parts, and
  Laredo's rule reads three columns.
- 2026-10-02 — Join the work type to a building permit's class only.
  Philadelphia's fire-suppression permits for a new building say "New
  Construction" and its zoning approvals "New construction, addition, GFA
  change"; joined, both would read as new buildings.
- 2026-10-02 — Laredo: a residential or commercial construction permit under
  the "New Construction" tab is a new building, filed under the Census
  Bureau's new-building categories ("SINGLE FAMILY DETACHED", "OFFICES,
  BANKS"), except a mobile home's installation permit. The additions,
  alterations and conversions group sits under the same tab, so the tab alone
  cannot say so. Its alterations read by kind rather than as changes of use
  (the group's name says "Conversions"), and its "Other" permits by kind
  ("SIGN PERMIT").
- 2026-10-02 — Augusta: `PERMCODE` names the trade its type leaves out.
  PREL is electrical, PRPL plumbing and PRMH mechanical, inferred from the
  types under each code: "Service Change", "Generator" and "Solar" under
  PREL, "Septic to Sewer" under PRPL, the HVAC "Change Out"s under PRMH.
- 2026-10-02 — Measure on each source's own vocabulary weighted by its
  counts (a year of Laredo's permits, 2026's for Philadelphia, the newest
  1,000 rows of Chattanooga's and Augusta's), replayed through the old and
  new producers; then poll each feed live twice.

## Current step

Done.

## Next step

Gainesville's permits from Alachua County's layer, whose type and sub-type
split the same way.
