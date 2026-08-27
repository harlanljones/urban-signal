# Stream log — probe-miami-dade — 2026-08-27

US-199 sub-stream. Finish Miami-Dade row-level probe from the host fingerprint.
Do not write `docs/research/wave-3-probe-miami.md` (parent stream owns it).

## Claim

- **Stream id:** `probe-miami-dade`
- **Leaf files I will create/edit:**
  - `.streams/probe-miami-dade.md` (this file)
  - `docs/research/wave-3-probe-miami-dade.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Search Miami-Dade ArcGIS Hub + `gisweb.miamidade.gov` REST for permits,
311, SLA, deeds. Row-level newest-watermark probe. Tier 1/2/3.

## Decisions

- 2026-08-27 12:31 PT — Fingerprint: Hub at opendata.miamidade.gov /
  gis-mdc.opendata.arcgis.com (search + data.json + DCAT live). Not
  Socrata (domain not found). Not CKAN. REST 11.1 at
  gisweb.miamidade.gov includes folders `311`, `EnerGov`, others.
  gis.miamigov.com timed out.
- 2026-08-27 13:05 PT — Row-level probe complete. Wrote
  `docs/research/wave-3-probe-miami-dade.md`. Platform = ArcGIS Hub
  (`8Pc9XBTAsYuxx9Ny`) + gisweb 11.1. DCAT/data.json HTTP 200 but
  truncated JSON — discovery used Hub search v1. gisweb `311/` folder
  is empty; EnerGov is not the permit register.
- Tiers: PERMITS **2** (`miamidade_permit_data/0`, issued **2026-08-25**,
  address-only `PropertyAddress`); 311 **3** (public slices through
  2023 frozen; `data_311_2024` Token Required); SLA **1** (Local
  Business Tax view, 193,868 pts, YEAR=2026, LAT/LON 100%); DEEDS **1**
  (`MD_ComparableSales/MapServer/5`, `DOS_1` **20260821**, native
  points + grantor/book). Wave-3-ready **yes**, partial (no live 311).

## Current step

Leaf complete. Research file + this log updated. No spine edits.

## Next step

Orchestrator synthesizes US-199 with Broward / Fort Lauderdale /
parent Miami streams. This stream does not comment on or close Linear.
