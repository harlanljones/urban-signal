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
headers and deleted. Three hosts refused a first request and were not asked
again: ARCountyData and the City of Fort Smith's website answered 403, and
Fort Smith's GIS portal reset the connection.

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

The north-eastern and western groups follow with their registrations.

| Tier (families) | Before (with #106) | With these feeds |
|---|---|---|
| 4 | 30 | 30 |
| 3 | 44 | 44 |
| 2 | 48 | **54** (Midland, Longview, Charleston SC, Odessa, Waco, Lexington) |
| 1 | 35 | 29 |

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
  windows back to October 2024, so the cap is 5,000: three pages of 2,000.
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
  from 2025-07-09, held 2,445, so the cap is 5,000: one page.
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

## Held

| Metro (missing) | Source | Why held | Re-check when |
|---|---|---|---|
| Charleston, SC (`deeds`) | Charleston County's parcels on its public GIS server (`gisccapps.charlestoncounty.org`, `ENERGOV/energov_css/MapServer/4`, "Parcels with attributes", 197,687 polygons) carry each parcel's latest deed, recording date and price: 3,898 recorded in the 90 days to 2026-10-02, 94.8% of them inside the metro box, the newest on 2026-09-25, about a week behind. Berkeley County's parcel lines carry their sales two weeks late, a quarter of them inside the box; Dorchester County's are four weeks late, under a licence that bars adding them to any pay-for-use location without written approval. | The County distributes parcel attributes only on request, and its terms bar republishing them without written approval. A spec reads one source, and Berkeley's covers only the north of the box. | The County's terms allow republishing, or it grants approval. |
| Charleston, SC (`311`) | The City GIS's `MissedCollectionSixMonths` layer (`External/Applications/MapServer/96`): 1,500 missed garbage and trash collections over a rolling six months, 852 in 90 days, each with its own reference number and point; its closing date is text. The City's monthly request sheets on ArcGIS Online are uploaded by hand under a new service name each month, carry no request id, and stop with August's, which holds garbage requests only. | One kind of request, from solid waste. Registered as the metro's `311`, it would mark Charleston as covered where the City publishes no request stream. | The City publishes its service requests as one layer with ids. |
| Tyler (`permits`) | The City's `Permit_Data_With_XY` layer (`services5.arcgis.com/RmXXW3PwBZGOxlSe`): 29,994 permits issued from 2023-01-02, about 540 a month, the newest on 2026-07-24, though the item was modified on 2026-09-29: a monthly export for the City's permits dashboard. `Active_Construction_Sites` in the same org is current (113 issued in 90 days, newest 2026-09-25) but holds only new construction, shells and grading still open, 1,047 sites that leave the layer when they close. | The export ran 70 days behind on 2026-10-02, and the active sites are a slice of the permits. | The export moves past 2026-07-24 and keeps pace. |
| Beaumont (`permits`) | The City's Cityworks server publishes the new residential and commercial permits still open, for its "Construction and SUP Map" (`cityworks.beaumonttexas.gov/CityworksNAD/gis/1/1/rest/services/qe/FeatureServer/8` and `/7`): 80 and 37 rows on 2026-10-02, 20 and 9 issued in 90 days, with times of day; a permit leaves when it closes, and the server rejects relative dates. | New construction only, and only while open. Registered as the metro's permits, they would mark Beaumont as covered while missing its trade, roofing and remodelling permits. | The City publishes all its permits. |
| Texarkana (`permits`) | MyGov's daily "Permits Issued in the last month" workbook for the Texas city (`public.mygov.us/tx_texarkana`, report 370): 289 permits started in about a month, each with its number and address, 170 of them issued (2026-09-01 to 2026-10-02). Its dates are text (`MM/DD/YYYY`) and it has no coordinates; the five-year workbook beside it (14,142 rows) has no permit number and lists health inspections, restaurant permits, zoning and street cuts among its types. | The Excel client compares text dates as strings and drops the spec's date format, so it can neither window nor order the workbook, and nothing in the workbook separates building permits from the rest. | The Excel client reads text dates as dates. |
| Abilene (`permits`) | MyGov's "TCADBuildingPermitsWithProjInfo" workbook for the City (`public.mygov.us/tx_abilene`, report 371): 652 permits, each with its number and coordinates, all issued in August 2026. It is generated once a month (last on 2026-09-28), each file replaces the last, and its times read "MM/DD/YYYY at H:MM AM". The City's other permit reports are PDFs, and its GIS server reset the connection twice. | Monthly and a month behind, and the permits producer cannot read its dates. | MyGov publishes a daily permits workbook, or a monthly feed is accepted and the producer reads the format. |

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
