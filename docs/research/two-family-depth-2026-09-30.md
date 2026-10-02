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

New Haven's requests come from SeeClickFix's own ArcGIS Online org, whose
service listing held 28 public views on 2026-10-02: request views for 22
places, a sandbox copy and a Survey123 form. Besides New Haven's, one covers
a registered metro that lacks requests: Lincoln's, a two-family metro with
`permits` and `sla`, which registers and gives Lincoln a third family. The
others cover metros that already have `311` (Tacoma's own, and suburbs in
the Denver, Kansas City, Seattle and San Francisco boxes), places whose
namesake metro is in another state (Salem, Massachusetts; Midland County,
Michigan), cities outside the nearest registered box (St. Petersburg beside
Tampa, Chapel Hill beside Durham, Fort Lauderdale beside Miami-Dade), and
places with no registered metro (Birmingham, Provo, Tuscaloosa, Clayton
County, Hilton Head Island, Jupiter and Moses Lake).

The 40 two-family metros with `permits` and `sla` were probed for `311` and
deeds on 2026-10-02 in four groups. The thirteen interior metros
(Albuquerque, Boise, Bozeman, Evansville, Fort Worth, Laredo, Las Cruces,
Missoula, Nampa, Sioux Falls, Topeka, Wichita and Worcester) ran live from
05:15Z to 06:14Z (curl default User-Agent, at least 2.2 seconds between
requests to a host on a clock shared with the other groups, no personal or
free-text column requested). Deeds were left out in New Mexico, Texas,
Montana, Idaho and Kansas, which do not disclose sale prices. Albuquerque's
and Topeka's `311` register, which gives each a third family; Missoula's
drainage reports and Worcester's work orders and parcel sales are held, and
the other gaps have no source.

The ten western metros (Anaheim, Aurora, Boulder, Fort Collins, Henderson,
Inland Empire, Portland, Salem, Vancouver and Yakima) ran from 05:00Z to
06:35Z under the same rules. Yakima's `311` and deeds register, which gives
Yakima all four families. The same host had stopped taking ISO date strings
since the 2026-08-28 probe, so every Yakima permits poll after the first was
failing; that is repaired here too. Deeds sources for Aurora, Boulder, Fort
Collins, Salem and Vancouver are checked separately.

The eight Florida metros (Cape Coral, Gainesville, Lakeland, Melbourne,
Ocala, Orlando, Port St. Lucie and Tampa) ran from 04:58Z to 06:56Z under the
same rules. Cape Coral's `311` and deeds register, which gives Cape Coral all
four families. The property appraisers' sales for Gainesville, Lakeland,
Ocala and Tampa are registrable too and follow separately, as does a repair
of Ocala's and Orlando's permits, which read the statewide cadastral layer
under other counties' numbers. Tampa's requests need a token, Gainesville's
stopped in 2023, and the other metros publish none. Nothing registrable
turned up for deeds in Melbourne, Orlando or Port St. Lucie: Brevard's and
St. Lucie's appraisers refused the probe (403), Orange County's server
answered some queries with a filter page, and Port St. Lucie's parcel copy
carries only the annual roll's sales.

The permits repair followed on 2026-10-02. The Department of Revenue
numbers Florida's counties alphabetically from Alachua at 11, so the codes
Ocala's and Orlando's specs sliced the statewide parcel layer by, 42 and 48,
are Jackson and Levy counties; Marion is 52 and Orange 58. The specs also
asked for the 2025 roll, which the layer no longer holds, and a year-built
cohort of parcels is not a permit stream in any case. Orlando now reads the
City's own permit applications, placed on the City's own address points,
and Ocala's permits are retracted: the City publishes none. The probe of
the nine south-eastern metros, written up with their registrations, found
Macon-Bibb's registered permits layer drawing every polygon in St.
Catharines, Ontario, so those permits are retracted too. Ocala and
Macon-Bibb keep their SNAP retailers and drop to one family.

The nine south-eastern metros (Augusta, Bowling Green, Columbus GA,
Greenville, Huntsville, Macon-Bibb, Savannah, Spartanburg and Wilmington NC)
ran from 05:00Z to 06:52Z under the same rules, with two sales layers read
again at about 09:00Z. Augusta's `311`, the open requests Cityworks
publishes, and Wilmington's deeds, New Hanover County's parcel points with
their latest sales, register, which gives each a third family. Augusta's own
sales are keyed months late, Greenville's had not moved in five weeks,
Spartanburg's carry no price, and Savannah's and Macon-Bibb's are annual
rolls, so those five are held; the other gaps have no source.

The Florida sales followed later on 2026-10-02. Tampa's, Gainesville's and
Ocala's register, which gives Tampa and Gainesville a third family and Ocala
a second. Lakeland's are held: Polk County's nightly sales file unpacks to
518 MB, and the CSV client reads a zip member whole, so the feed waits for a
streaming read.

Lakeland's sales followed the same day, once the CSV client read a zip member
as a stream instead of whole, which gives Lakeland a third family.

The western sales followed the same day. Vancouver's, Boulder's, Fort
Collins's and Salem's register, which gives each a third family: Clark
County's taxlots carry each parcel's latest sale, and the Boulder, Larimer
and Marion County assessors publish their sales as files that the polls
place on each county's parcel layer. Larimer's file is 101 MB, so the CSV
client now decodes a plain download as it reads it, and Larimer's parcel
layer pages only by the object-id field it types, which the ArcGIS client
now finds. Aurora's are held: Arapahoe County's parcels, which cover most of
the city, carry sales about eight weeks after their date, and Adams County's
daily table covers only the city's Adams side.

Worcester's work orders followed on 2026-10-02, which gives Worcester a third
family. Their table has no geometry, and each row's point is two columns of
Massachusetts State Plane feet; a spec can now declare such columns and their
coordinate system, and the scheduler converts each row's point before the
producer reads it. The tier counts from here on are in the one-family pass's
table ([one-family-depth-2026-10-02.md](one-family-depth-2026-10-02.md)).

