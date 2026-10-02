# One-family depth pass — 2026-10-02

`docs/signal-roadmap.md` gate E3 splits results by metro tier (all four signal
families versus partial). The two-family pass
([two-family-depth-2026-09-30.md](two-family-depth-2026-09-30.md)) probed the
missing families of the two-family metros; this pass turns to the 35 metros
with one family, `sla` alone: the USDA SNAP retailers, or for the nine Texas
metros the state's real-estate broker licences. Macon-Bibb, which fell to one
family when its permits were retracted, was probed hours earlier in the
south-eastern pass and is left out.

The other 34 were probed live on 2026-10-02 in four groups (curl default
User-Agent, at least 2.2 seconds between requests to a host on a clock the
groups shared, no owner, applicant, reporter, contact or free-text column
requested). Workbooks that carried such columns were read only by their other
headers and deleted. Hosts that refused a request were not asked again:
ARCountyData, the City of Fort Smith's website, the Cities of Harrisburg's
and Wilmington's websites and West Des Moines's answered 403, New Castle
County's GIS answered 472, Fort Smith's GIS portal reset the connection, the
City of Dover's website returned an error page, and Buffalo's open data
portal refused the permits dataset's rows (403). New York's sales search and
the City of Portland, Maine's website failed certificate checks and were not
queried.

The nine Texas metros (Abilene, Amarillo, Beaumont, Longview, Midland, Odessa,
Texarkana, Tyler and Waco) ran from 14:14Z to 15:27Z. Texas does not disclose
sale prices, so deeds were left out except on Texarkana's Arkansas side.
Midland's and Longview's permits and Odessa's and Waco's `311` register, which
gives each a second family. Tyler's, Beaumont's, Texarkana's and Abilene's
permits are held; the other gaps sit in vendor systems with no public rows.

The nine southern metros (Alexandria, Charleston SC, Fort Smith, Huntington
WV, Jackson MS, Jonesboro, Lake Charles, Lexington and Monroe) ran from 14:13Z
to 15:16Z under the same rules. Louisiana and Mississippi do not disclose sale
prices. Charleston's permits and Lexington's `311` register, which gives each
a second family. Charleston County's sales are held on the County's terms and
the City's missed-collection requests as one kind of request; the other gaps
have no public source.

The eight north-eastern metros (Albany, Buffalo, Syracuse, Harrisburg,
Manchester NH, Portland ME, Dover and Wilmington DE) ran from 14:13Z to
15:50Z. Manchester's deeds register, from the City's own parcels, which the
August probe missed. Buffalo's holes-in-road work orders are held as one kind
of request, Manchester's public works tickets because resident intake stopped
on 2026-09-02, and Buffalo's 2026-27 roll because its deed dates are empty.
New York's county and state layers carry deed book and page only, and the
other gaps sit in vendor systems (SeeClickFix, EnerGov, Camino, TRAKiT,
Infor) with no public rows.

