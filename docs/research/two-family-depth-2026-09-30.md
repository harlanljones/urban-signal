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
held; ten metros have no permits source. The deeds probe ran from 19:32Z to
20:27Z under the same rules, with no grantor or grantee column requested, for
nine of the twelve: Houston, Kansas City and Santa Fe were left out because
Texas, Missouri and New Mexico do not disclose sale prices. Charlotte's deeds
register first, which gives Charlotte all four families, and Toledo's follow,
which gives Toledo a third. Three metros' sources are held and four metros
have none.

The permits and `311` probe of the fifteen ran in two batches. The seven
southern and western metros (Anchorage, Asheville, Charleston WV, Peoria,
Reno, Richmond and Roanoke) were probed live on 2026-09-30 from 20:07Z to
20:50Z (curl default User-Agent, at least ten seconds between requests to a
host, no applicant, contact or free-text column requested). Asheville's
permits register, which gives Asheville a third family; three narrow feeds
are held, and nothing usable turned up for the other ten gaps. The eight
north-eastern metros (Allentown, Bridgeport, Burlington, Canton, Frederick,
New Haven, Providence and Rochester) were probed from 20:06Z to 21:00Z
(curl default User-Agent, at least eleven seconds between requests to a
host; captures that held personal data were deleted). Allentown's permits
register, which gives Allentown a third family; Burlington's frozen permits
export and Providence's right-of-way permits are held, and the other five
metros have no permits source. Allentown's and New Haven's `311` register
next (checked live on 2026-10-02), which gives Allentown all four families
and New Haven a third; Burlington's and Rochester's request exports are held
as frozen, and Bridgeport, Canton, Frederick and Providence publish no
requests.

