"""Registered aggregate market series (US-363 §1.1 / §2.5).

Series are national files keyed by geography, not city feeds, so they live
here rather than in ``CityRegistration.datasets``: a city can hold at most one
``DatasetSpec`` per ``FeedType``, while a single metro carries rent, value,
forecast, house-price-index and fair-market-rent series at once. Forcing them
into the city registry would either collapse five series into one spec or
fork ``FeedType`` five ways for feeds that emit no events at all.

Every entry was verified live 2026-08-28:

  ZORI zip        Zip_zori_uc_sfrcondomfr_sm_month.csv        through 2026-07-31
  ZHVI zip        Zip_zhvi_uc_sfrcondo_tier_..._month.csv     HTTP 200
  ZHVF metro      Metro_zhvf_growth_uc_sfrcondo_..._month.csv HTTP 200
  FHFA HPI metro  hpi_master.csv                              186,011 rows;
                  the (traditional, purchase-only, quarterly, MSA) slice is
                  14,200 rows over 100 MSAs, latest 2026 Q2
  HUD SAFMR zip   huduser.gov/hudapi/public/fmr/...           HTTP 401 without
                  a Bearer token (endpoint alive, credential required)
  ACS ZCTA        api.census.gov/data/2023/acs/acs5           key required

**Attribution is not optional for the Zillow series.** Zillow's ToU §4.C
permits derivative works from the aggregate research data *with attribution on
every surface that renders it*; ``attribution`` carries the exact string, and
``ZILLOW_ATTRIBUTION`` is the constant a rendering surface should assert
against. §5 of the same ToU bans automated querying of zillow.com proper — the
research CSV host used here is the published download channel, and each fetch
is one whole-file GET on the publisher's own monthly cadence.

Credentialed series (HUD, Census) declare their environment variable and fail
with a readable error when it is unset, rather than silently returning zero
rows.
"""

from __future__ import annotations

from typing import Dict, List

from src.producers.series_client import (
    LONG_ROWS,
    PROFILE_BULK_CSV,
    PROFILE_CENSUS_API,
    PROFILE_REST_API,
    WIDE_DATES_AS_COLUMNS,
    SeriesSpec,
)

ZILLOW_ATTRIBUTION = "Data Provided by Zillow Group"

_ZILLOW_CSV = "https://files.zillowstatic.com/research/public_csvs"

