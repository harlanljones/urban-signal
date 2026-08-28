# Wave 3 Phase-0 probe — Charleston, WV (US-319)

**Date of probe: 2026-08-27/28.** Row-level reads where any anonymous
endpoint answered; otherwise hostname fingerprints recorded as honest
negatives.

**Verdict: REJECT (all four families Tier 3).** Charleston has no open-data
program at all. The ticket hint (`charlestonwv.opendata.arcgis.com`) is a
**private-org Hub placeholder** — no catalog, no datasets.

Platform: none resolved. City web presence is Drupal
(`charlestonwv.gov`, redirects from `cityofcharleston.org`). A GIS web
box exists at `gisweb.charlestonwv.gov` but serves only classic Story
Map apps; no ArcGIS REST root answered. Not Socrata, not CKAN, not
ArcGIS Hub (private).

---

## Method, and its limits

1. Hostname fingerprints (TLS handshake fails without `-k` on the GIS
   box; http→https redirect loops on the city site): `cityofcharleston.org`,
   `www.cityofcharleston.org`, `maps./gis./data.cityofcharleston.org`,
   `charlestonwv.gov`, `gisweb./gis./maps.charlestonwv.gov`,
   `gis./map.kanawha.us`, `kanawha.us`, `mapwv.gov` (WV statewide).
2. ArcGIS Hub v3 probe on `charlestonwv.opendata.arcgis.com` →
   `401 private org id not accessible`.
3. AGOL global searches (`"Charleston, WV"`, `tags:"charleston wv"`,
   owner sweeps): only third-party/student layers (VITA, Marshall
   classwork), no city org, no family datasets.
4. City site walk: `charlestonwv.gov` nav; business registration is a
   **PDF application form**; "Get Customer Service" is a Drupal page
   (403 to anonymous crawling on the deep page); no permit online
   portal linked; `rentalregistration.cityofcharleston.org` is a
   rental-registration app (200) with no open data surface found.
5. Story Map config (`gisweb.charlestonwv.gov/storymaps/arttour/`,
   js.arcgis.com 4.11) contains no REST MapServer references — the
   underlying services, if any, are not anonymously discoverable.

Limits: deep city-site pages 403 (bot protection), so platform names
for Charleston's 311 intake and permit intake are unconfirmed from the
site itself; no anonymous GIS REST endpoint was found to row-probe.
Kanawha County (`gis.kanawha.us` 404 on REST roots; Assessor is a
qPublic-style UI) offers no deeds stream either.

---

## Headline table

| Family | Finding | Tier |
|---|---|---|
| **PERMITS** | No portal, no extract; applications are PDF/paper; no Accela/Tyler citizen portal found | **3** |
| **311** | Web form / phone ("Citizen Support"); no CRM feed; no SeeClickFix place confirmed | **3** |
| **SLA** | WV municipal B&O/business registration — PDF application form on `charlestonwv.gov`; no registry feed | **3** |
| **DEEDS** | Kanawha County Clerk (index UI); county GIS REST 404 | **3** |

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `charlestonwv.opendata.arcgis.com` | Hub placeholder, **private org** (401) |
| `cityofcharleston.org` (+www, maps, gis, data) | DNS resolve but TLS fail / no service |
| `charlestonwv.gov` | Drupal city site; GIS link = storymaps only |
| `gisweb.charlestonwv.gov` | IIS; storymaps 200; `/arcgis/rest/services` 404 |
| `gis.kanawha.us` / `map.kanawha.us` / `kanawha.us` | no REST roots |
| `mapwv.gov` | WV statewide clearinghouse; no city REST |
| AGOL org search | no city org; placeholder owner only |
| Socrata discovery / CKAN | absent |

## Decision

**Reject Charleston WV for Wave 3.** No platform, no feeds, no portal
beyond PDFs and web forms. Re-probe only if the city launches an open
data program. Stamp: 2026-08-28.
