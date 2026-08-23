# New Orleans & Austin — verification pass (candidate → implementation-ready)

**Date of verification: 2026-08-23.** Every dataset below was re-probed live on that
date, independently of the morning survey in `city-expansion-candidates.md`. "Updated"
is the dataset's own `rowsUpdatedAt` from `/api/views/<id>.json`, converted to UTC.
Row counts are `$select=count(*)`; column lists come from the view metadata plus a
1-row fetch; "newest" is `$order=<watermark> DESC&$limit=1`.

## Method, and its limits

Probes per dataset: view metadata (`rowsUpdatedAt`, full column list), one raw row,
`count(*)`, newest-row date, and targeted counts where a caveat needed numbers
(zero-coordinate rates, date spans, null-geocode rates). Schema mapping was done by
reading each shared producer's `parse_socrata_row` fallback chain and checking every
field name against it literally.

Limits: Socrata's discovery API no longer indexes `data.austintexas.gov` at all
(see Austin section), so the Austin licenses/deeds search had to be structural as
well as textual — absence is confirmed by query list *and* catalog state, but a
dataset that is both unlisted and unknown cannot be ruled out by any remote probe.
Nearby-domain checks were surface-level; anything not directly probed to the row
level is marked unverified.

## Headline

**Build order stands: New Orleans first, Austin second** — but NOLA's permits pick
changes: register **`rcm3-fn58` ("Permits"), not `nbcf-m6c2`**, which is dead-stale.
NOLA is now four-for-four on feed types (with one heavily caveated deeds stand-in).
Austin registers as a two-feed partial city like Los Angeles.

---

## New Orleans, LA — `data.nola.gov` — verified, with one dataset swap

| Feed | Dataset | Updated | Coordinates | Watermark | New fallbacks needed |
|---|---|---|---|---|---|
| 311 | `2jgv-pqrq` 311 OPCD Calls (2012-Present) | 2026-08-23 | `latitude`/`longitude` direct (+ `geocoded_column`) | `date_created` | 3 required + 1 shared guard (below) |
| Licenses | `hjcd-grvu` Occupational Business Licenses | 2026-08-22 | `latitude`/`longitude` direct (+ `location` dict) | `businessstartdate` | 5 required |
| Permits | **`rcm3-fn58` "Permits"** (not `nbcf-m6c2`) | 2026-08-23 | `location_1` dict, zero nulls | `issuedate` | 6 required |
| Deeds | `hpm5-48nj` NORA Sold Properties (caveated) | 2026-08-11 | `geocoded_column` dict only | `sale_date` | 5 required |

### Permits staleness verdict: publishing lapse on the OLD feed; superseded, use `rcm3-fn58`

The prior survey's staleness question resolves cleanly:

- Old pick `nbcf-m6c2` ("Building Permits (2018-present)"): `rowsUpdatedAt` frozen at
  **2025-08-17** — byte-identical to the value behind the survey's stamp, i.e. no
  refresh in the intervening year. Its newest permit is **2024-12-05**; there are
  **zero rows dated 2025 or 2026** (year-band counts: 4,786 in 2024, 0 after). The
  feed stopped receiving records ~8 months before its last metadata touch.
- The domain now carries **`rcm3-fn58` ("Permits")**: `rowsUpdatedAt` **2026-08-23**,
  346,547 rows spanning 2012-01-01 → **2026-08-22** with no gap (annual bands
  2018–2025 run 17.9k–25.8k/yr; 11,782 already in 2026). Fully geocoded:
  **zero nulls** in `location_1` across all 346k rows.
- A third candidate, `72f9-bi28` ("Permits - BLDS", updated 2026-08-20, 462k rows),
  is an Accela historical import with **100% NULL locations** (all 462,082) —
  unusable for an H3 pipeline regardless of freshness.

Conclusion: the city stopped refreshing the old map-oriented extract and publishes a
newer, better general permits extract under a new ID. Not a dead program — a dead
dataset ID. Register `rcm3-fn58` (`endpoint=.../resource/rcm3-fn58.json`,
watermark `issuedate`, id key `numstring`).

### NORA Sold Properties honesty check

It really is redevelopment-authority disposals, not market deeds — quantify the
narrowness:

