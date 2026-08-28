# Wave 3 Phase-0 probe — Fresno, CA

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. Catalog/Hub `modified` is a label only; freshness evidence
is newest-row-by-watermark.

Linear: **US-329**. Ticket hint was ArcGIS Hub + Accela
(`fresno-prod.accela.com`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `cityoffresno.opendata.arcgis.com` | ArcGIS Hub (the fresno/data-fresno `opendata.arcgis.com` variants don't exist) | STAC `/items` search: `q=permit` → **3 hits, all Survey123 forms/results** (not permits); `q=311/license/sale/deed` → **0** |
| `fresno-prod.accela.com` | Accela production server; `/Fresno/` = "Welcome to the City of Fresno!" Citizen Access portal (HTTP 200) | **UI-only** — no anonymous bulk REST / CivicData export |
| `www.civicdata.com` | Accela CivicData CKAN | `package_search?q=fresno` → **1 package: "Illegal Dumping"** (wrong family) |
| Socrata | none (`domains=data.fresno.gov` → not found) | — |

## Summary

| Family | Tier | Newest watermark | Geocode | Register? |
|---|---|---|---|---|
| Permits | **3** — Accela Citizen Access is UI-only; Hub has Survey123 forms, no permit dataset | n/a | n/a | **no** |
| 311 | **3** — no dataset (`q=311` → 0); `311.fresno.gov` DNS-fail | n/a | n/a | **no** |
| SLA | **3** — zero license datasets | n/a | n/a | **no** |
| Deeds | **3** — Fresno County recording; no transaction stream | n/a | n/a | **no** |

**Wave-3-ready: no.** Register nothing.

## Evidence

- Hub permit "hits" are `survey123_*_form` / `survey123_*_results` items
  (internal survey collection, mod 2026), not a permit register.
- Accela ACA (`fresno-prod.accela.com/Fresno/`) serves the citizen search UI
  only; anonymous Automation API is token-gated (Accela standard). No CivicData
  CKAN mirror (1 unrelated package).
- `fresno.gov/311` → 400; `311.fresno.gov` → DNS fail. No Open311.

## Registration contract (`fresno`)

None. `get_dataset()` raises for PERMITS / 311 / SLA / DEEDS. Re-probe if
Fresno exports Accela records to CivicData or publishes a city Hub dataset.
