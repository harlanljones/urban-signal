# Stream log — city-port-st-lucie — US-289

## Claim

- Stream id: city-port-st-lucie
- Leaf files I will create/edit:
  - apps/api/src/spatial/cities/port_st_lucie.py
  - apps/api/src/producers/field_maps_port_st_lucie.py
- Spine files I expect to need (manifest-bound):
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/config.py
  - apps/api/src/serving/dashboard.py

## Intent

Onboard Port St. Lucie, FL as a new metro (Southeast). Verify a public permits
feed; register it (ArcGIS FeatureServer found). Add SNAP SLA (FL slice).
Register CityId.port_st_lucie in REGISTRY + ALIASES, export city in
`cities/__init__.py`, wire METRO_META and byte-sync the dashboard, and update
product facts.

## Decisions

- Verified public permits layer via Web AppBuilder config:
  https://services1.arcgis.com/YdUP5V6WwzeG8T8r/arcgis/rest/services/Permits/FeatureServer/0
  (DateIssued watermark, PermitID OID)
- SLA: SNAP fallback per ticket (snap_sla_spec("FL")).

## Current step

- Geometry and leaf registration authored; registry + aliases updated; dashboard
  METRO_META wired; product facts added.

## Next step

- Export dashboard static copy; run pytest -m interlock; fix any invariants.
