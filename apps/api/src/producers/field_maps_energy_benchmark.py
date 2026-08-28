"""Per-city field maps for building energy-benchmarking feeds (US-363 §2.7).

Three cities publish an annual benchmarking disclosure on Socrata and none of
them agrees on a single column name:

* NYC LL84 ``5zyy-y8am`` — 253 columns, ``report_year``, ENERGY STAR under
  ``energy_star_score``, EUI under ``site_eui_kbtu_ft``, native
  ``latitude``/``longitude`` (re-probed 2026-08-28: max report_year 2024,
  n=103,259; 1,354 of the 39,090-row 2024 cohort have a null coordinate).
* Chicago ``xq83-jr8c`` — ``data_year`` (max 2023, the feed lags a year,
  n=28,329), native lat/lng plus a Socrata ``location`` container, and a
  city-specific ``chicago_energy_rating`` alongside ``reporting_status``.
* Seattle ``teqw-tu6e`` — ``datayear`` (max 2024, n=34,699), all-lowercase
  columns, ``compliancestatus`` + ``ghgemissionsintensity``, ``demolished``
  boolean.

Every numeric column on the NYC feed carries the string sentinel
``"Not Available"`` (and Seattle uses ``"NA"`` on its use-type columns). The
parser coerces those to null rather than 0 — a building with no reported EUI
is not a building with an EUI of zero, and averaging the difference would
silently drag every hex mean toward the floor.

This module is a leaf: the shared ``field_maps.py`` dispatch is untouched.
Maps are keyed by canonical ``ContextObservationEvent`` field names plus the
metric catalogs, which the producer walks to emit one observation per
(building, metric, report year).
"""

from typing import Any, Dict, List

# Sentinel strings that mean "no value", never 0.0.
NOT_AVAILABLE_SENTINELS = frozenset(
    {
        "",
        "na",
        "n/a",
        "not available",
        "not applicable",
        "not available: standalone property",
        "unavailable",
        "none",
        "null",
        "-",
        "--",
    }
)

# Metric name -> (column candidates, unit). The producer emits one
# ContextObservationEvent per metric that resolves to a real number, so a
# building missing ENERGY STAR still contributes its EUI and GHG rows.
# Column spellings verified live 2026-08-28.
NYC_ENERGY_METRICS: Dict[str, Dict[str, Any]] = {
    "energy_star_score": {
        "columns": ["energy_star_score"],
        "unit": "score",
    },
    "site_eui": {
        "columns": ["site_eui_kbtu_ft", "weather_normalized_site_eui"],
        "unit": "kbtu_per_sqft",
    },
    "source_eui": {
        "columns": ["source_eui_kbtu_ft", "weather_normalized_source"],
        "unit": "kbtu_per_sqft",
    },
    "ghg_total": {
        "columns": ["total_location_based_ghg"],
        "unit": "metric_tons_co2e",
    },
    "ghg_intensity": {
        "columns": ["total_location_based_ghg_1"],
        "unit": "kg_co2e_per_sqft",
    },
    "gross_floor_area": {
        "columns": ["property_gfa_calculated", "property_gfa_self_reported"],
        "unit": "sqft",
    },
}

CHICAGO_ENERGY_METRICS: Dict[str, Dict[str, Any]] = {
    "energy_star_score": {
        "columns": ["energy_star_score"],
        "unit": "score",
    },
    "site_eui": {
        "columns": ["site_eui_kbtu_sq_ft", "weather_normalized_site_eui_kbtu_sq_ft"],
        "unit": "kbtu_per_sqft",
    },
    "source_eui": {
        "columns": ["source_eui_kbtu_sq_ft", "weather_normalized_source_eui_kbtu_sq_ft"],
        "unit": "kbtu_per_sqft",
    },
    "ghg_total": {
        "columns": ["total_ghg_emissions_metric_tons_co2e"],
        "unit": "metric_tons_co2e",
    },
    "ghg_intensity": {
        "columns": ["ghg_intensity_kg_co2e_sq_ft"],
        "unit": "kg_co2e_per_sqft",
    },
    "gross_floor_area": {
        "columns": ["gross_floor_area_buildings_sq_ft"],
        "unit": "sqft",
    },
    "chicago_energy_rating": {
        "columns": ["chicago_energy_rating"],
        "unit": "rating",
    },
}

