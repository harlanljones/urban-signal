# Phase-0 probe — Lafayette, LA (South Central)

**Date of probe: 2026-08-30 (UTC).** Row-level reads (newest-row watermark by
`ORDER BY <col> DESC`, total counts, geometry/spatial-ref, and geocode-field
checks) on the LCG self-hosted ArcGIS Server, the LCG ArcGIS Online org, the
suspected Hub, and the LCG website portals.

Linear: **US-266**. Ticket hint: Parish GIS — **(LC-GIS)**, est. pop **~478K
(Lafayette Parish)**, **Fit Medium**. Region: South Central.

**Verdict: REJECT — all four signal families are Tier 3.** No registrable live
row-level municipal feed satisfies ADR 0004's "live + (native | address)
geocode" bar. The permit and 311 channels are both **vendor/auth-walled SaaS**
(Tyler Portico and Microsoft Dynamics 365) with no public bulk REST; the two
public ArcGIS surfaces that look promising are **wrong grain** (a
condemnation-hold restriction table, not permit issuance) or **stale/narrow**
(a 2020 Hurricane Delta brush viewer, not a live 311 feed). Deeds reduce to an
**assessment-roll snapshot** (no transaction stream); the only license-adjacent
layer is a **special-needs registry with heavy PII** (not business licenses).

**This probe does NOT authorize a municipal leaf build** (no `cities/lafayette.py`,
no `field_maps_lafayette.py`, no test file) and **triggers no spine hold**
(no `CityId.lafayette` / `ALIASES` / `REGISTRY` / `METRO_META` dashboard chip).
The interlock gate (`pytest -m interlock`) is not implicated.

---

## Method, and its limits

1. **Host fingerprinting first.** Every candidate hostname was probed for
   `http_code` / DNS before any content read — this avoids chasing ghost
   paths.
2. **The ticket hint hostname is stale.** `gis.lafayettela.gov` → **NXDOMAIN**
   (`curl` exit 6). The real self-hosted server is **`maps.lafayettela.gov`**
   (ArcGIS Server). The suspected Hub `lafayette-la.opendata.arcgis.com`
   resolves but its DCAT feed returns **`Domain record not found`** (404) — a
   stale Hub domain record, not a portal.
3. **AGOL org sweep.** The canonical public org is owner **`lcgdata`**
   (Lafayette Consolidated Government), org id **`fOr4AY8t0ujnJsua`**, **278
   public items** enumerated in full (keyword sweep over every service name).
   A second org, `xQcS4egPbZO43gZi` (owner `CajunCodeFest`), hosts the only
   public permit-named service — but it is **token-gated**.
4. **"Layer 0 is not always layer 0" gotcha respected.** `LCG_Permit_Status
   /0` returns `Address_Points`, not permits — the permit table is **layer id
   1**. `CitizenProblems/0` is the 311 candidate. `CollectorGDB_Permit_gdb/0`
   is a survey form.
5. **Tier definitions (ADR 0004 §Consequences + the wave-3 roadmap):** Tier 1 =
   live + natively geocoded; Tier 2 = live + address-geocodable (ADR-0004
   geocoder); Tier 3 = stale / no portal / wrong grain / vendor-locked without
   a bulk API / SaaS-walled.

Limits: The Dynamics-365 portal was probed only for public API surface
(oData/`_api`/`api/data`), not driven as an authenticated session, since it
requires credentials. The Tyler Portico permit portal was probed at its public
landing (`vendor-access/registration`), which is enough to establish
"no anonymous bulk REST". Both are reported as SaaS-walled (Tier 3), not
exhaustively enumerated.

---

## Host / platform table

