# Stream log — norfolk-g2 — 2026-08-24

## Outcome (2026-08-24)

Completed under US-75. Norfolk gains COMPLAINTS_311 (nbyu-xjez): watermark
creation_date, id service_request_number, cadence 7, needs_geocode +
geocode_context "Norfolk, VA", 5-entry field_map. Producers gained a
parse-time geocode hook gated on the registry declaration
(geocode_row_if_declared) because Avro doubles reject null coordinates —
coordinate-less wire events are impossible without schema evolution.

**Backend addition:** CensusBackend over geocoding.geo.census.gov
onelineaddress (TIGER range interpolation). The services hostname named in
research is unreachable from this environment and its addressbatch endpoint
rejects uploads on the reachable host; per-address endpoint works and is the
plan's substrate anyway. geocode_backend setting selects census|nominatim.

**G5'/G8' evidence (live, newest 500 rows of nbyu-xjez through the real
producer):** events 479/500 = **95.8%**; resolved coordinates 95.8%;
null-H3 **4.2%** <= 5%. Determinism re-check post-flush on Census:
108/108 identical.

**SLA (dpi6-sct5) REVERTED under G8':** ~34% of newest rows carry the literal
placeholder 'NO NORFOLK ADDRESS REQUIRED' (special-event licenses); real
addresses resolve ~100%, but feed-level resolved rate is ~65% — far above the
5% null-H3 ceiling. Candidate field_map pinned in tests for a future scoped
revisit. Registry carries the full rationale.

**Cross-stream repair (concurrent US-106 work):** scheduler _save_state
crashed on unwritable state paths (/data is container-only) and its new
default-test failed against .env overrides. Added an OSError guard mirroring
the tolerant read side, made the default-assertion hermetic
(Settings(_env_file=None)). Suite went red->green independent of US-75 scope.

**Gates:** interlock 20 passed; full suite 650 passed / 3 skipped / 0 failed;
ruff clean on touched files.
