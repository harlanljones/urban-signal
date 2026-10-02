# Stream log — wrong-place-permits — 2026-10-02

## Claim

- **Stream id:** `wrong-place-permits`
- **Leaf files created/edited:**
  - corpus files `orlando.yaml` (the City's permits in place of the statewide
    layer), `ocala.yaml` and `macon_bibb.yaml` (permits removed);
    `cities/orlando.py` and `cities/macon_bibb.py` (the module notes)
  - `fl_cadastral_spec.py` and `field_maps_fl_cadastral.py` (county codes
    11–77)
  - `socrata_client.py` and `acquisition.py` (a Socrata `select` reaches the
    server as `$select`)
  - tests: `test_orlando_permits.py` and `test_wrong_place_permits.py` (new);
    `test_fl_cadastral_spec.py`, `test_producers_orlando.py`,
    `test_snapshot_reach.py` (two gaps gone) and `test_scheduler.py` (the
    fixture refuses live requests)
  - notes in `docs/research/two-family-depth-2026-09-30.md` and
    `snapshot-reach-2026-09-30.md`, this file, `.streams/dispatch-log.md`,
    and dated lines in `.streams/city-macon_bibb.md` and
    `.streams/us398-fl-cadastral.md`
- **Spine files touched:** `config.py` (Orlando's permits and address
  points; Macon-Bibb's permits setting removed). `pytest -m interlock`
  passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/macon_bibb.json`, `cities/ocala.json` and `cities/orlando.json`.
  The dashboard lists metros by name, so it is unchanged.

## Intent

Repair or retract three permit feeds that read somewhere other than their
metro: Ocala's and Orlando's statewide parcel slices (Jackson and Levy
counties) and Macon-Bibb's layer (St. Catharines, Ontario).

## Decisions

- 2026-10-02 — Number the statewide layer's counties 11–77 (Alachua 11, Dade
  23, Marion 52, Orange 58), as four live parcels placed them, and register
  it for no metro: a year-built cohort of parcels is not a permit stream.
- 2026-10-02 — Read Orlando's permits from the City's permit applications,
  issued permits only, newest first, and place them on the City's own address
  points by `SitusAddress` before the geocoder: the geocoder alone placed 683
  of the newest 1,000 and missed whole new subdivisions; with the address
  points 973 were placed. The parcel-number join placed fewer (780) and
  spread some parcels' points over kilometres, so it is not used.
- 2026-10-02 — Cap a poll at 3,000 permits: the newest issue date trailed
  the table's update by eight days, so a week of permits (about 1,000) can
  land at once, and a newest-first poll never reaches rows past its cap.
- 2026-10-02 — Retract Ocala's and Macon-Bibb's permits rather than leave
  them registered: neither publishes a current permit stream (the public
  folder of Ocala's City GIS holds 61 new commercial projects; Macon-Bibb's
  own layer stops in 2017).

## Current step

Done.

## Next step

Register the Florida deeds (Gainesville, Lakeland, Ocala, Tampa). Orlando's
metro box ends at 81.22° W, west of the City's south-eastern neighbourhoods,
which hold 4% of its permits; widening it would change the map's tiles and
belongs to its own change.