| Host / surface | Result | Notes |
|---|---|---|
| `gis.lafayettela.gov` (hint) | **NXDOMAIN** | the hint hostname is dead; not the server |
| `maps.lafayettela.gov/arcgis/rest/services` | **Live** — self-hosted ArcGIS Server | 240 services, 15 folders (AerialsBase, BaseLayers, Caching, CityWorks, EditableLayers, Geoprocessing_Tools, JavaScriptApplication, MGO, Mosquito, Onbase, OpenData_Downloads, Pictometry, Police, Utilities, + 7 root) |
| `lafayette-la.opendata.arcgis.com` | **Stale Hub domain** | HTTP 200 shell but DCAT → 404 `Domain record not found`; search API → 401/private |
| `data.lafayettela.gov` | **NXDOMAIN** | not a portal |
| AGOL org `lcgdata` (`fOr4AY8t0ujnJsua`) | **Live** — public AGOL org | 278 public items (infrastructure + assessment layers) |
| AGOL org `xQcS4egPbZO43gZi` (CajunCodeFest) | **Private/canceled** | `Lafayette_Planning_And_Zoning_Permits` item → 403 "Subscription is canceled"; service URL → 499 "Token Required" |
| `lafayettela-of.finance.socrata.com` | **Open Finance dashboard** | budget/vendor transparency only; `api.us.socrata.com/api/catalog/v1?domains=…` → **0 results** (no open-data datasets) |
| `www.lafayettela.gov` (LCG) | **Live** | GovStack site; links to permit portal, 311 portal, GIS gallery |
| `311lafayette.services/en-US` | **Live but auth-walled** | Microsoft Dynamics 365 / Power Portal (see 311 below) |
| `lafayettecsdgovla.tylerportico.com` | **Live but auth-walled** | Tyler Portico permit portal (see permits below) |

No Socrata open-data domain; no CKAN `datastore_search`; no Hub DCAT.

---

## Headline matrix

| Family | Endpoint (closest public surface) | Watermark / newest row | Geocode | Count | Recent window | Tier |
|---|---|---|---|---|---|---|
| **PERMITS** | `maps.lafayettela.gov/…/EditableLayers/LCG_Permit_Status/FeatureServer/1` (`Permit_Status` TABLE, id 1) | `DATETIME` = **2026-08-04** (~26 d) — but restriction holds/warnings, no issuance | none (table; `SITE_ADDRESS` mostly null; ref via `ADDR_PT_ID_R`) | 31,158 | n/a — wrong grain | **3** |
| **PERMITS (portal)** | `lafayettecsdgovla.tylerportico.com/va/vendor-access/…` (Tyler Portico) | n/a — vendor registration SPA, no public records | n/a | n/a | n/a | **3** |
| **311** | `services.arcgis.com/fOr4AY8t0ujnJsua/…/CitizenProblems_…/FeatureServer/0` (`JerryBrushWithLocation`) | `CreationDate` = **2020-10-29** (Hurricane Delta) | native point `esrignss_latitude` | 5,546 | **0 in 30/60 d** (all 2020) | **3** |
| **311 (portal)** | `311lafayette.services/en-US` (Dynamics 365) | n/a — login wall, no public oData | n/a | n/a | n/a | **3** |
| **SLA** | no municipal registry. `LASR_Registry_Form` is a special-needs register | `CreationDate`-driven but wrong domain | native point | n/a | wrong domain + PII | **3** |
| **SLA (portal)** | LCG business-permits/licenses pages (Tyler Portico intake) | n/a — application pages | n/a | n/a | n/a | **3** |
| **DEEDS** | `services.arcgis.com/fOr4AY8t0ujnJsua/…/dbo_Parcels_with_CAMA_Data_View/FeatureServer/0` | `last_edi_1` = **2026-04-06** (snapshot, uploaded 2026-04-29) | polygon wkid 3452 | 119,666 | n/a — assessment roll, no transaction stream | **3** |

---

## PERMITS — Tier 3 (wrong grain; only candidate is token-gated)

The only permit-named public layer is
`maps.lafayettela.gov/arcgis/rest/services/EditableLayers/LCG_Permit_Status/FeatureServer/1`
(**layer id 1** — `0` is `Address_Points`). Verify before build: the layer is a
**`Table`** (no geometry), 31,158 rows, fields `OBJECTID, ADDR_PT_ID_R,
SITE_ADDRESS, RES_TYPE, DEPT_DIV, D_CONTACT, D_EMAIL, ARCHIVE, RES_DETAILS,
RES_DATE, DATETIME`.

