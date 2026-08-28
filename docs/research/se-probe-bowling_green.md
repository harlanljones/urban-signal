# SE live probe — Bowling Green, KY / Warren County (US-300)

**Probe date: 2026-08-28 (UTC).** Live re-probe of `webgis.bgky.org`
(city ArcGIS Server) done by the `city-bowling_green` leaf stream; results
judged on **live row freshness** (watermark), not catalog timestamps.

Linear: **US-300**. Brief hint: Bowling Green city ArcGIS / CCPC building
permits.

**Verdict: PARTIAL-REGISTRABLE — one live feed (PERMITS).** `CCPC/
CCPC_Building_Permits_2010` is a native-point ArcGIS Server 11.5 service
with a genuinely fresh, genuinely spatial building-permit layer. The other
three target families have no viable live row-level feed and are **NOT
registered** (partial registration is allowed; `get_bowling_green_dataset`
raises for them).

---

## Method (and its limits)

1. `https://webgis.bgky.org/server/rest/services/` service directory
   enumeration (`/server/rest/services?f=json`), filtered to the `CCPC`
   folder.
2. Per-layer `/FeatureServer/<id>?f=json` layer metadata (oid field, date
   fields, `maxRecordCount`, service type).
3. `/query` live probes: where-clause watermark tests, `returnCountOnly`
   cadence counts, `orderByFields` new-set pulls, `returnExtentOnly`
   extent grounding, and `outSR=4326` geometry checks.
4. Family sweeps against the same service and neighboring county/state
   doors (Warren PVA, KY geoportal) for the three absent families.
5. Host quirk verification: bare-ISO where-clause vs ANSI `DATE` literal.

Limits: The `webgis.bgky.org` host is **ANSI-date-literal** — a through-the-
`ArcGISClient` probe of a bare ISO watermark comparison returns ArcGIS error
400, so minute-level cadence cannot be exercised with an ISO string; the
`DATE 'YYYY-MM-DD HH:MM:SS'` form works. Nothing in this probe judged
differently than the prior successful run.

---

## Probe table

| Family | Platform | Endpoint | Watermark col + newest value | 7d / 60d / total | Geo | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | arcgis | `webgis.bgky.org/server/rest/services/CCPC/CCPC_Building_Permits_2010/FeatureServer/5` | `created_date` 2026-08-24T18:06:08+00:00 (date-typed editor-tracking) | 22 / 386 / 29,691 | **native point** (KY-North SP 102680, `outSR=4326` honored) | **Tier 2 / registrable** |
| COMPLAINTS_311 | — | `Code_Cases/13` froze 2023-01-31; `CCPC_Compliance_Inspections/2` = EPSC/construction compliance | n/a | n/a | n/a | **NOT-VIABLE** (family mismatch / frozen) |
| SLA | — | no license register in the 978-dataset org | n/a | n/a | n/a | **NOT-VIABLE** |
| DEEDS | — | `WARCO/Parcel_Reference` parcel snapshot, no fresh sales; warrenpva.com unreachable; KY geoportal only Webster Co | n/a | n/a | n/a | **NOT-VIABLE** |

---

## PERMITS detail (the one registrable feed)

* **Layer:** "Building Permits 2010+" — `FeatureServer/5`, ArcGIS Server
  11.5, city-owned (`webgis.bgky.org` is the City of Bowling Green's host).
* **Watermark:** `created_date` — the ArcGIS 11.5 editor-tracking column,
  **date-typed** (epoch-ms on the wire, flattened to ISO by the client).
  Newest live value 2026-08-24T18:06:08+00:00 (PermitNum `2026-1314`, a
  24-unit apartment project at 2633 Mt Victor Lane; OBJECTID 113479).
* **Cadence:** 7d=22, 60d=386, total=29,691 — a live weekly-plus register.
* **Geometry:** **native point layer**, KY-North State Plane 102680/2247.
  The client always requests ``outSR=4326``, so every row rides in as WGS84
  `latitude`/`longitude` (verified live; none of the attributes carry a
  lat/lng column — geometry only). `needs_geocode` is declared **defensively
  only**; `non_spatial` is NOT set. No `state_plane_crs` declaration needed
  because coordinates arrive already in 4326.
* **OID / maxRecordCount:** `objectIdField=OBJECTID`, `maxRecordCount=2000`
  (verified live) — the spec declares `max_record_count=2000`,
  `order_by`/`oid_field="OBJECTID"`.
* **Address shape:** no single street line — split across `St_Number` /
  `St_Name`. No neighborhood/parcel key (SPID is a site-plan designation,
  not a parcel id). The field map leaves `address_street` unmapped so the
  producer never emits a number-only half-address; the coordinates come from
  the native geometry.
* **Registered whole:** no server-side status/type filter declared.
* **Extent (outSR=4326, `returnExtentOnly`):** lat 36.795-37.179, lng
  -86.661--86.125 — the metro bbox is padded to that.

### Host quirk — ANSI date-literal (spine delta note)

`webgis.bgky.org` rejects a **bare ISO** watermark comparison:

```
where=created_date >= '2026-08-20T00:00:00+00:00'  -> ArcGIS error 400
where=created_date >= DATE '2026-08-20 00:00:00'   -> works (count=49)
```

This is a host string-comparison limitation, **not** a schema property —
`created_date` is a true `esriFieldTypeDate`, so `ArcGISClient` flattens
epoch-ms to ISO and **no ADR-0005 text-watermark declaration is needed**. The
spine delta must note that a `DATE '...'` literal is required at this host;
`watermarks.py` is **not** edited in this leaf.

### Geocoder caveat (documented only; `geocoder.py` not touched)

The `_STATE_RE` state-token regex falsely matches `MT` in the street name
`MT VICTOR LANE`, so an address-context append is skipped for a Mt Victor
geocode fallback (`M T` → MT state token, verified live). This path is never
taken here because the row carries native coordinates; it is documented in
the module docstring and the stream log only.

---

## Decision

**PARTIAL-REGISTRABLE — PERMITS only.** Register the CCPC permits layer and
nothing else. `get_bowling_green_dataset(FeedType.COMPLAINTS_311 / SLA /
DEEDS)` raises a readable `KeyError`. Leaf files written:

* `apps/api/src/spatial/cities/bowling_green.py`
* `apps/api/src/producers/field_maps_bowling_green.py`
* `apps/api/tests/unit/test_producers_bowling_green.py`

Spatial grounding: 7 divisions (DOWNTOWN_UNIVERSITY, EAST_LOOP,
SCOTTSVILLE_CORRIDOR, NASHVILLE_SOUTHWEST, CAMPBELL_SOUTH,
RUSSELLVILLE_NORTHWEST, EAST_COUNTY_TRANSPARK) and 10 submarkets anchored on
live 2025+ permit-row coordinates (Mt Victor, Lovers Lane, Scottsville Rd,
Nashville Rd, Bluestem Sheldrake, Three Springs Rd, Russellville Rd, KY
Transpark, Fountain Square, WKU), all self-verified to nest inside their
division bbox inside the metro bbox (Parcel-extent-grounded). Spine delta
(enum member, aliases, registry entry, `METRO_META` + byte-synced
`apps/dashboard/public/index.html`) is deferred to the serial interlock hold.
