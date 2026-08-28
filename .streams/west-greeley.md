# Stream log — west-greeley — 2026-08-28

## Claim

- **Stream id:** west-greeley
- **Leaf files I will create/edit:** NONE — REJECTED
- **Spine files I expect to need:** NONE

## Intent

Live-probe Greeley, CO (greeleygov.com ArcGIS Hub) for verifiable official
open-data feeds (permits / 311 / SLA licenses / deeds). If 1-4 official
machine-readable feeds verify with real rows + watermarks, build a leaf city
module (greeley.py + field_maps_greeley.py + test_producers_greeley.py). If
no verifiable official feed exists, report REJECT with evidence. Never use a
stale mirror.

## Decisions

- 2026-08-28 00:00Z — Precedents read (aurora.py two-feed state-plane; field_maps_greenville.py; test_producers_greenville.py; city_registry.DatasetSpec typed keys). Phase A probe begins.
- 2026-08-28 00:05Z — ArcGIS Online org `pfd9xSB0fCRnWvDl` (City of Greeley, CO) identified. 149 public items enumerated — none are permits/311/SLA/deeds. All items are infrastructure GIS (parcels, zoning, streets, transit, trails, parks, buildings, addresses, utilities, flood, environmental) + Survey123 forms + traffic counts. No transactional feeds.
- 2026-08-28 00:10Z — Self-hosted ArcGIS Servers (svr, svr3, svr5) fully enumerated across ALL folders (Basemap_Services, Data_Services, Hosted, OpenData, Public, BaseDataServices, ComDev, EHHServices, PublicSafety, PublicSpace, Trakit, etc.). No permit/311/SLA/deed FeatureServers found.
- 2026-08-28 00:15Z — eTRAKiT (CentralSquare TRAKiT) at `trakit.greeleygov.com/etrakit/` confirmed as the city's permitting/license/code enforcement system. Search pages (`Search/permit.aspx`, `Search/case.aspx`, `Search/license2.aspx`) all redirect to `login.aspx` — login-gated, no public machine-readable API. No public API endpoints (`/api/`, `/odata/`, `/webservices/`) found.
- 2026-08-28 00:20Z — 311 system identified as Citysourced (`greeleyco.citysourced.com`). No public API — all standard Open311 and REST API endpoints return 404. iOS app only.
- 2026-08-28 00:25Z — Weld County sites (maps.weldgov.com, gis.weldgov.com) unreachable. County recorder deeds unreachable.
- 2026-08-28 00:30Z — Verified open-data-greeley.hub.arcgis.com is the same AGOL org. No additional datasets.
- 2026-08-28 00:35Z — Colorado state-level liquor license Socrata feed (`data.colorado.gov/resource/ier5-5ms2.json`) verified: 260 Greeley rows with geocoded `location` points. This is a state-level feed already registered in the spine under Denver's SLA (`where="city = 'Denver'"`). Not a greeleygov.com municipal feed — noted for potential spine reuse.

## Current step

Phase A probe complete. All 4 candidate feed categories (permits, 311, SLA, deeds) have NO verifiable official greeleygov.com municipal machine-readable feed. REJECT.

## Outcome — REJECT

**Greeley, CO — REJECTED.** No verifiable official municipal machine-readable open data feed exists for permits, 311/service requests, SLA/business licenses, or recorded deeds.

### Evidence summary

| Feed | Platform | Verifiable? | Detail |
|------|----------|-------------|--------|
| Permits | eTRAKiT (CentralSquare) | NO | Login-gated ASP.NET web app; no public API |
| 311 / Service Requests | Citysourced | NO | No public API — iOS app only |
| SLA / Business Licenses | eTRAKiT (CentralSquare) | NO | Login-gated; same system as permits |
| Deeds (Weld County) | County recorder | NO | County servers unreachable |

### Watermark / count data
N/A — no feeds verified.

### Notable: CO state liquor feed
The Colorado state liquor license registry (`data.colorado.gov/resource/ier5-5ms2.json`, Socrata) covers Greeley with 260 rows, geocoded `location` points, and is already registered in the spine for Denver's SLA (`where="city = 'Denver'"`). This is a state-level feed, not a greeleygov.com municipal feed. If the spine later adds CityId.GREELEY, the CO liquor feed could be reused with `where="city = 'Greeley'"` for a minimal SLA registration — same pattern as Denver's US-372 SLA slice.

### Recommended Linear comment
REJECT — Greeley, CO has no verifiable municipal open-data feed. The city's permits, licenses, and code enforcement live in CentralSquare eTRAKiT (login-gated, no public API). 311 runs on Citysourced (no public API). Greeley's ArcGIS Online org (149 items) and 3 self-hosted ArcGIS Servers contain only infrastructure GIS layers — no transactional feeds. The Colorado state-level liquor license Socrata feed (data.colorado.gov) covers Greeley with 260 rows but is a state-level feed registered in the spine, not a per-city candidate. Mark US-242 as Wontfix / not feasible.

### Spine delta
NONE — no spine registration recommended. If the wave lead later decides to register Greeley, the CO liquor feed (already in spine for Denver) is the only candidate SLA source, and the eTRAKiT login-gated surface would need a separate access arrangement.