| Tier (families) | Before (with #91) | With Charlotte's permits (#92) | With Charlotte's deeds (#93) | With Toledo's deeds (#94) | With Asheville's permits (#95) | With Allentown's permits (#96) | With Allentown's and New Haven's `311` |
|---|---|---|---|---|---|---|---|
| 4 | 26 | 26 | **27** (Charlotte) | 27 | 27 | 27 | **28** (Allentown) |
| 3 | 29 | **30** (Charlotte) | 29 | **30** (Toledo) | **31** (Asheville) | **32** (Allentown) | 32 (New Haven in, Allentown up) |
| 2 | 68 | 67 | 67 | 66 | 65 | 64 | 63 |
| 1 | 34 | 34 | 34 | 34 | 34 | 34 | 34 |

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

### Charlotte, NC — `deeds`

- **Source:** the same county server's
  `TaxParcelSales/FeatureServer/0` ("Tax Parcel Sales"), a polygon layer
  listing the county's recorded transfers on each parcel's outline. The
  2026-08-25 sweep read the City's parcel layer, which carries no sales, and
  the county's old REST path (`maps.mecklenburgcountync.gov/agsadaptor`),
  which answers 404. The probe found the county's current server through an
  ArcGIS Online search, and `TaxParcelSales` among the 147 services its root
  lists.
- **Shape:** 1,598,291 rows on 2026-09-30, one per transfer and property. In
  the 90-day window, 8,925 rows hold 8,765 distinct transfer and parcel pairs
  (the rest repeat a pair on another property row of the same parcel) under
  7,183 deeds; one deed covers 119 parcels. `legalreference` (the deed's book
  and page) and `transferid` are never empty. 5,806 of the 8,925 rows carry a
  price; the rest hold zero or nothing. The layer also names the grantor and
  grantee; the spec's `select` names seven other columns.
- **Freshness:** a sale date holds the day alone, stored as midnight Eastern.
  On 2026-09-30 the newest was 2026-09-22 (8 rows, against 99 on 2026-09-21)
  and none was future-dated. Nothing changed between 19:37Z and 20:14Z, so the
  ledger runs about eight days behind and is not rebuilt daily.
  `expected_cadence_days` is 7, so the staleness alarm waits 14 days.
- **Window:** the server evaluates `saledate >= CURRENT_DATE - INTERVAL '90'
  DAY AND saledate <= CURRENT_TIMESTAMP`, so a poll sends no date literal (the
  host, which rejects ISO literals, is already in `ANSI_DATE_LITERAL_HOSTS`
  for backfills). The window held 8,925 rows on 2026-09-30; over the past year
  a 90-day window held 8,514 (January to March 2026) to 11,009 (April to June
  2025), so the cap is 15,000.
- **Ids and order:** a row is its transfer and parcel (`transferid` with
  `parcelid`), so a deed covering several parcels publishes an event for each,
  and a transfer repeated on a parcel's other property rows publishes once.
  Each event carries the deed's book and page as its document id, so a deed's
  parcels share a Kafka key. The snapshot reads `saledate DESC, objectid
  DESC`, which has no ties.
- **Placement:** each row's outline comes back in WGS84 and the event stands
  at the centroid of its outer ring; every row in the window lies inside the
  metro box. The county is the metro, so nothing is clipped and no geocoder is
  asked.
- **Mapping:** the book and page (then the transfer id) as the document id,
  the sale date as the recorded date, the sale price as the amount, the parcel
  id and the deed type (`deeddescription`: warranty, special warranty, quit
  claim and so on).
- **Not chosen:** the same server's `TaxParcel_camadata` parcel layer runs
  three days fresher but keeps only each parcel's latest sale, holds three
  future-dated rows (one in the year 9997), and splits the deed's book and
  page into two columns, so no single column names the deed.
- **Poll:** every six hours, the whole window as a snapshot (nine pages of
  1,000 rows); the cross-run dedup drops the rows already published.
- **Live check:** two polls of the registered spec through the real scheduler
  against the live layer, Kafka mocked. The first read 8,925 rows in ten
  requests (the metadata and nine pages) and published 8,765 events, one per
  transfer and parcel, dated 2026-07-02 to 2026-09-22 under 7,183 deeds; the
  other 160 rows repeated a transfer on another property row of its parcel,
  and none was dead-lettered. All 8,765 lie inside the metro box, 7,381 of
  them inside the City's division box, and 5,712 carry a price. By type, 4,612
  are warranty deeds, 1,612 special warranty deeds, 901 quit claims, 709
  multiple listings, 607 non-warranty deeds, 180 correction deeds, 66
  trustee's deeds, 30 commissioner's deeds and 48 other types. The second poll
  read the same 8,925 rows in nine requests and published none. Neither poll
  read a grantor or grantee value or queried a geocoder.

### Toledo, OH — `deeds`

- **Source:** the Lucas County Auditor's ArcGIS Online layer `Lucas_Sales`,
  `services3.arcgis.com/T8dczfwPixv79EgZ/arcgis/rest/services/Lucas_County_TaxParcels/FeatureServer/1`,
  which puts each recorded sale of real property in the county at a point.
  Earlier probes ([probe-toledo.md](probe-toledo.md)) read the Auditor's own
  GIS server, `lcaudgis.co.lucas.oh.us`, whose public layers carry no sale
  columns; the hosted layer turned up through an ArcGIS Online search.
- **Shape:** 60,834 rows on 2026-09-30, recorded from 2020-12-07, one per
  sale and parcel. In the 90-day window, 2,296 rows hold 2,014 sales; 157
  sales convey several parcels (one conveys 23), and `SALESID` with
  `PARCELID` never repeats. Every row carries a price and a point. The layer
  also names the grantor and grantee; the spec's `select` names six other
  columns.
- **Freshness:** the recorded date (`RECORDDT`) holds the day alone, stored
  as midnight UTC. On 2026-09-30 the newest was Friday 2026-09-25, nothing
  was future-dated, and the layer had last been edited on Monday 2026-09-28,
  so it looks rebuilt weekly through the Friday before (inferred from one
  week). `expected_cadence_days` is 7, so the staleness alarm waits 14 days.
  The transfer date (`TRANSDT`) runs a median of ten days earlier and is not
  used.
- **Window:** the server evaluates `RECORDDT >= CURRENT_DATE - INTERVAL '90'
  DAY AND RECORDDT <= CURRENT_TIMESTAMP`. The window held 2,296 rows on
  2026-09-30, and over the past year a 90-day window held 2,154 (October to
  December 2025) to 2,628 (July to September 2025), so the cap is 4,000.
- **Ids and order:** a row is its sale and parcel (`SALESID` with
  `PARCELID`), so a sale conveying several parcels publishes an event for
  each. Each event carries the sale's number as its document id, so a sale's
  parcels share a Kafka key. The snapshot reads `RECORDDT DESC, OBJECTID
  DESC`, which has no ties.
- **Placement:** each sale is a point, and the layer covers the whole
  county: 2,154 of the window's 2,296 rows lie inside the metro box, and
  `metro_clip` skips the 142 that lie outside it, to its west, south and
  east. No geocoder is asked.
- **Mapping:** the sale's number (then the parcel) as the document id, the
  recorded date, the sale amount, the parcel id and the instrument type
  (`INSTRTYP`: WD warranty deed, SV survivorship deed, FD fiduciary deed, LW
  limited warranty deed, QC quit claim and so on).
- **Poll:** every six hours, the whole window as a snapshot (three pages of
  1,000 rows); the cross-run dedup drops the rows already published.
- **Live check:** two polls of the registered spec through the real scheduler
  against the live layer, Kafka mocked. The first read 2,296 rows in four
  requests (the metadata and three pages), skipped the 142 outside the metro
  box and published 2,154 events, one per sale and parcel, recorded from
  2026-07-02 to 2026-09-25 under 1,882 sales, all with a price; none was
  dead-lettered and no row repeated. 944 lie inside the City's seven
  neighbourhood boxes. By instrument, 1,447 are warranty deeds, 223
  survivorship deeds, 184 fiduciary deeds, 119 limited warranty deeds, 102
  quit claims, 26 sheriff's deeds, 20 `PS`, 16 `CO` and 17 other types. The
  second poll read the same 2,296 rows in three requests and published none.
  Neither poll read a grantor or grantee value or queried a geocoder.

### Asheville, NC — `permits`

- **Source:** the City of Asheville's Accela permits view,
  `gis.ashevillenc.gov/server/rest/services/Permits/AccelaPermitsView/MapServer/2`,
  which puts each permit at a point. The 2026-08-28 pass
  (`.streams/city-asheville.md`) looked only at the City's ArcGIS Hub, which
  does not list it; the probe found it by walking the City server's folders.
- **Shape:** 66,072 rows on 2026-09-30, opened from 2014-01-02, one per
  permit: `record_id` (like `26-07120`) never repeats. The layer also carries
  each record's name, description, notes and comments, a licence number and a
  business name; the spec's `select` names eight other columns. Three rows
  carry a job value, none from the past year, so events carry no cost.
- **Freshness:** `date_opened` holds the day alone, stored as midnight
  Eastern (04:00Z in summer), though 18 of the 690 permits published in the
  live check carry it a second later. Late on Wednesday afternoon
  (2026-09-30) the newest permit was Tuesday's, and none is opened at
  weekends, so the layer looks refreshed overnight through the day before
  (inferred from one day). `expected_cadence_days` is 3, so the staleness
  alarm waits six days. The layer has no issue date, so both dates on an
  event are the day the permit was opened, and its status (`record_status`)
  says whether it has been issued.
- **A window, not a watermark:** a watermark on `date_opened` lands on
  04:00:01Z whenever one of the newest day's permits carries the extra
  second. The next poll's filter (`date_opened > timestamp '2026-09-29
  00:00:01'`) would then pass over any permit of that day that reached the
  layer later. So the server evaluates a 90-day window instead, and the
  cross-run dedup drops the permits already published. The host rejects ISO
  date literals, so it joins `ANSI_DATE_LITERAL_HOSTS` for a backfill's
  window; it reads timestamp literals in Eastern time.
- **Window:** `date_opened >= CURRENT_DATE - INTERVAL '90' DAY AND
  date_opened <= CURRENT_TIMESTAMP`, less right-of-way, temporary-event,
  outdoor-vendor and over-the-counter records and the home-occupation and
  occupational subtypes. The window held 697 permits on 2026-09-30, of the
  842 opened in those 90 days, and over the past year a 90-day window held
  727 (June to August 2026) to 1,047 (August to October 2025), so the cap is
  1,500.
- **Ids and order:** the permit number keys each event. The snapshot reads
  `date_opened DESC, objectid DESC`, which has no ties.
- **Placement:** each permit is a point (stored in State Plane feet; the
  client asks for WGS84). Seven of the window's 697 permits have no point,
  and `metro_clip` skips them, as it skips Scottsdale's unplaced requests;
  every other permit lies inside the metro box. No geocoder is asked.
- **Mapping:** the permit number, the opened date (as both the filing and
  the issue date), the subtype as the job type (then the record type), the
  status, the site address and the parcel number (`apn`). Subtypes name new
  buildings and demolitions, which map to new construction and demolition;
  the rest (`Existing Building`, `Accessory Structure`, `Trade`, `Site Work`
  and so on) map to minor alterations.
- **Poll:** every six hours, the whole window as a snapshot, in one page.
- **Live check:** first, the probe's incremental draft of the spec. Its
  first poll read the newest 1,000 permits, published 985 and left the
  watermark at `2026-09-29T04:00:01`, so its second poll asked for
  `date_opened > timestamp '2026-09-29 00:00:01'`. Then two polls of the
  registered spec through the real scheduler against the live layer, Kafka
  mocked. The first read 697 permits in two requests (the metadata and one
  page), skipped the 7 without a point and published 690, opened from
  2026-07-02 to 2026-09-29; none was dead-lettered and no permit repeated.
  63 are new buildings, 35 demolitions and 592 other work. By status, 312
  are issued, 109 wait on the applicant, 106 are in plan check, 50 are
  finaled, 40 are `CC Issued`, 17 newly received, 17 reissued, 14 revoked
  and 25 in other states. The second poll read the same 697 permits in one
  request and published none. Neither poll queried a geocoder.

### Allentown, PA — `permits`

- **Source:** the City's Tyler EnerGov building permits view,
  `services1.arcgis.com/WUqVDRuvIiIiH2Pl/arcgis/rest/services/EnerGov_Building_Permits_Current/FeatureServer/0`,
  on the same ArcGIS Online org as the parcel layer Allentown's deeds come
  from. It puts each permit at a point. Earlier passes read only that parcel
  layer; the probe found the permits by a keyword search of the org. The
  City's own GIS server holds reference layers and EnerGov's map service, no
  permits.
- **Shape:** 5,812 rows on 2026-09-30, issued from 2025-01-02, one per
  permit: `PERMITNUMBER` (like `COA-BP-2026-02658`) never repeats. The layer
  carries no names. Every permit in the window is a building permit
  (`TYPE`), and its class (`WORKCLASS`) says only residential (581) or
  commercial (238), not the work, so every event's job type is `OT` (minor
  alteration). It carries no cost.
