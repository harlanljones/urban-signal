# Stream log — southeast-wave (orchestrator) — 2026-08-28

Wave-6 orchestrator stream for the **Metro Expansion — Southeast** milestone
close-out. Linear US-334 lead ticket resolved first.

## Claim

- **Stream id:** `southeast-wave`
- **Leaf files:** none (orchestrator). Close-out + serial spine hold.
- **Spine files expected in the hold:** `apps/api/src/spatial/city_registry.py`
  (CityId + ALIASES + REGISTRY), `apps/api/src/config.py` (endpoint settings),
  `apps/api/src/spatial/cities/__init__.py` (exports),
  `apps/api/src/serving/dashboard.py` (METRO_META),
  `apps/api/src/producers/watermarks.py` (ANSI_DATE_LITERAL_HOSTS),
  `apps/dashboard/public/index.html` (regenerate).

## Disposition of every Southeast milestone ticket (all 20, evidence-based)

### Registered / resolved (7)
| Ticket | City | Feeds | Status |
|---|---|---|---|
| US-334 | Orlando | SLA (BTR primary + STR companion) | Already registered wave-3 via US-194; verified + **Done** |
| US-337 | Miami-Dade | (registered) | Registered (`city_registry.py:4903`); gate-enforced wiring — resolve Done |
| US-335 | Memphis | (registered) | Registered (`city_registry.py:4969`); gate-enforced wiring — resolve Done |
| US-298 | Savannah | PERMITS (res /comm companion) | **NEW** — needs spine hold |
| US-300 | Bowling Green | PERMITS | **NEW** — needs spine hold |
| US-303 | Tallahassee | PERMITS + 311 + DEEDS | **NEW** — needs spine hold |
| US-301 | Spartanburg | PERMITS + SLA | **NEW** — needs spine hold |

### NOT registrable today (13) — research complete, evidence + re-probe triggers recorded
- US-299 Myrtle Beach — zero live feeds (county hub = 10 static datasets; city permits email-only; county RMC/311 login-gated). Gulfport-MS/FL city-name trap documented.
- US-302 Athens-Clarke — all families frozen/date-baked (2019 debts; Plans Review monthly rotating URL); only Transactional 2026-08-26 is date-baked. Hub = reference catalog only.
- US-341 Columbia SC — permits frozen 2024-11/2026-01, 311 2026-01, STR 2025-05; EnerGov/live systems on internal `.ads` estate; no county deeds.
- US-343 Knoxville — permits stale 2026-02-24; no 311/SLA/deeds; real door = knoxgis Hub (421 datasets) whose only transactional export is 6mo stale.
- US-345 Mobile — city ArcGIS Server = EnerGov reference layers only; 311 QAlert key-gated; no license register; deeds login-walled.
- US-339 Birmingham — CKAN archives frozen (permits 2017 / 311 2019 / licenses 2016); Jefferson Co GIS DNS-dead; Accela UI-only.
- US-306 Biloxi — Cityworks Permit/Request layers EMPTY; WorkOrder = public-works only; county circuit-clerk 499; assessment snapshot. "HarrisonCADWebService" = Harrison County **TX**.
- US-305 Gulfport — permits web-forms; SLA frozen 2024-12-12; deeds = ownership cadaster no sales. "Gulfport_Permits" = Gulfport **FL**.
- US-304 Pensacola — all login-gated web forms (Fortis/TESS, Comcate, MyGovernmentOnline, escpa SaleSearch); parcels no sales.
- US-336 Atlanta — KEEP-DEFERRED (vendor SPA Accela no bulk REST; only extracts frozen 2026-01/2022).
- US-338 Jacksonville — KEEP-DEFERRED (JAXEPICS SPA; last-sale-on-parcel overlay rejected; Duval PA laggy no-price).
- US-342 Fort Lauderdale — KEEP-DEFERRED (permits frozen 2026-03-16; 311 frozen 2022; SLA null-issued; deeds Broward-wide → belongs at a `broward` county CityId).
- US-344 Huntsville — stays EXCLUDED (standing decision: conditional mid-Sept re-probe).
- US-293 Gainesville — already In Review on Linear (untouched).

## Spine-delta payload for the 4 NEW registrations (from leaf agents, 2026-08-28)

### REGISTRY/Config/Enum — all four
CityId enum: `SAVANNAH = "savannah"`, `BOWLING_GREEN = "bowling_green"`,
`TALLAHASSEE = "tallahassee"`, `SPARTANBURG = "spartanburg"` (after TUCSON).
Aliases per city (in _HANDWRITTEN_ALIASES):
- savannah: savannah, savannah_ga, savannah ga, sav, chatham_county_ga, chatham county ga
- bowling_green: bowling_green, bowling green, bowling_green_ky, bowling green ky, bowling-green, bgky, warren_county_ky, warren county ky
- tallahassee: tallahassee, tallahassee_fl, tallahassee fl, leon_county_fl, leon county fl, tlh
- spartanburg: spartanburg, spartanburg_sc, spartanburg-sc, spartanburg sc, spartanburg county, spartanburg_county_sc

