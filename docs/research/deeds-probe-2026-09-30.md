# Deeds for the metros one family short — 2026-09-30

On 2026-09-30, 22 metros had permits, 311 and licences but no deeds. Two
probes checked each one live the same day for a public, row-level record of
property transfers with a date, a price and a way to place it on the map.
Three registered first. Tempe followed later the same day from the Maricopa
County Assessor's parcel layer, with Chandler, Glendale and Scottsdale, which
gain deeds as a third family, and Phoenix, whose deeds move to the same layer.
Bend followed from Deschutes County's sales table, with a scheduler flag that
keeps a county-wide source's rows inside the metro box, and Medford from
Jackson County's sales layer, once the ArcGIS client could read that server's
responses. Tacoma followed from Pierce County's weekly sales file, once the
CSV client could read a file with no header row and the parcel join could
keep to the city's own parcels. Two are held and thirteen have none. Pierce
County, which had permits and licences only, then took deeds from Tacoma's
file across the whole county.

| Verdict | Metros |
|---|---|
| Registered here | Nashville, Hartford, Denver; then Tempe (with Chandler, Glendale, Scottsdale and a Phoenix repair); then Bend; then Medford; then Tacoma |
| Held | Minneapolis, San Diego |
| No source | Austin, Baton Rouge, Billings, Dallas, El Paso, Los Angeles, Louisville, Memphis, Montgomery AL, Sacramento, San Antonio, San Jose, St. Louis |

| Tier (families) | Before | After Denver, Hartford, Nashville | After Maricopa | After Bend | After Medford | After Tacoma | After Pierce County |
|---|---|---|---|---|---|---|---|
| 4 | 18 | 21 | 22 (Tempe) | 23 (Bend) | 24 (Medford) | 25 (Tacoma) | **26** (Scottsdale) |
| 3 | 33 | 30 | 32 (Chandler, Glendale, Scottsdale in; Tempe out) | 31 | 30 | 29 | 29 (Pierce County in; Scottsdale out) |
| 2 | 72 | 72 | 69 | 69 | 69 | 69 | 68 |
| 1 | 34 | 34 | 34 | 34 | 34 | 34 | 34 |

Phoenix already counted deeds, from a file that dead-lettered every row, so
its tier does not change. Scottsdale reached four families between the last
two columns, with its 311 (`four-family-depth-2026-09-30.md`).

## Registered

All of them read a parcel-level record of each parcel's most recent transfer,
filtered to transfers dated in the 90 days before each poll, and read that
window whole every six hours. Their record id joins the parcel, the transfer
date and the instrument, so a parcel's next sale is new to the snapshot and
an unchanged row is not re-published. A sale that reaches the source weeks
after its date is still inside the window when it arrives. None of them
requests an owner column or sends an address to the geocoder.

### Nashville — the parcel layer's last transfer

- **Source:** Metro Nashville's Hub "Parcels" layer,
  `services2.arcgis.com/HdTo6HJqh92wn4D8/.../Parcels_view/FeatureServer/0`
  (287,139 parcels), in the same ArcGIS org as the city's permits and 311
  layers. The publisher says it is updated daily; its edit stamp read
  2026-09-30 11:10Z.
- **Shape:** one row per parcel holding its last transfer. `OwnDate` is the
  transfer date: 0 to 7 days before the recording date written into
  `OwnInstr` on 197 of 199 sampled rows. `SalePrice` is the price, and
  `OwnInstr` is a two-letter instrument type, the recording date and a
  sequence. `Lat` and `Lon` are native and never null.
- **Window:** 4,373 transfers in the 90 days to 2026-09-30, 2,688 of them
  priced (quit claims are almost all $0). The newest two to three weeks are
  thin because transfers arrive late. One row is dated 2026-12-17, so the
  filter also stops at today.
- **Cap:** 7,000 rows.

### Hartford — the assessor's last sale, placed on its parcel

- **Source:** the city's CAMA property table,
  `utility.arcgis.com/.../HartfordOpenDataTables/FeatureServer/6` (28,453
  accounts), behind the same proxy base as the registered permits layer.
  `LastSaleDate` ran to 2026-09-22, with sales on every business day since
  mid-August except Labor Day.