- **Freshness:** `ISSUEDATE` holds the day at midnight UTC, though five of
  the window's 819 permits carry a time of day. The layer was reloaded at
  00:47Z on 2026-09-30 with permits through the day before, and its object
  ids look reassigned with each reload (the newest permits carry the
  lowest). No permit is issued at weekends, so `expected_cadence_days` is 3
  and the staleness alarm waits six days.
- **A window, not a watermark:** as with Asheville, one permit stamped with
  a time on the newest day would make the next watermark filter strict and
  pass over that day's later permits, so the server evaluates `ISSUEDATE >=
  CURRENT_DATE - INTERVAL '90' DAY AND ISSUEDATE <= CURRENT_TIMESTAMP` and
  the cross-run dedup drops the permits already published. The window held
  819 permits on 2026-09-30, and six 90-day windows since the layer begins
  held 737 to 1,016 (the most from April to June 2025), so the cap is 2,000.
- **Ids and order:** the permit number keys each event. The snapshot reads
  `ISSUEDATE DESC, PERMITNUMBER DESC`; the permit number, not the object id,
  breaks ties, since the object ids look reassigned with each reload.
- **Placement:** every permit is a point inside the metro box. No geocoder
  is asked.
- **Mapping:** the permit number, the issue date, the application date (127
  of the window's permits were applied for after their issue date), the
  class as the job type, the status, the site address, the ZIP code and the
  parcel number. The address is split across five columns (house number,
  direction, street name, street type and post-direction), which
  `compose_permit_address` in `cities/allentown.py` joins, as Cape Coral's
  and Henderson's do.
- **Poll:** every six hours, the whole window as a snapshot, in one page.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 819
  permits in two requests (the metadata and one page) and published all
  819, issued from 2026-07-02 to 2026-09-29, each with a composed address;
  none was dead-lettered and no permit repeated. By status, 627 are issued,
  183 complete and 9 in other states. The second poll read the same 819
  permits in one request and published none. Neither poll queried a
  geocoder.

### Allentown, PA — `311`

- **Source:** the requests residents file through the City's Survey123
  problem reporter, published as a public view,
  `services1.arcgis.com/WUqVDRuvIiIiH2Pl/arcgis/rest/services/311_Submission_Dashboard_View/FeatureServer/0`,
  on the same ArcGIS Online org as Allentown's permits and deeds layers. It
  puts each request at a point. The keyword search of the org that found the
  permits found it too. Allentown also appears on SeeClickFix, which was not
  probed.
- **Shape:** 713 rows on 2026-10-02, filed from 2025-10-17, one per request:
  `globalid` never repeats. The form stores the issue and the status as codes
  (`130245`, `1`) that only the layer's coded-value domains name ("Report a
  Pothole", "New Request"). Each issue belongs to one department, so the
  department column adds nothing. The layer has no closing date.
- **Personal data:** the form's address and cross street, the staff notes,
  the vegetation description and the contact flag stay on the server;
  `select` names five columns. Three of the 710 addresses on 2026-09-30
  contained an "@", and the one the probe saw was an e-mail address.
- **Freshness:** 266 requests in the 90 days to 2026-10-02, about three a
  day; the newest arrived at 02:55Z that morning. The longest quiet spell in
  the 90 days to 2026-09-30 was 2.1 days, so `expected_cadence_days` is 3 and
  the staleness alarm waits six days.
- **Watermark:** `CreationDate`, the time the layer received each request,
  so a request that arrives later never carries an earlier time. The stored
  watermark drops the milliseconds, so the strict filter reads the newest
  request again and the dedup drops it.
- **Decoding:** the ArcGIS client did not decode coded-value domains, so the
  spec sets a new `decode_domains`: the client reads the layer's domains with
  its metadata and replaces each coded value with its name, keeping a value
  the domain does not list (eight statuses read "Received", which the domain
  lacks). Every other ArcGIS feed reads its values as stored.
- **Placement:** 12 requests filed without a point sit at 0,0, and
  `metro_clip` skips them before the parser would dead-letter them. Every
  other request lies inside the metro box. No geocoder is asked.
- **Poll:** every 15 minutes, newest first by `CreationDate DESC, objectid
  DESC`; the default cap of 1,000 rows holds every request the layer has.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read all 713
  requests with the metadata and one page, which answered 503 once before
  the client's retry read it; it skipped the 12 at 0,0 and published 701,
  filed from 2025-10-17 to 2026-10-02; none was dead-lettered and no request
  repeated. By issue, 240 read "Other", 185
  potholes, 48 sidewalk issues, 46 street maintenance, 44 illegal dumping
  and 36 streetlights out, and 10 name no issue. By status, 461 are
  completed, 115 in progress, 72 referred, 41 new, 8 received and 4 open.
  The second poll sent `CreationDate > '2026-10-02T02:55:21'`, read the
  newest request again and published nothing. Neither poll queried a
  geocoder.

### New Haven, CT — `311`

- **Source:** the City runs its 311 service on SeeClickFix, which publishes
  the City's requests as a public view in its own ArcGIS Online org,
  `services8.arcgis.com/fz3KpsKgK9InMjh8/arcgis/rest/services/Public_SCF_Requests_New_Haven_CT/FeatureServer/0`.
  It puts each request at a point. Earlier passes found SeeClickFix's API
  restricted; the view sits in SeeClickFix's org, not the City's. The item
  dates from 2019 and 2020, and SeeClickFix created a per-issue view for the
  City under a newer process on 2026-04-08, so this one may be retired some
  day; it was live on 2026-10-02.
- **Shape:** 148,905 rows since 2007 on 2026-09-30, one per request:
  SeeClickFix's request `id` never repeats, and it keys each event rather
  than the view's object id, which a rebuild of the view would reassign.
  Every request in the 90 days to 2026-09-30 (3,536) was public and
  unmoderated; the spec filters on `private = '0'` so a private one stays
  on the server if it ever reaches the view.
- **Personal data:** the summary, description, address, assignee, photo
  links and page link stay on the server; `select` names six columns.
- **Freshness:** about forty requests a day (thirty-three a day in the week
  to 2026-10-02); the newest was twelve minutes old when the probe read the
  view on 2026-09-30. `expected_cadence_days` is 1.
- **Watermark:** `created_at`, the time the request was filed. Of the 500
  rows the view received last, two arrived after a request filed later
  than they were, by two minutes at most, so a poll that fell between them
  would pass over the earlier one; every registered `311` feed follows its
  filing time the same way.
- **Filters:** attribute filters only. A spatial filter or a whole-table
  distinct read on the view times out at about 55 seconds.
- **Placement:** every request is a point. 33 of the 1,000 newest lie south
  of the metro box (41.253 to 41.27 N, 72.89 to 72.90 W), on the City's
  Morris Cove shore, so the spec does not clip. No geocoder is asked.
- **Poll:** every 15 minutes, newest first by `created_at DESC, id DESC`,
  under the default cap of 1,000 rows, which reached back to 2026-09-01 on
  the first poll.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read and
  published 1,000 requests filed from 2026-09-01 to 2026-10-02, 547 of them
  with a closing date; none was dead-lettered and no request repeated. The
  first page timed out at 30 seconds and then answered 503 before the
  client's third try read it in 16 seconds; four later reads of a page took
  about a second each, so the view looks slow only when it has been idle.
  By category, 149 are missed trash or recycling, 143 illegal dumping, 107
  parking violations, 61 private property issues, 60 parks requests and 58
  tree requests. By status, 544 are closed, 252 accepted and 204 open. The
  second poll sent `(private = '0') AND created_at > '2026-10-02T02:55:34'`,
  read nothing and published nothing. Neither poll queried a geocoder.

## Held

| Metro (missing) | Source | Why held | Re-check when |
|---|---|---|---|
| Dayton (`deeds`) | The Montgomery County Auditor's `TaxParcelSales2025_public` layer (`services8.arcgis.com/O6MENQVX63Jn4008`, points): 24,274 sales from 2023-01-03, edited 2026-07-10, newest sale 2026-06-05, so the 90-day window was empty on 2026-09-30. The previous edition was edited on 2023-12-29. Its recorded date is empty on every row and the deed's book and page are two columns. The City's `DaytonParcel` layer fails every query, and its `Parcels_Join` sales table was loaded once, on 2025-04-06. | The last two editions came two and a half years apart, so a 90-day window would sit empty most of the time. | The Auditor republishes monthly or faster. |
| Oakland (`deeds`) | The Alameda County Assessor's `Assessor_Office_Ownership_Transfer_List` table (`services5.arcgis.com/ROBnTHSNjoZ2Wm1P`): 187,908 transfers from 2023-04-01 to the 2025-03-31 roll cut-off, edited 2025-07-07, unchanged since the 2026-08-24 check. The county's parcel layer dates each parcel's latest document but carries no price. | Published once a year and 18 months old. | The 2026 edition appears. |
| Omaha (`deeds`) | Nebraska's statewide parcel layer (`gis.ne.gov`, `StatewideParcelsExternal`) carries each Douglas County parcel's last sale, but it was loaded once, on 2026-01-01, and the newest non-future sale is 2025-12-02, so the 90-day window was empty. The county's own sales search answered 403 (Akamai) and was not asked again; the state's sales file needs a login. | Annual, and the window is empty. | NebraskaMAP loads more often, or the county opens a sales layer. |
| Anchorage (`311`) | The Anchorage Police Department's `APD_CampReports` layer (`services2.arcgis.com/Ce3DhLRthdwbHlfF`, points, edited 2026-09-30): 3,139 camp reports completed since 2026-01-01, 1,334 in 90 days, each with its own `CAMPID`. Its public report layer (3,739 rows) has no stable id. | Reports of camps and trash alone, from the police, not a service-request stream. Registered as the metro's `311`, they would mark Anchorage as covered where the Municipality publishes no requests. | The Municipality publishes its service requests. |
| Reno (`311`) | The Washoe County Sheriff's Office graffiti, dumping and abandoned-vehicle tracker (`AGOL_WCSO_Graffiti_Dumping_AbandonedVehicles4/FeatureServer/4`): 13,957 reports since 2013-08-15, 135 in 90 days (71 graffiti, 55 abandoned vehicles, 5 dumping, 4 encampments) across Reno, Sparks and unincorporated Washoe; ISO literals accepted. | Three issue types from the sheriff, about one and a half a day. Registered as the metro's `311`, they would mark Reno as covered where the City's own request system publishes nothing (its Reno Direct folder needs a token). | Reno Direct publishes its requests. |
| Roanoke (`permits`) | The City's `ROWPermitsPublic` layer (`maps.roanokeva.gov`, Transportation): 9,125 permits applied for since 2003, 146 in 90 days; water lines, utility poles, sewers, gas lines and hydrants. | Right-of-way utility and excavation permits, not building permits. Registered as the metro's permits, they would mark Roanoke as covered where the City publishes no building permits (its TRAKiT layers hold reference data, and its weekly permit PDFs stop in October 2022). | The City publishes building permits. |
| Burlington (`permits`) | The City's `OpenGov_Building` export (`services1.arcgis.com/1bO0c7PxQdsGidPK`): 141,701 permits with their own coordinates. Its newest update stamp is 2026-04-27, the layer was last edited on 2026-04-28, and it had not changed since the 2026-08-27 probe; the City's zoning and fire-marshal exports carry the same stamp. | Frozen for five months, so a window would sit empty. | The update stamp moves past 2026-04-27. |
| Providence (`permits`) | Public Works' `ENG_Permits_(view)` layer (`services6.arcgis.com/wv9mHoqblhTsnqdG`, layer 81): 12,750 road-opening and physical-alteration permits since 2022-04-14, 853 issued in 90 days; a permit number repeats across rows (6,637 distinct), and 85% of the 90-day rows fall inside the metro box. The building-permits export in the same org stops on 2023-12-14 and names applicants and contractors. | Right-of-way permits, not building permits. Registered as the metro's permits, they would mark Providence as covered where the City publishes no building permits (they live in OpenGov's ViewPoint Cloud). | The City publishes building permits. |
| Burlington (`311`) | The City's `SeeClickFix` export (`services1.arcgis.com/1bO0c7PxQdsGidPK`, points): 53,597 requests, the newest filed on 2026-04-26, the layer last edited on 2026-04-27. Its filing date is text ("4/26/2026 6:48 PM"). SeeClickFix itself is still the City's live system. | Frozen for five months, like the City's permits export. | The export moves past 2026-04-26. |
| Rochester (`311`) | The City's `311_Case_Data` layer (`services2.arcgis.com/yoz1ZtATTCokO9nU`): 51,721 cases filed from 2021-01-02 to 2022-02-07, data last edited on 2022-12-12, with no successor in the org. | Frozen since 2022. | A current requests layer appears. |
| Kansas City (`permits`) | Overland Park's `Building_Permits` layer (`services1.arcgis.com/YQsWDBr0DjMtoTQo`, a hosted layer last rebuilt on 2026-09-30): 13,824 permits over a rolling window from 2024-01-02, newest 2026-09-29, 429 in 30 days, ISO literals accepted, `CaseNumber` unique; 84% of recent rows carry a point and the rest an address. | It covers one suburb in Kansas, roughly a tenth of the metro's people, while the metro's `311` and licences are Kansas City, Missouri's. Registered as the metro's permits, it would mark Kansas City as covered where the City itself has none. | Kansas City, Missouri publishes current permits, or enough suburbs publish that the metro can take them together. |

## Not now

| Metro (missing) | Why not | Re-check when |
|---|---|---|
| Anchorage (`permits`) | The Municipality's permit activity reports are monthly PDFs, and its SmartGov hosted layers hold address points and parcels only; the one permits layer a title search of its ArcGIS Online org found (marijuana, 211 rows) stops on 2023-04-24. | A permits layer or extract appears. |
| Bridgeport (`permits`) | Permits live in Tyler EnerGov (the "Park City Portal"); the City's ArcGIS Online org (183 items) and Hub hold no permit layer, and `data.ct.gov` carries statewide counts only. | A permits layer appears. |
| Canton (`permits`) | Permits live in iWorQ (live since 2025-10-01). The Canton building folder on Stark County's server lists no anonymous services, and neither the City's nor the county's ArcGIS Online org holds a permit layer. | A permits layer appears. |
| Charleston, WV (`permits`, `311`) | The City GIS folders for the Building Commission and for QAlert (CWV311) need a token, and permits are PDFs and paper forms. The Kanawha County Assessor's server holds parcels, imagery and addresses only. | Either folder opens. |
| Dayton (`permits`) | The City's GIS holds only the code-complaint layer in its two Accela services and no permits in its Hansen, building-services, planning or viewer services. Permits live in Accela Citizen Access (`DAYTON`). | A permits layer appears on the City GIS. |
| Frederick (`permits`) | Neither the county's permitting portal nor the City's OpenGov portal has a feed. Maryland's "City of Frederick Issued Permits" dataset (`xrz3-9xhj`) stops in 2014, and the county server's planning and permitting services hold zoning and development pipelines, not issued permits. | A permits layer appears. |
| Honolulu (`permits`) | `data.honolulu.gov` `4vab-c87q` (432,021 rows) is an archive titled "through June 30, 2025" whose newest issue date is 2025-07-01. Nothing in the 72-dataset catalog or ArcGIS Online succeeds it. | A successor dataset appears. |
| Houston (`permits`) | The City's CKAN (99 datasets) publishes a monthly summary workbook, and its single- and multi-family extracts in ArcGIS Online end in 2024 (edited 2025-05-19). The permit web maps point at an unpublished `Permit_Viewer` (404). `cohegis.houstontx.gov` could not be reached (the egress proxy answered 502 twice). | A permits layer appears on the City GIS. |
| Indianapolis (`permits`) | `data.indy.gov` (651 datasets) and `gis.indy.gov` hold no permits, and the BNSDPW service needs a token. Permits live in Accela Citizen Access (`INDY`). | A permits dataset appears on either. |
| Kansas City (`permits`) | The City's Socrata permits (`ntw8-aacc`, 681,036 rows) stopped on 2025-05-09; its records link to the City's Tyler EnerGov portal, which has no public row API, and nothing newer is in the 202-dataset catalog. See Held for Overland Park. | A current extract appears on `data.kcmo.org`. |
| New Haven (`permits`) | Permits live in OpenGov's ViewPoint Cloud. An ArcGIS Online search for the City (322 hits) and the City's GIS account (144 items) found no permit layer, and `data.ct.gov` carries statewide counts only. The City's GIS server reset both connections and was not asked again. | A permits layer appears. |
| Oakland (`permits`) | No permits dataset among the 313 on `data.oaklandca.gov`, or on the Alameda County and Berkeley portals. Permits live in Accela Citizen Access (`OAKLAND`). | A permits dataset appears. |
| Omaha (`permits`) | Permits live in Accela Citizen Access (`OMAHA`). Douglas County's `Planning Wreck Permits` (demolitions only) stops on 2024-02-23, and MAPA's regional permits layer (51,978 rows) holds only new buildings over $25,000 and demolitions, updated yearly (newest 2025-12-31). | A permits layer appears on `dcgis.org`. |
| Oxnard–Ventura (`permits`) | Oxnard's Socrata `vmzx-48vx` stopped on 2024-12-03 and the domain now redirects to an OpenGov budget site with no row API. Ventura County's permitting service covers mining, oil and communication facilities only, and the City of Ventura publishes none. | A permits layer appears in either City's ArcGIS Online org. |
| Peoria (`permits`, `311`) | The City GIS (`gis.peoriagov.org`) holds reference layers only, its EnerGov map display among them, and no permit or request table; permits live in Tyler EnerGov, and Peoria Cares (`311`) runs on SeeClickFix. Peoria County's server holds parcels, sales and zoning. | A permits or requests layer appears on the City GIS. |
| Reno (`permits`) | Reno, Sparks and Washoe County permit through one Accela system (ONE Regional Licensing and Permitting) with no public layer. The City's `Permits_Issued` layer (463 rows) stops in September 2022, and the Washoe County Assessor's permit layers stop in 2019. | A permits layer or extract appears. |
| Richmond (`permits`, `311`) | The City's residential construction layer still needs a token (499, checked again on 2026-09-30) and the commercial one answers 400. For requests, the Socrata portal holds only a SeeClickFix sample from 2014 and 2015, and RVA311 publishes no extract. | The construction layers open or RVA311 publishes an extract. |
| Rochester (`permits`) | Permits live in Infor (since May 2023). The City's server (12 of its 39 folders walked) and ArcGIS Online org hold none, and its demolitions layer now needs a token. | A permits layer appears. |
| Santa Fe (`permits`) | The City and County ArcGIS Online orgs hold only parking-permit zones, and the permitting system was not identified. | A permits layer appears in either org. |
| Toledo (`permits`) | `gis.toledo.oh.gov` has no permits layer and ArcGIS Online has none for Toledo or Lucas County. `permits.toledo.oh.gov` answered one request with a 403 (CloudFront "Request blocked") and was not asked again. | A permits layer appears on the City GIS. |
| Tulsa (`permits`) | The Tulsa County Assessor's `Building_Permit` layer (6,154 rows, no address) ends on 2025-09-18. The City's server answers "Token Required" on every folder checked except `CustomerCare` (its 311). | The Assessor's layer moves past 2025-09-18 or the City opens a permits service. |
| Asheville (`311`) | The Asheville App runs on SeeClickFix, whose public API returns reporters and descriptions with no way to leave them out. The City server's old requests view is stopped ("MapServer not started"), and its Accela services view is code enforcement that stops in December 2018. | The City publishes a requests layer. |
| Bridgeport (`311`) | "Bridgeport 311" runs on SeeClickFix, and neither the City's ArcGIS Online org nor SeeClickFix's own org (where New Haven's view lives) holds a Bridgeport layer. | SeeClickFix publishes a view for the City. |
| Canton (`311`) | Requests run on SeeClickFix with no published layer; Canton Township's "Citizen Service Request" views are public but hold no rows. | SeeClickFix publishes a view for the City. |
| Frederick (`311`) | Frederick County's "FCG FixIT!" runs on SeeClickFix (since 2022) with no published layer, the City's "Report a Problem" is a web form, and Maryland's Socrata portal has no requests dataset. | SeeClickFix publishes a view for the county or City. |
| Providence (`311`) | PVD311 is a Power Apps portal with no public rows; the Socrata portal and the City's ArcGIS Online org (963 items) hold no requests, and SeeClickFix's Open311 feed for the City stopped in September 2021 when last checked (2026-08-27). | PVD311 publishes an extract. |
| Roanoke (`311`) | The City's QAlert layer (`QAlertIncidentsProd`) has the columns a `311` feed needs but returned no rows on 2026-08-28 or 2026-09-30. | The layer returns rows. |
| Honolulu (`deeds`) | No sales on `data.honolulu.gov` (72 datasets), the City's parcel layers, the state's parcel layer or the state's CKAN portal; the City's cadastral tables carry assessed values by tax year and no sale. Sales are searched one parcel or document at a time in qPublic and the Bureau of Conveyances. | A sales or conveyance dataset appears. |
| Indianapolis (`deeds`) | The City's parcel layers carry owners and assessed values but no sale; `data.indy.gov` (651 datasets) has only tax-sale and surplus reports, and the state's Gateway publishes annual assessment files, not sales disclosures. A statewide sales-disclosure layer on ArcGIS Online is a private compilation that names buyers and sellers and returned no Marion County rows. | The county or state publishes sales disclosures. |
| Oxnard–Ventura (`deeds`) | Ventura County's parcel layers carry only parcel numbers and coordinates, and no county server or ArcGIS Online item carries sales; California assessors do not publish prices. The Assessor's site answered with a "Request Rejected" page and was not asked again. | A sales or transfer layer appears. |
| Tulsa (`deeds`) | The Assessor's four ArcGIS Online services hold permits, parcel history, parcel-maintenance records and section shapes, none with a price. Deeds are the County Clerk's, in a paid Tyler recorder search. The Assessor's own ArcGIS Server could not be reached (the egress proxy answered 502 twice). | The Assessor's server can be reached and carries sales. |

A platform client would not unlock these cheaply: Accela Citizen Access
(Dayton, Indianapolis, Oakland, Omaha) is a search interface with no anonymous
bulk export, and the Tyler EnerGov portal behind Kansas City's permits has no
public row API either. Peoria's and Bridgeport's permits sit in Tyler EnerGov
too, and Reno's in the region's Accela; OpenGov's ViewPoint Cloud, which
holds New Haven's, Providence's and the City of Frederick's, was not probed. The same holds for deeds: Honolulu's and
Tulsa's sit behind one-record-at-a-time or paid recorder searches. For
`311`, SeeClickFix is the shared platform (Bridgeport, Canton, Frederick
County and Peoria, and behind Burlington's frozen export), and its public API
returns reporters and descriptions with no way to leave them out. The cheaper
route is the one New Haven's feed takes: SeeClickFix publishes public
ArcGIS views of some clients' requests in its own ArcGIS Online org, which
the existing ArcGIS client reads.
