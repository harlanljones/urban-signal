# Probe — Maricopa County Sales Affidavits CSV (Phoenix deeds)

**Probe stamp: 2026-08-28.** Downloaded live from this host; schema, row
counts, and date ranges below are read from the actual archive, not the
catalog. This deepens the wave-3 finding
(`docs/research/wave-3-probe-phoenix.md` §Deeds, which catalog-only read the
AGO item). Success criterion for the row-level probe: verify the pipe-delimited
schema and assess whether `CSVClient` can carry Phoenix deeds.

## Source

| | |
|---|---|
| Item | ArcGIS Online item `f3484c72a938497286adc4e5de7e9963` — "Sales Affidavits", type **CSV Collection** |
| Download | `https://www.arcgis.com/sharing/rest/content/items/f3484c72a938497286adc4e5de7e9963/data` (anonymous, `access: public`) |
| Size | 61,382,362-byte ZIP (deflate); uncompressed **272 MB** |
| Item `modified` | 2026-08-03 16:07 UTC (`1785773224000`); `created` 2026-01-13 |
| Archive members | `Data/Sales_Affidavits.txt` (272,679,594 B) + `File Spec/Sales Affidavits - File Spec.pdf` (116,981 B) |
| Download headers | `content-type: application/zip`, **no `Last-Modified` header** (see freshness gap below) |

## Schema — verified (pipe-delimited)

`Sales_Affidavits.txt` is **pipe-delimited** (UTF-8, `\n` line endings),
**912,807 rows** (1 header + 912,806 data rows), **44 columns**. Header:

```
PARCELNUMBER|SALEDATE_MMYYYY|SALEPRICE|DEEDNUMBER|DEEDDATE_MMDDYYYY|DEEDSTATUS|DEEDTYPE|
PROPERTYTYPECODE|PROPERTYTYPEDESCRIPTION|PROPERTYTYPEOTHERDESCRIPTION|SITUSADDRESS|SITUSSUITE|
SITUSCITY|SITUSZIP|GRANTOROWNERNAME|GRANTORADDRESSLINE1|GRANTORADDRESSLINE2|GRANTORCITY|GRANTORSTATE|
GRANTORZIP|GRANTORCOUNTRY|GRANTEEOWNERNAME|GRANTEEADDRESSLINE1|GRANTEEADDRESSLINE2|GRANTEECITY|
GRANTEESTATE|GRANTEEZIP|GRANTEECOUNTRY|FINANCETYPECODE|FINANCETYPEOTHERDESCRIPTION|DOWNPAYMENT|
PARTIALINTERESTINDICATOR|PARTIALINTERESTPERCENT|PARTIALINTERESTDESCRIPTION|MULTIPARCELINDICATOR|
NUMBEROFPARCELS|BUY_SELLRELATIONSHIPINDICATOR|BUY_SELLRELATIONSHIP|OWNEROCCUPANCYINDICATOR|
ASSESSORCODE|ASSESSORCODEDESCRIPTION|PERSONALPROPERTYINDICATOR|PERSONALPROPERTYVALUE|PERSONALPROPERTYDESCRIPTION
```

Sample row (byte-verbatim, 2026-08-28):

```
20904027B|012000|210000|000000267|01032000|X|JC|F|Commercial/Industria||22026 N 24TH AVE||PHOENIX|85027|
ROBBINS JEFFREY D/REBECCA M/ERIC C|22684 N 93RD ST||SCOTTSDALE|AZ|85255|USA|GRIM GARY L/CATHY J|
25411 N 11TH AVE||PHOENIX|AZ|85027|USA||||N|||Y|1|N|||X|ABSENCE OF REJECT/WARNING/EXEMPT CODE|N||
```

The canonical SLA/deeds field-mapping targets map cleanly: `license_id` ←
`DEEDNUMBER`/`PARCELNUMBER`, `effective_date` ← `DEEDDATE_MMDDYYYY`,
`premises_name` ← `GRANTEEOWNERNAME`, `address_street` ← `SITUSADDRESS`,
`borough` ← `SITUSCITY`, `estimated_cost`-class value ← `SALEPRICE`.

## Data quality — verified (full 912,806-row scan)

| Metric | Value |
|---|---|
| Rows | 912,806 data rows |
| Deed dates (clean 8-digit) | 912,806 of 912,806 — **1 dirty row** (`DEEDDATE="IA"`) |
| Sale dates (clean 6-digit) | **247 dirty rows** — empty, or an address leaks in (`SALEDATE="680 58TH PL NO 9"`), and those rows carry empty `PARCELNUMBER` |
| Empty `SALEPRICE` | 24,503 rows |
| `DEEDSTATUS` | `X` on 912,806 rows, `50266` on 1 (constant-ish) |
| Future `DEEDDATE` sentinels | **~134 rows**, years 2050–2099 (scattered; top = 2097/2098/2094) |
| Recency | 2026 deed rows: **48,605**; 2025: 77,582; 2021 peak: 80,103 |

