# Wave 3 Phase-0 probe — Huntington, WV (US-320)

**Date of probe: 2026-08-27/28.** AGOL item sweeps + city-site walk;
row-level reads where any anonymous endpoint answered (none did for the
families).

**Verdict: REJECT (all four families Tier 3).** Huntington publishes
reference GIS (zoning, boundaries, parcels, address points) but no
transactional feed for any family. The ticket hint "city ArcGIS Hub" is a
**private-org placeholder**.

Platform: none open. City GIS staff publish to AGOL
(`currys2@huntingtonwv`, 165 items, ~50 feature services — all
reference layers). City web site is `cityofhuntington.com`. Permits are
processed by the Inspections & Permits department **by email**
(`permits@huntingtonwv.gov`); the address-points layer is explicitly
named "Huntington Address Points **for Tyler Technologies**" — permit
system is Tyler (EnerGov-class), no citizen portal found.

---

## Method, and its limits

1. Hostname fingerprints: `www.cityofhuntington.com` (200),
   `gis./maps.cityofhuntington.com` (DNS fail), `huntingtonwv.gov`
   (DNS fail), `huntingtonwv.opendata.arcgis.com` (Hub placeholder →
   **401 private org**), `/arcgis/rest/services` on the city host (404).
2. AGOL sweeps: `owner:"currys2@huntingtonwv"` (165 items) and citywide
   keyword searches; title grep for permit / 311 / request / license /
   sale / deed / transfer / violation / complaint — zero family hits.
3. City-site walk (`cityofhuntington.com`): building-permit pages
   describe fees/requirements only; `huntington-wv-311` page names
   **SeeClickFix** (app-store links); `/i-want-to/report/` pages are
   web forms; Inspections & Permits page gives an email contact.

Limits: the Tyler citizen portal, if one exists, is not linked from the
city site; no anonymous REST endpoint was found to row-probe. SeeClickFix
is third-party intake, not a municipal CRM extract (Phoenix / Providence /
Albuquerque precedent) — not probed further and not a candidate.

---

## Headline table

| Family | Finding | Tier |
|---|---|---|
| **PERMITS** | Email/PDF intake; Tyler-backed internal; no extract, no citizen portal found | **3** |
| **311** | SeeClickFix app ("Huntington WV 311") — third-party intake, not a municipal bulk feed | **3** |
| **SLA** | Business license via city Services (page + process); no registry feed | **3** |
| **DEEDS** | Cabell/Wayne County clerks (UI); no stream found | **3** |

---

## What exists (for the record)

- `Huntington Address Points for Tyler Technologies` — evidence of the
  internal Tyler permit/CAD stack, not a public extract.
- Reference feature services only: Zoning (2022/2026 updates), City
  Boundary (March 2026 / May 2026 updates — actively maintained),
  Parcel Data, Blight & Dilapidation Survey, EPL Mapping, Neighborhood
  Associations (2026), Parking Meters, CSO, Fiber.
- City Boundary/Parcels layers are fresh — the GIS team is active; the
  gap is transactional data publication, not capacity.

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `huntingtonwv.opendata.arcgis.com` | Hub placeholder, **private org** (401) |
| `gis./maps.cityofhuntington.com`, `huntingtonwv.gov` | DNS fail |
| `cityofhuntington.com/arcgis` | 404 |
| AGOL `currys2@huntingtonwv` | 50 FS, zero family datasets |
| Socrata discovery / CKAN | absent |

## Decision

**Reject Huntington WV for Wave 3.** No registerable feed in any family.
Re-probe if the city exposes a Tyler citizen-access extract or opens the
Hub org. Stamp: 2026-08-28.