| Tier (families) | Before (with #91) | With Charlotte's permits (#92) | With Charlotte's deeds (#93) | With Toledo's deeds (#94) | With Asheville's permits (#95) | With Allentown's permits (#96) | With Allentown's and New Haven's `311` (#97) | With Lincoln's `311` (#98) | With Albuquerque's and Topeka's `311` (#99) | With Yakima's `311` and deeds (#100) | With Cape Coral's `311` and deeds (#101) | With the wrong-place permits retracted (#102) | With Augusta's `311` and Wilmington's deeds (#103) | With Tampa's, Gainesville's and Ocala's deeds (#104) | With Lakeland's deeds (#105) | With the western deeds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 26 | 26 | **27** (Charlotte) | 27 | 27 | 27 | **28** (Allentown) | 28 | 28 | **29** (Yakima) | **30** (Cape Coral) | 30 | 30 | 30 | 30 | 30 |
| 3 | 29 | **30** (Charlotte) | 29 | **30** (Toledo) | **31** (Asheville) | **32** (Allentown) | 32 (New Haven in, Allentown up) | **33** (Lincoln) | **35** (Albuquerque, Topeka) | 35 | 35 | 35 | **37** (Augusta, Wilmington NC) | **39** (Tampa, Gainesville) | **40** (Lakeland) | **44** (Vancouver WA, Boulder, Fort Collins, Salem) |
| 2 | 68 | 67 | 67 | 66 | 65 | 64 | 63 | 62 | 60 | 59 | 58 | 56 | 54 | 53 (Ocala in, Tampa and Gainesville up) | 52 | 48 |
| 1 | 34 | 34 | 34 | 34 | 34 | 34 | 34 | 34 | 34 | 34 | 34 | **36** (Ocala, Macon-Bibb) | 36 | 35 | 35 | 35 |

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

### Lincoln, NE — `311`

- **Source:** the City's requests reach SeeClickFix, which publishes them as
  a public view in its own ArcGIS Online org, beside New Haven's:
  `services8.arcgis.com/fz3KpsKgK9InMjh8/arcgis/rest/services/SCF_Requests_Public_Lincoln_NE/FeatureServer/0`.
  It puts each request at a point. The 2026-08-30 probe found only the
  City's request form.
- **Shape:** 96,332 rows since 2011 on 2026-10-02, one per request: they
  carry 96,331 distinct ids, and the 11,858 requests filed in the year to
  2026-10-02 carry 11,858. Every request in the 90 days to 2026-10-02
  (4,211) was public and named the City of Lincoln as its agency; two were
  moderated. The spec filters on `private = '0'`, as New Haven's does.
- **Personal data:** the address, assignee, photo links, page link and the
  view's editing accounts stay on the server; `select` names seven columns.
  The view has no summary or description column.
- **Freshness:** forty to sixty requests a day from May to August and
  fifteen to twenty-eight from November to February (4,211 in the 90 days to
  2026-10-02). The longest quiet spell in the year to 2026-10-02 was 1.04
  days, from 2025-12-13 to 2025-12-14, so `expected_cadence_days` is 1.
- **Watermark:** `CreationDate`, the time the view received each request.
  Among the 1,000 rows it received last, those times follow the object ids
  without exception, while two rows arrived after a request filed 14 minutes
  later than they were, which a watermark on the filing time `created_at`
  could pass over. Half the requests reached the view within three seconds
  of filing, and the slowest took 15 minutes. The stored watermark drops the
  milliseconds, so each poll reads the newest request again and the dedup
  drops it.
- **Placement:** every request is a point. 977 of the 1,000 newest lie
  inside the metro box; 19 lie just south of it (40.69 to 40.72 N), three
  north-east of it (40.91 to 40.94 N) and one just east. They are all the
  City's requests, so the spec does not clip. No geocoder is asked.
- **Poll:** every 15 minutes, newest first by `CreationDate DESC, id DESC`,
  under the default cap of 1,000 rows, which reached back to 2026-09-04 on
  the first poll.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read and
  published 1,000 requests filed from 2026-09-04 to 2026-10-02, 685 of them
  closed, with the metadata and one page; none was dead-lettered and no
  request repeated. By category, 218 are tall grass or weeds, 140 tree
  issues, 82 "LTU General", 64 street issues other than potholes, 62
  potholes and 52 sidewalk repairs. By status, 685 are closed, 251 accepted,
  63 open and one in progress. The second poll sent `(private = '0') AND
  CreationDate > '2026-10-02T02:46:02'`, read the newest request again and
  published nothing. Neither poll queried a geocoder.

### Albuquerque, NM — `311`

- **Source:** the City's ABQ311 requests, joined to assessor parcels, on the
  City GIS server:
  `coageo.cabq.gov/cabqgeo/rest/services/CRM_Service_Requests_MIL1/MapServer/0`
  (ArcGIS Server 10.81; the FeatureServer twin needs a token). The
  2026-08-27 probe saw its queries time out. Those were unbounded queries,
  which still do not answer within 60 seconds; a query bounded by date
  answers in two to four.
- **Shape:** one row per request and parcel: 288,000 rows in the year to
  2026-10-02, about 790 a day. A request joined to several parcels repeats
  with the same `CRM_ID`: the 1,887 rows filed in the day to 06:13Z on
  2026-10-02 held 1,814 requests, one of them on 43 rows and two on 12.
  Events are keyed on `CRM_ID`, so the poll publishes each request once.
- **Window:** the spec reads at most the last day, `CREATEDTIME >=
  CURRENT_TIMESTAMP - INTERVAL '1' DAY`. The server's clock runs on local
  time, so the day is about 30 hours. `CREATEDTIME` holds real times in UTC
  and follows `CRM_ID` without exception among those 1,814 requests, and the
  server takes ISO literals, so the incremental filter needs no ANSI entry.
- **An unreadable row:** one request filed between 18:02:27Z and 18:02:48Z
  on 2026-09-30 cannot be read. A count over any window that holds it fails
  ("Failed to execute query."), and a row query over such a window returns
  no rows at all, with or without geometry: the 47 rows filed from 17:30Z up
  to it come back on their own, and none once the window runs past it.
  Quarterly counts over the rest of the year to 2026-10-02 all succeed, so
  it is the only such row in that year. A poll whose window held a row like
  it would read nothing until that row was more than a day old, and would
  then catch up on the day since.
- **Personal data:** the address, subject, description, notes, staff
  accounts, councillor's name and zoning inspector stay on the server;
  `select` names six columns.
- **Placement:** every request is a point. 1,823 of the 1,824 requests the
  first live poll published lie inside the metro box, and one lies just
  east of it; the spec does not clip. No geocoder is asked.
- **Poll:** every 15 minutes, newest first by `CREATEDTIME DESC, CRM_ID
  DESC`, with a 3,000-row cap so that a first poll reads the whole day
  (1,897 rows on 2026-10-02).
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 1,897 rows
  with the metadata and two pages and published 1,824 requests filed from
  00:30Z on 2026-10-01 to 06:13Z on 2026-10-02; the dedup dropped 73
  repeats, and none was dead-lettered. 1,491 are closed, 243 new, 89 pending
  and one updated. By type, 1,054 are missed trash pickups, 192 large-item
  pickups, 163 trash or recycling carts, 39 animal-welfare dispatches, 32
  commercial solid-waste requests and 31 solid-waste questions. The second
  poll sent `(CREATEDTIME >= CURRENT_TIMESTAMP - INTERVAL '1' DAY) AND
  CREATEDTIME > '2026-10-02T06:13:00'` and read nothing; a count of the
  requests filed after 06:13:00Z returned 0 two minutes later. Neither poll
  queried a geocoder.

### Topeka, KS — `311`

- **Source:** the `CityworksViews` folder on the City's ArcGIS server, which
  serves Topeka's permits, also serves the City's 311 requests as Cityworks
  holds them:
  `maps.topeka.gov/arcgis/rest/services/CityworksViews/SCF_E311_Requests/FeatureServer/0`
  (ArcGIS Server 11.5). The 2026-08-30 probe found 311 only as a Cityworks
  UI.
- **Shape:** 65,189 requests since 2013-09-10 on 2026-10-02, one point
  each; the 8,825 filed in the year to 2026-10-02 carry 8,825 `requestid`s.
  Half of the 2,925 filed in the 90 days to 2026-10-02 went to the code
  department (nuisance complaints and abandoned vehicles), the rest to
  streets, forestry, police, traffic, engineering and storm water. The view
  holds Cityworks service requests, whichever department takes them, so the
  spec keeps them all.
- **Personal data:** each request's description, details, address,
  initiator, assignee and Cityworks link stay on the server; `select` names
  eight columns.
- **Freshness:** about 24 requests a day: 8,825 in the year to 2026-10-02,
  from 396 in November 2025 to 1,296 in June 2026, with no day missing. The
  longest quiet spell was 0.89 days, so `expected_cadence_days` is 1.
- **Watermark:** `datetimeinit`, which holds real times in UTC (the layer
  declares UTC) and follows the view's object ids and request ids without
  exception over that year. The view answers 400 to an ISO literal
  (`datetimeinit > '2026-09-25T00:00:00'`) and takes `timestamp '...'`, so
  its path joins `ANSI_DATE_LITERAL_HOSTS`. The host cannot: the permits
  view there takes ISO strings and answers 400 to `date_issued > timestamp
  '2026-09-01 00:00:00'`.
- **Placement:** all 2,925 requests filed in the 90 days to 2026-10-02 lie
  inside the metro box, and the spec does not clip. No geocoder is asked.
- **Poll:** every 30 minutes, newest first by `datetimeinit DESC, ObjectId
  DESC`, under the default cap of 1,000 rows, which reached back to
  2026-08-26 on the first poll.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read and
  published 1,000 requests filed from 2026-08-26 to 2026-10-02 with the
  metadata and one page; none was dead-lettered. By problem code, 367 are
  nuisance complaints, 109 abandoned vehicles, 86 potholes, 79 tree limbs or
  brush, 35 police parking issues and 27 homeless encampments; 631 are
  closed, 319 open and 28 in progress. The second poll sent `datetimeinit >
  timestamp '2026-10-02 00:03:53'`, read the newest request again and
  published nothing. Neither poll queried a geocoder.

### Yakima, WA — `311`

- **Source:** the City's YakBack requests on the City GIS server that serves
  Yakima's permits:
  `gis.yakimawa.gov/arcgis/rest/services/YakBack/PublicRequest/MapServer/0`
  (ArcGIS Server 11.3). The 2026-08-28 probe found it but left it
  unregistered, because its `status` is an integer and the event takes text.
- **Shape:** one point per request over a rolling three years: 16,177 rows
  from 2023-10-01 on 2026-10-02, and 5,208 filed from 2025-10-01 to
  2026-10-02. `type` (13 values) and `status` (open, closed) are coded
  domains, which the spec reads as their names (`decode_domains`). One
  request appears twice, open and closed, and publishes once.
- **Freshness:** about 14 requests a day, with one day of that year without
  any. The longest quiet spell was 1.49 days, so `expected_cadence_days` is
  1.
- **Watermark:** `dateOpened`. Request ids follow it over that year except
  for two ids from an older series and one request entered six days late
  (opened 2026-06-12, numbered among 2026-06-19's), which a
  `dateOpened` watermark would pass over.
- **Literals and zone:** the layer answers 400 to an ISO literal and takes
  `timestamp '...'`. So does the permits layer on the host, which took ISO
  strings on 2026-08-28: its second poll sent `IssuedOnDate >=
  '2026-09-25T00:00:00'` and failed, as every permits poll after the first
  had been failing. The host joins `ANSI_DATE_LITERAL_HOSTS`. The 311 layer
  declares Pacific Standard Time without daylight saving, and literals are
  read in that fixed zone. Its values are local clock times, though, so
  from March to November they read an hour late: at 06:55Z on 2026-10-02
  the newest request read 07:50:33Z. The future guard keeps the watermark
  at the newest request already past, the next poll reads the newer one
  again, and the dedup drops it.
- **Personal data:** the requester's name, email and phone, the staff
  columns, the address, the description and the completion notes stay on
  the server; `select` names six columns.
- **Placement:** 1,242 of the 1,243 requests filed in the 90 days to
  2026-10-02 lie inside the metro box, and the other has no point, so it is
  dead-lettered. The spec does not clip. No geocoder is asked.
- **Poll:** every 30 minutes, newest first by `dateOpened DESC, requestId
  DESC`, under the default cap of 1,000 rows, which reached back to
  2026-07-22 on the first poll.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 1,000
  requests with the metadata and one page, published 999 filed from
  2026-07-22 to 2026-10-02, and dead-lettered the one without a point. By
  type, 261 are "Other", 205 parking, 120 blight or trash, 119 graffiti, 91
  animal complaints and 57 parks or trees; 863 are closed and 136 open. The
  watermark stayed at 05:49:39Z, and the second poll sent `dateOpened >
  timestamp '2026-10-01 21:49:39'`, read the 07:50:33Z request again and
  published nothing. The permits feed, polled twice the same way, read 1,000
  permits and then the four issued on 2026-09-25 again, with `IssuedOnDate
  >= timestamp '2026-09-25 00:00:00'`. No poll queried a geocoder.

### Yakima, WA — `deeds`

- **Source:** the Yakima County Assessor's parcels as the City GIS server
  publishes them:
  `gis.yakimawa.gov/arcgis/rest/services/Assessor/AssessorParcels/MapServer/1`
  (ArcGIS Server 11.3, 105,110 polygons), each with its latest sale: excise
  number, gross price, sale date and use code. The 2026-08-28 probe found
  only the county's own sales layers, which stop in 2016 and 2024.
- **Window:** `SALE_DATE` is text, month first and unpadded (`9/9/2026`). As
  text, `9/9/2026` sorts above `9/23/2026`, so no comparison reads a window,
  but the server casts the text (`CAST(SALE_DATE AS DATE)`) and answered the
  cast over every row. The snapshot reads the sales of the last 90 days: 453
  county-wide on 2026-10-02, dated 2026-07-06 to 2026-09-23. Sales reach the
  layer about nine days after they close: 2026-09-22 and 2026-09-23 had
  three each, and nothing later had arrived.
- **Rows:** a parcel with several owners repeats once per owner (one repeat
  in the window), and a sale can convey several parcels (the 208 sales
  published carry 192 excise numbers), so a row is its parcel, date and
  excise number. Every sale in the window has a price.
- **Personal data:** owner names, roles and shares, mailing addresses and
  the seller stay on the server; `select` names seven columns.
- **Placement:** the client takes each parcel's centroid. 208 of the 452
  distinct sales lie inside the metro box and the rest elsewhere in the
  county, so the spec clips to the box. No geocoder is asked.
- **Poll:** every six hours, by object id (the text dates cannot order the
  rows), under the default cap of 1,000 rows; the busiest three months of
  2026 held 594 sales county-wide.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 453 rows
  with the metadata and one page and published 208 sales dated 2026-07-06 to
  2026-09-23: 149 single-unit homes, 27 undeveloped lots and 10 two-to-four
  unit buildings among them. It dropped the repeat and the 244 sales outside
  the box and dead-lettered none. The second read the same 453 rows and
  published nothing. No event carried a party name, and neither poll queried
  a geocoder.

### Cape Coral, FL — `311`

- **Source:** the City's `311 Issues NonSpatial` table on the server that
  serves Cape Coral's permits:
  `capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/MapServer/4`
  (ArcGIS Server 11.5).
- **Shape:** one row per request since 2020-12-17 (110,827 rows), with
  WGS84 `X` and `Y` columns and no geometry. 6,953 were created in the 90
  days to 2026-10-02, about 77 a day, every one inside the metro box: the
  City's own requests, no Fort Myers or county rows. 435 of those rows
  repeat a request in every column the poll reads, so requests key on
  `Issue_id` and publish once.
- **Freshness:** the table is loaded in one overnight cut. The 2026-10-01 cut
  ended with a request created at 02:09 EDT, and at 09:05Z on 2026-10-02 no
  newer cut had landed, so `expected_cadence_days` is 2.
- **Watermark and zone:** `CreateDate`, real times of day. The table's dates
  are Eastern with daylight saving, and the host already takes ANSI
  literals for the permits, so the scheduler renders the watermark as an
  Eastern `timestamp '...'` literal.
- **Personal data:** the site address and its parts, the title and both
  free-text descriptions stay on the server; `select` names nine columns.
  The City's Hub item "311 Issues" points at a second copy, the
  `311Issues` point layer, which also names the requester and is not read.
- **Placement:** the table's own coordinates; the spec clips to the box,
  which skipped nothing in the live check. No geocoder is asked.
- **Poll:** every 30 minutes, newest first by `CreateDate DESC, OBJECTID
  DESC`, under the default cap of 1,000 rows, which reached back to
  2026-09-18 on the first poll.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live table, Kafka mocked. The first read 1,000 rows
  with the metadata and one page, published 942 requests created from
  2026-09-18 to 2026-10-01, and dropped 58 repeats; none was dead-lettered.
  By type, 300 go to Waste Pro, the City's hauler, 94 are stormwater
  maintenance, 63 code compliance questions, 59 swale drainage complaints
  and 49 code violations; 648 are closed, 288 open and 6 cancelled. The
  watermark stopped at 06:09:26Z, and the second poll sent `CreateDate >
  timestamp '2026-10-01 02:09:26'`, read the newest request again (its time
  runs past the second) and published nothing. No poll queried a geocoder.

### Cape Coral, FL — `deeds`

- **Source:** the Lee County Property Appraiser's parcels on the County's
  ArcGIS Online org:
  `services2.arcgis.com/LvWGAAhHwbCJ2GMP/arcgis/rest/services/Lee_County_Parcels/FeatureServer/0`
  (565,114 polygons, edited nightly at about 08:50Z), each with its latest
  sale: date, price, transaction code and instrument number. The three older
  sales on a row are never newer than the first.
- **Window:** the sales dated in the 90 days before each poll, county-wide:
  6,765 on 2026-10-02, dated 2026-07-05 to 2026-09-25. Every date is midnight
  Eastern. Sales reach the layer two to three weeks after their date, and
  the window re-reads them when they do. March to May 2026 held 11,253, so
  the cap is 17,000.
- **Rows:** one per parcel. An instrument can convey several parcels (the
  4,409 published carry 4,232 instrument numbers), so a row is its parcel,
  date and instrument. Every sale published has a price, and 4,385 are
  $10,000 or more.
- **Personal data:** the owner block, the mailing address and the legal
  description stay on the server; `select` names eight columns.
- **Placement:** each parcel's own `LATITUDE` and `LONGITUDE`. The spec
  clips to the metro box, which leaves out most of Lehigh Acres to the
  east, Bonita Springs to the south and the outer islands to the west. No
  geocoder is asked.
- **Poll:** every six hours, newest first by `S_1DATE DESC, OBJECTID DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 6,765 rows
  with the metadata and seven pages and published 4,409 sales: 1,855 in
  Cape Coral, 1,325 in Fort Myers, 428 in North Fort Myers, 224 in the part
  of Lehigh Acres inside the box and 185 in Estero. It skipped 2,356 outside
  the box and dead-lettered none. The second read the same 6,765 rows and
  published nothing. No event carried a party name, and neither poll
  queried a geocoder.

### Orlando, FL — `permits` (repaired)

- **Replaces:** the statewide cadastral layer under `ASMNT_YR = 2025 AND
  CO_NO = 48`, read once a year as a year-built cohort: Levy County's
  parcels, from a roll the layer no longer holds (it held only the 2026 roll
  on 2026-10-02).
- **Source:** the City's permit applications on its Socrata portal,
  `data.cityoforlando.net/resource/ryhf-m453` (1,111,255 applications,
  966,954 of them issued; rows updated 2026-10-01 19:30Z).
- **Shape:** one row per application, each with its own permit number. 6,977
  permits were issued in the 90 days to 2026-10-02, the newest on
  2026-09-23: 2,143 building, 1,522 electrical, 1,100 mechanical, 840
  plumbing, 682 engineering and 454 fire permits among them. Issue dates are
  whole days.
- **Freshness:** the newest issue date trailed the row update by eight days,
  so `expected_cadence_days` is 7 and the staleness alarm waits 14. A week of
  permits can therefore land at once; the seven working days to 2026-09-23
  issued 1,000.
- **Type:** the work type ahead of the application type ("New Building
  Permit", "Roof Building Permit"), joined on the server, so new buildings
  read as new construction and trade permits as trade work. The application
  type stands in when the work type is empty.
- **Personal data:** the property owner, parcel owner, contractor (name,
  address and phone), private provider and project name columns stay on the
  server; `select` names ten columns. The scheduler now forwards a Socrata
  spec's `select` as `$select`; it had forwarded `select` to ArcGIS and CARTO
  only.
- **Placement:** the rows carry no point (one of the 6,977 has one). Each
  permit takes the City's own address point for its address, from the
  "Orlando Addresses" layer
  (`services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/Address_Point/FeatureServer/22`,
  120,252 points, edited 2026-09-27) matched on `SitusAddress`, which held one
  point per matched address. The Census geocoder places the rest with
  `Orlando, FL`. On its own the geocoder placed 683 of the newest 1,000
  permits and missed whole new subdivisions: all 87 in Vista Park, all 38 in
  Southeastern Oaks and 51 of 72 in Lake Nona South. Where both placed a
  permit, the two points were a median 41 metres apart.
- **Poll:** hourly, newest first by `issue_permit_date DESC, :id`, issued
  permits only (`issue_permit_date IS NOT NULL`: Socrata sorts empty dates
  first). A newest-first poll never reaches rows past its cap, so the cap is
  3,000, three weeks of permits. The watermark is the issue date, compared
  with `>=`, so each poll re-reads the newest day and drops it as seen.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live table and address layer, Kafka mocked, with the
  geocoder answering from one Census batch request. The first read 3,000
  permits issued from 2026-08-20 to 2026-09-23 in three pages and published
  2,912: the address points placed 2,860 (51 requests to the layer) and the
  geocoder 52 of the 140 it was asked about. The 88 neither placed were
  dead-lettered; in a check of the newest 1,000, 19 of the 27 unplaced were at
  the airport. 121 of the 2,912 lie east of the metro box, in the City's
  south-eastern neighbourhoods (Meridian Park, Southeastern Oaks, Storey Park
  and Sunbridge). By type, 1,407 are trade permits, 1,307 minor alterations,
  142 new buildings and 41 demolitions. The second poll sent
  `issue_permit_date >= '2026-09-23T00:00:00'`, read that day's 166 permits
  again with four requests to the address layer, and published nothing. No
  event carried a name.

### Augusta, GA — `311`

- **Source:** the City's open service requests as Cityworks publishes them,
  listed in the City's ArcGIS Online org as "All Open SRs":
  `augcw.augustaga.gov/CityworksForms/gis/2/5799/rest/services/cw/FeatureServer/1`.
- **Shape:** one point per request since 2016-10-01: 12,471 open on
  2026-10-02 and none closed. A request leaves the layer when it closes, so
  no closure reaches the feed; statuses change in place until then. 2,855
  were created in the 90 days to 2026-10-02, 99% of them inside the metro
  box.
- **Filter:** `ProblemCode NOT LIKE 'LOCATE UTILITIES%' AND ProblemCode <>
  'Subpoenas' AND ProblemCode NOT LIKE 'C&M%'` leaves out the utility-locate
  tickets from excavators (about 820 of those 2,855), the subpoena queue (51)
  and the crews' daily start entries (30), and keeps 1,948.
- **Server:** it ignores `resultOffset`, takes the first `resultRecordCount`
  rows in the requested order before it applies the `where`, and flags every
  short page as truncated, though its metadata says it cannot page. The
  client read the flag as more to come and asked for the next page, which
  the server answered with the same rows, until its cap: a four-row poll
  would have taken 250 requests. The client now stops after one page on a
  layer that says it cannot page, so each poll is one request for the
  newest 1,000 rows of every kind (23 days on 2026-10-02), filtered on the
  server.
- **Watermark and zone:** `DateTimeInit`, true UTC instants. The server
  reads a zone-less literal as Eastern time and declares no zone: on
  2026-10-02 `DateTimeInit > '2026-10-01T20:04:15'` matched 7 of the 20
  requests created after 20:04:15 UTC, and the same instant written in
  Eastern time, or with a `Z`, matched all 20. The scheduler stores the
  watermark without a zone, so the client now lends the host's layers
  Eastern time (`LITERAL_TIME_ZONE_BY_HOST`), as a layer that declares its
  zone already gets.
- **Personal data:** the free text (details, comments and resolution), the
  staff who opened, closed or cancelled a request, and the problem address
  stay on the server; `select` names six columns. The server always adds
  `Description`, a one-to-one label of the problem code, and its own
  state-plane coordinates; the producer reads neither.
- **Placement:** each request's own point, which the server reprojects. The
  spec clips to the metro box. No geocoder is asked.
- **Poll:** every 30 minutes, newest first by `DateTimeInit DESC, REQUESTID
  DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked, after one metadata
  request. The first poll took one query, read 630 requests created from
  2026-09-08 to 2026-10-02 and published 628; the clip skipped 2, one of
  them more than 300 km south of the box, and none was dead-lettered. By
  type, 62 are mosquito complaints, 42 water leaks, 38 right-of-way
  complaints, 26 abandoned vehicles, 24 ditch complaints, 22 sinkholes and 22
  traffic signal faults; 386 are `INITIATE`, 104 `ASSIGNED` and 90
  `QAQCCOMPLETE`. The watermark stopped at 08:38:02Z, and the second poll,
  one query again, sent `DateTimeInit > '2026-10-02T04:38:02'`, read the
  newest request again (its time runs past the second) and published
  nothing. Without the zone it would have sent 08:38:02, which the server
  reads four hours late. No poll queried a geocoder.

### Wilmington, NC — `deeds`

- **Source:** New Hanover County's parcels as points on the County GIS server
  that serves Wilmington's permits:
  `gis.nhcgov.com/server/rest/services/Layers/PropertyPoints4326/MapServer/0`
  (ArcGIS Server 11.5, 115,880 points), each with its latest sale: date,
  price, instrument, deed book and page, and the municipality.
- **Window:** the sales dated in the 90 days before each poll: 2,401 on
  2026-10-02, dated 2026-07-05 to 2026-09-23. Dates and prices are text
  (`2026-09-11 00:00:00`); the server casts the dates, so the window is the
  `CAST(SALE_DATE AS DATE)` filter Yakima's deeds use, and its upper bound
  leaves out two sales dated 2029 and 3025. April to June 2026 held 2,898,
  so the cap is 4,500.
- **Rows:** one per parcel. A deed can convey several parcels, and its book
  and page repeat across them, so a row is its parcel and sale date. 1,349
  of the 2,401 carry a price. By instrument, 1,422 are `WD` (warranty
  deeds), 231 `QC`, 193 `SW`, 151 `OB`, 100 `EA` and 69 `NW`.
- **Freshness:** the layer carries no refresh stamp. On 2026-10-02 the
  newest sale was nine days old, its day held 16 sales against 35 to 41 on
  full days, and three reads over the County's night (05:33Z, 06:00Z and
  09:02Z) found the layer unchanged, so it is loaded less often than weekly.
  `expected_cadence_days` is 30, so the staleness alarm waits 60 days.
- **Personal data:** the owner, the owner's mailing address and the legal
  description stay on the server; `select` names six columns, and the layer
  is never read without it.
- **Placement:** each parcel's own point. All 2,401 lie inside the metro box,
  so the spec does not clip. No geocoder is asked.
- **Poll:** every six hours, newest first by `SALE_DATE DESC, OBJECTID DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 2,401 rows
  with the metadata and three pages and published all 2,401; by municipality
  code, 1,046 are `FD`, 1,024 `WM`, 183 `CB`, 72 `KB`, 56 `WB` and 20 `BD`.
  None was dead-lettered. The second read the same 2,401 and published
  nothing. No event carried a party name, and neither poll queried a
  geocoder.

### Tampa, FL — `deeds`

- **Source:** the City of Tampa's copy of the Hillsborough County Property
  Appraiser's parcels, on the server that serves Tampa's permits and
  licences:
  `arcgis.tampagov.net/arcgis/rest/services/Parcels/TaxParcel/FeatureServer/0`
  (531,613 polygons, the whole county), each with its latest sale's date and
  price. The Property Appraiser's own ArcGIS Online layer holds the same
  parcels, but its newest sale was a week older (2026-09-11 against
  2026-09-18).
- **Window:** the parcels whose sale falls in the 90 days before each poll,
  county-wide: 3,886 on 2026-10-02, dated 2026-07-06 to 2026-09-18. Every
  date is midnight UTC. Sales reach the layer three to four weeks after
  their date (the week to 2026-09-06 held 237 against 400 to 530 in the
  full weeks before it, and the two weeks after it 8), and the window
  re-reads them when they do. May to July 2026 held 6,441, so the cap is
  10,000.
- **Rows:** one per parcel, keyed on folio and sale date, so a parcel that
  sells again publishes again. Every sale in the window has a price, and
  3,882 of the 3,886 are $10,000 or more, so the layer appears to carry each
  parcel's latest qualified sale (inferred: it names no qualification code).
- **Freshness:** the layer carries no edit stamp. On 2026-10-02 its newest
  sale was 14 days old, and two reads 50 minutes apart found it unchanged.
  `expected_cadence_days` is 30, so the staleness alarm waits 60 days.
- **Personal data:** the owner, the mailing address, the trade name and the
  legal description stay on the server; `select` names four columns.
- **Placement:** each polygon's centroid, which the client computes. The spec
  clips to the metro box, which leaves out Plant City, Lithia, Wimauma,
  Ruskin and Sun City Center. No geocoder is asked.
- **Poll:** every six hours, newest first by `S_DATE DESC, OBJECTID DESC`;
  the object id orders a day's sales, which a date alone left free to
  repeat across pages.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 3,886 rows
  with the metadata and four pages and published 2,468 sales dated
  2026-07-06 to 2026-09-08; by division, 635 are in `BRANDON_EAST`, 620 in
  `CARROLLWOOD_NORTH`, 514 in `TAMPA_HEIGHTS_SEMINOLE`, 267 in
  `SOUTH_TAMPA_PALMA`, 168 in `DOWNTOWN_CHANNEL`, 157 in
  `WESTSHORE_INTERNATIONAL` and 107 in `HYDE_PARK_BAYSHORE`. It skipped
  1,418 outside the box and dead-lettered none. The second read the same
  3,886 rows in four pages and published nothing. No event carried a party
  name, and neither poll queried a geocoder.

### Gainesville, FL — `deeds`

- **Source:** the Alachua County Property Appraiser's nightly extract,
  `s3.amazonaws.com/acpa.cama/ACPA_CAMAData.zip` (73 MB, linked from the
  Property Appraiser's map site), rebuilt at 07:27 GMT on 2026-10-01 and
  again the next night. Of its thirteen members the feed reads only
  `Sales.txt` (59 MB unpacked): every recorded sale in the county, 510,529
  lines, one per parcel and sale, tab-delimited with a header and no party
  names.
- **Window:** the sales dated in the 90 days before each poll, county-wide:
  2,486 on 2026-10-02, dated 2026-07-04 to 2026-09-30. Dates are whole days,
  and sales arrive one to two weeks after their date. The upper bound keeps
  out one sale keyed for 2079-08-24. The busiest 90 days of the last two
  years, to 2025-08-26, held 3,484, so the cap is 6,000.
- **Rows:** a row is its parcel, date, book and page: 125 lines of the 2,486
  share a parcel and a date with another, and the file's line number
  renumbers a parcel's sales whenever it sells again. 2,090 carry a price
  above zero and 1,242 one of $10,000 or more. By deed type, 1,176 are `WD`
  (warranty deeds), 391 `MS`, 320 `SD`, 190 `QD`, 144 `DD` and 88 `OD`.
- **Freshness:** the extract's members share one build minute, and two
  nightly builds were seen in a row. `expected_cadence_days` is 7, since
  sales arrive a week or two late, so the staleness alarm waits 14 days.
- **Personal data:** `Sales.txt` holds no names, and `select` names seven of
  its eleven columns. The owner and legal-description members are never
  read, and the parcel join asks the parcel layer for `Prop_ID` alone,
  never its owner or mailing columns.
- **Placement:** each sale takes its parcel's centroid from the Property
  Appraiser's `PublicParcel` layer
  (`services.arcgis.com/cNo3jpluyt69V8Ek/arcgis/rest/services/PublicParcel/FeatureServer/0`),
  joined on `prop_id` in lists of at most 100. The spec clips to the metro
  box, which leaves out Newberry, High Springs, Alachua, Archer and
  Hawthorne. No geocoder is asked.
- **Poll:** once a day: one download, `Sales.txt` filtered and sorted newest
  first in memory, then the join.
- **CSV client:** a bare `CURRENT_DATE` now resolves to today, so a window
  can close at today; before, the client ignored it and the 2079 sale came
  through. And the client now decides whether a file opens with a one-cell
  title line from its first two rows instead of parsing all of them: on
  Alachua's file that parse added 572 MB to the poll's peak memory, and the
  whole read now adds 52 MB.
- **Deed types:** the extract pads its codes (`WD` and eight spaces), so the
  deeds producer now strips a mapped deed type.
- **Live check:** two polls of the registered spec through the real
  scheduler, Kafka mocked. The first downloaded the extract once, read 2,486
  sales, asked the parcel layer for the metadata and 25 lists of parcels,
  and published 1,556 sales dated 2026-07-06 to 2026-09-30: by division, 662
  in `NORTHWEST`, 459 in `SOUTHWEST_SOUTHEAST`, 308 in `DOWNTOWN_UF` and 127
  in `NORTHEAST`. It skipped 930
  outside the box, 10 of them on parcels the layer does not hold, and
  dead-lettered none. The second read the same 2,486 and published nothing.
  No event carried a party name, and neither poll queried a geocoder.

### Ocala, FL — `deeds`

- **Source:** the Marion County Property Appraiser's parcels on the City of
  Ocala's GIS server:
  `gis.ocalafl.org/arcgis/rest/services/Public/Parcels/FeatureServer/0`
  (ArcGIS Server 11.3, 290,085 polygons, "updated weekly from data provided
  by the Property Appraiser's office"), each with its latest sale: a year
  (`yr1`) and month (`mo1`) with no day, the official-records book and page,
  a price and the parcel's own point. The Property Appraiser's yearly sales
  files are dated by month too, carry no coordinates and name the owner, so
  the layer is the simpler read.
- **Window:** the server computes it from `yr1 * 12 + mo1`: the current month
  and the three before it, so on 2026-10-02 July to October, 7,472 sales.
  September, the month just ended, held about a third of a full month, since
  sales land two to three weeks late. The upper bound leaves out a sale
  keyed for November. April to June 2026 held 9,946, so the cap is 15,000.
- **Rows:** one per parcel, keyed on parcel, book and page. 51 polygons carry
  a sale but no parcel number, some sharing a book and page (`DETH` and
  `REGS`, `UNRE` and `INST`); they would publish under no parcel and key as
  one another, so the filter leaves them out. Every sale published has a
  price: 3,510 of the 6,365 are $10,000 or more, and 2,750 are $100 or
  less.
- **Dates:** `compose_deed_date` in the leaf dates each sale the first of
  its month, as Allentown's leaf does for its monthly sales.
- **Freshness:** the layer carries no edit stamp. A sale lands dated up to a
  month back, so `expected_cadence_days` is 45 and the staleness alarm waits
  90 days.
- **Personal data:** the owner's name and the mailing address stay on the
  server; `select` names nine columns.
- **Placement:** each parcel's own point. The spec clips to the metro box,
  which leaves out the far east and west of the county. No geocoder is
  asked.
- **Poll:** every six hours, newest first by `yr1 DESC, mo1 DESC, OBJECTID
  DESC`.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 7,472 rows
  with the metadata and eight pages and published 6,365 sales dated
  2026-07-01 to 2026-10-01, 6,138 of them in the `OCALA_CORE` division. It
  skipped 1,107 outside the box and dead-lettered none. The second read the
  same 7,472 rows and published nothing. No event carried a party name, and
  neither poll queried a geocoder.

### Lakeland, FL — `deeds`

- **Source:** the Polk County Property Appraiser's nightly extract,
  `www.polkflpa.gov/FTPPage/downloader.ashx?filename=ftp_sales.zip&dir=%5CAppraisalData%5C`
  (55 MB, listed on the Property Appraiser's bulk-data page). Its one member,
  `FTP_CAMA/ftp_sales.txt`, was rebuilt at 04:02 on 2026-10-02: every
  recorded sale in the county, 3,034,532 lines and 518 MB unpacked, one per
  parcel and sale, comma-separated and quoted with a header. Two of its
  fifteen columns name the grantor and grantee.
- **Window:** the sales dated in the 90 days before each poll, closed at
  today: 8,450 county-wide on 2026-10-02, dated 2026-07-04 to 2026-09-24,
  none in the future. Sales arrive one to several weeks after their date:
  the weeks of 2026-09-07 and 2026-09-14 held about 400 each, against 800 to
  1,000 a week in July and August.
- **Reach:** the filter first keeps the parcels numbered from `23` to `25`.
  A Polk parcel number starts with its range and township (`2328…` lies west
  of `2428…`, and `2429…` south of it), and on 2026-10-02 each of the 89,769
  parcels of the City's layer touching the metro box started `23`, `24` or
  `25`; the layer's 11,315 others lie north-west and east of the box. The
  parcel test runs before the date's, so the other rows skip the date parse,
  and the window holds 3,464 rows instead of 8,450: the join asks the City's
  server 66 times a poll instead of 166, and publishes the same 1,885 sales.
  The busiest 90 days in reach since October 2024, from 2025-02-17, held
  5,272, so the cap is 8,000.
- **Rows:** a row is its parcel, date, book and page: 222 lines of the 8,450
  share a parcel and a date with another, and a deed's book and page repeat
  across its parcels, but the four together repeat for none. The deed type is
  the extract's description; county-wide, 5,285 are warranty deeds, 1,235
  quit claims, 887 life estates and 490 miscellaneous documents. 968 lines
  carry no price and 4,897 one of $10,000 or more.
- **Freshness:** the bulk files share one nightly build, and the newest sale
  was eight days old. `expected_cadence_days` is 14, so the staleness alarm
  waits 28 days.
- **Personal data:** `select` names six of the fifteen columns: the grantor
  and grantee are parsed with each line and dropped before it is kept, and
  no spec maps them. The parcel join asks the City's layer for `PARCELID`
  alone.
- **Placement:** each sale takes its parcel's centroid from the City's
  parcel layer (`arcgis.lakelandgov.net/maps/rest/services/LandBase/Parcels/MapServer/10`,
  177,779 polygons over the city and the country around it), joined on
  `parcel_id` in lists of at most 51 (the client's URL limit for 18-digit
  quoted ids). The spec clips to the metro box. No geocoder is asked.
- **Poll:** once a day: one download, the member decompressed and filtered
  as it is read, the window sorted newest first in memory, then the join.
- **CSV client:** a zip member is now read as a stream: decompressed and
  decoded a megabyte at a time, in the encoding the whole member would have
  chosen (UTF-8, else cp1252, else UTF-8 with replacement characters, found
  in a first pass over the member), and handed to the parser a line at a
  time. Read whole, Polk's member added 1,041 MB to a read's peak memory;
  streamed, 6 MB. The title-line check reads the stream's first two rows and
  passes the rest on untouched, and the archive closes once its lines are
  read.
- **Live check:** two polls of the registered spec through the real
  scheduler, Kafka mocked. The first downloaded the extract once, read 3,464
  sales, asked the City's layer for its metadata and 66 lists of parcels,
  and published 1,885 sales dated 2026-07-06 to 2026-09-23, 592 of them in
  the `LAKELAND_CORE` division. It skipped 1,579 outside the box, 100 of
  them on parcels the layer does not hold, and dead-lettered none. The
  second read the same 3,464 and published nothing. An earlier pair of
  polls without the parcel filter read 8,450 rows, sent 166 lists and
  published the same 1,885. No event carried a party name, and no poll
  queried a geocoder.

### Vancouver, WA — `deeds`

- **Source:** Clark County's hosted taxlots,
  `services2.arcgis.com/ylxwjFBdCPBzP16d/arcgis/rest/services/TaxlotsforPublicUse/FeatureServer/0`
  ("Taxlots for Public Use"): 196,272 polygons, each with its latest sale's
  date, price and excise number. It carries the same rows and values as the
  County's own `ClarkView_Public/TaxlotsPublic` MapServer on
  `gis.clark.wa.gov`, whose portal item is titled "delete by 10122026". The
  2026-08-28 probe rejected Vancouver's deeds as a recorder web app; it had
  not noticed the sale columns on the taxlots.
- **Window:** the taxlots whose sale is dated in the 90 days before each
  poll, closed at the request's time: 1,637 county-wide on 2026-10-02,
  newest 2026-09-11, none in the future. Sales reach the layer four to eight
  weeks after their date: 1,218 in July, 518 in August and 8 in September,
  against 1,280 to 1,560 a month from March to June. Part of the dates carry
  a time of day, so the window runs on the server rather than on a watermark.
- **Reach:** the layer keeps only each taxlot's latest sale, so an older
  window loses the taxlots sold again since. The 90 days from 2026-04-01 held
  4,221, the most of the windows checked, so the cap is 6,000: three pages
  of 2,000.
- **Rows:** a row is its taxlot and sale date; a later sale of the taxlot
  changes the date and publishes anew. A sale over several taxlots shares its
  excise number, which is the event's id where it has one (39 of the 1,637
  have none and take the taxlot's). The layer carries no deed type, so each
  sale publishes as a DEED. 1,072 of the 1,637 carry a price.
- **Freshness:** the layer's publish stamp was 2026-09-27 and the newest sale
  21 days old. `expected_cadence_days` is 21, so the staleness alarm waits
  42 days.
- **Personal data:** `select` names six columns. The owner's id, the tax
  bill, the situs address and the legal description stay on the server.
- **Placement:** the client reduces each polygon to its centroid, and the
  spec clips to the metro box: a third of the county's sales lie north and
  east of it. No geocoder is asked.
- **Poll:** every six hours, newest first.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live layer, Kafka mocked. The first read 1,637 rows
  in three requests and published 1,113 sales dated 2026-07-06 to
  2026-09-04. It skipped 524 outside the box and dead-lettered none. The
  second read the same 1,637 and published nothing. No event carried a party
  name, and neither poll queried a geocoder.

### Boulder, CO — `deeds`

- **Source:** the Boulder County Assessor's "All Sales" file,
  `assessor.boco.solutions/ASR_PublicDataFiles/Sales.csv` (50 MB, listed on
  the Assessor's data-download page, which says the files are refreshed at
  4 a.m. daily). Every sale in the county by account: 752,371 rows on
  2026-10-02, in seven columns, none naming a party. The 2026-08-28 probe
  rejected the County's `PropSearch_SALES` table, which holds the same
  sales, for its future-dated rows and its dates the server would not
  filter.
- **Window:** the sales dated in the 90 days before each poll, closed at
  today: 1,806 county-wide on 2026-10-02. Eight rows are dated in the future,
  as far as 2057, and the bound keeps them out. The newest past sale was
  dated 2026-09-28, and the dates run dense to 2026-09-18: sales reach the
  file two to four weeks after their date.
- **Reach:** the busiest 90 days since October 2024, from 2025-02-24, held
  4,334, so the cap is 6,000.
- **Rows:** a row is its deed number and account. A deed over several
  accounts repeats its number, but the pair repeats for none. The deed type
  is the Assessor's code (`SW`, `WD`, `QD`, `BN`, `SJ`, `WJ` lead).
- **Freshness:** `expected_cadence_days` is 14, so the staleness alarm waits
  28 days.
- **Personal data:** the file names no party. The parcel join asks the
  County's parcel layer for `AccountNo` alone; its owner and mailing columns
  stay on the server.
- **Placement:** each sale takes its account's parcel centroid from
  `maps.bouldercounty.org/arcgis/rest/services/PARCELS/PARCELS_OWNER/MapServer/0`
  (140,985 polygons), joined on `strap`, which is the account number: the
  probe matched 1,605 of the window's 1,611 accounts, where three hosted
  parcel layers matched 24 to 29%. The spec clips to the metro box, which
  leaves out Longmont, Lafayette and the mountain towns. No geocoder is
  asked.
- **Poll:** once a day: one download, decoded and filtered a line at a time,
  the window sorted newest first in memory, then the join.
- **Live check:** two polls of the registered spec through the real
  scheduler, Kafka mocked. The first downloaded the file once, read 1,806
  sales, asked the parcel layer for its metadata and 22 lists of accounts,
  and published 715 sales dated 2026-07-05 to 2026-09-18. It skipped 1,091
  outside the box, 5 of them on accounts the layer does not hold, and
  dead-lettered none. The second read the same 1,806 and published nothing.
  Neither poll queried a geocoder.

### Fort Collins, CO — `deeds`

- **Source:** the Larimer County Assessor's public sales table,
  `storage.googleapis.com/lc-public/asr/assessor-public-sales.csv` (101 MB,
  listed on the Assessor's public data portal), rebuilt overnight: every sale
  in the county by account, 661,961 rows. Two of its eleven columns name the
  grantor and grantee.
- **Window:** the sales dated in the 90 days before each poll, closed at
  today: 2,597 county-wide on 2026-10-02, none in the future. The newest was
  dated 2026-09-08, 24 days earlier: 1,458 sales were dated in July, 1,190 in
  August and 97 in September. A fifth of the dates carry a time of day, so a
  sale dated today with a time waits for the next day's window.
- **Reach:** the busiest 90 days since October 2024, from 2025-03-31, held
  4,337, so the cap is 6,000.
- **Rows:** a row is its reception number and account. A deed over several
  accounts repeats its reception number, but the pair repeats for none. The
  deed type is the Assessor's description (special warranty deeds, quit
  claims and warranty deeds lead).
- **Freshness:** `expected_cadence_days` is 21, so the staleness alarm waits
  42 days.
- **Personal data:** `select` names seven of the eleven columns: the grantor
  and grantee are parsed with each line and dropped before it is kept, and
  no spec maps them. The parcel join asks the County's layer for `SCHEDNUM`
  alone; its owner names and mailing addresses stay on the server.
- **Placement:** each sale takes its account's parcel centroid from the
  County's "Tax Parcels" layer,
  `maps1.larimer.org/arcgis/rest/services/MapServices/Parcels/MapServer/3`
  (181,269 polygons), joined on the schedule number: the account without its
  letter, one parcel each. Condominium units share a parcel number, so a
  join on it would fetch every unit's polygon for each sale. The spec clips
  to the metro box. No geocoder is asked.
- **Poll:** once a day: one download, decoded and filtered a line at a time,
  the window sorted newest first in memory, then the join.
- **CSV client:** a plain download is now decoded as it is read, in the
  encoding `response.text` would have used and with the same replacement of
  undecodable bytes, and handed to the parser a line at a time. Read as
  `response.text`, Larimer's file added 385 MB to a read's peak memory: the
  text again, twice while httpx joined it. Decoded as it is read, 1 MB. The
  lines and the rows come out the same.
- **ArcGIS client:** Larimer's parcel layer names no object-id field, and its
  object ids are `OBJECTID_1`. The client ordered each page by `OBJECTID`, and
  the server answered 400 to the first. It now takes the field the layer
  types as its object id when it names none.
- **Live check:** two polls of the registered spec through the real
  scheduler, Kafka mocked. Before the ArcGIS fix both dead-lettered on that
  400. After it, the first downloaded the file once, read 2,597 sales, asked
  the parcel layer for its metadata and 30 lists of schedule numbers, and
  published 1,043 sales dated 2026-07-06 to 2026-09-07. It skipped 1,554
  outside the box, 11 of them on accounts the layer does not hold, and
  dead-lettered none. The second read the same 2,597 and published nothing.
  No event carried a party name, and neither poll queried a geocoder.

### Salem, OR — `deeds`

- **Source:** the Marion County Assessor's sales file for the year,
  `apps.co.marion.or.us/AO/PropertySalesData/2026SalesData.csv` (3.4 MB,
  listed on the Assessor's data center page, which says it is updated weekly
  by an automated process; it was rewritten at 06:00 UTC on 2026-10-02): 6,481
  lines, one per sale, account and situs. The last four of its 42 columns
  name the grantor and grantee and give their addresses.
- **Window:** the lines dated in the 90 days before each poll, closed at
  today: 1,544 on 2026-10-02. Three sales are dated in November and December
  2026, and the bound keeps them out. The newest past sale was dated
  2026-09-27, and the dates run dense to 2026-09-18: sales reach the file
  about two weeks after their date.
- **Reach:** the busiest 90 days since January 2025, from 2026-04-20, held
  3,092 (June 2026 alone held 1,719), so the cap is 5,000.
- **Rows:** a row is its sale and account. A sale repeats on a line for each
  situs and code area of an account: 342 of the 1,544 lines repeated a sale
  and an account, and publish once. The deed type is the file's description;
  a blank one publishes as a DEED.
- **Year files:** the spec maps 2026 and 2027 to their files and turns to
  the new one on 1 January. While the 2027 file is missing, the poll falls
  back to the 2026 file; once it exists, sales of late December 2026 posted
  after the turn are not read.
- **Freshness:** `expected_cadence_days` is 14, so the staleness alarm waits
  28 days.
- **Personal data:** `select` names six of the 42 columns. The grantor and
  grantee names and addresses and the situs address are parsed with each
  line and dropped before it is kept, and no spec maps them. The parcel join
  asks the Assessor's layer for `TAXLOT` alone.
- **Placement:** each sale takes its taxlot's centroid from the Assessor's
  `Parcels` layer
  (`services3.arcgis.com/SXXjryU22GsO8OEC/arcgis/rest/services/Parcels/FeatureServer/0`,
  115,385 polygons), joined on `map_taxlot`. The layer is an extract last
  edited on 2025-09-15, so taxlots created since then do not place: the probe
  matched 1,044 of the window's 1,111 taxlots. The spec clips to the metro
  box. West Salem lies in Polk County, which the file does not cover, and
  Polk's GIS answered HTTP 500 to the probe twice. No geocoder is asked.
- **Poll:** once a day: one download, decoded and filtered a line at a time,
  the window sorted newest first in memory, then the join.
- **Live check:** two polls of the registered spec through the real
  scheduler, Kafka mocked. The first downloaded the 2026 file once, read
  1,544 lines, asked the parcel layer for its metadata and 20 lists of
  taxlots, and published 666 sales dated 2026-07-06 to 2026-09-27. It
  skipped 733 lines outside the box, 77 of them on taxlots the layer does not
  hold, and 145 repeated lines inside it, and dead-lettered none. The second
  read the same 1,544 and published nothing. No event carried a party name,
  and neither poll queried a geocoder.

### Worcester, MA — `311`

- **Source:** the City's Customer Service Request System work orders, "CSRS
  Work Orders 2021 to Present" on the City's ArcGIS Online org, a hosted
  table:
  `services1.arcgis.com/j8dqo2DJE7mVUBU1/arcgis/rest/services/CsrsWorkOrders_TEST/FeatureServer/0`.
  The item says the table is updated weekly; it was last rebuilt at 10:30Z
  on 2026-10-02, with requests logged through 2026-09-30. Its licence lets
  the data be distributed freely.
- **Shape:** one row per request since 2021-01-01: 382,882 on 2026-10-02,
  15,926 logged in the 90 days before, each with its own id. 60% came by
  phone and 35% through SeeClickFix. The columns are the request id, the
  day and time logged, the street and cross street, the type (143 in the 90
  days), priority, status, source, the division it went to, whether and
  when it closed, and the point.
- **Point:** the table has no geometry. `X_Coordinate` and `Y_coordinate`
  are NAD83 Massachusetts Mainland State Plane, US survey feet (EPSG:2249):
  the probe's 398 newest rows converted to points from 42.227° to 42.335° N
  and 71.878° to 71.753° W, inside the city. The spec declares the
  coordinate system and the two columns (`state_plane_*`), and the
  scheduler converts each row's point before the producer reads it; a
  backfill does the same. Streets carry no house numbers, so nothing is
  geocoded.
- **Filter:** `X_Coordinate IS NOT NULL AND Y_coordinate IS NOT NULL AND
  Request_Type <> 'Water Mains / Street Light Mark Outs'`. 15 of the 15,926
  requests had no coordinates. 1,502 asked Water Engineering to mark out its
  mains and street light cables ahead of an excavation, 1,123 of them
  through SeeClickFix: contractors' notices, which Augusta's spec leaves out
  as utility-locate tickets. The other 14,414 are read. Requests from the
  City's own task forces and inspectors stay in: they report conditions in
  the street, from bulk items in the public way to street lights out.
- **Watermark:** `Date_Logged`, a date-only column the table writes as
  `2026-09-30`. A whole day keeps its boundary with `>=`, so each poll reads
  the newest day again and the dedup drops what it published. The table
  takes the scheduler's ISO literal on that column.
- **Reach:** the busiest 16 days of the year to 2026-09-30, from 2026-01-20,
  logged 6,660 requests besides mark-outs (the busiest day, 2026-01-27, 1,237
  of every kind). A poll reads newest first and stops at its cap, so the cap
  is 10,000, enough for a weekly update after a missed one. A first poll
  reads the newest 10,000, about nine weeks.
- **Freshness:** `expected_cadence_days` is 7, so the staleness alarm waits
  14 days.
- **Personal data:** the table holds no requester, contact or description
  columns. `select` names nine columns and leaves the street, cross street,
  source, priority and time of day on the server.
- **Placement:** each request's converted point. The spec does not clip:
  907 of the first poll's 10,000 lay at the city's north, east and south
  edges, past the metro box, and are kept, as Worcester's permits and
  licences keep theirs.
- **Poll:** every six hours, newest first by `Date_Logged DESC, ObjectId
  DESC`, in pages of 1,000.
- **Live check:** two polls of the registered spec through the real
  scheduler against the live table, Kafka mocked, from 18:20Z on
  2026-10-02. The first took a metadata request and ten pages, read 10,000
  requests logged from 2026-07-30 to 2026-09-30, converted every point and
  published all 10,000, with none dead-lettered. By type, 999 are the
  public works task force's bulk items in the public way, 784 parking
  enforcement, 574 the inspections task force, 539 trash bags not collected
  and 446 trash on private property; 5,965 are closed, 1,495 accepted and
  987 open, and 6,998 carry a closing day. The watermark stopped at
  2026-09-30, and the second poll, one request, sent `Date_Logged >=
  '2026-09-30T00:00:00'`, read that day's 200 requests again and published
  nothing. No poll queried a geocoder.
- **Other specs with State Plane columns:** four declared them already.
  Boston's licences carry no other coordinates, and the licence producer
  converted them itself with the same function, so their points do not
  change: a live poll converted 992 of 1,000 (8 have none). Aurora's permits
  and licences and Tempe's crime reports carry the columns beside their
  geometry, so only a row without geometry is converted, and Tempe's
  producer still reads a row's own latitude and longitude columns first.
  Such an Aurora row used to be dead-lettered (permits) or published without
  a point (licences). None of the newest 1,000 rows of each of the three
  feeds lacked geometry on 2026-10-02.

## Retracted

| Metro (feed) | What it read | Why retracted | Re-check when |
|---|---|---|---|
| Ocala (`permits`) | The statewide cadastral layer under `ASMNT_YR = 2025 AND CO_NO = 42`, read once a year as a year-built cohort (registered 2026-08-28). | 42 is Jackson County (Marion is 52, 286,275 parcels), the layer holds only the 2026 roll, and a parcel roll is not a permit stream. The only permit layer in the City GIS's public folder, "New Building Projects" (`gis.ocalafl.org`, `Public/GrowthManagement/FeatureServer/19`), holds 61 new commercial permits issued from 2025-09-04 to 2026-07-20. | The City or Marion County publishes its permits. |
| Macon-Bibb (`permits`) | `services6.arcgis.com/Yx1h0qHJ9wIpQWuU/arcgis/rest/services/Building_Permits_Public/FeatureServer/0` (registered 2026-08-28). | Its 21,930 polygons lie between 43.11° and 43.23° N and 79.32° and 79.18° W: the City of St. Catharines, Ontario's permits, none inside Macon's box. The County's own `BuildingPermits` layer (org `zPFLSOZ5HzUzzTQb`) was last edited on 2021-01-04, and its newest print date is 2017-02-21. | The County publishes current permits. |

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
| Missoula (`311`) | The City's "Report Drainage Issue" Survey123 layer (`services.arcgis.com/HfwHS0BxZBQ1E5DY/.../Illicit_Discharge/FeatureServer/0`): 329 reports since 2022-04-30, 34 in 90 days, each with a point and an arrival stamp. | One issue type, about twelve reports a month with bursts of what look like staff tests, on a layer the public can edit. Registered as the metro's `311`, it would mark Missoula as covered where the City publishes no request stream. | The City publishes its requests. |
| Worcester (`deeds`) | MassGIS's statewide parcels for Worcester (`TOWN_ID = 348`) carry each parcel's last sale: 47,703 parcels, the newest sale on 2026-04-17. | An annual assessor roll: no sale in the 90 days to 2026-10-02. | MassGIS loads Worcester more often. |
| Augusta (`deeds`) | The County's "All Sales" point layer (`gismap.augustaga.gov`, `Map_LayersTS/MapServer/404`, 111,717 rows) and its base `sales` table: sale key, date, price and parcel. The table is live (122 rows added between 06:56Z and 09:03Z on 2026-10-02, 114 of them dated April to June), and its newest sale was dated 2026-06-24. | Sales are keyed three to five months after they close, so the 90-day window was empty. | The newest sale comes within about a month of the poll. |
| Greenville (`deeds`) | The City's parcel layer (`citygis.greenvillesc.gov`, `GeneralData/GeneralData_WebMercator/MapServer/2`, 90,470 parcels) carries each parcel's latest deed date, price, and book and page: 1,188 sales in the 90 days to 2026-10-02, 897 of them inside the metro box. Its three sibling services publish the same table. | The newest sale was dated 2026-08-28, none fell in the last 30 days, and the layer has no edit stamp. | A newer sale appears. |
| Spartanburg (`deeds`) | Spartanburg County's `GIS/CAMA_Parcels` layer (`maps.spartanburgcounty.org`, 182,863 polygons): sale dates (2,072 in the 90 days to 2026-10-02, entered about six weeks late), deed book and page and the instrument number. | No row in the layer has a price, and no column names the document type. | A price or document type appears. |
| Savannah (`deeds`) | The Chatham County Board of Assessors' parcels (`pub.sagis.org`, `Savannah/PropertyValue/MapServer/13`, 127,033 rows) carry each parcel's sale price, year, month and day, and book and page. | An annual roll: every dated row was updated on 2026-06-22, and the newest 2026 sale is dated 2026-01-21. | The roll is updated more often. |
| Aurora (`deeds`) | Arapahoe County's `OpenDataService` parcel layer (`gis.arapahoegov.com`, 233,721 polygons) carries each parcel's latest sale: 1,232 in the 90 days to 2026-10-02, 1,026 of them inside the metro box, newest 2026-09-23. The Assessor posts sales about eight weeks after their date: 1,341 in July, 56 in August and 35 in September, against 1,500 to 1,700 a month in the spring. Its weekly transfer file runs as far behind and sits behind a click-through agreement. Adams County's `Property_Sales` table (`services3.arcgis.com/4PNQOtAivErR7nbT`) is loaded each business day, newest 2026-09-30, and joins to the County's parcels, but 18% of its sales lie in the metro box. No Douglas County source turned up. | A spec reads one source. Arapahoe's layer alone would report Aurora's sales two months after the fact and miss its Adams and Douglas sides; Adams's table alone covers only the city's northern part. | Arapahoe posts sales within a few weeks of their date, or a feed can read two counties. |
| Macon-Bibb (`deeds`) | The County's hosted CAMA layers (org `zPFLSOZ5HzUzzTQb`) carry each parcel's sale date and price. | Annual digests: the two 2025 layers' newest sales are dated 2024-12-06 and 2026-02-05. | A current digest or a sales layer appears. |

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
| Boise (`311`) | Requests go through departmental web forms with no published rows; the City's ArcGIS Online org (69 matching items) and Hub (88 datasets) hold inventories and police calls. | A requests layer appears. |
| Bozeman (`311`) | The City's ArcGIS Online org holds a daily-counts table (last edited 2025-01-22) and a 2019 pothole inventory; its Cityworks folder needs a token. | Cityworks requests are published. |
| Fort Worth (`311`) | MyFW runs on a vendor CRM with no public rows; `data.fortworthtexas.gov` holds ten datasets, none of them requests, and the City's `mapit` server holds code violations, crime and permits. | A requests dataset appears. |
| Laredo (`311`) | The CKAN portal's newest request slice (fiscal 2023–24, 37,468 rows) stops on 2024-06-26 and carries no location; only the 2014–2018 slice has coordinates. | A current slice with locations appears. |
| Las Cruces (`311`) | Requests run on Tyler Portico with no row API; the City's ArcGIS server holds permits, business registrations and code enforcement, and its ArcGIS Online org and Hub hold no request layer. | A requests layer appears. |
| Nampa (`311`) | Requests and code complaints go through a CivicPlus web form; the City's public map service holds 45 static layers. | A requests layer appears. |
| Wichita (`311`) | The City's app runs on SeeClickFix, and neither its ArcGIS server nor its ArcGIS Online org holds a request layer; its facility work orders are internal and the service is stopped. | SeeClickFix publishes a view for the City. |
| Sioux Falls (`311`, `deeds`) | Requests go through SeeClickFix, and the City's VUEWorks work orders are unpublished; the City GIS has pothole totals, code cases and police calls. South Dakota does not disclose sale prices: the City's parcel layer carries no sale, and the county GIS answered 403 and was not asked again. | SeeClickFix publishes a view for the City. |
| Evansville (`311`, `deeds`) | Requests reportedly run on SeeClickFix (not confirmed on a City page), and the City's ArcGIS Online org and Hub hold no request layer. The City-County GIS server answered "Could not access any server machines" four times from 05:46Z to 06:12Z, so its assessor sales layers, named in older web maps, could not be checked; the registered permits there fail with it. | The GIS server answers again. |
| Honolulu (`deeds`) | No sales on `data.honolulu.gov` (72 datasets), the City's parcel layers, the state's parcel layer or the state's CKAN portal; the City's cadastral tables carry assessed values by tax year and no sale. Sales are searched one parcel or document at a time in qPublic and the Bureau of Conveyances. | A sales or conveyance dataset appears. |
| Indianapolis (`deeds`) | The City's parcel layers carry owners and assessed values but no sale; `data.indy.gov` (651 datasets) has only tax-sale and surplus reports, and the state's Gateway publishes annual assessment files, not sales disclosures. A statewide sales-disclosure layer on ArcGIS Online is a private compilation that names buyers and sellers and returned no Marion County rows. | The county or state publishes sales disclosures. |
| Oxnard–Ventura (`deeds`) | Ventura County's parcel layers carry only parcel numbers and coordinates, and no county server or ArcGIS Online item carries sales; California assessors do not publish prices. The Assessor's site answered with a "Request Rejected" page and was not asked again. | A sales or transfer layer appears. |
| Tulsa (`deeds`) | The Assessor's four ArcGIS Online services hold permits, parcel history, parcel-maintenance records and section shapes, none with a price. Deeds are the County Clerk's, in a paid Tyler recorder search. The Assessor's own ArcGIS Server could not be reached (the egress proxy answered 502 twice). | The Assessor's server can be reached and carries sales. |
| Bowling Green (`311`, `deeds`) | City requests go through an in-house request form behind a login, and the code-case layer stopped on 2023-01-31. Warren County's parcel layer has prices and deed book and page but no sale date. | A requests layer or a dated sales column appears. |
| Columbus, GA (`311`, `deeds`) | Requests run on QAlert, whose folder on the City GIS holds reference layers only, and the City's 311 service is an address registry. The tax assessors' parcel layer has deed book and page but no sale date or price. | A requests or sales layer appears. |
| Greenville (`311`) | The City's request dashboards read hosts on its internal network, and its public "Greenville Cares" form layer refuses queries. | A requests layer opens. |
| Huntsville (`311`, `deeds`) | Requests run on Comcate, with no public rows, and the City's ArcGIS Online org holds no request or sales layer. The City's parcel layers carry values but no sale, and no Madison County GIS host resolved. | A requests or sales layer appears. |
| Macon-Bibb (`311`) | Requests run on SeeClickFix. The County's org holds exports last modified in April 2024 or earlier and one live debris layer on SeeClickFix's geoservice, which answered 503 at 05:33Z and 06:39Z. | SeeClickFix publishes a readable view for the County. |
| Savannah (`311`) | The City's OneView 311 services hold district polygons, the County's QAlert folder reference layers, and the open Cityworks work orders cover trees only. | A requests layer appears. |
| Spartanburg (`311`) | The County's EnerGov layer holds code enforcement, not requests, and neither the County's site nor ArcGIS Online shows a request platform. | A requests layer appears. |
| Wilmington, NC (`311`) | New Hanover County's 311 portal runs on Salesforce, and its two public web maps hold reference layers only; the City's GIS holds no request layer. | Either publishes its requests. |

A platform client would not unlock these cheaply: Accela Citizen Access
(Dayton, Indianapolis, Oakland, Omaha) is a search interface with no anonymous
bulk export, and the Tyler EnerGov portal behind Kansas City's permits has no
public row API either. Peoria's and Bridgeport's permits sit in Tyler EnerGov
too, and Reno's in the region's Accela; OpenGov's ViewPoint Cloud, which holds
New Haven's, Providence's and the City of Frederick's, was not probed. The
same holds for deeds: Honolulu's and Tulsa's sit behind one-record-at-a-time
or paid recorder searches. For `311`, SeeClickFix is the shared platform
(Bridgeport, Canton, Frederick County, Macon-Bibb, Peoria, Sioux Falls, Wichita and
probably Evansville, and behind Burlington's frozen export), and its public
API returns reporters and descriptions with no way to leave them out. The
cheaper route is the one New Haven's and Lincoln's feeds take: SeeClickFix
publishes public ArcGIS views of some clients' requests in its own ArcGIS
Online org, which the existing ArcGIS client reads.