- **5,618 rows total**, sale dates 1980-03-03 → **2026-07-22** (still updating).
  Only **872 sales since 2020** and **191 since 2024** (~60–80/yr recent rate)
  versus NYC ACRIS's ~1M+ documents or King County's continuous excise stream.
- Composition: Auction 2,226 / Lot Next Door 1,748 / Development 1,575 /
  Alternative Land Use 69 — discounted disposals to adjacent owners and development
  partners by design, so ordinary market transactions are structurally absent.
- **No price field exists** in the schema (`identifier`, `property_address`,
  `zip_code`, `geopin`, `council_district`, `disposition_channel`, `sale_date`,
  `geocoded_column`). Every parsed DeedEvent would carry `document_amount = 0.0`,
  which guts the main signal the deeds topic feeds.

Recommendation: **register, but optionally and last**, under `FeedType.DEEDS` with a
comment in the Seattle/King County style ("NORA's own disposals, not recorded deeds;
no consideration amount; ~80 rows/yr"). It keeps New Orleans a full four-feed city,
and the parser cost is small, but nothing downstream should treat it as market
volume. If implementation time is tight, ship NOLA with three feeds first.

### Data-quality quirks worth encoding

- 311: 40,893 of 1,022,041 rows (~4%) have `latitude`/`longitude` of `0.0` or null.
  The SLA producer has a 0,0 guard; **the 311 producer does not** — without one,
  those rows land in an H3 cell in the Gulf of Guinea. Either add the same guard to
  `Complaints311Producer.parse_socrata_row` (shared-producer edit — see refactor note)
  or filter `$where latitude != '0.0' AND latitude IS NOT NULL` in ingestion.
- Licenses: 8,978/37,548 (**~24%**) zero/null coordinates (the existing SLA 0,0
  guard covers this); 6,694 rows (~18%) have `city != 'NEW ORLEANS'` — the feed
  leaks some out-of-parish businesses (sample: Madisonville, St. Tammany Parish).
  Metro-bbox filtering handles this; no code change. Seven rows carry future-dated
  `businessstartdate` (max seen 2027-02-27) — harmless for a watermark if you order
  DESC and tolerate clock-skew rows, but don't treat newest-row date as "now".

---

## Austin, TX — `data.austintexas.gov` — verified partial city

| Feed | Dataset | Updated | Coordinates | Watermark | New fallbacks needed |
|---|---|---|---|---|---|
| Permits | `quv8-5ckq` Issued Building Permits | 2026-08-08 | `latitude`/`longitude` direct (+ `the_geom`, `location`) | `issue_date` | 2 required |
| 311 | `xwdj-i9he` Austin 311 Public Data | 2026-08-23 | **`sr_location_lat`/`sr_location_long` explicit** | `sr_created_date` | 5 required |
| Licenses | none found (see below) | — | — | — | — |
| Deeds | none found (see below) | — | — | — | — |

The prior survey's "(verify)" on 311 coordinates resolves positively: explicit lat/lng
columns exist, and only 14,972 of 2,526,218 rows (~0.59%) are null/zero. Newest SR:
2026-08-22. Permits refreshed 2026-08-08 with newest `issue_date` 2026-08-06
(7,626 permits YTD 2026) — consistent with a weekly cadence, live.

### Why the harder search found nothing: the domain left the discovery mesh

Eleven queries were run against Austin's domain — `beer license`, `alcohol`,
`standard industrial`, `business license`, `business`, `real estate`, `property
sales`, `foreclosure`, `deed`, `excise`, `assessor` (plus `permits`, `license` as
controls). Every scoped query returned **zero results** — including `q=permits`,
which must be wrong since `quv8-5ckq` served rows minutes earlier. The explanation is
structural: an unfiltered domain query now returns exactly three datasets, all
internal "Site Analytics: … (ODP Dashboard)" views. Austin has migrated its public
catalog to the Texas Open Data Portal, leaving data.austintexas.gov as a serving
shell for legacy resources with an emptied catalog. There is nothing left to find by
searching it; licenses/deeds would live (if anywhere) statewide or countywide.

### Nearby-domain sweep (bounded, ~15%)

- **TABC statewide alcohol licenses — real candidate, blocked on geocoding.**
  `7hf9-qc9f` "TABC License Information" (data.texas.gov): 126,415 rows, updated
  2026-08-22, rich license fields (`license_id`, `license_type`, `license_status`,
  `current_issued_date`, `expiration_date`, `trade_name`, `owner`, address text,
  `county`). And `kguh-7q9z` "TABCLicenses", updated 2026-08-23, 78,338 rows. This
  is Texas's analogue of NYSLA and covers Austin — but **neither dataset has a single
  coordinate column** (full column lists checked). Registering either today means
  geocoding addresses out-of-band first. Park it; revisit if Austin needs an SLA feed.
- **Travis County:** `data.traviscountytx.gov` answers with Socrata headers
  (`X-Socrata-Region: aws-us-east-1-fedramp-prod`) but is a shell — its own catalog
  API returns `"Domain not found"`, `/api/views` 404s, homepage 301s. County deed
  records are not reachable via Socrata here. *Unverified beyond these probes.*
- **Louisiana statewide:** no Socrata portal resolves (`data.la.gov`,
  `data.louisiana.gov`, `opendata.la.gov` — NXDOMAIN); federated search surfaces
  Baton Rouge's `data.brla.gov` (wrong parish). Orleans Parish Assessor is not on
  Socrata (assessor parcel site only; not probed further — *unverified*).

Austin therefore registers two feeds, like Los Angeles. That is still worth doing:
its permits feed is the richest in the pipeline (four distinct date columns,
valuation breakdowns, units/floors).

---

## Zero-guesswork schema mapping (existing chains vs. required fallbacks)

Checked literally against each producer's `parse_socrata_row` chain. "✓" = already
matches an existing fallback; "NEW" = a city-specific spelling the chain lacks.

### NOLA 311 `2jgv-pqrq` → `complaints_311_producer.py`

| Field | Column | Status |
|---|---|---|
| incident_id | `service_request` (or `rowid`) | NEW |
| complaint_type | `request_type` | ✓ |
| created_date | `date_created` | NEW |
| closed_date | `case_close_date` | NEW |
| lat/lng | `latitude`/`longitude` | ✓ (4% zeros — see guard note) |
| descriptor | `request_reason` | NEW (optional; falls back to type) |
| incident_address | `final_address` | NEW (optional) |
| zipcode | none in schema | n/a |
| status | `status` / `request_status` | ✓ |

Required new fallbacks: **3** (`service_request`, `date_created`, `case_close_date`)
plus the 0,0-coordinate guard (one shared edit).

Heuristic collision to note: the producer auto-detects Chicago when it sees
`sr_number`/`sr_type`; NOLA 311 has neither, and `run_stream` passes `city_id`
explicitly anyway — harmless, but add a comment if you ever rely on sniffing.

### NOLA licenses `hjcd-grvu` → `sla_licenses_producer.py`

| Field | Column | Status |
|---|---|---|
| license_id | `businesslicensenumber` | NEW |
| effective_date | `businessstartdate` | NEW (chain has `business_start_date`, not concatenated) |
| license_type | `businesstype` | NEW |
| dba | `businessname` | NEW (chain has `business_name`, not concatenated) |
| premises_name | `ownername` | NEW |
| lat/lng | `latitude`/`longitude` | ✓ (24% zeros — existing 0,0 guard applies) |
| nested point | `location` dict | ✓ |
| address | `address` | ✓ |
| expiration_date | none in schema | n/a |
| status | default ACTIVE | ✓ |

Required new fallbacks: **5**. Registry: watermark `businessstartdate`, id_keys
`["businesslicensenumber"]`.

### NOLA permits `rcm3-fn58` → `dob_permits_producer.py`

| Field | Column | Status |
|---|---|---|
| job_id | `numstring` (e.g. `26-24265-HVAC`) | NEW (`prmtid`/`objectid` exist as alternates) |
| lat/lng | `location_1` dict `{latitude, longitude}` | NEW (loc-list; chain has `location` but not `location_1`) |
| cost | `constrval` | NEW |
| job_type | `type` (e.g. "Mechanical HVAC") | NEW recommended — otherwise falls through to `description` free text and misclassifies |
| issuance_date | `issuedate` | NEW (chain has `issued_date`, not concatenated) — also the watermark |
| filing_date | `filingdate` | NEW |
| status | `currentstatus` | NEW (optional; else defaults ISSUED) |
| borough | `subdivision` / `zoning` / `historicdistrict` / `councildist` | NEW optional (H3 division resolution covers) |
| address_street | `address` | ✓ |
| zipcode | none in schema | n/a |

Required new fallbacks: **6** (numstring, location_1, constrval, issuedate,
filingdate, type). Note `pin` (parcel number) also exists — do NOT let it near the
job-id chain; it belongs in comments only.

### NOLA deeds `hpm5-48nj` → `deeds_acris_producer.py`

| Field | Column | Status |
|---|---|---|
| doc_id | `identifier` | NEW |
| recorded_date | `sale_date` | NEW — also the watermark |
| bbl | `geopin` | NEW (chain has `pin`/`PIN`, not `geopin`) |
| lat/lng | `geocoded_column` dict | NEW (loc-list lacks `geocoded_column`) |
| doc_type | `disposition_channel` | NEW (optional; yields AUCTION/DEVELOPMENT/LOT NEXT DOOR) |
| document_amount | no price column exists | always 0.0 — accepted loss, see verdict |
| party1/party2 | none in schema | n/a |
| block/lot | none (`geopin` is assessor PIN, not block/lot) | n/a |
| borough | `council_district` | NEW optional |

Required new fallbacks: **5** (identifier, sale_date, geopin, geocoded_column,
optionally disposition_channel).

Detection note: NORA rows contain `geopin`, which does not collide with the
Chicago-sniffing `"pin" in row` check (exact-key match), and `city_id` is passed
explicitly in practice.

### Austin permits `quv8-5ckq` → `dob_permits_producer.py`

| Field | Column | Status |
|---|---|---|
| job_id | `permit_number` | ✓ |
| lat/lng | `latitude`/`longitude` | ✓ |
| job_type | `permit_type` | ✓ (but values are generic — "Building Permit"; consider adding `work_type` before it for NB/DM signal) |
| issuance_date | `issue_date` | ✓ — also the watermark |
| cost | `total_job_valuation` | NEW |
| filing_date | `application_date` | NEW |
| status | `status` | ✓ |
| zipcode | `zip_code` | ✓ |
| units/stories | `number_of_units` / `number_of_floors` | NEW optional (model fields exist; chain lacks spellings) |
| borough | `council_district` | NEW optional |
| address_street | street parts partially combine; `permit_location` | NEW optional |

Required new fallbacks: **2** (`total_job_valuation`, `application_date`). Optional
polish: work_type, number_of_units, number_of_floors, council_district.

### Austin 311 `xwdj-i9he` → `complaints_311_producer.py`

| Field | Column | Status |
|---|---|---|
| incident_id | `sr_number` | ✓ |
| lat/lng | `sr_location_lat`/`sr_location_long` | NEW ×2 |
| complaint_type | `sr_type_desc` | NEW (exact-key check means `sr_number`'s cousin `sr_type_desc` does NOT match `sr_type`) |
| created_date | `sr_created_date` | NEW — also the watermark |
| closed_date | `sr_closed_date` | NEW |
| status | `sr_status_desc` | NEW optional |
| zipcode | `sr_location_zip_code` | NEW optional |
| address | `sr_location` | NEW optional |
| borough | `sr_location_council_district` | NEW optional |

Required new fallbacks: **5**. Same Chicago-sniffing collision note as NOLA 311 —
here it actually fires on auto-detect (`sr_number` in row ⇒ "chicago"), so keep
passing `city_id` explicitly and consider tightening that heuristic during the
refactor below.

---

## Refactor trigger assessment: the field-mapping table is now due

The prior survey said: "Two or three more cities and that chain-of-fallbacks approach
is worth replacing with a per-city field-mapping table declared alongside the
DatasetSpec." With NOLA + Austin added, the cities needing non-trivial per-city
spellings become **four** (Seattle ArcGIS `PIN`/`SaleDate`, LA `lon`/`valuation`,
NOLA ~19 required fallbacks across four feeds, Austin ~7). That crosses the line.

Concrete evidence from this pass:

- **26 required new `or row.get(...)` fallbacks** across six feeds if done the old
  way — most of them trivial renames (`businessstartdate` vs `business_start_date`,
  `issuedate` vs `issue_date`, `constrval` vs `valuation`), i.e. pure mapping-table
  content, not logic.
- Two producers need **shared-code behavior edits** anyway (311's missing 0,0 guard;
  the `sr_number`⇒Chicago detection heuristic that Austin 311 trips). Editing those
  files once per city forever is worse than editing them once now.
- `DatasetSpec.extra` already exists as the natural home: e.g.
  `extra={"field_map": {"job_id": ["numstring"], "lat": ["location_1.latitude"], ...}}`.
  The refactor can stay additive — chains remain as defaults, maps override per city.

Verdict: **trigger fires. Do the mapping-table refactor as part of (or immediately
before) the NOLA implementation**, not after both cities — NOLA alone carries 19 of
the 26 fallbacks, so building it chain-style then refactoring means touching every
producer twice.

---

## Implementation plan sketch (ordered)

1. **Refactor prerequisite (spine-touching, small):** per-city field-map support in
   the four shared producers reading `DatasetSpec.extra["field_map"]`, plus the 311
   0,0-guard and the detection-heuristic fix. Gate: `pytest -m interlock` per
   `docs/agents/parallel-streams.md` — this step edits spine-manifest files, so it
   should land as its own spine stream before city leaves fan out.
2. **New Orleans city module** — `src/spatial/cities/new_orleans.py`: METRO_BBOX
   (Orleans + Jefferson + St. Bernard parishes), DIVISION_BBOXES / DIVISIONS
   (~10–15 planning-district-shaped divisions), SUBMARKETS. Hand-authoring this is
   the bulk of the effort (compare seattle.py: ~370 lines, four top-level dicts).
   Registry: `CityId.NEW_ORLEANS`, aliases `new_orleans`, `nola`, `orleans_parish`;
   job_suffix `"nola"`; register PERMITS (`rcm3-fn58`), COMPLAINTS_311
   (`2jgv-pqrq`), SLA (`hjcd-grvu`), DEEDS (`hpm5-48nj`) with the NORA caveat
   comment; config endpoints `socrata_nola_{permits,311,licenses,deeds}_endpoint`.
   NOLA field_map: 19 entries per tables above.
3. **NOLA tests** — fixture rows captured from each live feed (one per feed plus a
   0,0-coord row for 311/licenses and a future-dated licenses row), asserting parse
   through the mapping table; registry lookup test asserting `get_dataset(nola,
   FeedType.DEEDS)` works and error messages stay readable.
4. **Austin city module** — `src/spatial/cities/austin.py`: METRO_BBOX (Travis +
   Williamson + Hays), divisions/submarkets. Registry: `CityId.AUSTIN`, aliases
   `austin`, `travis_county`; job_suffix `"austin"`; register PERMITS (`quv8-5ckq`)
   and COMPLAINTS_311 (`xwdj-i9he`) only — SLA/DEEDS deliberately absent like LA's
   311/deeds, with a comment pointing at TABC's un-geocoded statewide feeds;
   config endpoints `socrata_austin_{permits,311}_endpoint`. Austin field_map: ~7
   entries.
5. **Austin tests** — same shape as NOLA's, plus a regression test pinning the
   `sr_number` heuristic behavior.
6. **Backfill notes:** NOLA 311 is 1.02M rows (paginate fine); Austin 311 is 2.53M
   rows — set generous `max_records`/backfill windows; NOLA permits rcm3 backfills
   cleanly from 2012 thanks to full coverage.

Estimated per-city cost after the refactor: mostly the hand-authored geography
module; producer code limited to mapping-table entries and tests.

## Bottom line

- **NOLA: build first.** Four feeds verified live today; swap the permits dataset ID
  to `rcm3-fn58` (old ID dead-stale since 2024-12 data, superseded — evidence above);
  NORA deeds register last and caveated.
- **Austin: build second.** Permits + 311 verified; licenses/deeds confirmed absent
  (catalog hollowed by ODP migration; TABC feeds un-geocoded).
- **Refactor: yes, before or with NOLA.** 26 new fallbacks across four cities trips
  the threshold; the mapping table pays for itself immediately.