- **It is a permit-restriction / hold / warning table, not permit issuance.**
  Row-level: `RES_TYPE` distribution = `Other` 27,432 / `Warning` 3,277 /
  `Hold` 444 / `Active` 1 / null 4; `DEPT_DIV` mostly null (31,039) with a
  handful of `CDP Planning` (52) / `CDP Permits` (30) / `CDP Compliance` (25).
  Newest rows are condemnation holds ("Hold Permitting and Inspections for
  condemnation … No applications for permitting are to be taken in without
  approval from the Compliance Division (Micki Boudreaux 8764)"),
  `DATETIME` = **2026-08-04**.
- **No issuance columns.** No permit number, no declared valuation, no work
  type, no geometry, and `SITE_ADDRESS` is null on the sampled newest rows
  (records join to address points via `ADDR_PT_ID_R`). This is a compliance
  signal, **wrong grain** for the permits (capex) family → **Tier 3**.
- **The public permit portal is Tyler Portico.** `lafayettecsdgovla.tylerportico.com/va/vendor-access/registration`
  (Tyler Technologies) — a credential/vendor-registration SPA with no
  anonymous bulk records endpoint → **Tier 3** SaaS, same vendor-locked class
  as other Portico cities.
- **`CollectorGDB_Permit_gdb`** (hosted, layer `survey_collector`) is a narrow
  Public Works street/culvert/driveway `survey_collector` form (fields
  `permit_id, name_of_applicant_or_firm, type_of_project, Pipe_dia,
  Culet…, F_date, PermitStatus`) — point wkid 3857, not building-permit
  issuance.
- **The lone "Planning And Zoning Permits" FeatureServer is private.**
  `https://services.arcgis.com/xQcS4egPbZO43gZi/…/Lafayette_Planning_And_Zoning_Permits/FeatureServer/0`
  → **`499 "Token Required"`** (item is a canceled subscription, 403 "SB_0006")
  — not a public feed.

## 311 — Tier 3 (SaaS wall; only public GIS layer is a stale 2020 viewer)

The operational channel is a **Microsoft Dynamics 365 Customer Service / Power
Portals** site: `https://www.311lafayette.services/en-US` (links carry the
`/interaction-type-deflection?id=<guid>` pattern — the CDX Power-Portal
submission pattern). Probes: page loads with **Login / Sign in**; public
oData paths (`/_api/`, `/api/data/v9.2`, `/_api/data`, `/odata`) all **404**.
No anonymous bulk incident feed → **Tier 3** (same Dynamics/SaaS class as
other rejected portals).

The only public 311-shaped ArcGIS layer is
`services.arcgis.com/fOr4AY8t0ujnJsua/…/CitizenProblems_…/FeatureServer/0`
(item listed as *JerryBrushWithLocation*): 5,546 rows, point geometry, fields
`probid, category, probtype, details, poc*/locdesc, status, resolution,
resolutiondt, CreationDate, EditDate, esrignss_latitude, Zone`. Row-level:
newest `CreationDate` = **1604006695088 ms = 2020-10-29**, `probtype =
"Hurricane Delta"`, `category` coded domain = `{Brush Pile, Powerlines}`, all
`poc*` null, `esrignss_latitude` ≈ 30.2285 (native WGS84). This is a **stale,
narrow 2020 storm brush/powerline viewer**, not a live community 311 feed —
**0 rows in any 30/60 d window** → **Tier 3**.

The self-hosted `CityWorks` folder is **not** service requests: `ServiceRequest`
is drainage **coulee** hydrology ("consist of Coulees Minor and Major");
`ServiceLayers` = inlets, pump stations, hydrants, culverts, centerlines,
bridges, sidewalks, maintained buildings, owned properties; `PWstreetMaintenance`
= street type; `TrafficandTransport` = parking meters/markings/signals/work
zones. No citizen-request rows anywhere.

## SLA / business licenses — Tier 3 (no registry; wrong-domain GIS layer)

No municipal business-license registry was found in the full 278-item `lcgdata`
catalog (keyword sweep over every service name). The only license-adjacent
public layer is:

- **`LASR_Registry_Form`** (`…/LASR_Registry_Form_view/FeatureServer/0`): point
  layer, 1,000 max records; fields `badge, name, nickname, address, date_of_birth,
  age, cell_phone, home_phone, race, gender, hair_color, eye_color, height,
  weight, scars_, care_Facility, medical_care, primary_diagnosis,
  Coexisting_diagnosis, notes, condition, how_communicate, comm_disablity`
  plus three contact blocks. This is the **Louisiana Special At-Risk (LASR)
  vulnerable-person registry** — heavy PII (DOB, medical, race, physical
  descriptors) and the wrong domain for a business-license signal → **do not
  register** (wrong grain + severe PII).

LCG's website business "permits and licenses" (alcoholic-beverage, bar-cards,
municipal, sound-variance, special-event, sign) are **application / intake
pages** routed to the Tyler Portico portal — no license-records data feed.
No statewide LA license open-data feed was resolved within this municipal-leaf
scope (a state-companion superfeed, if ever wanted, would be a separate,
non-leaf decision — the TX-cluster precedent).

## DEEDS / sales — Tier 3 (assessment-roll snapshot, no transaction stream)

