# Wave 3 Phase-0 probe — Tucson, AZ

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. Hub `item.modified` is a label only; freshness evidence is
newest-row-by-watermark.

Linear: **US-328**. Ticket hint was ArcGIS Hub + Tyler/EnerGov
(`gisdata.tucsonaz.gov`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `gisdata.tucsonaz.gov` | ArcGIS Hub ("Tucson Open Data", owner `City_Of_Tucson`) | STAC `/items` search |
| `gis.tucsonaz.gov/arcgis/rest/services/PublicMaps/OpenData_EconomicDevelopment/MapServer` | City ArcGIS Server — the family layers (`PDSD_PERMITS_ALL` L0/L2, `BUSLIC` L1/L3) | live |
| Accela | Tucson P&D runs Accela; no ACA host resolvable (`aca/citizenaccess/accela.tucsonaz.gov` DNS-fail) | no bulk surface |

## Summary

| Family | Dataset | Newest watermark | Geocode | 7d / 60d | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `OpenData_EconomicDevelopment/MapServer/0` `PDSD_PERMITS_ALL` | `DATEISSUED` **2022-10-20**; `GIS_APPEND_DATE` 2022-12-12; **0 rows ≥2026** | point + address parts | **0 / 0** | **3** |
| **311** | none on Hub (`q=311` → 0); `tucsonaz.gov/311` is HTML | — | — | — | **3** |
| **SLA** | `MapServer/3` `BUSLIC` (Business Licenses Open Data) | `DT_START` max non-future **2026-05-29**; future-dated 2026-09 rows exist (layer maintained) | native point + `FULLADDRESS` | ~0 / 2 non-future | **2** (borderline — see caveat) |
| **DEEDS** | none (Pima County recording) | — | — | — | **3** |

**Wave-3-ready: partial (SLA only, with a staleness caveat).**

## Permits — Tier 3 (do not register)

- `PDSD_PERMITS_ALL` L0 (4,024 rows) and L2 (282 rows, **all date fields
  null**): max `DATEISSUED` **2022-10-20**, max `ENTERED_DATE` 2022-10-18,
  max `GIS_APPEND_DATE` 2022-12-12; **0** rows issued since. Row-level freeze
  (the Hub item mod of 2025/2026 would have lied).
- Columns exist (`PERMIT_NUMBER`, `DATEISSUED`, `Valuation`, address parts,
  point geometry) — if Tucson ever resumes the ETL this is the registrable
  endpoint. Today it is an archive.

## 311 — Tier 3

No 311/service-request dataset on the Hub. `www.tucsonaz.gov/311` is HTML.

## SLA — Tier 2 (borderline; register with guards)

- **URL:** `https://gis.tucsonaz.gov/arcgis/rest/services/PublicMaps/OpenData_EconomicDevelopment/MapServer/3`
- **Rows:** 93,483 (`BUSLIC`). Point geometry; `FULLADDRESS`,
  `STREETNUM/DIR/NAM/SUF`, `CITY`, `STATE`, `ZIP_CODE`, `ACC_NUM`, `ACC_NAME`,
  `NAIC_CODE/DESC`, `LIC_TYPE`, `LIC_STATUS`, `HOME_OCCUPATION`, `OWN_TYPE`,
  `DT_START`.
- **Watermark:** `DT_START` (license start). Newest rows are
  **future-dated applications** (max `DT_START` **2026-09-12**, e.g.
  Trader Joe's #288 "Application" status) — the layer **is maintained**
  (a frozen layer would not contain 2026-09 rows). Newest non-future start:
  **2026-05-29**; **358** rows with `DT_START` in 2026.
- **Caveat:** effective issuance cadence is slow — only 2 non-future rows in
  the 60d window vs 391 at Henderson. Watermark must **exclude future-dated
  `DT_START` sentinels** (like Albuquerque) and set
  `expected_cadence_days` generously (e.g. 7–30) so staleness alerts don't
  false-positive.
- **Geocoding:** native point geometry (+ address fallback) → Tier 2/1 seam;
  no separate lat/lng columns, geometry is native.
- **Id keys:** `ACC_NUM` + `LIC_TYPE` + `OBJECTID`.

## Deeds — Tier 3

Pima County Recorder/Assessor have no anonymous bulk deed/sales stream.

## Registration contract (`tucson`)

| Feed | Dataset (watermark) | Platform | field_map budget | Quirks tests must pin |
|---|---|---|---|---|
| SLA | `OpenData_EconomicDevelopment/MapServer/3` (`DT_START`) | arcgis | ~8 | exclude future `DT_START` sentinels; slow cadence; `get_dataset` raises for PERMITS / 311 / DEEDS (permits layer exists but frozen — a `where` guard must prevent accidental registration) |

Suggested spec payload (leaf `cities/tucson.py`, not applied this ticket):

```
SLA
  endpoint: https://gis.tucsonaz.gov/arcgis/rest/services/PublicMaps/OpenData_EconomicDevelopment/MapServer/3
  platform: arcgis
  watermark_col: DT_START
  watermark_exclude_future: true
  id_keys: [ACC_NUM, LIC_TYPE, OBJECTID]
  extra:
    expected_cadence_days: 7
    field_map:
      license_id: [ACC_NUM]
      dba: [ACC_NAME]
      license_type: [LIC_TYPE, NAIC_DESC]
      status: [LIC_STATUS]
      effective_date: [DT_START]
      address_street: [STREETNUM, STREETDIR, STREETNAM, STREETSUF]
      zipcode: [ZIP_CODE]
      # lat/lng from geometry (outSR=4326)
```
