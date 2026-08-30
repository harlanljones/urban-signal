"""SeriesSpec-shaped plain dict for the FTA NTD Complete Monthly Ridership feed (US-402).

LEAF data — NOT registered anywhere. Field names mirror the ``SeriesSpec``
dataclass in ``src/producers/series_client.py`` exactly (``SeriesSpec(**spec)``
constructs from this dict with zero massaging) so the spine can copy it
mechanically during the interlock hold.

Source: Socrata SODA mirror of the National Transit Database Complete Monthly
Ridership (with Adjustments and Estimates) at
``datahub.transportation.gov/resource/8bui-9xvu``. Keyless, refreshed weekly,
~2-month lag (verified 2026-08-30: rows present through 2026-06-01). Rows are
per (agency, UZA, mode, TOS, month) with four numeric measures:

    UPT  unlinked passenger trips
    VRM  vehicle revenue miles
    VRH  vehicle revenue hours
    VOMS vehicles operated in maximum service

The ``series_id`` is ``ntd_monthly_ridership`` and the key is
``(city_id, series_id, month)`` — an upsert into ``macro_series`` via the
existing ``SeriesClient``/``MacroSeriesStore`` pattern (US-363 §1.1). One SODA
query covers every registered city; no per-city machinery.

``PROFILE_SOCRATA`` is a new profile constant (``"socrata"``) deliberately not
yet recognized by ``SeriesClient.fetch``: the spine phase adds the SODA
dispatch that pages the endpoint through the existing ``SocrataClient``.
Declaring it here keeps the spec data-complete without inventing machinery.
"""

from __future__ import annotations

# New series profile for a keyless Socrata SODA JSON endpoint. Not wired into
# SeriesClient.fetch yet — the spine phase adds the dispatch branch.
PROFILE_SOCRATA = "socrata"

NTD_MONTHLY_RIDERSHIP_ENDPOINT = "https://datahub.transportation.gov/resource/8bui-9xvu.json"

# The four NTD monthly measures and their units. Each is a distinct series key
# so a metric is never overwritten by another.
NTD_MEASURES: dict[str, str] = {
    "upt": "unlinked_passenger_trips",
    "vrm": "vehicle_revenue_miles",
    "vrh": "vehicle_revenue_hours",
    "voms": "vehicles_max_service",
}

# Source columns carried on every NTD monthly ridership row.
NTD_FIELDS: tuple[str, ...] = (
    "ntd_id",
    "agency",
    "uza_name",
    "mode",
    "tos",
    "date",
    "upt",
    "vrm",
    "vrh",
    "voms",
)


def ntd_ridership_spec(measure: str = "upt") -> dict:
    """SeriesSpec-shaped dict for one NTD monthly measure.

    ``SeriesSpec(**ntd_ridership_spec("upt"))`` constructs unchanged. ``measure``
    is one of NTD_MEASURES; the value rides in ``value_col`` so a long-row/SODA
    parser picks up the right cell, and the unit travels with the observation.
    """
    if measure not in NTD_MEASURES:
        raise ValueError(
            f"unknown NTD measure {measure!r}; expected one of {sorted(NTD_MEASURES)}"
        )
    return {
        "series_id": f"ntd_{measure}",
        "source": "ntd",
        "dataset_id": NTD_MONTHLY_RIDERSHIP_ENDPOINT,
        "profile": PROFILE_SOCRATA,
        "geography_level": "metro",
        "geography_col": "uza_name",
        "metro_col": "uza_name",
        "value_col": measure,
        "period_cols": ["date"],
        "period_type": "month",
        "auth": "none",
        "unit": NTD_MEASURES[measure],
        "cadence_days": 7,
        "ingestion_mode": "full",
        "notes": (
            "FTA NTD Complete Monthly Ridership (Socrata 8bui-9xvu). Weekly "
            "refresh, ~2-month lag. Keyed (city_id, series_id, month); one SODA "
            "query covers every registered city. UZA name -> city resolution is "
            "a hand-authorable crosswalk (spine)."
        ),
    }


# Canonical spec: unlinked passenger trips, the headline ridership measure.
NTD_MONTHLY_RIDERSHIP_SPEC: dict = ntd_ridership_spec("upt")