- **Shape:** one row per account: `LastSaleDate`, `LastSalePrice`,
  `LastSalecode` (Valid Sale, Corr/Conveni, Plottage, Will and others) and
  `LegalRef` (book and page). The table has no geometry, so each sale takes
  the centroid of its parcel in the city's Parcels layer
  (`.../OpenData_Housing_Development/MapServer/11`), joined `ParcelNumber` to
  `PARCELNUMBER`. 200 of 200 sampled sales matched, and 353 of 353 in the
  live poll.
- **Mailing columns:** the table's `City`, `State` and `Zip10` are the
  owner's mailing address, not the property's. They stay off the request
  with the owner columns.
- **Rejected alternatives:** the state OPM sales set (`5mzw-sjtu`), which the
  2026-08-30 New England probe recommended, is published annually and ends
  on 2025-09-30. The city's own sales table (layer 5) stopped on 2026-01-09.
- **Cadence:** the service has no edit stamp, so `expected_cadence_days` is
  14 until a later read shows how often it loads.

### Denver — the parcel layer's last sale

- **Source:** the assessor's parcel layer,
  `services1.arcgis.com/zdB7qR0BtYrg0Xpl/.../ODC_PROP_PARCELS_A/FeatureServer/245`
  (240,430 parcels), which carries each parcel's last sale: `SALE_DATE`,
  `SALE_PRICE`, `RECEPTION_NUM` and `ASAL_INSTR` (warranty, special warranty,
  quit claim and so on).
- **Window:** 2,445 sales in the 90 days to 2026-09-30. Sales reach the layer
  four to six weeks after their date.
- **Why not the sales table:** the per-transfer table
  (`ODC_real_property_sales_and_transfers/FeatureServer/60`) keeps every
  transfer, but it has no geometry, and its `PARID` is a number that has lost
  `SCHEDNUM`'s leading zeros. 0 of 200 sampled sales matched a parcel as
  sent, and 198 of 200 once padded to 13 digits. The parcel join cannot pad
  a key, and the parcel layer's own fields need no join, so the table stays
  a candidate.
- **Cap:** 4,000 rows.

### Tempe, Chandler, Glendale, Scottsdale and Phoenix — the Assessor's latest deed

- **Source:** the Maricopa County Assessor's parcel layer,
  `gis.mcassessor.maricopa.gov/arcgis/rest/services/Parcels/MapServer/0`
  (ArcGIS Server 11.5), which carries each parcel's latest deed:
  `DEED_NUMBER`, `DEED_DATE`, `SALE_PRICE` and native `LATITUDE`/`LONGITUDE`.
  Its `JURISDICTION` column names the city, so each feed reads its own.
- **Window:** the filter is `JURISDICTION = '<city>' AND DEED_DATE >=
  CURRENT_DATE - INTERVAL '90' DAY AND DEED_DATE <= CURRENT_TIMESTAMP`, which
  the server evaluates itself. The upper bound keeps out 173 deeds in the five
  cities dated 2044 to 2099.
- **Dates:** the host answers 400 to an ISO date literal
  (`DEED_DATE > '2026-09-01T00:00:00'`) and accepts
  `timestamp '2026-09-01 00:00:00'`, so it joins `ANSI_DATE_LITERAL_HOSTS`.
  A snapshot poll sends no literal; a backfill with a start date does.
- **Price:** `SALE_PRICE` is text, filled where an affidavit was processed:
  3,772 of Phoenix's 9,224 deeds and 308 of Tempe's 783. A deed without one
  publishes with an amount of 0.
- **Freshness:** on 2026-09-30 the newest deed was dated 2026-09-22, and
  daily counts fall off after 2026-09-16, so the newest full day trails by
  about two weeks and the layer loads about weekly (inferred from the
  counts). `expected_cadence_days` is 14, so the alarm waits 28 days.
- **Several parcels, one deed:** 783 Tempe rows carry 761 deed numbers, and
  Phoenix's 9,224 carry 8,417. The record id joins `APN`, `DEED_DATE` and
  `DEED_NUMBER`, so each parcel's row publishes; PostGIS keeps one row per
  deed (see "Not covered here").
