# Wave 3 Phase-0 probe — Grand Rapids, MI

**Date of probe: 2026-08-28 (UTC).** Socrata fingerprint, Hub catalog
enumeration, AGOL org-owner sweeps, Accela fingerprint, and row-level
reads on survivors.

Linear: **US-357**. Ticket hint: ArcGIS Hub
(`grdata-grandrapids.opendata.arcgis.com`) + Accela; historically
`data.grandrapidsmi.gov` was Socrata.

**Verdict: NO REGISTER (all four families Tier 3).** The historical
Socrata is **decommissioned** — `data.grandrapidsmi.gov` returns
**"Domain Decommissioned" (400)** and Socrata discovery says domain not
found. The `grdata` Hub is live but tiny (24 items, all
reference/planning). Permits run on **Accela Citizen Access**
(`aca-prod.accela.com/GRANDRAPIDS`, 200 — UI only). The AGOL org holds
KPI/metric layers, parking, zoning, and county-parcel snapshots — no
permit records, 311, licenses, or deeds.

---

## Method, and its limits

1. Socrata discovery (`domains=data.grandrapidsmi.gov` → not found) and
   direct fetch (400 "Domain Decommissioned" — the historical portal is
   explicitly retired).
2. Hub catalog: `grdata-grandrapids.opendata.arcgis.com` v3 API →
   `numberMatched: 24`; full listing (fire districts, historic
   landmarks, wards, sidewalks, crash data, neighborhoods, ACS clips).
3. AGOL org sweep: city publishers
   `*@grand_rapids.mi.us_grandrapids` (306 + 106 + 91 items sampled) —
   KPI/equity dashboards, `GRParcels_with_Condos` (CAMA snapshot,
   modified 2026-08), `AR_2025` residential annual review (rental
   certification program data on Kent County parcel keys), parking,
   zoning.
4. Accela fingerprint: `aca-prod.accela.com/GRANDRAPIDS/Default.aspx` →
   200 (citizen permits/inspections portal).
5. 311: `311.grcity.us` redirects to the city's "311 Customer Service"
   info page — no public service-request dataset anywhere probed.

Limits: the city org's item titles were sampled (~78 titles read across
owners); keyword-scoped org searches were polluted by global results
and relied on owner enumeration instead. Kent County surfaces were not
row-probed (parcel snapshots in the city org already show the CAMA
pattern); a county deed/sales stream cannot be fully ruled out.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | none public. Accela ACA `aca-prod.accela.com/GRANDRAPIDS` is the permit workflow | n/a | n/a | n/a | **3** |
| **311** | none. 311 is a call-center info page (`grandrapidsmi.gov/living-in-gr/311-customer-service/`); no dataset in Hub (24 items) or org | n/a | n/a | n/a | **3** |
| **SLA** | none. No business/occupational license dataset. `AR_2025`/Residential Annual Review is the rental-certification program keyed to county parcels (not occupational licenses) | n/a | n/a | n/a | **3** |
| **DEEDS** | none. `GRParcels_with_Condos` / `AR_2025` are Kent County CAMA/assessment snapshots (owner, taxable value, no transaction stream) | n/a | n/a | n/a | **3** |

**Keep or reject: needs-triage / defer.** The Socrata decommission is
the headline: the ticket's "historically Socrata" premise no longer
exists, and nothing replaced it at family grain.

---

## Portal inventory

| Surface | What it is | Feed? |
|---|---|---|
| `data.grandrapidsmi.gov` | **Decommissioned** Socrata (400, "Domain Decommissioned") | gone |
| `grdata-grandrapids.opendata.arcgis.com` | ArcGIS Hub, 24 reference items | no family feeds |
| AGOL org `*_grandrapids` | KPI metrics, parking, zoning, CAMA parcels, rental annual review | no family feeds |
| `aca-prod.accela.com/GRANDRAPIDS` | Accela Citizen Access (permits) | UI only |
| `311.grcity.us` | 311 info page (call center) | no data |
| Kent County | CAMA snapshots (via city org); no deed stream probed | no |

---

## Decision

**Do not register Grand Rapids as a Wave-3 metro.** All four families
Tier 3: decommissioned Socrata, UI-only Accela, reference-only Hub and
org, no 311 feed, no deeds. Leave ticket in needs-triage. Re-probe
triggers: the city republishing permit/311 extracts on the Hub or a new
data host (the org is actively maintained — parcels and KPIs land
monthly). Stamp: 2026-08-28.
