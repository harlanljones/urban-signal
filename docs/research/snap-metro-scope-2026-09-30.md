# SNAP licences scoped to each metro — 2026-09-30

The 54 metros whose `sla` family is the USDA SNAP retailer layer now each read
their own state inside their own metro bbox. Before this change every SNAP job
read its whole state, and the scheduler's 1,000-row cap meant every metro in a
state received the same 1,000 retailers.

## Before and after

| | Before | After |
|---|---|---|
| Filter | `State = 'XX'` | `State = 'XX' AND Latitude BETWEEN … AND Longitude BETWEEN …` (the metro bbox) |
| Rows per poll | the state's first 1,000 by `ObjectId` (the whole state in Alaska and Hawaii, which hold fewer) | every retailer in the metro bbox |
| Metro retailers reached, all 54 metros | 5,694 of 34,686 (16%) | 34,686 of 34,686 |
| Rows from outside the metro, per round of polls | 47,656 of 53,350 (89%) | none |
| Metros with every retailer | Anchorage, Honolulu | all 54 |

Five of the 18 four-family metros depend on SNAP for licences: Cleveland (99 of
948 before), Columbus (105 of 1,080), Pittsburgh (31 of 526), Raleigh (163 of
1,466) and Tallahassee (19 of 242).

## Why the statewide filter failed

`snap_sla_spec(state)` filtered the national layer by state only and ran in
snapshot mode, which re-reads the table on every poll and emits only ids the
dedup cache has not seen. `poll_job` caps each poll at the job's `batch_limit`
(1,000 unless the spec declares more), and the ArcGIS client orders pages by the
layer's OID field. So each poll returned the same 1,000 lowest-`ObjectId` rows in
the state, tagged with the job's city, and never reached the rest. The US-364
comment in `city_registry.py` accepted state-level coarseness on the assumption
that metro scoping would happen downstream; the cap made it a truncation instead.

## The change

- `snap_sla_where(state, bbox)` builds the filter, and `snap_sla_spec` now takes
  the metro bbox (required) and an optional `batch_limit`.
- Each of the 54 corpus files carries the helper's output as its `where`.
  `test_producers_snap.py::TestSnapMetroScope` checks that every SNAP block equals
  `snap_sla_spec(state, metro_bbox, batch_limit)`.
- The 18 metros whose bbox holds more than two thirds of the default cap (667
  retailers or more) declare a `batch_limit`: 2,000, 3,000, or 7,000 for
  Houston. Every cap is at least 1.5 times the metro's count, which the same
  test class checks against the counts below, so a new SNAP metro has to bring
  its own count.
- The state term stays. It keeps a bbox that crosses a state line to the
  metro's own state, which matters for Prince George's County, whose bbox also
  covers 587 retailers outside Maryland (DC and northern Virginia). Across the 12 metros whose bbox
  crosses a line, 908 out-of-state retailers stay out, as they did before.

## Evidence

- Per-metro counts: `returnCountOnly` queries on the layer, one per metro at a
  3-second spacing: statewide, inside the bbox and state, and inside the bbox in
  any state. The exact `where` string each registry spec now carries was
  re-counted afterwards and matched all 54.
- "Received before": for each of the 26 states, the first 1,000 rows by
  `ObjectId` under `State = 'XX'` (the old filter, cap and order), counted inside
  each metro's bbox.
- Live `poll_job` through the real scheduler and ArcGIS client, Kafka mocked:
  Tallahassee fetched and published 242 of 242 (one page), Houston 4,205 of
  4,205 (five pages under its 7,000 cap), with no DLQ routes and every event
  inside the metro bbox. A second poll of each deduplicated every row.