**Watermark trap (confirmed).** Both date columns are fixed-width text that is
NOT lexicographically chronological:
- `SALEDATE_MMYYYY` — century trap: `"121999"` (Dec 1999) > `"082026"` (Aug
  2026) lexicographically. A text watermark max is always a 19xx December row.
- `DEEDDATE_MMDDYYYY` — month-day-first trap: `"01012026"` (Jan 2026) <
  `"12312025"` (Dec 2025) lexicographically; naive max is `"12312096"`
  (a 2096 sentinel); valid max ≤ 2026 is `"12312025"`, so the watermark never
  advances past a December row even when 2026 rows exist.

This is the same false-stale-alarm class the US-372 leaf documented for OR CCB
`orig_regis_date` / MO `original_date` (`.streams/us372-state-licenses.md`).

## CSVClient feasibility — assessment

`CSVClient.paginate` (`apps/api/src/producers/csv_client.py`) is the right
shape: download-once, client-side filter, generator of batches. Findings:

1. **zip_member — SUPPORTED.** `_read_zip_member(payload, "Sales_Affidavits.txt")`
   already handles the nested `Data/` folder (basename match). The St. Louis CSB
   precedent (`csb.zip`/`{year}.csv`) proves the path.
2. **Pipe delimiter — NOT SUPPORTED.** `csv.DictReader(io.StringIO(csv_text))`
   hardcodes the comma delimiter. Maricopa is `|`-delimited. **Gap:** CSVClient
   needs a `delimiter: str = ","` parameter threaded into `paginate()` →
   `csv.DictReader(..., delimiter=...)`. A one-line leaf change in the same
   spirit as the existing `zip_member` kwarg.
3. **Scheduler forwarding — NOT WIRED.** `zip_member` is already documented as
   not forwarded by the scheduler ("wiring it is a later spine hold"). Any
   Maricopa registration needs the same spine hold to forward `zip_member`
   (and the new `delimiter`) from `DatasetSpec` → scheduler job metadata →
   `_paginating_client_for().paginate(...)`.
4. **Freshness — GAP.** The staleness probe's CSV path reads the download
   endpoint's `Last-Modified` header; the AGO download returns **no
   Last-Modified**. The item's `modified` field (2026-08-03) lives on the AGOL
   REST metadata API, which the probe does not read. Options: (a) extend the
   probe with a CSV-Collection branch reading `items/{id}?f=json` `modified`;
   (b) accept `alarm_exempt` with the item-modified recorded as a label.
5. **Volume.** 272 MB uncompressed, ~912k rows, downloaded and parsed every
   cycle. Fine at weekly cadence; heavy at daily.
6. **Id keys.** Multi-parcel deeds share one `DEEDNUMBER`
   (`MULTIPARCELINDICATOR="Y"` — the sample shows one deed on two parcels), so
   `id_keys` should be `["PARCELNUMBER", "DEEDNUMBER"]` (per-parcel sale) or
   accept deed-level dedup with `["DEEDNUMBER"]`. Dirty rows (empty parcel,
   address-in-date) must be dropped by an id guard.

## Verdict

**FEASIBLE, not Wave-4-ready.** The pipe-delimited schema is verified and maps
cleanly onto the deeds field-mapping contract; the CSV Collection is public,
fresh (item modified 2026-08-03; 48,605 deed rows dated 2026), and
`CSVClient` needs only a `delimiter` parameter plus the already-planned
scheduler `zip_member` forwarding. Three things gate a real registration:

1. CSVClient `delimiter` param (leaf).
2. A spine hold forwarding `zip_member` + `delimiter` through the scheduler.
3. A freshness decision: snapshot ingestion (deeds as a full-replace registry,
   KC-SLA/OR-CCB precedent) with either a probe extension for AGOL item
   `modified` or `alarm_exempt`, since the date columns are lexicographically
   unusable as watermarks and 134 future-DEEDDATE sentinels exist.

Snapshot-mode ingestion with `watermark_col=""` + id-dedup diff is the
recommended shape (mirrors the OR CCB `g77e-6bhs` registration in this same
hold); the future-deed-date rows pass through the event verbatim and the
consumer-side guard (US-111 pattern) ignores them.

Filed as a probe doc; a Phoenix-deeds registration ticket should cite this
assessment and carry the CSVClient + scheduler spine deltas.