- **Owner columns:** `OWNER_NAME`, the `MAIL_*` block and `INCAREOF` stay off
  the request through `select`.
- **Phoenix:** its deeds read the Maricopa County Sales Affidavits file until
  now, a 61 MB zip of 903,301 affidavits that dead-lettered every row
  (`feed-health-2026-09-30.md`). The file's field map stays in the Phoenix
  module as a candidate. 33 of Phoenix's 9,224 deeds lie north of its metro
  box's 33.86° edge, at 33.87 to 33.89° N along I-17, and the layer puts them
  in Phoenix. They publish at their parcels; widening the box is left out of
  this change.
- **Caps:** Phoenix 15,000, Scottsdale 5,000, Chandler 3,000, Glendale 2,500
  and Tempe 2,000, each at least 1.5 times its window. Pages hold 1,000 rows,
  so the five take 18 requests a poll, about 72 a day.

### Bend — the county's sales, placed on their taxlots and kept to the box

- **Source:** Deschutes County's `GIS_SALES` table,
  `services1.arcgis.com/znO8Hz1SuVVohYhZ/.../Taxlots/FeatureServer/8`
  (109,474 rows, one per taxlot, each holding its two latest sales; `_1` is
  the newest). Its edit stamp read 2026-09-30 09:33Z, so it reloads
  overnight (one observation). The feed reads `Sales_Date_1`,
  `Total_Sales_Price_1`, `Book_Page_1` (the recording's year and number) and
  `Reject_Description_1`, the assessor's verdict on the sale (unconfirmed,
  grantor and grantee the same, related parties, new construction,
  confirmed), which becomes the event's `doc_type` as Hartford's sale code
  does.
- **Placement:** the table has no geometry, so each sale takes its taxlot's
  centroid from the county's taxlot polygons (`Taxlots/FeatureServer/0`),
  joined `Taxlot` to `TAXLOT`: 2,104 of the 2,105 sales in the window.
- **Only Bend's sales:** the table has no city column. The account table's
  `City` is the postal city, which puts 238 of 1,220 "BEND" sales outside
  the metro box, and its `UGB` column is empty. So the filter keeps the four
  township-ranges under the box: each of the 50,356 taxlots that touch the
  box starts with `1711`, `1712`, `1811` or `1812`, and 1,048 of the county's
  2,105 sales fall on them. A new `metro_clip` flag then skips each row whose
  placed point lies outside the box, or that the join could not place,
  before dedup and without dead-lettering it: 29 on 2026-09-30, leaving
  1,019.
- **Window:** the sales dated in the 90 days before each poll, up to now. The
  upper bound keeps out 38 sales in the county dated after today (the earlier
  probe saw years 2027, 2044 and 4004 among them).
- **Several taxlots, one sale:** 1,019 rows carry 943 recording numbers. The
  record id joins `Taxlot`, `Sales_Date_1` and `Book_Page_1`.
- **Party columns:** `Seller_1`, `Buyer_1`, `Seller_2` and `Buyer_2` stay off
  the request through `select`.
- **Freshness:** the newest sale was dated 2026-09-26, and daily counts taper
  after mid-September. `expected_cadence_days` is 7.
- **Cap:** 2,500 rows. A poll takes about 20 requests: two pages and the
  taxlot lookups, which the client batches about 60 to a query.

### Medford — the city's sales on the county's layer

- **Source:** Jackson County's `PropertySales` layer,
  `spatial.jacksoncountyor.gov/arcgis/rest/services/Demog/PropertySales/FeatureServer/0`
  (ArcGIS Server 10.91, 60,490 rows), which holds each account's latest sale
  on the account's taxlot polygon. The feed reads `SalesDate`, `SalesPrice`,
  `DocumentNumber` (the recording's year and number), `maptaxlot` and
  `DocumentTypeDescription` (warranty deed, bargain and sale, foreclosure),
  which becomes the event's `doc_type`.
- **Only Medford's sales:** `SiteCity` tells the city (`MEDFORD`, 304 sales
  in 90 days) from the unincorporated land with Medford addresses
  (`MEDFORD/COUNTY`, 44). The filter keeps `MEDFORD`, the area the city's
  permits, 311 cases and licences cover. 303 of the 304 lie inside the metro
  box; one vacant lot sits about 25 metres east of its edge and publishes, as
  Phoenix's deeds north of its box do.
