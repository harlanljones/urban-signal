# Two-family depth pass — 2026-09-30

`docs/signal-roadmap.md` gate E3 splits results by metro tier (all four signal
families versus partial), and the four-family pass
([four-family-depth-2026-09-30.md](four-family-depth-2026-09-30.md)) and the
deeds pass ([deeds-probe-2026-09-30.md](deeds-probe-2026-09-30.md)) have now
probed the missing family of every three-family metro. This pass turns to the
two-family metros that could reach four: twelve had `311` and `sla` but
neither `permits` nor `deeds` (Charlotte, Dayton, Honolulu, Houston,
Indianapolis, Kansas City, Oakland, Omaha, Oxnard–Ventura, Santa Fe, Toledo
and Tulsa), and fifteen have `sla` and `deeds` but neither `permits` nor
`311`.

The permits probe for the twelve ran live on 2026-09-30 from 19:32Z to 20:10Z
(curl default User-Agent, at least 12 seconds between requests to a host, no
owner or applicant column requested). One metro moves up; one suburb's feed is
held; ten metros have no permits source. The deeds and `311` probes are
recorded here as they register.

| Tier (families) | Before (with #91) | After |
|---|---|---|
| 4 | 26 | 26 |
| 3 | 29 | **30** (Charlotte) |
| 2 | 68 | 67 |
| 1 | 34 | 34 |

## Registered

### Charlotte, NC — `permits`

- **Source:** Mecklenburg County's own ArcGIS Server,
  `meckgis.mecklenburgcountync.gov/server/rest/services/BuildingPermits_Accela/FeatureServer/0`
  ("Building Permits Accela"), a point layer the county rebuilds from its
  Accela permitting system. The August probes (US-78 on 2026-08-24 and the
  2026-08-25 sweep) read the City's server, `gis.charlottenc.gov`, whose
  Accela service holds reference polygons and parcel tables, and recorded
  "Accela portal (no bulk API)"; the sweep's guess at a county REST path
  returned 404. The county's ArcGIS Online search surfaces only a legacy
  "Building Permit Locations" item (modified 2024-04-05); the Accela layers
  turned up by listing the county server's services from its root.
- **Shape:** 58,961 rows on 2026-09-30, issued from 2024-01-29, one row per
  permit and parcel. In the 90 days to 2026-09-29, 16 permits span several
  parcels (three equipment changeouts span 126, 71 and 28) and
  `permit_number` with `cama_parcel_number` never repeats. 4,006 rows have no
  issue date (permits not yet issued). The layer also carries the owner's
  name, phone, mailing address and email, and free-text descriptions; the
  spec's `select` names ten other columns.
- **Freshness:** an issue date holds the day alone, stored as midnight
  Eastern. On 2026-09-30 the newest day was 2026-09-29 (140 permits,
  unchanged from 19:46Z to 20:05Z) and no row was future-dated, so the layer
  is rebuilt overnight through the day before. 748 permits were issued in the
  seven days from 2026-09-23, 3,308 in 30 days and 10,800 in 90: 118 to 193
  each weekday and 2 to 9 on weekend days. `expected_cadence_days` is 2, so
  the staleness alarm (twice the cadence) does not fire on a newest date that
  is a day old by design.
- **Filter:** the server rejects ISO literals (`issue_date >=
  '2026-09-29T00:00:00'` returns 400 "Unable to complete operation") and
  takes `issue_date >= timestamp '2026-09-29 00:00:00'`, read in Eastern time
  as the layer declares, so the host joins `ANSI_DATE_LITERAL_HOSTS`. Under
  `issue_date DESC` the server sorts rows without a date first, so the spec's
  `where: issue_date IS NOT NULL` keeps a first poll from reading only
  unissued permits.
- **Ids and order:** each permit publishes once, keyed by its permit number
  as Augusta's permit-and-parcel rows are, at its first parcel under
  `issue_date DESC, permit_number, cama_parcel_number`. That order has no
  ties, so offset paging cannot shift rows between pages.
- **Mapping:** `type_of_work` gives the job type (New is new construction,
  Demolition a demolition, Alteration and Addition alterations; equipment
  changeouts, standalone commercial buildings, pools and upfits fall to
  other), with the system-computed construction cost (blank on about half the
  rows, mostly equipment changeouts), the permit status, the project's own
  address, ZIP and parcel number, and the town (`tax_jurisdiction`) as the
  source neighbourhood.
- **Poll:** hourly, newest first, with the default cap of 1,000 rows (about
  six weekdays of permits).
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 1,000 rows
  in two requests (the metadata and one page) and published 997 permits
  issued from 2026-09-21 to 2026-09-29; the other three rows were further
  parcels of permits already published, and none was dead-lettered. All 997
  lie inside the metro box, 822 of them inside the City's division box; by
  town, 789 are in Charlotte, 73 in Huntersville, 42 in Cornelius, 36 in
  Matthews, 24 in Mint Hill, 18 in Davidson, 13 in Pineville and 2
  unincorporated. The second poll sent `(issue_date IS NOT NULL) AND
  issue_date >= timestamp '2026-09-29 00:00:00'`, read the newest day's 140
  permits again and published none. Neither poll queried a geocoder.

## Held

| Metro (missing) | Source | Why held | Re-check when |
|---|---|---|---|
| Kansas City (`permits`) | Overland Park's `Building_Permits` layer (`services1.arcgis.com/YQsWDBr0DjMtoTQo`, a hosted layer last rebuilt on 2026-09-30): 13,824 permits over a rolling window from 2024-01-02, newest 2026-09-29, 429 in 30 days, ISO literals accepted, `CaseNumber` unique; 84% of recent rows carry a point and the rest an address. | It covers one suburb in Kansas, roughly a tenth of the metro's people, while the metro's `311` and licences are Kansas City, Missouri's. Registered as the metro's permits, it would mark Kansas City as covered where the City itself has none. | Kansas City, Missouri publishes current permits, or enough suburbs publish that the metro can take them together. |

## Not now

| Metro (missing) | Why not | Re-check when |
|---|---|---|
| Dayton (`permits`) | The City's GIS holds only the code-complaint layer in its two Accela services and no permits in its Hansen, building-services, planning or viewer services. Permits live in Accela Citizen Access (`DAYTON`). | A permits layer appears on the City GIS. |
| Honolulu (`permits`) | `data.honolulu.gov` `4vab-c87q` (432,021 rows) is an archive titled "through June 30, 2025" whose newest issue date is 2025-07-01. Nothing in the 72-dataset catalog or ArcGIS Online succeeds it. | A successor dataset appears. |
| Houston (`permits`) | The City's CKAN (99 datasets) publishes a monthly summary workbook, and its single- and multi-family extracts in ArcGIS Online end in 2024 (edited 2025-05-19). The permit web maps point at an unpublished `Permit_Viewer` (404). `cohegis.houstontx.gov` could not be reached (the egress proxy answered 502 twice). | A permits layer appears on the City GIS. |
| Indianapolis (`permits`) | `data.indy.gov` (651 datasets) and `gis.indy.gov` hold no permits, and the BNSDPW service needs a token. Permits live in Accela Citizen Access (`INDY`). | A permits dataset appears on either. |
| Kansas City (`permits`) | The City's Socrata permits (`ntw8-aacc`, 681,036 rows) stopped on 2025-05-09; its records link to the City's Tyler EnerGov portal, which has no public row API, and nothing newer is in the 202-dataset catalog. See Held for Overland Park. | A current extract appears on `data.kcmo.org`. |
| Oakland (`permits`) | No permits dataset among the 313 on `data.oaklandca.gov`, or on the Alameda County and Berkeley portals. Permits live in Accela Citizen Access (`OAKLAND`). | A permits dataset appears. |
| Omaha (`permits`) | Permits live in Accela Citizen Access (`OMAHA`). Douglas County's `Planning Wreck Permits` (demolitions only) stops on 2024-02-23, and MAPA's regional permits layer (51,978 rows) holds only new buildings over $25,000 and demolitions, updated yearly (newest 2025-12-31). | A permits layer appears on `dcgis.org`. |
| Oxnard–Ventura (`permits`) | Oxnard's Socrata `vmzx-48vx` stopped on 2024-12-03 and the domain now redirects to an OpenGov budget site with no row API. Ventura County's permitting service covers mining, oil and communication facilities only, and the City of Ventura publishes none. | A permits layer appears in either City's ArcGIS Online org. |
| Santa Fe (`permits`) | The City and County ArcGIS Online orgs hold only parking-permit zones, and the permitting system was not identified. | A permits layer appears in either org. |
| Toledo (`permits`) | `gis.toledo.oh.gov` has no permits layer and ArcGIS Online has none for Toledo or Lucas County. `permits.toledo.oh.gov` answered one request with a 403 (CloudFront "Request blocked") and was not asked again. | A permits layer appears on the City GIS. |
| Tulsa (`permits`) | The Tulsa County Assessor's `Building_Permit` layer (6,154 rows, no address) ends on 2025-09-18. The City's server answers "Token Required" on every folder checked except `CustomerCare` (its 311). | The Assessor's layer moves past 2025-09-18 or the City opens a permits service. |

A platform client would not unlock these cheaply: Accela Citizen Access
(Dayton, Indianapolis, Oakland, Omaha) is a search interface with no anonymous
bulk export, and the Tyler EnerGov portal behind Kansas City's permits has no
public row API either.