config.py endpoint settings (defaults):
- arcgis_savannah_permits_endpoint = `https://pub.sagis.org/arcgis/rest/services/Savannah/BuildingPermit_FC/FeatureServer/1`  (+ endpoint `.../0` as companion `commercial_building_permits`)
- arcgis_bowling_green_permits_endpoint = `https://webgis.bgky.org/server/rest/services/CCPC/CCPC_Building_Permits_2010/FeatureServer/5`
- arcgis_tallahassee_permits_endpoint / `_311_endpoint` / `_deeds_endpoint` (see leaf FEED_SPECS; hosts `intervector.leoncountyfl.gov` `TLC_OverlayPermitsActive_D_WM/MapServer/0`, `LCPW_InforServiceRequest_D_WM/MapServer/1`, `LCPA_Last3YearsSales_D_WM/MapServer/0`)
- arcgis_spartanburg_permits_url / `_sla_url` (both = `.../EnerGov/EnerGov_Spatial_Collections/FeatureServer/5`; per-family `where` module filters)

watermarks.py `ANSI_DATE_LITERAL_HOSTS` += **pub.sagis.org**, **webgis.bgky.org**,
**intervector.leoncountyfl.gov**, **maps.spartanburgcounty.org** (all 400 on plain
ISO date literals; the 4 leaf agents verified ANSI `DATE '...'` works on each).

Per-city REGISTRY parameter detail: see the agent reports / leaf FEED_SPECS.
Key values: savannah watermark `IssuedDate_DATE` id_keys `["PermitNumber","OBJECTID"]`
cadence 7 needs_geocode True context "Savannah, GA", order_by OBJECTID, max 2000;
bowling_green watermark `created_date` id_keys `["PermitNum","OBJECTID"]` cadence 1
needs_geocode True (defensive; native coords) context "Bowling Green, KY", native-point,
NO non_spatial, max 2000; tallahassee 3 feeds (permits cadence 7; 311 producer_key "311"
with `where="CALLDTTM <= CURRENT_TIMESTAMP"`; deeds cadence ~1) needs_geocode False,
all three need explicit `oid_field` (no layer publishes objectIdField — ESRI_OID/OBJECTID);
spartanburg PERMITS cadence 1 + SLA cadence 30 needs_geocode False, `where` module filters.

METRO_META (serving/dashboard.py) + byte-synced apps/dashboard/public/index.html:
`bowling_green: {name: 'Bowling Green / Warren County'}`,
`tallahassee: {name: 'Tallahassee / Leon County'}`,
`savannah: {name: 'Savannah / Chatham County'}`,
`spartanburg: {name: 'Spartanburg County'}`.

## BLOCKER — spine hold NOT applied this session

Do NOT apply the above spine edits blindly. Two problems, both external:

1. **Lost leaf artifacts.** The batch-1/2 leaf modules for the 4 registered
   cities (savannah.py, bowling_green.py, tallahassee.py, spartanburg.py +
   field_maps + tests) were written by subagent sessions into a working tree
   that was SWITCHED (main -> `chore/restore-metros-and-columbus`) mid-session.
   They are not on disk and not in the only stash. They must be REBUILT (re-run
   the 4 leaf agents) before the spine can reference them.
2. **Concurrent west-coast spine hold.** This same tree also carries a west-coast
   wave: `anaheim/chandler/inland_empire/long_beach` staged, and the SAME spine
   files (city_registry.py, config.py, dashboard.py, index.html,
   test_city_leaf_naming.py) mid-hold by that orchestrator. Holding the southeast
   spine on top of an in-progress west hold on a different branch would interleave
   two orchestrators on one spine — the torn-write the interlock forbids.

Correct next step (in order): let the west-coast hold land/merge on a stable
branch, regenerate the 4 southeast leaf modules (re-dispatch the leaf agents from
this file's spine-delta payload), then apply the spine serially and run
`pytest -m interlock` + full suite + `export_dashboard` byte-sync.

## SPINE HOLD APPLIED (2026-08-28, later) — resolved the BLOCKER

Leaf modules regenerated; the spine hold was applied after confirming the
west-coast wave had left the spine files (its staged files were removed when
main returned; the remaining city_registry/config diffs are US-372 CO liquor
licenses, not west-related). Applied: CityId enum (+4), _HANDWRITTEN_ALIASES
(+27), config.py (+8 endpoints), cities/__init__ imports + __all__ (+4),
REGISTRY entries (savannah PERMITS+companion, bowling_green PERMITS,
tallahassee PERMITS+311+DEEDS, spartanburg PERMITS+SLA), watermarks.py
ANSI_DATE_LITERAL_HOSTS (+4 hosts), serving/dashboard.py METRO_META (+4),
regenerated apps/dashboard/public/index.html via scripts/export_dashboard.py.

## Validations (post-hold)

- `pytest -m interlock` → **24 passed / 0 failed** (all four cities wired on
  the map + snapshot export + res-5 grid tiles + closure/containment/
  completeness + endpoints-in-settings + platform clients).
- Leaf suites + canonical-naming `test_city_leaf_naming.py` → 303 passed.
- `test_watermarks.py` → 7 passed (ANSI host additions).
- config `Settings` model loads with the new endpoint defaults.
- One reconciled leaf test: bowling_green's
  `test_not_registered_city_no_borough_resolution` →
  `test_registered_city_resolves_borough` (city is now registered).

## Final state

Every Southeast milestone ticket dispositioned on Linear (7 registered/resolved,
9 NOT-VIABLE, 3 KEEP-DEFERRED — all with evidence comments + re-probe triggers).
Open by standing only: US-344 huntsville (excluded, conditional mid-Sept
re-probe), US-293 gainesville (pre-existing In Review).
COMMITS DEFERRED: `git commit`/`git push` permission-denied this session — all
wave-6 leaf, spine, index.html and registry changes are UNCOMMITTED on the
working tree; human commits before merge.