- **Placement:** the client takes each polygon's centroid (`outSR=4326`), so
  there is no join and no geocoder query. One account had no polygon and
  publishes without coordinates.
- **Reading the server:** every response carries `Content-Security-Policy :
  frame-ancestors ...`, with a space before the colon. httpx's parser (h11)
  rejects the line, and the standard library's reader stops at it and loses
  the headers after it, `Content-Length` among them. The ArcGIS client now
  sends requests to the hosts in `TOLERANT_HEADER_HOSTS` through the standard
  library with a reader that drops that space (`src/producers/tolerant_http.py`)
  and hands back ordinary httpx responses. The staleness probe's metadata
  request goes the same way. The county's portal host
  (`jcportal.jacksoncountyor.gov`) sends the header well formed, but its
  taxlot layer carries no sales.
- **Window:** the sales dated in the 90 days before each poll, up to now. The
  upper bound keeps out 9 county sales dated after today (one reads 2621).
- **Dates:** the server answers 400 to `SalesDate >= '2026-09-01T00:00:00'`
  and accepts `timestamp '2026-09-01 00:00:00'`, so it joins
  `ANSI_DATE_LITERAL_HOSTS`. A snapshot poll sends no literal; a backfill
  with a start date does.
- **Several accounts, one sale:** 304 rows carry 291 document numbers. The
  record id joins `AccountId`, `SalesDate` and `DocumentNumber`.
- **Party columns:** `Grantor`, `Grantee` and `DocumentURL` (a link to the
  recorded deed) stay off the request through `select`.
- **Freshness:** the newest sale was dated 2026-09-25, five days before the
  probe. `expected_cadence_days` is 7.
- **Cap:** the default 1,000 rows, more than three times the window. The
  first poll in a process takes two requests (the layer's metadata, then one
  page) and each later poll one.

### Tacoma — the county's sales file, placed on the city's parcels

