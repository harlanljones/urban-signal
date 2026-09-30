# Deeds for the metros one family short — 2026-09-30

On 2026-09-30, 22 metros had permits, 311 and licences but no deeds. Two
probes checked each one live the same day for a public, row-level record of
property transfers with a date, a price and a way to place it on the map.
Three register here, four have a source that needs client work first, two
are held and thirteen have none.

| Verdict | Metros |
|---|---|
| Registered here | Nashville, Hartford, Denver |
| Source found, needs client work | Tempe (and a Phoenix repair), Bend, Medford, Tacoma |
| Held | Minneapolis, San Diego |
| No source | Austin, Baton Rouge, Billings, Dallas, El Paso, Los Angeles, Louisville, Memphis, Montgomery AL, Sacramento, San Antonio, San Jose, St. Louis |

| Tier (families) | Before | After |
|---|---|---|
| 4 | 18 | **21** (Denver, Hartford, Nashville) |
| 3 | 33 | 30 |
| 2 | 72 | 72 |
| 1 | 34 | 34 |

## Registered

All three read a parcel-level record of each parcel's most recent transfer,
filtered to transfers dated in the 90 days before each poll, and read that
window whole every six hours. Their record id joins the parcel, the transfer
date and the instrument, so a parcel's next sale is new to the snapshot and
an unchanged row is not re-published. A sale that reaches the source weeks
after its date is still inside the window when it arrives. None of the three
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

## Sources that need client work first

| Metro | Source | What it needs |
|---|---|---|
| Tempe, and Phoenix | Maricopa County Assessor Parcels, `gis.mcassessor.maricopa.gov/arcgis/rest/services/Parcels/MapServer/0`: the latest deed on each parcel (`DEED_NUMBER`, `DEED_DATE`) with native `LATITUDE`/`LONGITUDE`, refreshed about weekly (inferred from daily counts). Tempe (`JURISDICTION = 'TEMPE'`) had 783 deeds in 90 days; `SALE_PRICE` is text and filled on 308 of them. | The host rejects ISO and epoch date literals, so it joins `ANSI_DATE_LITERAL_HOSTS`; pages hold 1,000 rows. The same layer can replace Phoenix's file source, which dead-letters every row today (`feed-health-2026-09-30.md`). |
| Bend | Deschutes County `GIS_SALES`, `services1.arcgis.com/znO8Hz1SuVVohYhZ/.../Taxlots/FeatureServer/8`: each taxlot's two most recent sales, refreshed overnight, joined to its polygon (`/0`) on `TAXLOT` (200 of 200). | The table is county-wide with no city column (Bend is 1,220 of 2,105 sales in 90 days), so it needs a city filter through the situs table (`/1`) or a box after the join. |
| Medford | Jackson County `PropertySales`, `spatial.jacksoncountyor.gov/arcgis/rest/services/Demog/PropertySales/FeatureServer/0`: the latest sale per account with price and document number, two to three days behind; 310 Medford sales in 90 days. | The server sends a malformed `Content-Security-Policy` header that the HTTP client rejects on every request, and it accepts only ANSI date literals. |
| Tacoma | Pierce County's weekly `sale.zip` (`online.co.pierce.wa.us/datamart/`), every sale since 1997, joined to the county's `Tax_Parcels` layer. | The file is pipe-delimited with no header row, which the CSV client cannot read. It is county-wide, so it needs a box filter, and it runs four to five weeks behind. |

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

No poll made a geocoder query or requested an owner column. A first poll
took 4 to 8 requests and 10 to 20 seconds.

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

## Not covered here

- **A deed on several parcels.** Each parcel's row publishes, but the rows
  share one instrument number, and PostGIS keeps one row per `doc_id`, as it
  does for Las Vegas, Lynchburg and Columbus. In Nashville's sample, 7 of 200
  instruments covered more than one parcel.
- **The candidates above.** Maricopa (Tempe and Phoenix) is next; Bend,
  Medford and Tacoma each need the client change named in their row.
