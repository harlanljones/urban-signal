# Wave 3 Phase-0 probe — Mobile, AL

**Date of probe: 2026-08-28 (UTC).** Hub DCAT-US v3 catalog enumeration,
AGOL org keyword sweep, portal-page scraping for platform fingerprints,
and REST folder walks. Row-level reads attempted on every public survivor.

Linear: **US-345**. Ticket hint: municipal GIS / Alabama ARGIS.

**Verdict: NO REGISTER (all four families Tier 3).** Mobile publishes a
67-item ArcGIS Hub of reference GIS layers; the operational systems are
**Tyler EnerGov** (permits/311 intake) and a **QAlert** 311 citizen
portal, both UI-only. No city-owned permit-record, service-request,
license, or deed feed is anonymously queryable anywhere probed.

---

## Method, and its limits

1. Host fingerprints: `data.mobile.gov`, `opendata.mobile.gov`,
   `gis.mobile.gov`, `maps.mobile.gov` (DNS fail);
   `cityofmobile.opendata.arcgis.com` (Hub, 200);
   `maps.imagisaas.com` / `imagisaas.com` (DNS fail — the ticket-era
   "Alabama ARGIS" host is gone); `www.alabamagis.com` (200, state
   GIS portal); `gis.mobilecountyal.gov/server/rest/services` (200).
2. Hub catalog: v3 `collections/dataset/items` → `numberMatched: 67`;
   full listing captured (zoning, parcels, addresses, storm water,
   garbage routes, ROW Permitting, …). Keyword filter works on this
   install (`permit` → ROW_Permitting only).
3. AGOL org sweep: city owner `gis_cityofmobile` (417 items) keyword
   searches for permit / service request / 311 / business license /
   sale / deed — only ROW Permitting (right-of-way, wrong grain) and
   a smoke-detector request view.
4. Platform fingerprints from the city's own pages:
   `cityofmobile.gov/live/311/` links **Tyler EnerGov self-service**
   (`energovpub.tylerhost.net/apps/selfservice#/home`) and **Mobile 311
   QAlert portal** (`cityofmobile.public.311service.com`).
5. QAlert API probe: `/api/requests` returns the SPA HTML, not JSON
   (QAlert exposes APIs only with an issued key). County REST folder
   walk found reference layers only (easements, site plans, addresses).

Limits: QAlert's tenant API was not exercised with credentials (no key);
an EnerGov OData/OpenData endpoint cannot be ruled out without a tenant
login. The `imagisaas.com` hint could not be pursued (host gone).

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | none public. Tyler EnerGov self-service (`energovpub.tylerhost.net/apps/selfservice`) is the permit workflow; Hub/AGOL expose only `ROW_Permitting` (right-of-way permits — wrong grain for building permits) | n/a | n/a | n/a | **3** |
| **311** | QAlert citizen portal `cityofmobile.public.311service.com` (SPA; API key required); no public service-request layer in Hub or AGOL org | n/a | n/a | n/a | **3** |
| **SLA** | none. No business-license dataset in Hub (67 items) or AGOL org (417 items) | n/a | n/a | n/a | **3** |
| **DEEDS** | none. County GIS is reference layers; `PARCEL_DETAILS`/`Address_Parcel_Combo_Hosted` in the Hub are parcel snapshots (no transaction stream) | n/a | n/a | n/a | **3** |

**Keep or reject: needs-triage / defer.** No T1/T2 family. Re-probe
triggers: Mobile publishing permit records or 311 extracts to the Hub
(cadence of recent Hub items suggests an active GIS team), or a public
QAlert data endpoint appearing.

---

## Portal inventory

| Surface | What it is | Feed? |
|---|---|---|
| `cityofmobile.opendata.arcgis.com` | ArcGIS Hub, 67 datasets, all reference GIS | no family feeds |
| AGOL org `gis_cityofmobile` | 417 items | ROW Permitting only (wrong grain) |
| `energovpub.tylerhost.net/apps/selfservice` | Tyler EnerGov citizen portal (permits, code) | UI only |
| `cityofmobile.public.311service.com` | QAlert 311 portal | UI only (API key-gated) |
| `gis.mobilecountyal.gov/server/rest/services` | County ArcGIS Server (reference/ops layers) | no family feeds |
| `maps.imagisaas.com` | former AL ARGIS host | DNS fail |
| Socrata / CKAN | no domain found | no |

---

## Decision

**Do not register Mobile as a Wave-3 metro.** All four families Tier 3:
EnerGov and QAlert are operational UIs without anonymous feeds, and the
Hub/AGOL/county surfaces are reference layers only. Leave ticket in
needs-triage. Stamp: 2026-08-28.