- **Source:** the Pierce County Assessor-Treasurer's data mart,
  `online.co.pierce.wa.us/datamart/sale.zip` (20.8 MB). The county's Data
  Downloads page says the mart's files are updated weekly; every file in the
  2026-09-25 build, which this note reads, is stamped 01:00 Pacific that
  Friday. Its `sale.txt` lists every sale in the county since
  1997-01-01, a line for each parcel a sale covers (646,457 lines, 89 MB),
  pipe-delimited with no header row; the Assessor-Treasurer's layout sheet
  names the 13 columns. Unlike the other sources here it lists every sale,
  not each parcel's latest, and the feed reads it once a day. It reads
  `ETN` (the excise tax number the Auditor issues at recording), `Parcel
  Number`, `Sale Date`, `Sale Price` and `Deed Type` (statutory warranty
  deed, bargain and sale, trustee's deed), which becomes the event's
  `doc_type`.
- **Reading the file:** the CSV client now takes a spec's `columns` for a
  file with no header row, so the first line is read as a sale. It also
  splits lines itself instead of through `io.StringIO`, which held four
  bytes a character: parsing this file peaked at 339 MB instead of 510 MB
  (tracemalloc), about 15 seconds a poll.
- **Placement:** each sale takes its parcel's centroid from the county's
  `Tax_Parcels` layer
  (`services2.arcgis.com/1UvBaQ5y1ubjUPmd/.../Tax_Parcels/FeatureServer/0`),
  joined `Parcel Number` to `TaxParcelNumber`: 2,314 of the window's 2,428
  parcels matched. Most of the rest are mobile homes and leaseholds, which
  have no parcel polygon of their own.
- **Only Tacoma's sales:** neither the file nor the layer names a city, but
  the layer's `Tax_Area_Code` tells it. Of the 75,908 parcels whose label
  point lies inside the City's limits (`Tacoma_City_Limits` on the City's
  ArcGIS Online org), 75,859 carry one of seven codes (005, 006, 010, 011,
  015, 025, 026), 47 carry 0 and two sit on the boundary; the four parcels
  with those seven codes outside the limits are each within 80 metres of it.
  The parcel join gains a `where`, so the layer places a sale only on a
  parcel with one of those codes, and `metro_clip` skips every sale left
  unplaced. The box alone would have kept 232 sales outside the city, a
  third of the 688 it holds: 82 on unincorporated land, 77 in Lakewood, 49
  in University Place, 19 in Fircrest and 5 in Ruston (label points in the
  county's `Cities_in_Pierce_County` polygons). The clip also skips the
  city's sales past the box's edges, 20 of 472: 11 to the east, around
  Northeast Tacoma and the port, and 9 to the west, along the Narrows.
- **Window:** the sales dated in the 90 days before each poll. No sale in the
  file is dated after its build, so there is no upper bound.
- **Several parcels, one sale:** 452 rows carry 440 excise tax numbers. The
  record id joins `ETN` and `Parcel Number`, the layout's primary key, which
  no two of the 646,457 lines share.
- **Party columns:** every line names the grantor and the grantee, and a
  file cannot leave columns on the server. The spec names them in `columns`
  and leaves them out of `select`, so the client drops them from each row as
  it reads it and no row the scheduler handles carries them.
- **Freshness:** a sale reaches the file four to five weeks after its date.
  In the 2026-09-25 build, the week to 2026-08-26 holds 219 sales against
  268 to 370 in earlier weeks, and seven are dated later (the newest
  2026-09-11). A sale stays in the window for about eight weeks after it
  arrives. `expected_cadence_days` is 7, the build's cadence: the staleness
  probe reads the file's `Last-Modified`, since its row check does not open
  a zip member.
- **Cap:** 5,000 rows, twice the county's window. A poll takes one download
  and about 35 requests to the parcel layer: its metadata once, then the
  lookups, about 70 quoted parcel numbers to a query.

### Pierce County — Tacoma's file, the whole county

Pierce County had permits and licences but no 311 or deeds, so it sits two
families short and outside the 22 above. Its deeds come from the same file.

- **Source:** the `sale.zip` Tacoma reads, read the same way: the lines dated
  in the 90 days before each poll, the parties dropped as each line is read,
  the record id joining `ETN` and `Parcel Number`, once a day with a
  5,000-row cap. One setting declares the file for both feeds.
- **Placement:** Pierce County's metro is the county. Its box spans it, and
  its submarkets run from downtown Tacoma to Gig Harbor, Puyallup and Graham.
  So the parcel join has no `where`: each sale takes its parcel's centroid
  wherever the `Tax_Parcels` layer has one. On 2026-09-30 the layer placed
  2,317 of the window's 2,432 lines, all inside the box (latitudes 46.74 to
  47.40, longitudes -122.84 to -121.53), and `metro_clip` skipped the 115 it
  could not place, mostly mobile homes and leaseholds.
- **Overlap with Tacoma:** 688 of the placed sales lie inside Tacoma's box,
  and the 452 that Tacoma publishes publish under Pierce County as well, as
  the county's box holds the city. Record ids carry each job's name and each
  snapshot job keeps its own seen-set, so neither feed skips the other's
  rows.
- **What publishes:** 2,317 sales dated 2026-07-02 to 2026-09-11, every one
  priced, under 2,156 excise tax numbers. Among them are 2,135 statutory
  warranty deeds, 75 bargain and sale deeds, 38 trustee's deeds after
  foreclosure, 26 quit claims, 13 special warranty deeds, 10 easements and 6
  sheriff's deeds.
- **Cost:** a second download of the 20.8 MB file each day, and about 35
  requests a poll to the parcel layer, as for Tacoma.

## Held

- **Minneapolis:** Hennepin County's parcel layer
  (`gis.hennepin.us/.../LAND_PROPERTY/MapServer/1`) carries each parcel's last
  sale with native coordinates, but its `SALE_DATE` is a month (`YYYYMM`), it
  is compiled monthly, and the newest month is about half complete at each
  compile. The city's own sales table ends on 2025-09-30.
- **San Diego:** the SANDAG parcel layer
  (`geo.sandag.org/server/rest/services/Hosted/Parcels/FeatureServer/0`)
  carries the recorded document that created each parcel's current record,
  with its date and type, but no price, and it publishes monthly about five
  weeks behind. Its `docdate` is `MMDDYY` text, which does not sort.

