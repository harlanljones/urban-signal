# Stream log — deeds-seattle-replacement — 2026-08-24

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** deeds-seattle-replacement
- **Leaf files I will create/edit:** docs/research/seattle-deeds-replacement.md, .streams/deeds-seattle-replacement.md
- **Spine files I expect to need:** NONE (read-only research stream; registering a replacement is explicitly out of scope — spine edit for another hold)

## Intent

Find a live, official replacement source for the dead Seattle DEEDS feed
(PARCEL_SALES3YR_AREA_287 ArcGIS FeatureServer, frozen since 2025-11).
Deliverable: docs/research/seattle-deeds-replacement.md with verified
candidates (live-API recency evidence where reachable), a single
recommendation + runner-up with endpoint URL, watermark_col, platform,
geometry notes, caveats; explicit note that registration is a spine edit via
the interlock process.

## Decisions

Appended as made. Findings go here the moment they are learned (F5) —
not at the end.

- 2026-08-24 — Repo constraints pinned: SEATTLE DEEDS is platform="arcgis",
  watermark_col="SaleDate", extra oid_field=OBJECTID (city_registry.py:531);
  endpoint setting arcgis_kc_sales_url (config.py:113). Producer supports
  socrata/arcgis/carto/ckan clients; row parser falls back across
  SalePrice/sale_price, PIN/property_index_number, lat/lng keys
  (deeds_acris_producer.py:107-231), so any candidate needs at most a field_map.
- 2026-08-24 — KC AGO org Ej0PsM5Aw677QF1W (= kingcounty.maps.arcgis.com)
  hosts 1,171 services; PARCEL_SALES3YR_AREA_287 is the ONLY sales-named one.
  Re-verified dead today: lastEditDate 2025-11-28T12:53:38Z, 110,857 rows,
  max SaleDate 2025-11-20.
- 2026-08-24 — gismaps.kingcounty.gov Property/KingCo_PropertyInfo MapServer
  layer 3 "Property sales in the last 3 years" is the SAME frozen extract
  (identical 110,857 count, identical top SaleDate). Not a fix.
- 2026-08-24 — KEY FIND: SDC catalog (900 entries embedded in
  www5.kingcounty.gov/sdc Metadata page) lists `rpsale_extr` = Real Property
  Sale Record Assessor extract table: transaction-level (ExciseTaxNum+MAJOR+
  MINOR), 2,435,130 rows, SALEDATE/SALEPRICE/RECNUMBER/buyer/seller/
  SALEINSTRUMENT fields, "updated on a weekly basis", LastUpdated 2026-08-18 —
  but Sharing Status **Not Public**; AGO item read returns 403 GWM_0003 and
  the service is absent from the anonymous directory. Global AGOL search finds
  no public rpsale-derived view.
- 2026-08-24 — data.kingcounty.gov (Socrata): zero excise/deed datasets,
  nothing sales-related beyond pet licenses. data.seattle.gov: zero relevant.
  WA state Socrata (data.wa.gov): none. geo.wa.gov Current_Parcels
  (Parcels_2026, lastEditDate 2026-04-09): 17 fields, no sale/excise columns —
  boundaries only. PSRC: aggregates only, no sale-level public product.
  REALPROP_AREA_1289 / PARCEL_EXTR_213 / parcel_address_pub_area: live but
  per-parcel snapshots or county-acquisition inventory — not transactions.
- 2026-08-24 — Watermark caveat identified: parse_watermark handles string
  "%Y%m%d" but misreads bare int YYYYMMDD as epoch seconds
  (watermarks.py:32-34); matters for Assessor-extract date storage.
- 2026-08-24 — Findings doc written: docs/research/seattle-deeds-replacement.md
  (comparison table of 6 candidates incl. rejections; recommendation =
  rpsale_extr blocked on access; runner-up = Assessor DataDownload bulk zip;
  interim posture options documented; spine-edit/interlock note included).

## Outcome

DONE. No live anonymous official replacement API exists for King County
deeds/sales today. Recommendation: pursue access to KCGIS's weekly
`rpsale_extr` AGO feature table (item 96ff1f46173541b9a021a5fef1fdb8a9;
watermark_col=SALEDATE; non-spatial → PIN join to PARCEL_AREA_439 or accept
null coords initially); runner-up: new bulk-file producer path against the
Assessor DataDownload zip. Both are spine work; feed stays known-dead until then.

## Next step

If resumed: hand off to a spine hold that (a) contacts KCGIS
(giscenter@kingcounty.gov) for rpsale_extr access/public sharing and legal
review of the item's terms-of-use block, and (b) decides interim registry
posture (document-dead comment vs partial unregistration) through the
interlock gate (`pytest -m interlock` from apps/api).
