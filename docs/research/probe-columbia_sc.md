# Wave 3 Phase-0 probe — Columbia, SC

**Date of probe: 2026-08-28 (UTC).** Hub DCAT-US v3 search, AGOL org
enumeration (476 items), item-graph traversal into app data sources, and
row-level attempts on every public survivor.

Linear: **US-341**. Ticket hint: ArcGIS Hub (`coc-colacitygis.opendata.arcgis.com`).

**Verdict: NO REGISTER (all four families Tier 3).** The Hub is real and
public but tiny — **11 datasets** (arrests, zoning, code violations, parks,
boundaries) — and none are permits, 311, licenses, or deeds. The city's AGOL
org (`ColaCityGIS`, 476 items) holds reference layers and dashboards only;
the operational systems (Tyler EnerGov for permits, Cityworks for service
requests, an internal GIS server `gisinweb3.columbiasc.gov` for business
licenses) are not published as anonymous feeds.

---

## Method, and its limits

1. Hub fingerprint: `coc-colacitygis.opendata.arcgis.com` Hub v1/v3 APIs
   live; `collections/dataset/items?limit=1` → `numberMatched: 11`; full
   11-item listing captured. The Hub `q` parameter does not filter on this
   install, so the enumeration (not keyword search) is the authoritative
   catalog read.
2. AGOL org enumeration: `owner:ColaCityGIS` (total 476; first 100 titles
   read) plus targeted `title:`/keyword searches for permit / 311 /
   service request / work order / license / sales / deed.
3. App-graph: "Business License Internal" (public Experience) →
   "BLBusinessWM-Internal" web map → layer URLs on
   `gisinweb3.columbiasc.gov` (internal) and `gis.columbiasc.gov`
   (both unresolvable publicly).
4. Host fingerprints: `311.columbiasc.gov`, `gis.columbiasc.gov`,
   `data.richlandcountysc.gov`, `gis.richlandcountysc.gov` — all DNS fail.

Limits: only the first 100 of 476 org items were titled; the remainder are
web maps/dashboards already pattern-matched by the keyword searches. An
unpublished ArcGIS Server feed cannot be ruled out, but every referenced
internal host was identified via the app graph.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | none. EnerGov reference layers only (`services1.arcgis.com/Mnt8FoJcogKtoVBs/.../EnergovInformationPublic/FeatureServer` — zoning/overlay/parcel layers, no permit records); `BullSTDistrictDevelopment` is a single-district tracker | n/a | n/a | n/a | **3** |
| **311** | none public. Cityworks (`CitworksWO2` dashboard in org); no 311 layer in org or Hub; `311.columbiasc.gov` DNS fail | n/a | n/a | n/a | **3** |
| **SLA** | "Business License Internal" Experience (public app) → `BLBusinessWM-Internal` web map → `gisinweb3.columbiasc.gov/arcgis/rest/services/Projects/BLBusinesses/MapServer/*` — **internal host, no external DNS** | n/a | n/a | n/a | **3** |
| **DEEDS** | none. Richland/Lexington county GIS hosts DNS fail; no sales/transfer dataset in Hub or org | n/a | n/a | n/a | **3** |

**Keep or reject: needs-triage / defer.** Wrong-grain candidates noted:
`CodeViolationProperty` (Feature Service, code-enforcement violations —
inspection output, not citizen 311) is the closest thing to an activity
feed in the Hub and is worth a look only if a code-violation family is
ever defined.

---

## Portal inventory

| Surface | What it is | Feed? |
|---|---|---|
| `coc-colacitygis.opendata.arcgis.com` | ArcGIS Hub, **11 datasets** (crime, zoning, code violation, parks) | no family feeds |
| AGOL org `ColaCityGIS` (`colacitygis.maps.arcgis.com`, org id visible in service URLs: `Mnt8FoJcogKtoVBs`) | 476 items: reference layers, dashboards, apps | no family feeds |
| Tyler EnerGov | City permitting/land management system; only reference layers public | UI/system only |
| Cityworks | 311/work-order system (`CitworksWO2` dashboard) | UI only |
| `gisinweb3.columbiasc.gov` | Internal ArcGIS Server (business licenses) | internal only |
| Richland / Lexington county GIS | DNS fail from outside | none found |

---

## Decision

**Do not register Columbia as a Wave-3 metro.** All four families Tier 3:
no permit records feed (EnerGov reference layers only), no public 311
(Cityworks internal), business licenses on an internal GIS server, no
deeds stream. Leave ticket in needs-triage. Re-probe triggers: city
publishing permit records or Cola311 data to the Hub, or the
`BLBusinesses` service appearing on a public host. Stamp: 2026-08-28.