## No source

| Metro | Why not |
|---|---|
| Austin, Dallas, El Paso, San Antonio | Texas does not disclose sale prices. The appraisal districts publish annual rolls, the parcel layers carry no deed fields (Travis County's one deed layer covers 737 county-owned parcels), and the county clerks are search forms. `traviscad.org`, `gis.elpasotexas.gov` and `epcad.org` answered 403 and were not retried, so El Paso rests on its earlier note (`south-central-city-candidates.md`). |
| Baton Rouge | The parish tax roll (`myfc-nh6n`) is annual with no price, and its `transfer_date` is nearly empty for 2025. The clerk's records are a paid subscription, and the assessor's site answered 403. |
| Billings | Montana does not disclose sale prices, and no city, county or state layer has a sale column. |
| Los Angeles | The Assessor's `pais_sales_parcels` layer has sales with prices but stopped on 2024-06-05. The roll tables are annual, and the city's Measure ULA table has only a ZIP code and a month. |
| Louisville | The PVA's land-sales layer is maintained but lists vacant land only (13 sales in 90 days). `Urban_Parcels` transfers end on 2024-01-18. |
| Memphis | Neither the city Hub nor its ArcGIS org has a sales layer. The Register of Deeds is a search form, and two Shelby County hosts answered 403. |
| Montgomery, AL | The city's parcel layer has instrument columns that are all empty and no price. The county's parcel services need a token. |
| Sacramento | The county parcel layer has no sale fields, and the Assessor treats sales data as confidential. |
| San Jose | Santa Clara County sells its transfer list and recorder index; nothing is open. |
| St. Louis | `prclsale.zip` is re-stamped daily, but its newest sale is 2024-11-25, and the city's parcel points end on the same date. |

## Earlier notes this changes

- **Nashville:** the 2026-08-25 coverage sweep matched catalog titles only
  and recorded deeds as absent; the Parcels layer carries them.
- **Denver:** `wave-3-feed-expansion.md` §7 (NO-GO) looked for a join from
  the sales table; the parcel layer needs none.
- **Hartford:** the New England probe's statewide recommendation does not
  hold (annual, ends 2025-09-30), and the column is `daterecorded`, not
  `date_recorded`.
- **Tempe, Bend, Medford and Tacoma:** the earlier notes
  (`.streams/west-tempe.md`, `west-bend.md` and `west-medford.md`, and the
  2026-08-30 Pacific Northwest probe for Tacoma) found no source; each has
  one (above).
- **Phoenix:** `probe-maricopa-sales-affidavits.md` chose the affidavits
  file, and `wave-3-probe-phoenix.md` read the Assessor's host only through
  its scale-restricted `MaricopaDynamicQueryService` layers. The `Parcels`
  service on the same host answers row queries and carries the latest deed.
- **St. Louis:** the 2026-08-27 note counted 192,504 rows to 2026-02-11; the
  file now holds 94,276 rows ending 2024-11-25.

## Live check

Each spec was polled twice through the real scheduler against the live
source on 2026-09-30, with Kafka mocked.

| Feed | Fetched | Published | Placed in the metro box | DLQ | Dates | Priced | Second poll |
|---|---|---|---|---|---|---|---|
| Nashville `deeds` | 4,373 | 4,373 | 4,373 | 0 | 2026-07-02 to 2026-09-26 | 2,688 | 0 new of 4,373 |
| Hartford `deeds` | 353 | 353 | 353 | 0 | 2026-07-06 to 2026-09-22 | 268 | 0 new of 353 |
| Denver `deeds` | 2,445 | 2,445 | 2,445 | 0 | 2026-07-02 to 2026-09-24 | 2,193 | 0 new of 2,445 |
| Tempe `deeds` | 783 | 783 | 783 | 0 | 2026-07-02 to 2026-09-22 | 308 | 0 new of 783 |
| Chandler `deeds` | 1,573 | 1,573 | 1,573 | 0 | 2026-07-02 to 2026-09-17 | 604 | 0 new of 1,573 |
| Glendale, AZ `deeds` | 1,263 | 1,263 | 1,263 | 0 | 2026-07-02 to 2026-09-22 | 521 | 0 new of 1,263 |
| Scottsdale `deeds` | 2,507 | 2,507 | 2,507 | 0 | 2026-07-02 to 2026-09-22 | 1,032 | 0 new of 2,507 |
| Phoenix `deeds` | 9,224 | 9,224 | 9,191 | 0 | 2026-07-02 to 2026-09-22 | 3,772 | 0 new of 9,224 |
| Bend `deeds` | 1,048 | 1,019 (29 outside the box skipped) | 1,019 | 0 | 2026-07-02 to 2026-09-26 | 617 | 0 new of 1,019 |
| Medford `deeds` | 304 | 304 | 302 (one just east of the box, one without a polygon) | 0 | 2026-07-06 to 2026-09-25 | 304 | 0 new of 304 |
| Tacoma `deeds` | 2,432 | 452 (1,980 unplaced or outside the box skipped) | 452, all inside the city limits | 0 | 2026-07-02 to 2026-08-27 | 452 | 0 new of 452 |

No poll made a geocoder query or requested an owner column. A first poll of
the first three took 4 to 8 requests and 10 to 20 seconds; a first poll of
the Maricopa feeds took 2 to 10, spaced 2 seconds apart, and 5 to 48 seconds.
Bend's took 22 requests and 62 seconds, spaced 2.2 seconds apart,
Medford's 2 requests and 4 seconds, and Tacoma's one download and 35
requests to the parcel layer in 111 seconds, spaced the same way.

## Probe conduct

Both probes used their HTTP client's default User-Agent and put no name or
identity in any header, URL or payload. They requested no owner, grantor,
grantee or mailing column: samples named non-personal columns, and the two
downloaded files that carry party names (Maricopa's and Pierce's) were read
by column position for non-personal fields and then deleted. Eight hosts
answered 403 to their first request and were not requested again; no host
answered 429. For most of each run the probes spaced requests to a
host 2.2 seconds apart measured start to start, so after a slow response the
next request could follow in under 2 seconds (302 of 418 same-host pairs in
one probe, about 144 of 200 in the other's early period). Each switched to
measuring from the end of the response before finishing.

The Maricopa follow-up used the same default User-Agent and asked only for
counts, statistics and the feeds' own columns. Three of its requests followed
the previous response from the host by about 0.3 seconds, because each came
from a new process that did not share the pacing clock; within a process,
requests were at least 2 seconds apart.

The Bend follow-up kept one pacing clock across its processes, at least 2.2
seconds from the end of one response to the next request, and asked for no
party column. One request with a long taxlot list answered 404; the same
lookups went again as POST requests in batches of 500.

The Medford follow-up kept the same clock and asked only for counts,
statistics and non-personal columns. Until the client could read the county's
server, it sent its requests with curl and curl's default User-Agent; it also
searched ArcGIS Online's public catalogue for a copy of the layer on another
host and found none.

The Tacoma follow-up kept the same clock. It downloaded `sale.zip` four
times (twice to measure it, once for each live poll), read the saved copy by
column position for the non-personal columns, printed or kept no value from
the grantor and grantee columns, and deleted the copy afterwards. From the
parcel layer it asked only for `TaxParcelNumber`, `Tax_Area_Code` and the
label point (`Latitude`, `Longitude`), never the owner's mailing columns:
its metadata, 34 lookups of the window's parcels and 60 requests for the
116,698 parcels around the city, before the two live polls (69 requests).
With the City's limits, the county's city polygons and six catalogue
searches, it made 177 requests to ArcGIS hosts.

## Not covered here

- **A deed on several parcels.** Each parcel's row publishes, but the rows
  share one instrument number, and PostGIS keeps one row per `doc_id`, as it
  does for Las Vegas, Lynchburg and Columbus. In Nashville's sample, 7 of 200
  instruments covered more than one parcel.
- **The parcel outlines.** The Maricopa layer returns each parcel's polygon
  with its row, which the feeds do not need since the layer's own coordinates
  place the deed. The scheduler has no per-feed switch for `returnGeometry`.