| Metro | State | Statewide | In metro bbox | Received before | In bbox, other state | Cap after |
|---|---|---|---|---|---|---|
| Albuquerque / Bernalillo County | NM | 1,621 | 412 | 260 | 0 | 1,000 (default) |
| Alexandria | LA | 4,016 | 85 | 22 | 0 | 1,000 (default) |
| Anchorage | AK | 496 | 111 | 111 | 0 | 1,000 (default) |
| Asheville | NC | 8,908 | 175 | 23 | 0 | 1,000 (default) |
| Augusta | GA | 9,164 | 305 | 24 | 62 | 1,000 (default) |
| Boise / Ada County | ID | 1,078 | 231 | 218 | 0 | 1,000 (default) |
| Canton / Stark County | OH | 9,459 | 248 | 28 | 0 | 1,000 (default) |
| Cape Coral–Fort Myers | FL | 14,138 | 429 | 21 | 0 | 1,000 (default) |
| Charleston | SC | 5,000 | 433 | 94 | 0 | 1,000 (default) |
| Charlotte | NC | 8,908 | 1,036 | 116 | 66 | 2,000 |
| Chattanooga / Hamilton County | TN | 6,359 | 386 | 67 | 7 | 1,000 (default) |
| Cleveland / Cuyahoga County | OH | 9,459 | 948 | 99 | 0 | 2,000 |
| Columbus | OH | 9,459 | 1,080 | 105 | 0 | 2,000 |
| Columbus, GA | GA | 9,164 | 193 | 17 | 63 | 1,000 (default) |
| Dallas / Dallas County | TX | 20,490 | 1,970 | 101 | 0 | 3,000 |
| Dayton / Montgomery County | OH | 9,459 | 774 | 75 | 0 | 2,000 |
| Denver | CO | 3,134 | 1,202 | 361 | 0 | 2,000 |
| Durham / Durham County | NC | 8,908 | 208 | 23 | 0 | 1,000 (default) |
| El Paso / El Paso County | TX | 20,490 | 600 | 30 | 37 | 1,000 (default) |
| Evansville / Vanderburgh County | IN | 5,350 | 188 | 35 | 38 | 1,000 (default) |
| Fort Smith | AR | 2,489 | 114 | 49 | 2 | 1,000 (default) |
| Fort Worth / Tarrant County | TX | 20,490 | 1,806 | 73 | 0 | 3,000 |
| Gainesville | FL | 14,138 | 149 | 12 | 0 | 1,000 (default) |
| Greenville | SC | 5,000 | 219 | 46 | 0 | 1,000 (default) |
| Honolulu / City and County of Honolulu | HI | 854 | 505 | 505 | 0 | 1,000 (default) |
| Houston | TX | 20,490 | 4,205 | 183 | 0 | 7,000 |
| Huntsville, AL | AL | 4,815 | 261 | 45 | 0 | 1,000 (default) |
| Indianapolis / Marion County | IN | 5,350 | 946 | 134 | 0 | 2,000 |
| Jackson | MS | 2,896 | 316 | 99 | 0 | 1,000 (default) |
| Jonesboro | AR | 2,489 | 88 | 32 | 0 | 1,000 (default) |
| Lake Charles | LA | 4,016 | 148 | 46 | 0 | 1,000 (default) |
| Lakeland | FL | 14,138 | 210 | 10 | 0 | 1,000 (default) |
| Las Vegas / Clark County | NV | 1,985 | 1,317 | 688 | 0 | 2,000 |
| Macon-Bibb County | GA | 9,164 | 209 | 22 | 0 | 1,000 (default) |
| Melbourne / Palm Bay / Titusville | FL | 14,138 | 422 | 25 | 0 | 1,000 (default) |
| Memphis / Shelby County | TN | 6,359 | 825 | 92 | 18 | 2,000 |
| Monroe | LA | 4,016 | 129 | 38 | 0 | 1,000 (default) |
| Ocala / Marion County | FL | 14,138 | 310 | 18 | 0 | 1,000 (default) |
| Omaha | NE | 1,394 | 387 | 273 | 16 | 1,000 (default) |
| Pierce County | WA | 4,827 | 896 | 190 | 0 | 2,000 |
| Pittsburgh | PA | 9,569 | 526 | 31 | 0 | 1,000 (default) |
| Port St. Lucie | FL | 14,138 | 177 | 9 | 0 | 1,000 (default) |
| Prince George's County | MD | 3,732 | 1,078 | 275 | 587 | 2,000 |
| Raleigh / Wake County | NC | 8,908 | 1,466 | 163 | 0 | 3,000 |
| Reno / Washoe County | NV | 1,985 | 316 | 147 | 3 | 1,000 (default) |
| Rochester | NY | 16,274 | 400 | 21 | 0 | 1,000 (default) |
| Sacramento / Sacramento County | CA | 29,966 | 1,965 | 82 | 0 | 3,000 |
| San Antonio / Bexar County | TX | 20,490 | 1,536 | 69 | 0 | 3,000 |
| San Jose / Santa Clara County | CA | 29,966 | 755 | 18 | 0 | 2,000 |
| Tallahassee / Leon County | FL | 14,138 | 242 | 19 | 0 | 1,000 (default) |
| Toledo | OH | 9,459 | 439 | 41 | 9 | 1,000 (default) |
| Tulsa / Tulsa County | OK | 3,724 | 670 | 195 | 0 | 2,000 |
| Wichita | KS | 2,054 | 378 | 182 | 0 | 1,000 (default) |
| Wilmington, NC | NC | 8,908 | 262 | 32 | 0 | 1,000 (default) |

## Not covered here

The same cap applies to every other snapshot-mode feed (38 outside SNAP, GBFS
aside). Those are measured and fixed in `snapshot-reach-2026-09-30.md`.
