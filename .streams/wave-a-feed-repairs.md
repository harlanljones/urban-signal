# Stream log — wave-a-feed-repairs — 2026-08-23

## Claim

- **Stream id:** `wave-a-feed-repairs`
- **Leaf files I will create/edit:** `tests/unit/test_producers_la.py`,
  `.env.example`, `.streams/wave-a-feed-repairs.md` (this file)
- **Spine files I expect to need:** `src/config.py`,
  `src/spatial/city_registry.py`, `src/producers/complaints_311_producer.py`,
  `src/producers/deeds_acris_producer.py`

Single stream holds the interlock for the whole wave — no parallel dispatch,
so the one-at-a-time rule is satisfied trivially.

## Intent

Apply the config-line and registry repairs proved by
`docs/research/current-city-feed-gaps.md`: repoint SF deeds (`5cei-gny5` →
`wv5m-vpq2`, currently serving Eviction Notices), SF permits (`i98e-46e2` →
successor `i98e-djp9`), Chicago deeds (deleted `x5kz-z7if` → Cook County
Assessor Parcel Sales `wvhk-k5uv`), and register LA's relaunched MyLA311 feed
(`2cy6-i7zn`) with its parser fallbacks. Done looks like: gates green
(`pytest -m interlock` + full suite), no stale dataset IDs left in
`src/config.py` / `.env.example`, LA registering three feeds with DEEDS still
deliberately absent.

## Decisions

- 13:55 — Chicago deeds keeps platform `socrata`; new watermark `sale_date`,
  id keys `doc_no`/`row_id`/`pin`. Feed has NO coordinates; verified downstream
  tolerance before relying on it: `DeedEvent.h3_*` are Optional,
  `postgis_sync._extract_str(row.get("h3_res7"), "")` writes empty strings, and
  the features pipeline selects the column unguarded — same contract the KC
  ArcGIS path already exercises when geometry is missing.
- 13:56 — Adding the SLA producer's 0.0/0.0 "null island" guard to the 311
  parser while touching it: MyLA311's 6.2% ungeocoded rows include zero
  placeholders, and the SLA producer already established this exact guard with
  the identical rationale.
- 13:57 — LA 311 city sniffing keys on `casenumber`/`srnumber`/
  `department_name__c`, placed ahead of the SF branch per the survey note;
  backfill sets (2015–2024) use `srnumber`/`requesttype` so they resolve too.

## Current step

Done.

## Next step

None. Gates: `pytest -m interlock` 17/17; full suite 230/230. The one
pre-existing failure (`test_export_snapshot.py::test_manifest_shape`, stale
3-city assertion predating Seattle/LA) was fixed as leaf work so the suite is
green for future gate runs; ruff/mypy findings were baselined against HEAD and
are unchanged (pre-existing debt, not introduced here). Artifacts left
uncommitted — local policy denies `git commit`.