`services.arcgis.com/fOr4AY8t0ujnJsua/…/dbo_Parcels_with_CAMA_Data_View/FeatureServer/0`
(service description: "Parcel with CAMA Data view layer from LCG's sde.
Uploaded April 29, 2026"). **119,666** polygon parcels, wkid 3452 (LA South).
55 fields incl. `Owners, Property_Transactions, Property_Location, Assmt_Num,
Property_Type, Tot_Assessed_Value, Tot_Exempt, Tot_Taxable_Value, Mail_*,`
`last_edite` (editor), `last_edi_1` (date), `created_da`, `DateMapped`.

Row-level: newest `last_edi_1` = **2026-04-06** (snapshot cadence, ~5 months
stale at probe). `Property_Transactions` is a **text-embedded instrument
reference list**, e.g. `202500025898 (07-25-2025),,202500016897 (05-21-2025)<file>` —
no sale-price column, no per-transaction date column, no doc/periodization,
and the value is the **last sale(s) on a parcel** baked into a static
assessment roll. This is the same assessment-roll grain (El Paso `EPParcels`,
Sedgwick County, Tulsa County) that the earlier sweeps classified as **no
deeds/transfer feed** → **Tier 3**. There is no recorder/register-of-deeds
transaction service exposed.

---

## Hosts / surfaces rejected (with reason)

| Surface | Reason |
|---|---|
| `gis.lafayettela.gov` | NXDOMAIN — ticket hint hostname is dead |
| `lafayette-la.opendata.arcgis.com` | stale Hub domain record (DCAT 404, search 401/private) |
| `data.lafayettela.gov` | NXDOMAIN |
| `lafayettela-of.finance.socrata.com` | Open-Finance budget dashboard, not open data (catalog 0 datasets) |
| `xQcS4egPbZO43gZi` (CajunCodeFest) | `Lafayette_Planning_And_Zoning_Permits` private/canceled (403/499) |
| `lafayettecsdgovla.tylerportico.com` | Tyler Portico — credentialed vendor SPA, no bulk REST |
| `311lafayette.services` | Dynamics 365 Power Portal — login wall, no public oData |
| `CitizenProblems` / `JerryBrushWithLocation` | stale 2020 Hurricane Delta brush viewer (native geocode but Tier 3) |
| `LCG_Permit_Status/1` | address-restriction/condemnation holds, not permit issuance |
| `Parcels_with_CAMA_Data_View` | assessment-roll snapshot, no sale-price/transaction stream |

---

## Decision

**REJECT Lafayette, LA (`lafayette`, Lafayette Parish) for a municipal leaf
build — Tier 3 across all four families.** No public bulk REST endpoint
satisfies ADR 0004's row-level watermark + geocode requirement:

- **PERMITS** — Tier 3: Tyler Portico SaaS wall; the named public layer is a
  condemnation-hold restriction **table** (wrong grain), and the only
  permit-issuance FeatureServer is token-gated/private.
- **311** — Tier 3: Dynamics 365 Power Portal (login wall, no oData); the only
  public GIS layer is a **stale 2020 Hurricane Delta brush viewer** (0 rows in
  any recent window).
- **SLA** — Tier 3: no municipal business-license registry; the public
  license-adjacent layer is the **LASR special-needs registry** (severe PII,
  wrong domain).
- **DEEDS** — Tier 3: **assessment-roll polygon snapshot** (uploaded
  2026-04-29, newest edit 2026-04-06) with text-embedded instrument refs but
  no sale-price/date transaction stream.

**Do not create leaf files.** No `apps/api/src/spatial/cities/lafayette.py`, no
`apps/api/src/producers/field_maps_lafayette.py`, no
`apps/api/tests/unit/test_producers_lafayette.py` (0 tests — no tier justifies
a build). **Do not take a spine hold** — no `CityId.lafayette`, no
`_HANDWRITTEN_ALIASES`/`_HANDWRITTEN_REGISTRY` entry, no `METRO_META` chip, no
dashboard/`index.html` byte-sync, no snapshot/res-5 coverage. The interlock gate
(`pytest -m interlock`) is not implicated and was not run.

**Re-probe trigger:** a future public service satisfying ADR 0004 — e.g. a
`…/FeatureServer` or Hub/CKAN `datastore_search` that exposes row-level permit
or 311 records with a per-row watermark (`ORDER BY <col> DESC` freshest row
<60 d, or a live 30 d window > 0) and either native WGS84 point geometry or an
address column for the ADR-0004 geocoder — or a public Socrata `4x4` view (any
`*.socrata.com` domain with catalog membership). None is observed 2026-08-30.

Stamp: 2026-08-30.
