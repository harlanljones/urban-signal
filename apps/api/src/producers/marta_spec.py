"""DatasetSpec-shaped plain dict for the MARTA station entrances/exits feed (US-404).

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from this dict with zero massaging) so the spine can copy it
mechanically during the interlock hold.

Source: City of Atlanta Socrata mirror of MARTA rail station entrance/exit
counts, ``data.atlantaga.gov/resource/nwqk-3q5y``. Keyless, refreshed weekly,
station-level. Zero new machinery: rides the existing ``SocrataClient`` +
``DatasetSpec`` acquisition path. Output is a weekly station entrances/exits
context covariate on ``EnrichedH3Feature`` (no new event schema).

The feed has no per-row ``:updated_at`` watermark column, so the spec is
snapshot-mode: full pull, churn via cross-run id-dedup diff, freshness via
Socrata ``rowsUpdatedAt`` (the KC SLA precedent, US-134).
"""

from __future__ import annotations

MARTA_ENTRANCES_EXITS_ENDPOINT = "https://data.atlantaga.gov/resource/nwqk-3q5y.json"

# The station-level id keys are the Socrata primary/row id and the station
# code.  ``non_spatial`` is False — rows carry lat/lng, so the existing
# classify → geocode → H3 path sites them.
MARTA_ENTRANCES_EXITS_SPEC: dict = {
    "endpoint": MARTA_ENTRANCES_EXITS_ENDPOINT,
    "platform": "socrata",
    "watermark_col": "",
    "id_keys": [":id"],
    "topic": "",
    "interval_seconds": 604800,  # weekly
    "producer_key": "marta_entrances_exits",
    "expected_cadence_days": 7,
    "ingestion_mode": "snapshot",
    "order_by": ":id",
    "needs_geocode": False,
    "non_spatial": False,
    "field_map": {},
}