The western group (Des Moines, Grand Rapids, Madison, Long Beach, Modesto,
Santa Rosa, Stockton and Tucson, with Lincoln's missing deeds) ran from 14:16Z
to 15:30Z. Lincoln's deeds register from the Assessor's sales of the last 12
months, which gives Lincoln all four families, and Tucson's permits register
from a layer the August probe did not find. Pima County's yearly sales files,
Long Beach's requests, Polk County's sales and Sonoma County's parcel sales
are held; the other gaps have no public source, and Stanislaus and San
Joaquin counties publish no sale prices.

Two of the western holds came off the same afternoon, through two changes to
the CSV client: an endpoint written with `{year}` reads this year's file and
last year's, and a column that holds a point as `lat, lon` gives each row its
latitude and longitude. Tucson's deeds register from Pima County's sales
files, which gives Tucson three families, and Long Beach's `311` from the
City's request export, which gives it two.

A hold from the two-family pass came off next: Worcester's work orders, a
table whose points are two columns of Massachusetts State Plane feet, which
the scheduler now converts for any spec that declares them. That gives
Worcester a third family; the registration is written up with the
two-family pass ([two-family-depth-2026-09-30.md](two-family-depth-2026-09-30.md)).

| Tier (families) | Before (with #106) | With the Texas and southern feeds (#107) | With the north-eastern and western feeds (#108) | With two held sources (#109) | With Worcester's `311` |
|---|---|---|---|---|---|
| 4 | 30 | 30 | **31** (Lincoln) | 31 | 31 |
| 3 | 44 | 44 | 43 | **44** (Tucson) | **45** (Worcester) |
| 2 | 48 | **54** (Midland, Longview, Charleston SC, Odessa, Waco, Lexington) | **56** (Manchester, Tucson) | **56** (Long Beach in, Tucson up) | 55 |
| 1 | 35 | 29 | 27 | 26 | 26 |

## Registered

### Midland, TX — `permits`

- **Source:** the City's permits layer on its ArcGIS Online org, which its
  GeoStation Hub lists:
  `services.arcgis.com/0H6bQdxd9223gQB5/arcgis/rest/services/Permits/FeatureServer/0`,
  "Points representing permit requests/applications across all of Midland,
  Texas", loaded from the City's EnerGov system. The 2026-08-28 registration
  found no permits API.
- **Shape:** 88,614 rows on 2026-10-02, applied for since 2000, one per
  application, each at its point. `Name` is the permit type (32 in the 90
  days). The layer carries no cost, and its edit stamps stop on 2026-03-04:
  rows are loaded, not edited, and nothing marks when one arrived.
- **Window:** a row keeps the issue date and status it had when it was
  loaded. The layer dates 10 residential building permits issued in
  September 2026, against 73 to 101 a month from October 2025 to May 2026,
  while applications held at 89 to 140 a month. So the window runs on the
  application date, which every row carries: the applications made in the 90
  days before each poll, closed at the request's time, without fifteen types
  that are not building work (driveways and sidewalks, franchise utility
  work, oil and gas, water taps and meters, rights of way, water wells,
  special events, two specific-use designations, vendors, standalone parking
  lots, traffic control, salt-water disposal wells and cash-access
  businesses). Three of the names end in a space, and the filter spells them
  so. The window held 2,622 rows on 2026-10-02.
- **Reach:** the 90 days from 2025-04-10 held 3,786, the most of eight
  windows back to October 2024, so the cap is 5,000, read in pages of
  1,000.
- **Ids:** the permit number keys each event; four repeated in the window on
  2026-10-02.
- **Freshness:** the newest application, filed at 16:56:29Z on 2026-10-01,
  was still the newest at 15:18Z the next day, and no rows arrive at
  weekends, so `expected_cadence_days` is 3.
- **Personal data:** `select` names nine columns; the free-text description
  and the phone and contact columns stay on the server.
- **Mapping:** the permit number, the issue date where there is one, the
  application date, the permit type as the job type, the status, the site
  address, the ZIP code and the council district as the source
  neighbourhood. Electrical and plumbing permits read as alterations and
  signs and demolitions as their own classes; the rest, building permits
  among them, fall to the catch-all class, since the type does not say
  whether the work is new.
- **Placement:** each application at its own point; the clip skips the 10
  without one and the 2 west of the box. No geocoder is asked.
- **Poll:** every six hours, the whole window as a snapshot, newest first by
  `ApplyDate DESC, OBJECTID DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 15:37Z, Kafka mocked. The first read
  2,622 rows in four requests and published 2,606 applications made from
  2026-07-06 to 2026-10-01, 2,106 of them issued; it skipped 12 outside the
  box and 4 repeated permit numbers, and dead-lettered none. By status, 2,085
  are issued, 354 under review and 88 awaiting payment. The second read the
  same rows in three requests and published nothing. Neither poll queried a
  geocoder.

### Longview, TX — `permits`

- **Source:** the City's Cityworks permits behind its building permit
  dashboard, on its own ArcGIS Server:
  `cloud.longviewtexas.gov/arcgis/rest/services/AGOL/Building_Permit_Dashboard/MapServer/2`,
  found through the "All Dashboard Permits" item in the City's ArcGIS Online
  org. The org's own hosted permits layer needs a token.
- **Shape:** 19,548 rows on 2026-10-02, created from 2023-04-03, a row per
  permit and review period (`PERIOD_NUMBER` 0 to 4), so a permit repeats;
  `PERIOD_NUMBER <= 1` keeps one row per permit. The permit types are codes
  (`PLUMBPMT#`, `RESBLDG#`), and the project type (`PRJ_TYPE`) names the
  building where it is set.
- **Window:** the permits issued in the 90 days before each poll, closed at
  the request's time, without contractor registrations (placed at each
  contractor's own address, many outside Longview), right-of-way work and
  the pre-submittal, plan and site reviews: 1,027 rows on 2026-10-02.
- **Reach:** the 90 days from 2024-10-12 held 1,136, the most of eight
  windows back to October 2024, so the cap is 2,500: three pages of 1,000.
- **Freshness:** the newest permit was issued at 21:57:59Z on 2026-10-01
  (16:57 in Longview) and was still the newest at 15:19Z the next day: the
  layer carries permits to the close of the previous business day.
  `expected_cadence_days` is 3.
- **Personal data:** `select` names ten columns; the applicant, the work
  description, the case name and the project detail stay on the server.
- **Mapping:** the permit number, the issue and creation dates, the project
  type and then the type code as the job type, the status, the valuation
  (274 of the published permits carry one) and the site address. Neither the
  project type nor the code names the work, so 978 of the 1,002 permits fall
  to the catch-all class and 24 read as alterations.
- **Placement:** each permit at its own point; the clip skips the 25 south
  or west of the box. No geocoder is asked.
- **Poll:** every six hours, the whole window as a snapshot, newest first by
  `DATE_ISSUED DESC, OBJECTID DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 15:37Z, Kafka mocked. The first read
  1,027 rows in three requests and published 1,002 permits issued from
  2026-07-06 to 2026-10-01; it skipped 25 outside the box and dead-lettered
  none, and no permit repeated. By status, 630 are issued, 367 completed, 4
  cancelled and 1 in another state. The second read the same rows in two
  requests and published nothing. Neither poll queried a geocoder.

### Charleston, SC — `permits`

- **Source:** the City of Charleston's active permits on its GIS server,
  `gis.charleston-sc.gov/arcgis2/rest/services/External/Applications/MapServer/20`,
  the layer behind its "Active Permits - Last 18 Months" web map. The
  2026-08-25 candidates note found the City's new-construction layer on
  ArcGIS Online, which holds new construction alone (37 issued in the 90
  days to 2026-10-02); the 2026-08-28 registration took SNAP only.
- **Shape:** 18,540 rows on 2026-10-02, applied for from 2025-04-03, a
  rolling 18 months, each at its point with its parcel number. 1,833 have not
  been issued.
- **Window:** the permits issued in the 90 days before each poll, closed at
  the request's time (seven are dated as far ahead as 2027-03-09), without
  the permits that are not building work: engineering (private and utility
  work), operational permits (short-term rental renewals), rental
  registration, farmers markets, kitchen exhaust cleaning, fireworks, tents,
  tree removal and construction noise. Certificates of occupancy, signs,
  demolitions and the trades stay in. The window held 2,363 rows on
  2026-10-02.
- **A window, not a watermark:** `ISSUE_DATE` is midnight on most rows and
  carries a time of day on the rest (416 and 194 of the 610 issued in the 21
  days to 2026-09-30), so a watermark would pass over a day's later permits
  once one of its permits carried a time. The server evaluates the window,
  and the cross-run dedup drops the permits already published.
- **Reach:** the busiest of the five full 90-day windows the layer holds,
  from 2025-07-09, held 2,445, so the cap is 5,000, read in pages of 1,000.
- **Ids:** the permit number keys each event; one permit was listed twice in
  the window.
- **Freshness:** on Friday 2026-10-02 the newest permit had been issued at
  15:37Z on Wednesday, 46 hours before, and none from Thursday had arrived,
  though weekdays bring 38 to 55. The dashboard layer beside it
  (`MapServer/1134`) runs about a day ahead but leaves out the trades.
  `expected_cadence_days` is 4.
- **Coverage:** the City of Charleston only, its islands and West Ashley
  included; not North Charleston, Mount Pleasant or Summerville.
- **Personal data:** `select` names eleven columns; the description, the
  project and the assignee stay on the server.
- **Mapping:** the permit number, the issue and application dates, the work
  class and then the permit type as the job type, the status, the valuation,
  the site address, the ZIP code (1,233 of the published permits carry one)
  and the parcel number.
- **Placement:** each permit at its own point; the clip skips the 52 without
  one. No geocoder is asked.
- **Poll:** every six hours, the whole window as a snapshot, newest first by
  `ISSUE_DATE DESC, OBJECTID DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 15:38Z, Kafka mocked. The first read
  2,363 rows in four requests and published 2,310 permits issued from
  2026-07-06 to 2026-09-30; it skipped the 52 without a point and the
  repeated permit, and dead-lettered none. 297 are new construction, 952
  alterations and 1,061 in the catch-all class; 2,063 are issued, 229
  completed and 18 applied. The second read the same rows in three requests
  and published nothing. Neither poll queried a geocoder.

### Odessa, TX — `311`

- **Source:** the City's SeeClickFix requests ("Team Odessa", launched in June
  2025), which SeeClickFix publishes to the City's ArcGIS Online org through
  a federated server proxy:
  `utility.arcgis.com/usrsvcs/servers/d29bb427c9bc497fae24cbd89f5b8b6d/rest/services/ServiceRequests_OdessaTX/FeatureServer/0`
  ("Service request data published from SeeClickFix 311 CRM"). SeeClickFix's
  own public org, where New Haven's and Lincoln's views live, holds no
  Odessa view; a search for the item's description found this one.
- **Shape:** 5,366 rows on 2026-10-02, filed from 2025-06-22, one point per
  request; `id` never repeats. 13 are private, and the spec reads `private =
  '0'` only. Each request carries a category, a status (`closed`,
  `accepted`, `open`, `in_progress`) and its creation and closing times to
  the second.
- **Freshness:** 74 requests in the seven days to 2026-10-02, about ten a
  day; the newest was filed at 13:42:53Z that day. `expected_cadence_days` is
  2.
- **Watermark:** `created_at`. The layer's creation and edit stamps are
  empty, so nothing marks when a request reached it.
- **Personal data:** `select` names six columns; the reporter's name and
  e-mail, the summary and description, the address and the assignee stay on
  the server.
- **Placement:** each request's own point. The metro box stops at 31.94° N,
  short of north Odessa, so the clip skips about one request in seven (122
  of the 918 public requests in the 90 days to 2026-10-02). Widening the box
  would change the metro's grid tiles and is left for its own change. No
  geocoder is asked.
- **Poll:** every 15 minutes, newest first by `created_at DESC, id DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 15:39Z, Kafka mocked. The first read
  the newest 1,000 public requests, filed from 2026-06-28 to 2026-10-02, in
  two requests, and published 863; it skipped the 137 north of the box and
  dead-lettered none. By category, 179 report high weeds or grass, 53 junk
  vehicles, 52 illegal dumping and 44 potholes; 401 are closed, 344
  accepted, 112 open and 6 in progress. The second sent `(private = '0') AND
  created_at > '2026-10-02T13:42:53'`, found nothing newer and published
  nothing. Neither poll queried a geocoder.

### Waco, TX — `311`

- **Source:** the City's MyWaco requests (CitySourced), synced to a hosted
  layer on its ArcGIS Online org:
  `services2.arcgis.com/oUXiR7ziAPAzGw6X/arcgis/rest/services/MyWacoRequests/FeatureServer/6`.
  The item was last modified in 2024, but its rows are current.
- **Shape:** 22,861 rows on 2026-10-02, created from 2021-12-06, one point
  per request; `Id` never repeats. 671 of the 1,144 requests in the 90 days
  are private, and the spec reads `IsPrivate = 0` only: 11,244 public
  requests in all. A readable status (`StatusTypeReadable`: "Work Order
  Created", "Referred to Dept") stands before the open-or-closed flag.
- **Freshness:** the newest update stamp read 03:00:00Z on 2026-10-02 at two
  checks an hour apart: a nightly sync. 473 public requests in 90 days, about
  five a day; the newest was created at 16:54:08Z on 2026-10-01.
  `expected_cadence_days` is 2.
- **Watermark:** `DateCreated`. Its times run to the millisecond and the
  stored watermark keeps whole seconds, so each poll reads its newest request
  again and the dedup drops it.
- **Personal data:** `select` names seven columns; the author, assignee,
  customer and creator names, the description, the address, the reporting
  device and the images stay on the server.
- **Placement:** each request's own point; all 473 public requests in the 90
  days lay inside the box, and the clip guards against a misplaced one. No
  geocoder is asked.
- **Poll:** every six hours, newest first by `DateCreated DESC, OBJECTID
  DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 15:39Z, Kafka mocked. The first read
  the newest 1,000 public requests, created from 2026-04-09 to 2026-10-01, in
  two requests, and published all 1,000; none was dead-lettered. By type,
  127 report potholes, 91 high grass or weeds and 48 water leaks; 890 are
  closed and 45 in progress. The second sent `(IsPrivate = 0) AND
  DateCreated > '2026-10-01T16:54:08'`, read the newest request again and
  published nothing. Neither poll queried a geocoder.

### Lexington, KY — `311`

- **Source:** LFUCG's LexCall requests from its Salesforce CRM, published as
  "LexCall 311 Service Requests" on its ArcGIS Online org:
  `services1.arcgis.com/Mg7DLdfYcSWIaDnu/arcgis/rest/services/CitizenRequests_public/FeatureServer/0`.
- **Shape:** a rolling 30 days, 8,455 requests on 2026-10-02, filed from
  2026-09-02, each with its coordinates; one case number repeated. Each
  request carries a problem code, its label and the division it goes to, but
  no status or closing date, so every request publishes with the event's
  default status, Open.
- **Freshness:** the layer's edit stamp moved from 14:13Z to 14:43Z on
  2026-10-02, and requests arrive at about 300 a day, so
  `expected_cadence_days` is 1.
- **Watermark:** `CreatedDate`, filtered to `CreatedDate <= CURRENT_TIMESTAMP`
  so that a request dated ahead cannot pin it (none was on 2026-10-02).
- **Kept:** 14% of the requests go to Code Enforcement (1,205 in 30 days,
  nuisances and sidewalks). They are residents' requests routed to the
  division, not inspectors' code cases, so they stay.
- **Personal data:** `select` names nine columns; the address stays on the
  server.
- **Placement:** each request's own coordinates; 8,447 of the 8,455 lay
  inside the box. No geocoder is asked.
- **Poll:** every 15 minutes, newest first by `CreatedDate DESC, OBJECTID
  DESC`. `retention_days` and `rolling_window_days` are 30, as the layer
  keeps.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 15:39Z, Kafka mocked. The first read
  the newest 1,000 requests, filed from 2026-09-29 to 2026-10-02, in two
  requests, and published all 1,000; none was dead-lettered. 136 carry no
  problem or division and publish as Unknown; the commonest labels are
  "Missed Herbie" (74; Herbie is the City's garbage cart), "Missed YW
  Collection" (57), "Nuisance - Code Enforcement" (54) and "Request courtesy
  service" (49). The second sent `(CreatedDate <= CURRENT_TIMESTAMP) AND
  CreatedDate > '2026-10-02T14:58:11'`, found nothing newer and published
  nothing. Neither poll queried a geocoder.

### Lincoln, NE — `deeds`

- **Source:** the Lancaster County Assessor's property sales on the
  City-County GIS server:
  `gis.lincoln.ne.gov/public/rest/services/Assessor/PropertySales/FeatureServer/0`,
  "Property Sales - Points (last 12 months)", "provided by the Assessor's
  office"; layer 1 holds the same sales as parcel polygons. The 2026-08-30
  probe found no public bulk sales feed, and the "Lancaster County Property
  Sales" items on the City's open data hub stop at 2018.
- **Shape:** 3,980 sales on 2026-10-02, recorded from 2025-10-03 to
  2026-09-28, each at its point with its instrument number and type, parcel
  number, price and sale and recording dates (midnight UTC). Every sale
  carries a price; 960 of the 986 in the 90 days are residential.
- **Window:** the sales recorded in the 90 days before each poll, closed at
  the request's time: 986 rows on 2026-10-02 (875 by sale date). The server
  rejects ISO date literals and evaluates the relative window.
- **Reach:** the 90 days from 2026-04-19 held 1,371, the most in the layer's
  12 months (recordings ran from 199 in October 2025 to 514 in June 2026), so
  the cap is 2,500, read in pages of 1,000.
- **Ids:** the instrument number keys each event; two sales in the window
  were listed twice, parcel, price and day alike.
- **Freshness:** sales arrive on weekdays, four to seven days after they are
  recorded; the newest, recorded 2026-09-28, was unchanged between 14:18Z and
  15:14Z on 2026-10-02. `expected_cadence_days` is 7.
- **Personal data:** `select` names six columns; the layer's display name,
  the grantor, the grantee, the appraiser and the photo link stay on the
  server.
- **Mapping:** the instrument number, the recording date, the price, the
  parcel number and the instrument type (`WDEED`, `TRDEED`, `DEED`, `PRDEED`)
  as the document type.
- **Placement:** each sale at its point. The layer covers Lancaster County,
  and the clip keeps the metro box: 807 of the 986. No geocoder is asked.
- **Poll:** every six hours, the whole window as a snapshot, newest first by
  `RecordedDate DESC, OBJECTID DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 16:23Z, Kafka mocked. The first read
  986 rows in two requests and published 805 sales recorded from 2026-07-06
  to 2026-09-28 (750 `WDEED`, 51 `TRDEED`, 3 `DEED` and 1 `PRDEED`), every
  one with a price; it skipped 179 outside the box and the 2 repeated
  listings, and dead-lettered none. The second read the same rows in one
  request and published nothing. Neither poll queried a geocoder.

### Manchester, NH — `deeds`

- **Source:** the City's parcels on its own ArcGIS Server:
  `ags.manchesternh.gov/agsgis7/rest/services/Community/Parcels/MapServer/0`,
  33,997 polygons, each with its latest sale. The registration retracted on
  2026-09-30 named an ArcGIS Online org that does not exist, and the August
  probe found no sale source; the City's Hub is private.
- **Shape:** every row carries the same as-of stamp (03:59Z on 2026-10-02):
  the layer is rebuilt daily. Each sale has its book and page (`9986/1668`),
  price and land use, and its date as unpadded `M/D/YYYY` text. 172 of the 521
  sales in the 90 days carry a price of zero or none.
- **Window:** as text the dates do not compare, but the server casts them, so
  the spec reads the parcels whose cast sale date falls in the 90 days before
  each poll, closed at today: 521 rows on 2026-10-02. The 58 parcels the City
  keeps off its internet maps (`Suppress_Internet_Access = 'Yes'`) stay out;
  none had a sale in the window. A watermark on the sale date would pass over
  the sales the assessor posts late, so the poll rereads the window and the
  cross-run dedup drops the sales already published.
- **Reach:** the 90 days from 2026-05-04 held 735, the most found, so the
  default cap of 1,000 holds the window.
- **Ids:** a row is its parcel, sale date and book and page, since one deed
  can convey several parcels (478 books and pages among the 496 published
  sales); 3 rows inside the box repeated all three.
- **Freshness:** the newest sale, dated 2026-09-17, was 15 days old on
  2026-10-02, and September's 54 sales against 207 to 285 in each of the
  three months before show the assessor posting sales two to four weeks after
  they close. `expected_cadence_days` is 21, so the alarm waits six weeks.
- **Personal data:** `select` names six columns; owners and their mailing
  addresses stay on the server.
- **Mapping:** the book and page (the parcel number where there is none), the
  sale date as the recorded date, the price, the parcel number and the land
  use (`Single Fam`, `Condo`, `Two Family`) as the document type.
- **Placement:** each parcel's centroid. The layer covers the city, and the
  clip skips the 22 parcels south or east of the box. No geocoder is asked.
- **Poll:** every six hours, the whole window as a snapshot, paged by object
  id.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 16:32Z, Kafka mocked. The first read
  521 rows in two requests and published 496 sales dated from 2026-07-05 to
  2026-09-17 (283 single-family, 91 condominium and 45 two-family), 332 of
  them with a price; it skipped 22 outside the box and 3 repeated rows, and
  dead-lettered none. The second read the same rows in one request and
  published nothing. Neither poll queried a geocoder.

### Tucson, AZ — `permits`

- **Source:** the City's EnerGov residential building permits on its own
  ArcGIS Server:
  `gis.tucsonaz.gov/public/rest/services/PublicMaps/PermitsCode/MapServer/85`
  (`PDSD_ResidentialBldg`). The August probes found only the
  `PDSD_PERMITS_ALL` archive, which stops on 2022-10-20; the City's ArcGIS
  Online items for the `PermitsCode` layers were modified on 2026-09-03.
- **Shape:** 20,003 rows on 2026-10-02, the oldest issued in 1997, each at
  its point with its number, parcel, status, type, work class, census code,
  value, square footage and dates; 1,693 have not been issued. The commercial
  layer beside it (`/81`) held 315 permits in the 90 days, and the
  multi-family layer (`/84`) stopped on 2025-03-14.
- **Window:** the permits issued in the 90 days before each poll, closed at
  the request's time: 1,290 rows on 2026-10-02. Trade, solar, pool and fence
  permits stay in with the building work. The issue date is midnight UTC on
  1,257 of them and carries a time of day on 33, so the window runs on the
  server and the cross-run dedup drops the permits already published.
- **Reach:** the 90 days from 2025-08-17 held 1,329, the most in the two
  years before, so the cap is 2,500, read in pages of 1,000.
- **Ids:** the permit number keys each event; none repeated in the window.
- **Freshness:** 4 permits issued on 2026-10-02 were in the layer by 14:41Z
  that day, so it refreshes at least daily. `expected_cadence_days` is 3.
- **Personal data:** `select` names ten columns; the project name, the
  free-text description and the portal links stay on the server.
- **Mapping:** the permit number, the issue and application dates, the work
  class and then the type as the job type, the status, the value (zero on
  most trade permits), the site address and the parcel number. Model permits
  (homes built from a plan the City approved once: 141 in the window,
  averaging 2,331 square feet and $288,769) and new dwellings (29) are the
  new homes, but the job type codes read neither as new construction; new
  dwellings do read so in the normalized type. Additions and alterations
  read as alterations and demolitions as their own class; the rest falls to
  the catch-all class.
- **Placement:** each permit at its own point. About a fifth lie in the
  City's southern and south-eastern annexations, south of 32.15° N or east of
  110.78° W, outside the metro box, and the clip skips them; widening the box
  would change the metro's grid tiles and is left for its own change. No
  geocoder is asked.
- **Poll:** every six hours, the whole window as a snapshot, newest first by
  `ISSUEDATE DESC, OBJECTID DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer at 16:23Z, Kafka mocked. The first read
  1,290 rows in three requests and published 1,016 permits issued from
  2026-07-06 to 2026-10-02; it skipped 274 outside the box and dead-lettered
  none. 182 read as alterations, 14 as demolitions and 820 in the catch-all
  class; by normalized type, 26 are new construction, 182 major renovations
  and 150 mechanical, electrical or plumbing work. By status, 584 are issued,
  385 in inspections and 36 with inspections complete. The second read the
  same rows in two requests and published nothing. Neither poll queried a
  geocoder.

### Tucson, AZ — `deeds`

- **Source:** the Pima County Assessor's "Affidavit of Sales" files, one
  zipped CSV a sale year
  (`www.asr.pima.gov/Downloads/Data/sales/2026//SALE2026.ZIP`, member
  `Sale2026.csv` beside a disclaimer), listed by the Assessor site's download
  API and rebuilt nightly (last modified 2026-10-02 07:20:45 GMT). The
  County Recorder publishes no bulk feed.
- **Shape:** 15 columns and no names or addresses: the parcel, the
  affidavit's sequence number, the sale month (`YYYYMM`), the price, the
  property type, intended use, deed type, financing, validation note,
  buyer-seller relation, solar, personal property and partial interest flags,
  the recording date (`YYYY-MM-DD`) and the parcel use. The 2026 file held
  14,165 rows recorded from 2026-01-02 to 2026-09-25.
- **Years:** a file holds the sales that closed in its year, whenever they
  were recorded, so a sale closed in December and recorded in January sits in
  the earlier file. The 2025 file holds 813 sales recorded in January 2026,
  438 in February and 651 in March, and a few in each month since. The spec
  writes the year as `{year}` in the URL and the member, and the CSV client
  reads this year's file and then last year's. This year's file may not exist
  in the first days of January, and the Assessor's site answers a file it
  lacks with its own page and a 200 (asked for 2027's on 2026-10-02), so the
  client passes over a 404 or a web page for this year's file alone; any
  other failed download fails the poll.
- **Window:** the sales recorded in the 90 days before each poll, closed at
  the day: 4,319 rows county-wide on 2026-10-02, 4,257 from the 2026 file
  and 62 from the 2025 file.
- **Reach:** the 90 days from 2026-02-18 held 6,873 across the two files,
  the most in their two years, so the cap is 10,000. The client reads both
  files whole and filters and sorts them in memory.
- **Ids:** an affidavit can convey several parcels (12,863 sequence numbers
  cover the 14,165 rows of the 2026 file), so each event is the sequence
  number with the parcel. No pair repeats, within a file or across the two.
- **Freshness:** the newest recording was a week old on 2026-10-02, and the
  last days arrive thin (recording-day counts are dense to 2026-09-16), so
  `expected_cadence_days` is 10.
- **Personal data:** the file holds none, and `select` keeps five columns.
  The parcel join asks the centroid layer for the parcel number alone; its
  mailing columns stay on the server.
- **Mapping:** the sequence number as the document id, the recording date,
  the price (zero when blank), the parcel number and the deed type.
- **Placement:** each sale on its parcel's centroid from the County's parcel
  centroid layer
  (`gisdata.pima.gov/arcgis1/rest/services/GISOpenData/LandRecords/MapServer/0`),
  asked for each page's parcels in bounded `IN` clauses. About three in five
  sales lie elsewhere in the county, and the clip skips them. No geocoder is
  asked.
- **Poll:** once a day, the whole window as a snapshot, newest first by
  `recordingdate DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live files and layer from 17:10Z to 17:16Z, Kafka
  mocked. The first downloaded the two files (254,642 and 409,530 bytes),
  read 4,319 rows, placed every one in 62 join requests and published 1,727
  sales recorded from 2026-07-06 to 2026-09-25 (687 in July, 697 in August
  and 343 in September), 1,684 of them priced and 1,716 by warranty deed.
  It skipped 2,592 outside the box and dead-lettered none. The second read
  the same rows in 61 join requests and published nothing. Neither poll
  queried a geocoder.

### Long Beach, CA — `311`

- **Source:** the City's "Go Long Beach" service requests on its
  OpenDataSoft portal (`data.longbeach.gov`, dataset `service-requests`),
  through the portal's CSV export
  (`/api/explore/v2.1/catalog/datasets/service-requests/exports/csv`).
- **Shape:** 353,242 requests on 2026-10-02, the oldest created on
  2020-09-21, each with its case number, type, status, created and closed
  times, council district, ZIP code and point. The dataset has no requester,
  address or description fields.
- **Export:** the export takes the columns, a filter, the delimiter and the
  header style as parameters, so the spec's URL asks for seven columns, the
  requests created in the last seven days (`createddate >= now(days=-7)`),
  commas and field names (the defaults are semicolons and labels). Each point
  is one quoted `lat, lon` column (`geolocation`) that the server cannot
  split; the spec names it as its `point_col`, and the CSV client gives each
  row its latitude and longitude.
- **Window:** the requests created in the seven days before each download,
  1,314 at 14:46Z on 2026-10-02 (about 200 a weekday). The poll keeps the
  ones newer than its watermark.
- **Reach:** the cap is 2,000, so a first poll, or one after a missed week,
  reads the whole export.
- **Ids:** the case number keys each event; the 19,090 requests created in
  the 90 days to 2026-10-02 each had their own.
- **Freshness:** the export was rebuilt at 14:00:28Z on 2026-10-02, its
  newest request created at 13:31:45Z, and not again by 17:34Z; the August
  probe found requests created that afternoon. `expected_cadence_days` is 2.
- **Personal data:** none in the dataset, and the URL names its seven
  columns.
- **Mapping:** the case number, the created and closed times, the type, the
  status and the ZIP code.
- **Placement:** each request at its point. 2 of the 19,090 in the 90 days
  lay outside the metro box, and the clip skips such rows. No geocoder is
  asked.
- **Poll:** hourly, newest first by `createddate DESC`, incremental on
  `createddate`. The watermark keeps whole seconds and drops the export's
  `+00:00`, so the newest request reads as newer than it and comes back
  once; the dedup drops it.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live export at 17:34Z, Kafka mocked. The first
  downloaded the export once (141,217 bytes) and published 1,275 requests
  created from 2026-09-25 17:35Z to 2026-10-02 13:31Z: 580 dumped items,
  250 e-scooters, 159 graffiti and 68 tree maintenance; 358 in progress,
  339 closed and 282 closed and referred. It clipped none and dead-lettered
  none. The second downloaded the export again, re-read the newest request
  and published nothing. Neither poll queried a geocoder. A pair at 17:09Z
  under the default cap of 1,000 published only the newest 1,000 of the
  week, which is why the spec declares 2,000.

## Held

| Metro (missing) | Source | Why held | Re-check when |
|---|---|---|---|
| Charleston, SC (`deeds`) | Charleston County's parcels on its public GIS server (`gisccapps.charlestoncounty.org`, `ENERGOV/energov_css/MapServer/4`, "Parcels with attributes", 197,687 polygons) carry each parcel's latest deed, recording date and price: 3,898 recorded in the 90 days to 2026-10-02, 94.8% of them inside the metro box, the newest on 2026-09-25, about a week behind. Berkeley County's parcel lines carry their sales two weeks late, a quarter of them inside the box; Dorchester County's are four weeks late, under a licence that bars adding them to any pay-for-use location without written approval. | The County distributes parcel attributes only on request, and its terms bar republishing them without written approval. A spec reads one source, and Berkeley's covers only the north of the box. | The County's terms allow republishing, or it grants approval. |
| Charleston, SC (`311`) | The City GIS's `MissedCollectionSixMonths` layer (`External/Applications/MapServer/96`): 1,500 missed garbage and trash collections over a rolling six months, 852 in 90 days, each with its own reference number and point; its closing date is text. The City's monthly request sheets on ArcGIS Online are uploaded by hand under a new service name each month, carry no request id, and stop with August's, which holds garbage requests only. | One kind of request, from solid waste. Registered as the metro's `311`, it would mark Charleston as covered where the City publishes no request stream. | The City publishes its service requests as one layer with ids. |
| Tyler (`permits`) | The City's `Permit_Data_With_XY` layer (`services5.arcgis.com/RmXXW3PwBZGOxlSe`): 29,994 permits issued from 2023-01-02, about 540 a month, the newest on 2026-07-24, though the item was modified on 2026-09-29: a monthly export for the City's permits dashboard. `Active_Construction_Sites` in the same org is current (113 issued in 90 days, newest 2026-09-25) but holds only new construction, shells and grading still open, 1,047 sites that leave the layer when they close. | The export ran 70 days behind on 2026-10-02, and the active sites are a slice of the permits. | The export moves past 2026-07-24 and keeps pace. |
| Beaumont (`permits`) | The City's Cityworks server publishes the new residential and commercial permits still open, for its "Construction and SUP Map" (`cityworks.beaumonttexas.gov/CityworksNAD/gis/1/1/rest/services/qe/FeatureServer/8` and `/7`): 80 and 37 rows on 2026-10-02, 20 and 9 issued in 90 days, with times of day; a permit leaves when it closes, and the server rejects relative dates. | New construction only, and only while open. Registered as the metro's permits, they would mark Beaumont as covered while missing its trade, roofing and remodelling permits. | The City publishes all its permits. |
| Texarkana (`permits`) | MyGov's daily "Permits Issued in the last month" workbook for the Texas city (`public.mygov.us/tx_texarkana`, report 370): 289 permits started in about a month, each with its number and address, 170 of them issued (2026-09-01 to 2026-10-02). Its dates are text (`MM/DD/YYYY`) and it has no coordinates; the five-year workbook beside it (14,142 rows) has no permit number and lists health inspections, restaurant permits, zoning and street cuts among its types. | The Excel client compares text dates as strings and drops the spec's date format, so it can neither window nor order the workbook, and nothing in the workbook separates building permits from the rest. | The Excel client reads text dates as dates. |
| Abilene (`permits`) | MyGov's "TCADBuildingPermitsWithProjInfo" workbook for the City (`public.mygov.us/tx_abilene`, report 371): 652 permits, each with its number and coordinates, all issued in August 2026. It is generated once a month (last on 2026-09-28), each file replaces the last, and its times read "MM/DD/YYYY at H:MM AM". The City's other permit reports are PDFs, and its GIS server reset the connection twice. | Monthly and a month behind, and the permits producer cannot read its dates. | MyGov publishes a daily permits workbook, or a monthly feed is accepted and the producer reads the format. |
| Buffalo (`311`) | The City's Salesforce CRM mirrors public works' holes-in-road work orders to ArcGIS Online for its pothole tracker (`services8.arcgis.com/BMPgiPHUrkqJdtki`, `SF_Work_Order_Holes_In_Road_(view)/FeatureServer/1`): 5,420 since 2024-08-26, 873 in 90 days, unique work order numbers, each at its point. | One kind of request: potholes, cave-ins and other holes. Registered as the metro's `311`, it would mark Buffalo as covered while the CRM's other requests stay unpublished. | The City publishes its CRM requests as one layer with ids. |
| Manchester, NH (`311`) | Public works' Maximo tickets on the City's server (`DPW/SRPOINTS/FeatureServer`): 4,025 open and 60,847 closed, each at its point, from missed pickups to potholes, cave-ins and tree pruning, internal and resident tickets mixed; the dates are text. | Resident ticket intake stopped: the newest report was filed on 2026-09-02, 30 days before, though work orders still arrive. Residents now report through "Manchester NH Connect", a SeeClickFix app. | Tickets arrive again, or SeeClickFix publishes a view for the City. |
| Buffalo (`deeds`) | The City's 2026-27 assessment roll (`gis.buffalony.gov/server/rest/services/Tax/Parcels_20262027/FeatureServer/0`, 93,453 parcels) carries a sale price on 75,983 parcels, with deed book and page. | The deed date is empty on every row; the 2025-26 layer rejects queries on it, and Erie County's parcels carry no price. | The roll's deed dates load. |
| Des Moines (`deeds`) | Polk County Assessor's yearly residential sales file (`www.assess.co.polk.ia.us`, `info/web/exports/res/sales/polk/2026.csv`): 5,667 sales from 2026-01-01 to 2026-07-28 across the metro's cities, unique by book and page, all priced, placed only by site address. | The newest sale was 66 days old and the file was built on 2026-08-18; the 2025 file was rebuilt the same day and the 2024 file last on 2025-12-31, so rebuilds are irregular. The Auditor's parcel table, which carries the latest deed date without a price, sits on a host closed to these probes. | The file is rebuilt monthly or faster. |
| Santa Rosa (`deeds`) | Sonoma County's "Parcels Public" layer (`socogis.sonomacounty.ca.gov`, `CRAPublic/ParcelsPublic/FeatureServer/0`, 189,239 parcels) carries each parcel's latest sale: recording date, document number and price. | The Assessor posts sales about 145 days late: 23 were recorded in the 90 days to 2026-10-02, against 291 to 550 a month through April 2026, and the layer is complete only through 2026-05-11. | Posting catches up, or a window of about nine months is accepted. |

## Not now

| Metro (missing) | Why not | Re-check when |
|---|---|---|
| Abilene (`311`) | Requests run on SeeClickFix, whose public API returns reporters and descriptions with no way to leave them out, and SeeClickFix's public ArcGIS org (28 views on 2026-10-02) holds none for the City. | SeeClickFix publishes a view for the City. |
| Amarillo (`permits`, `311`) | Permits live in MGO Connect, which has no public data API; neither the City's ArcGIS Online org nor `data.texas.gov` holds a permits layer, and the City server an item names (`vm-gissvr01p.cityama.com`) cannot be reached from outside. No request system with published rows turned up, only phone numbers and street and alley request pages. | A permits layer appears or the City publishes requests. |
| Beaumont (`311`) | "Beaumont 311" runs on SeeClickFix, linked to Cityworks, and SeeClickFix's public org holds no view for the City. The Cityworks layers the City publishes are single-category lists: pothole repairs closed in 90 days, water discoloration calls and reported leaks. | SeeClickFix publishes a view for the City. |
| Longview (`311`) | CitySend runs on CitySourced with no public rows; the `Request_AGOL` layer in the City's org is a static sample of 166 requests from 2025-07-25 to 2025-10-20. | A requests layer with current rows appears. |
| Midland (`311`) | Requests run on SeeClickFix, which replaced the City's earlier 311 system, and the City's org holds no request layer; SeeClickFix's public org has a view for Midland County, Michigan, not Texas. | SeeClickFix publishes a view for the City. |
| Odessa (`permits`) | Permits live in MGO Connect, which has no public data API, and the City's org holds no MGO layer. | A permits layer appears. |
| Texarkana (`311`, `deeds`) | The Texas city's MyGov request module publishes no report, and its work-order reports are PDFs. On the Arkansas side, Miller County's parcels (`MCParcels`, a DataScout publication) and the state's parcel layer carry no sale date or price; sales sit behind the Assessor's DataScout search, and ARCountyData answered with a Cloudflare challenge (403). Texas does not disclose sale prices. The Arkansas city publishes no permits or requests. | A requests report or a Miller County sales layer appears. |
| Tyler (`311`) | "MyTyler" runs on Tyler Technologies' 311 app with no public rows; neither the City's ArcGIS Online org nor its GIS server holds a request layer. | A requests layer appears. |
| Waco (`permits`) | Permits live in Tyler EnerGov, whose GIS layers on the City's server hold template rows only (checked twice). The City's "Main Street Permits" layer covers the downtown district alone: 25 applications in 90 days. | EnerGov's GIS layers fill, or a citywide layer appears. |
| Alexandria (`permits`, `311`) | Permits go through My Permit Now, a hosted portal with no row API, and ArcGIS searches for the city or Rapides Parish return Alexandria, Virginia. "Alex Connects" runs on QAlert with no public rows. The regional planning commission's GIS server presented an expired certificate and was not queried. | A permits or requests layer appears. |
| Fort Smith (`permits`, `311`, `deeds`) | Permits live in CityView, and "Fort Smith Click & Fix" runs on SeeClickFix. The City's website answered the first request with an "Access Denied" page (403) and its GIS portal reset the connection, so neither was asked again; the City's ArcGIS Online org holds utility layers only. Sebastian County's assessor records are on ARCountyData (Cloudflare challenge, 403), and the state's parcel layer has no sale date or price. | A permits or requests layer appears, or Sebastian County publishes its sales. |
| Huntington (`permits`, `311`, `deeds`) | Permits go through a Tyler New World eSuite portal, and requests run on SeeClickFix; the City's ArcGIS Online org (177 items) holds reference layers. Cabell County's parcel layer carries deed book and page and appraisals, no sale date or price. | A permits or requests layer appears, or a sales layer. |
| Jackson, MS (`permits`, `311`) | Permits live in OpenGov's ViewPoint Cloud, and "Jackson 311" runs on CitySourced. The City's CKAN portal holds 33 datasets, the newest from 2021. Mississippi does not disclose sale prices. | A permits or requests layer appears. |
| Jonesboro (`permits`, `311`, `deeds`) | Applications go through an Avolve portal, and the City posts its monthly inspection permit reports as PDFs (newest September 2026). Requests go through CivicPlus's account-based Request Tracker and web forms. Craighead County's assessor records are on ARCountyData (Cloudflare challenge, 403), and its GIS services need a token. | A permits or requests layer appears, or Craighead County publishes its sales. |
| Lake Charles (`permits`, `311`) | Permits live in MGO Connect, and the City posts monthly permit reports as PDFs (newest July 2026); the parish GIS holds reference layers. The "ONE LC Action Line" runs on SeeClickFix. Louisiana does not disclose sale prices. | A permits layer appears or SeeClickFix publishes a view for the City. |
| Lexington (`permits`, `deeds`) | Permits live in Accela Citizen Access; LFUCG's ArcGIS Online org holds right-of-way permits and annual summaries, and its Hub finds no permits dataset. The Fayette County PVA publishes its sales as weekly PDF reports, and LFUCG's parcel layers carry no sale fields. | A permits layer appears, or the PVA publishes its sales as a table. |
| Monroe (`permits`, `311`) | Permits live in MGO Connect; the City's "Permitted Projects" layer is a one-off export of 203 permits from 2025-08-01 to 2026-03-13, last edited on 2026-03-18. Requests run on SeeClickFix. Louisiana does not disclose sale prices. | A current permits layer appears or SeeClickFix publishes a view for the City. |
| Albany (`permits`, `311`, `deeds`) | The City's ArcGIS Online org (231 items) holds reference layers and a 2023 parcels layer made for EnerGov, which likely runs its permits; its Hub answers 401. Requests go through SeeClickFix, whose public org holds no Albany view. Albany County's 2026 parcels, the state's tax parcels and the annual roll on `data.ny.gov` carry deed book and page only; New York's sales search is interactive, and its certificate did not verify here. | A permits layer, a SeeClickFix view or a sales table appears. |
| Buffalo (`permits`) | The open data portal still refuses the permits dataset's rows (403, as on 2026-08-27), and the City's GIS server holds Infor/Hansen base layers only. | The dataset's rows open, or a permits layer appears. |
| Syracuse (`permits`, `311`, `deeds`) | Permit applications moved to Camino, and the City's ArcGIS export of permits stops on 2025-08-16; requests moved to SeeClickFix, and the SYRCityline export stops on 2025-02-27. The City's 2025 parcel map has no sale fields, and no Onondaga County sales layer turned up. | Camino or SeeClickFix publishes rows, or a sales table appears. |
| Harrisburg (`permits`, `311`, `deeds`) | The City's website answered with a Cloudflare challenge (403) and was not asked again. The City's ArcGIS org holds street-cut and parking permits, a static workbook from 2025 and a Tyler tile service; the only request form is a Survey123 layer last edited in 2023. The City's parcel snapshot carries a purchase date with a 99/99/1999 sentinel and no price, and Dauphin County's tables carry document numbers only. | A permits or requests layer appears, or a sales table. |
| Manchester, NH (`permits`) | Permits run on CentralSquare TRAKiT, whose map service holds address, place and parcel points only, and the City's permit page links PDF forms. | A permits layer appears. |
| Portland, ME (`permits`, `311`, `deeds`) | The City's GIS server holds EnerGov base layers, capital projects and a static demolitions list. Requests run on SeeClickFix; the City's website failed its certificate check and was not queried. Parcel layers carry no price, and the Cumberland County registry is interactive only. | A permits layer or a SeeClickFix view appears, or a sales table. |
| Dover (`permits`, `311`, `deeds`) | The City's permits layer covers 2018 alone, and the state's permits layer is annual, its newest year 2024. Kent County's permits layer is current to 2026-09-04 but covers the County's own jurisdiction: 5 of its 139 permits of 2026 lie inside the City. The road-problem layer needs a token, the request forms are write-only, and Kent County's parcels carry deed references only. The City's website returned an error page and was not asked again. | The City publishes its permits or requests, or Kent County its sales. |
| Wilmington, DE (`permits`, `311`, `deeds`) | The City's website answered with an Akamai "Access Denied" (403) and New Castle County's GIS with "Request Blocked" (472), and neither was asked again. The City's ArcGIS org and Hub hold no permit or request layers, and its copy of the County's parcels has no sale fields. | The County's sales layer can be read, or the City publishes permits or requests. |
| Des Moines (`permits`, `311`) | Permits live in Tyler EnerGov's self-service portal, which answers an anonymous JSON search that no client here reads, and requests run on CitySourced and Tyler Portico with no public rows. West Des Moines's permit reports page answered with Akamai "Access Denied" (403). The City's Hub (62 datasets) holds neither. | An EnerGov client is built, or a permits or requests layer appears. |
| Grand Rapids (`permits`, `311`, `deeds`) | Permits live in BS&A Online and Accela, with no rows on the City's server, whose CRM services are spatial-join helpers without requests. Kent County's parcels carry no sale fields and its Hub is private. Ottawa County's arm's-length sales are current (706 in 90 days) but reach only the lakeshore townships at the box's west edge: 126 of the 706 lie inside it. | Kent County publishes its sales, or a permits or requests layer appears. |
| Madison (`permits`, `311`, `deeds`) | Unchanged since the 2026-09-30 probe: permits sit in Accela's interface, requests go through a web form, the City's owner-change date is empty, and Wisconsin's transfer returns sit in a session-only app. | A permits, requests or sales layer appears. |
| Long Beach (`permits`, `deeds`) | The City's open data portal lists 15 datasets, none of them permits or sales, and its ArcGIS org holds an annual housing report and 61 development projects. Los Angeles County's sales layer stopped on 2024-06-05. | A permits layer or a current sales source appears. |
| Modesto (`permits`, `311`, `deeds`) | The City's ArcGIS org (68 services) holds 2021 dashboards and reference layers; its TrakIT folder answered 403 to the August probe and its GIS host refuses the default User-Agent, so neither was asked. Requests run on PublicStuff, whose API returns requester fields with no way to leave them out. Stanislaus County publishes no sale prices. | A permits layer appears, or a request source without requester fields. |
| Santa Rosa (`permits`, `311`) | The City's permit layers are post-fire rebuild records last updated in 2020 and 2024, and Sonoma County's permit datasets cover unincorporated parcels and stop on 2025-05-30. Requests run on Accela's request management with no public rows. | A permits or requests layer appears. |
| Stockton (`permits`, `311`, `deeds`) | The City's Socrata permits stop on 2022-06-30 and its public works requests on 2024-03-26; "Ask Stockton" now runs on GOGov, and the GIS server's Accela folder needs a token. San Joaquin County's parcels carry no sale fields. | Current permits or requests appear. |
| Tucson (`311`) | Requests run on SeeClickFix (the City's app is SeeClickFix's), and SeeClickFix's public org holds no Tucson view; the City's Hub finds none. | SeeClickFix publishes a view for the City. |
