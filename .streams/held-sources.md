# Stream log — held-sources — 2026-10-02

## Claim

- **Stream id:** `held-sources`
- **Leaf files created/edited:**
  - `producers/csv_client.py` (an endpoint written with `{year}` reads this
    year's file and last year's; a `point_col` splits a `lat, lon` column)
    and `scripts/feed_staleness_probe.py` (dates such an endpoint by this
    year's file)
  - corpus files `long_beach.yaml` (a `311` spec) and `tucson.yaml` (a
    `deeds` spec), and their `cities/*.py` modules (the notes)
  - tests: `test_long_beach_311.py` and `test_tucson_deeds.py` (new);
    `test_csv_client.py`, `test_feed_staleness_probe.py` and
    `test_snapshot_reach.py`
  - notes in `docs/research/one-family-depth-2026-10-02.md` and
    `snapshot-reach-2026-09-30.md`, this file and `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the two sources), `city_registry.py`
  (`DatasetSpec.point_col`) and `scheduler.py` (forwards `point_col` to the
  CSV client). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and the two
  `cities/*.json`. The dashboard lists metros by name, so it is unchanged.

## Intent

Register the two sources the one-family probe held for want of a CSV client
change: Pima County's yearly sales files for Tucson's deeds and Long Beach's
request export for its `311`.

## Decisions

- 2026-10-02 — Write a yearly file's year as `{year}` in the endpoint and
  the zip member, and read this year's file and last year's, rather than a
  year map: Pima keys its files by the year a sale closed, so a window that
  reaches back past New Year needs both files, and the scheduler's year map
  names zip members, not URLs.
- 2026-10-02 — Pass over a missing file for this year alone (it may not
  exist in the first days of January): a 404, or a web page in its place,
  since the Assessor's site answers a file it lacks (2027's, asked once)
  with its own page and a 200. Any other failed download fails the poll, so
  a poll never publishes half its window as the whole.
- 2026-10-02 — Split Long Beach's `geolocation` in the CSV client, named by
  a typed spec field, rather than in the 311 producer: the column is the
  export's form of an OpenDataSoft geo point, and placing rows is the
  client's job for every other CSV feed.
- 2026-10-02 — Key Tucson's sales on the sequence number with the parcel:
  one affidavit can convey several parcels, and no pair repeats within a
  file or across the two.
- 2026-10-02 — Read Long Beach's last seven days with a cap of 2,000: the
  week held 1,314 on 2026-10-02, and a first poll under the default 1,000
  published only the newest 1,000. `expected_cadence_days` 2: the export was
  rebuilt once that day, at 14:00Z.
- 2026-10-02 — Leave the staleness probe's other gap, which reads a zipped
  file without its member, delimiter or column names, for its own change.

## Current step

Done.

## Next step

None for these two feeds. The other held sources wait on the re-checks named
in the research note.