SERIES_REGISTRY: Dict[str, SeriesSpec] = {
    # ------------------------------------------------------------------ #
    # Zillow — monthly on the 16th                                        #
    # ------------------------------------------------------------------ #
    "zori_zip": SeriesSpec(
        series_id="zori_zip",
        source="zillow",
        dataset_id=f"{_ZILLOW_CSV}/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv",
        profile=PROFILE_BULK_CSV,
        layout=WIDE_DATES_AS_COLUMNS,
        geography_level="zip",
        geography_col="RegionName",
        metro_col="Metro",
        period_type="month",
        unit="usd_per_month",
        cadence_days=31,
        attribution=ZILLOW_ATTRIBUTION,
        notes="Observed rent index, ZIP level. Verified through 2026-07-31 on 2026-08-28.",
    ),
    "zhvi_zip": SeriesSpec(
        series_id="zhvi_zip",
        source="zillow",
        dataset_id=f"{_ZILLOW_CSV}/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
        profile=PROFILE_BULK_CSV,
        layout=WIDE_DATES_AS_COLUMNS,
        geography_level="zip",
        geography_col="RegionName",
        metro_col="Metro",
        period_type="month",
        unit="usd",
        cadence_days=31,
        attribution=ZILLOW_ATTRIBUTION,
        notes="Home value index, ZIP level, smoothed + seasonally adjusted.",
    ),
    "zhvf_metro": SeriesSpec(
        series_id="zhvf_metro",
        source="zillow",
        dataset_id=(
            f"{_ZILLOW_CSV}/zhvf_growth/"
            "Metro_zhvf_growth_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
        ),
        profile=PROFILE_BULK_CSV,
        layout=WIDE_DATES_AS_COLUMNS,
        geography_level="metro",
        geography_col="RegionName",
        metro_col="RegionName",
        period_type="month",
        unit="pct_growth",
        cadence_days=31,
        attribution=ZILLOW_ATTRIBUTION,
        notes="Forward-looking home value forecast, metro level.",
    ),
    # ------------------------------------------------------------------ #
    # FHFA — public domain, quarterly release calendar                    #
    # ------------------------------------------------------------------ #
    "fhfa_hpi_metro": SeriesSpec(
        series_id="fhfa_hpi_metro",
        source="fhfa",
        dataset_id="https://www.fhfa.gov/hpi/download/monthly/hpi_master.csv",
        profile=PROFILE_BULK_CSV,
        layout=LONG_ROWS,
        geography_level="metro",
        # `place_id` on MSA rows is the CBSA code (10180 = Abilene, TX), which
        # the crosswalk resolves directly; `place_name` is the readable label
        # and the fallback path.
        geography_col="place_id",
        metro_col="place_name",
        value_col="index_nsa",
        period_cols=["yr", "period"],
        period_type="quarter",
        row_filter={
            "hpi_type": "traditional",
            "hpi_flavor": "purchase-only",
            "frequency": "quarterly",
            "level": "MSA",
        },
        unit="index",
        cadence_days=92,
        notes=(
            "Purchase-only quarterly MSA slice: 14,200 rows / 100 MSAs, latest "
            "2026 Q2 (measured 2026-08-28). The all-transactions and "
            "expanded-data flavors are larger but mix appraisals into the "
            "index; purchase-only is the transaction-grounded one."
        ),
    ),
    # ------------------------------------------------------------------ #
    # Credentialed — annual                                               #
    # ------------------------------------------------------------------ #
    "hud_safmr_zip": SeriesSpec(
        series_id="hud_safmr_zip",
        source="hud",
        dataset_id="https://www.huduser.gov/hudapi/public/fmr/data/2026",
        profile=PROFILE_REST_API,
        geography_level="zip",
        geography_col="zip_code",
        value_col="Two-Bedroom",
        period_type="fiscal_year",
        auth="bearer",
        auth_env="HUD_API_TOKEN",
        row_filter={"year": "2026"},
        unit="usd_per_month",
        cadence_days=365,
        notes="Small Area FMRs, ZIP-level 40th-percentile rents. Published each Oct 1.",
    ),
    "acs_median_gross_rent_zcta": SeriesSpec(
        series_id="acs_median_gross_rent_zcta",
        source="census",
        dataset_id=(
            "https://api.census.gov/data/2023/acs/acs5"
            "?get=NAME,B25064_001E&for=zip%20code%20tabulation%20area:*"
        ),
        profile=PROFILE_CENSUS_API,
        geography_level="zip",
        geography_col="zip code tabulation area",
        value_col="B25064_001E",
        period_type="year",
        auth="api_key",
        auth_env="CENSUS_API_KEY",
        row_filter={"year": "2023"},
        unit="usd_per_month",
        cadence_days=365,
        notes=(
            "Static structural baseline the dynamic rent series trend away "
            "from. Coordinate with US-361 (tract-level demographics) — same "
            "source, different table and geography."
        ),
    ),
}

# Series that need no credential and can therefore run unattended today.
KEYLESS_SERIES: List[str] = [
    sid for sid, spec in SERIES_REGISTRY.items() if spec.auth == "none"
]


def get_series(series_id: str) -> SeriesSpec:
    """Look up one series, with a readable error for an unregistered id."""
    try:
        return SERIES_REGISTRY[series_id]
    except KeyError as exc:
        raise KeyError(
            f"series {series_id!r} is not registered; known series: "
            f"{sorted(SERIES_REGISTRY)}"
        ) from exc