SEATTLE_ENERGY_METRICS: Dict[str, Dict[str, Any]] = {
    "energy_star_score": {
        "columns": ["energystarscore"],
        "unit": "score",
    },
    "site_eui": {
        "columns": ["siteeui_kbtu_sf", "siteeuiwn_kbtu_sf"],
        "unit": "kbtu_per_sqft",
    },
    "source_eui": {
        "columns": ["sourceeui_kbtu_sf", "sourceeuiwn_kbtu_sf"],
        "unit": "kbtu_per_sqft",
    },
    "ghg_total": {
        "columns": ["totalghgemissions"],
        "unit": "metric_tons_co2e",
    },
    "ghg_intensity": {
        "columns": ["ghgemissionsintensity"],
        "unit": "kg_co2e_per_sqft",
    },
    "gross_floor_area": {
        "columns": ["propertygfatotal", "propertygfabuildings"],
        "unit": "sqft",
    },
}

# Canonical ContextObservationEvent field -> column spellings.
NYC_ENERGY_FIELD_MAP: Dict[str, List[str]] = {
    "asset_id": ["property_id"],
    "asset_name": ["property_name", "address_1"],
    "period": ["report_year"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "address": ["address_1"],
    "zipcode": ["postal_code"],
    "borough": ["borough", "city"],
    "source_neighborhood": ["nta2020"],
    "category": ["primary_property_type", "primary_property_type_self"],
    "compliance": ["reason_s_for_no_score"],
}

CHICAGO_ENERGY_FIELD_MAP: Dict[str, List[str]] = {
    "asset_id": ["id"],
    "asset_name": ["property_name", "address"],
    "period": ["data_year"],
    "latitude": ["latitude", "location.latitude"],
    "longitude": ["longitude", "location.longitude"],
    "address": ["address"],
    "zipcode": ["zip_code"],
    "borough": ["community_area"],
    "source_neighborhood": ["community_area"],
    "category": ["primary_property_type"],
    "compliance": ["reporting_status"],
}

SEATTLE_ENERGY_FIELD_MAP: Dict[str, List[str]] = {
    "asset_id": ["osebuildingid"],
    "asset_name": ["buildingname", "address"],
    "period": ["datayear"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "address": ["address"],
    "zipcode": ["zipcode"],
    "borough": ["neighborhood"],
    "source_neighborhood": ["neighborhood"],
    "category": ["epapropertytype", "buildingtype", "largestpropertyusetype"],
    "compliance": ["compliancestatus"],
}

# Metric catalogs keyed by city id, consumed by the producer via
# ``metrics_for(city_id)``. Kept beside the field maps so a new city is one
# dict pair, not a producer edit.
ENERGY_METRICS_BY_CITY: Dict[str, Dict[str, Dict[str, Any]]] = {
    "nyc": NYC_ENERGY_METRICS,
    "chicago": CHICAGO_ENERGY_METRICS,
    "seattle": SEATTLE_ENERGY_METRICS,
}

# Compliance strings that count as "not compliant" for the per-hex
# non-compliance share. Compared case-folded after stripping.
NON_COMPLIANT_VALUES = frozenset(
    {
        "not compliant",
        "non-compliant",
        "noncompliant",
        "not submitted",
        "missing data",
        "error - correct default data",
    }
)


def metrics_for(city_id: str) -> Dict[str, Dict[str, Any]]:
    """Return the metric catalog for a city, or an empty catalog if unknown."""
    return ENERGY_METRICS_BY_CITY.get((city_id or "").lower(), {})


def is_missing(value: Any) -> bool:
    """True when a benchmarking cell means "no value" rather than a number.

    Socrata returns every one of these feeds' numerics as strings, and all
    three cities encode absence as prose (``"Not Available"``, ``"NA"``,
    ``"Not Applicable"``). Treating those as 0.0 would poison every hex mean.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in NOT_AVAILABLE_SENTINELS
    return False


def to_float(value: Any) -> "float | None":
    """Coerce a benchmarking cell to float, or None when it is a sentinel."""
    if is_missing(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def is_non_compliant(value: Any) -> "bool | None":
    """Classify a compliance string; None when the city reports nothing."""
    if is_missing(value):
        return None
    return str(value).strip().lower() in NON_COMPLIANT_VALUES
