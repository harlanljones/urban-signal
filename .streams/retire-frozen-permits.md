# Stream log — retire-frozen-permits — 2026-10-02

## Claim

- **Stream id:** `retire-frozen-permits`
- **Leaf files created/edited:**
  - corpus: `el_paso.yaml` and `melbourne.yaml` (the `permits` specs go)
  - `apps/api/src/spatial/cities/el_paso.py` and `melbourne.py` (what each
    metro's permits source was and why none is registered)
  - this file, `.streams/city-el-paso.md`, `.streams/US-296.md` and
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (`arcgis_el_paso_permits_url` and
  `arcgis_brevard_permits_url` go). `pytest -m interlock` passes.
- **Generated surfaces:** product facts (both metros' permits flag).

## Intent

Stop counting two permits feeds whose sources stopped years ago as live
coverage, and stop polling them.

## Decisions

- 2026-10-02 — El Paso's `NewResi2018_19` layer holds 4,683 permits issued
  2019-01-02 to 2021-07-30, and its siblings on ArcGIS Online nothing after
  2022-01-31. Its spec was alarm-exempt as a frozen snapshot, yet counted as
  the metro's permits family. The City's current new-construction layers are on
  `gis.elpasotexas.gov`, which answered every probe with Cloudflare's 403;
  measuring them from another network is the open step.
- 2026-10-02 — Melbourne's permits came from the City of Palm Bay's layer:
  150,427 permits issued 2004-01-12 to 2022-05-31, none since. No other
  Brevard County source has been found.
- 2026-10-02 — Both metros stay registered: El Paso keeps its `311`, licence
  and child-care feeds, Melbourne its SNAP licences.

## Current step

Done.

## Next step

El Paso's `Planning/NewResidential` and `Planning/NewCommercial` layers,
measured from a network the City's host does not refuse.
