# Wave 3 Phase-0 probe — Knoxville, TN (US-343)

**Date of probe: 2026-08-27/28.** Portal fingerprints + row-level reads
where anonymous endpoints existed (none did for the families).

**Verdict: REJECT (all four families Tier 3).** Knoxville's operational
systems are real — **Accela Citizen Access** for permits, **MyKnoxville**
app for 311, **KGIS** (Knoxville-Knox County GIS) — but none exposes an
anonymous watermarked feed. The ticket hint "Open Data + ArcGIS + Accela"
resolves to: empty Hub + token-gated GIS + UI-only Accela.

Platform: none registerable. `cityofknoxville.opendata.arcgis.com` is a
live Hub Search API endpoint with **numberMatched = 0** (empty catalog);
`knoxville.opendata.arcgis.com` is an 8 KB generic placeholder;
`data.knoxvilletn.gov` DNS-fails. `kgis.org/arcgis/rest/services`
answers **401** (token). Accela ACA tenant
`https://aca-prod.accela.com/KNOXVILLE/Welcome.aspx` is live (200).

---

## Method, and its limits

1. Hostname fingerprints: `data.knoxvilletn.gov` (DNS fail),
   `data.cityofknoxville.org` (DNS fail), both `.opendata.arcgis.com`
   hosts, `kgis.org` (+ REST paths), city site `www.knoxvilletn.gov`.
2. Hub v3 search on both Hub hosts (0 items / placeholder), DCAT feed
   (404 path), AGOL global searches for a City of Knoxville org —
   none found (staff items exist but `orgId` is not exposed publicly;
   owners like `elizabeth.semande`, `nick.schoenborn`,
   `aurin.lee` share planning layers, not transactional data).
3. Accela Develop 901 tenant probe: `KNOXVILLE` 200;
   `CITYOFKNOXVILLE`/`KNOX`/`KNOXTN` 404.
4. City-site walk: 311 department page names the **MyKnoxville** app
   (`apps.apple.com/us/app/my-knoxville/id1542821801`; site is hosted
   on Tyler CivicLive CDN). Permits/licenses pages link to Accela and
   PDF application forms (beer board, animal control, wrecker).

Limits: KGIS is the presumptive keep-c-current GIS mirror for the
Knoxville-Knox County region; anonymous access is refused (401) and no
public token was attempted. If the city ever publishes the KGIS open
subset anonymously, re-probe all families there.

---

## Headline table

| Family | Surface | Finding | Tier |
|---|---|---|---|
| **PERMITS** | Accela ACA `aca-prod.accela.com/KNOXVILLE` | Live **citizen portal** (search UI, account UI). No bulk extract found on the empty Hub or AGOL | **3** (portal named) |
| **311** | MyKnoxville app (Tyler CivicLive) | App/phone intake; no CRM feed; Hub has no 311 dataset | **3** |
| **SLA** | Knox County Clerk (business tax); city beer permits are PDFs | No registry feed | **3** |
| **DEEDS** | Knox County Register of Deeds; KGIS 401 | No anonymous transaction stream | **3** |

---

## Detail

### Permits — Tier 3 (portal only)

Accela Citizen Access is confirmed at
`https://aca-prod.accela.com/KNOXVILLE/Welcome.aspx`. Develop 901 bulk
API requires a paid contract; the ACA UI is not a feed. No Socrata/Hub
extract of permit records exists (Hub catalog empty; AGOL org absent;
`data.knoxvilletn.gov` does not resolve).

### 311 — Tier 3

MyKnoxville app handles service requests (Tyler CivicLive hosting).
The only 311-adjacent public data is the city's "Get Engaged" page. No
feed. (City of Knoxville is not a SeeClickFix place per app-store and
site evidence.)

### SLA — Tier 3

City business licenses are beer permits (PDF applications) and
Standard Industrial Classification listings; business tax licenses file
with the Knox County Clerk (state B&O regime). No open registry.

### Deeds — Tier 3

Knox County Register of Deeds document search is a UI. KGIS REST is
token-gated. No sales/deed dataset on the empty Hub.

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `data.knoxvilletn.gov`, `data.cityofknoxville.org` | DNS fail |
| `cityofknoxville.opendata.arcgis.com` | Hub v3 live, **0 items** |
| `knoxville.opendata.arcgis.com` | generic 8 KB placeholder |
| `kgis.org/arcgis/rest/services` | **401 token required** |
| AGOL org search | no city org |
| Socrata discovery / CKAN | absent |

## Decision

**Reject Knoxville for Wave 3.** Transactional portals exist (name them:
Accela ACA KNOXVILLE, MyKnoxville/Tyler, KGIS) but publish no
watermarked public extract in any family. Re-probe KGIS if it opens
anonymous read. Stamp: 2026-08-28.
