# Stream log — city-worcester — 2026-08-30

## Claim

- **Stream id:** `city-worcester`
- **Ticket:** US-419 (Worcester, MA onboarding leaf)
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/worcester.py` (new)
  - `apps/api/src/producers/field_maps_worcester.py` (new)
  - `apps/api/tests/unit/test_producers_worcester.py` (new)
  - `.streams/city-worcester.md` (this file)
- **Spine files I expect to need:** NONE at leaf time. The orchestrator adds
  `config.py` settings, `CityId` member, aliases, `CityRegistration`, and
  `cities/__init__.py` exports in a separate spine hold (see "Spine delta"
  below). I touch no spine file and do not git-commit.

## Intent

Deliver a spine-stable Worcester leaf: a `worcester.py` spatial module with the
canonical `WORCESTER_*` constants (metro bbox, 6 divisions, 8 submarkets),
`WORCESTER_FEED_SPECS` for two ArcGIS non-spatial Table feeds (permits + SLA),
`get_worcester_dataset`, and `REGISTRATION`; a `field_maps_worcester.py` with
permits + SLA field maps; and a `test_producers_worcester.py` mirroring the
buffalo/syracuse test shape with byte-verbatim live fixtures and real
producer-path parse tests. Tests pass WITHOUT a spine registration.

## Decisions

- 2026-08-30 — PROBE: both feeds are ArcGIS `Table` (non-spatial), host
  `services1.arcgis.com/j8dqo2DJE7mVUBU1`, objectIdField `ObjectId`,
  maxRecordCount **1000** (NOT the ticket's ~2000 — server-reported 1000).
- 2026-08-30 — PROBE: text `M/D/YYYY` dates are non-padded ("8/9/2026").
  Text `ORDER BY DESC` LIES (`8/9/2026` > `8/19/2026` lexically), and
  `ObjectId` is NON-MONOTONIC vs date (newest 8/2026 rows carry ObjectId
  2–315; 2015 rows carry 52725+). `order_by` MUST be the text watermark
  column; ADR-0005 typed watermark declared (`watermark_type="text"`,
  `watermark_format="%m/%d/%Y"`, Rochester precedent).
- 2026-08-30 — PROBE (TRUE newest, parsed calendar max): permits watermark
  `Permit_License_Issued_Date` = 8/21/2026 (2,896 rows in 2026); SLA watermark
  `Issued_Date` = 8/21/2026 (430 rows in 2026). Both event-driven (near-daily
  distinct dates through 8/21), ~9-day lag at probe → `expected_cadence_days=14`.
- 2026-08-30 — PROBE: SLA layer has NO business-name column (columns
  Record__/Record_Type/Issued_Date/Expiration_Date/Address/Type/Total_of_Fees/
  ObjectId) → `dba`/`premises_name` unmapped.
- 2026-08-30 — PROBE: richer sibling layer exists — `Business_Certificates_
  1963_to_Present/FeatureServer/0` (Business_Name/Cert__/File_Date/Exp_Date/
  Address; newest File_Date 08/27/2026, zero-padded). REPORTED, but leaf builds
  against `Food_Establishment_Licenses` per the ticket.
- 2026-08-30 — GEOGRAPHY: 6 divisions / 8 submarkets from real Worcester
  neighborhoods (Downtown, Canal District, Shrewsbury Street, Grafton Hill,
  Main South, Webster Square, Quinsigamond Village, Tatnuck, Greendale).

## Current step

All four files written; running the leaf test + interlock gate now.

## Next step

Report back with FEED_SPECS verbatim + spine delta; hand off to orchestrator.
