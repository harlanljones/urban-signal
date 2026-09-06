"""Census ACS 5-year API client and helpers (US-361 pilot & US-438 Bay Area dasymetric).

- Targets ACS 5-year estimates (`https://api.census.gov/data/{vintage}/acs/acs5`).
- Fetches block-group rows for one or more counties (state + county FIPS).
- Handles batching queries when variable count exceeds the Census API limit.
- Returns BGRow records consumable by `aggregate_blockgroup_to_h3` and `DasymetricInterpolator`.

Live fetch requires a Census API key provided in environment variable
`CENSUS_API_KEY` or passed explicitly. Tests run on fixtures without network access.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import httpx

from src.spatial.acs_baseline import ACS_BASELINE_FEATURES, BGRow
from src.spatial.acs_variables import (
    ACS_DASYMETRIC_VARIABLES,
    BAY_AREA_COUNTIES,
    get_required_acs_variable_codes,
)

DEFAULT_DATASET = "https://api.census.gov/data/2023/acs/acs5"
ENV_API_KEY = "CENSUS_API_KEY"
CENSUS_VARIABLE_BATCH_SIZE = 40


def variables_for_features(feature_names: Sequence[str] | None = None) -> list[str]:
    """Return the set of ACS variable codes needed for the given baseline features.

    Includes both estimate and MOE fields for sum features; ratio features contribute
    numerator and denominator estimate codes; median-approx features contribute only
    the median estimate and its "weight" proxy if the catalog specifies one.
    """
    names = feature_names or list(ACS_BASELINE_FEATURES.keys())
    vars_set: set[str] = set()
    for name in names:
        if name in ACS_BASELINE_FEATURES:
            f = ACS_BASELINE_FEATURES[name]
            if f.agg == "sum":
                if f.estimate_var:
                    vars_set.add(f.estimate_var)
                if f.moe_var:
                    vars_set.add(f.moe_var)
            elif f.agg == "ratio":
                if f.numerator_var:
                    vars_set.add(f.numerator_var)
                if f.denominator_var:
                    vars_set.add(f.denominator_var)
            elif f.agg == "weighted_median_approx":
                if f.estimate_var:
                    vars_set.add(f.estimate_var)
                if f.weight_var:
                    vars_set.add(f.weight_var)
        elif name in ACS_DASYMETRIC_VARIABLES:
            d_spec = ACS_DASYMETRIC_VARIABLES[name]
            vars_set.add(d_spec.estimate_var)
            vars_set.add(d_spec.moe_var)

    # GEO dimension columns
    vars_set.update(("state", "county", "tract", "block group"))
    return sorted(vars_set)


@dataclass(frozen=True)
class ACSClient:
    """Thin ACS Data API client for `acs5` block-group pulls."""

    api_key: str | None = None
    base_url: str = DEFAULT_DATASET
    timeout_s: float = 60.0
    vintage: int = 2023

    def _require_key(self) -> str:
        key = self.api_key or os.getenv(ENV_API_KEY) or ""
        if not key:
            raise RuntimeError(
                "Missing Census API key. Set CENSUS_API_KEY in the environment to enable live fetch."
            )
        return key

    def _build_url(self) -> str:
        if self.base_url != DEFAULT_DATASET:
            return self.base_url
        return f"https://api.census.gov/data/{self.vintage}/acs/acs5"

    def fetch_block_groups(
        self,
        state_fips: str,
        county_fips: Iterable[str],
        variable_codes: Sequence[str],
    ) -> list[dict[str, str]]:
        """Fetch block-group rows for the given state and counties.

        Handles query chunking to respect Census API variable count caps.
        Returns a list of dicts with keys matching the requested `variable_codes` plus
        the geography dimensions: `state`, `county`, `tract`, `block group`.
        """
        key = self._require_key()
        headers = {"User-Agent": "urban-signal-acs-client"}
        url = self._build_url()

        # Separate geo variables from requested census variables
        geo_vars = ["state", "county", "tract", "block group"]
        data_vars = [v for v in variable_codes if v not in geo_vars and v != "NAME"]

        # Chunk variables if needed (Census API limits 'get' list to ~50 variables)
        batches: list[list[str]] = []
        if data_vars:
            for i in range(0, len(data_vars), CENSUS_VARIABLE_BATCH_SIZE):
                batches.append(data_vars[i : i + CENSUS_VARIABLE_BATCH_SIZE])
        else:
            batches.append([])

        merged_by_geoid: dict[str, dict[str, str]] = {}

        with httpx.Client(timeout=self.timeout_s, headers=headers, follow_redirects=True) as client:
            for cty in county_fips:
                cty_clean = cty.zfill(3)
                for batch in batches:
                    query_vars = batch + [v for v in geo_vars if v not in batch]
                    get_param = ",".join(query_vars)
                    params = {
                        "get": get_param,
                        "for": "block group:*",
                        "in": f"state:{state_fips} county:{cty_clean}",
                        "key": key,
                    }
                    resp = client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    if not data or not isinstance(data, list) or not data[0]:
                        continue
                    header = data[0]
                    for row in data[1:]:
                        rec = {col: val for col, val in zip(header, row)}
                        s = rec.get("state", "")
                        co = rec.get("county", "")
                        tr = rec.get("tract", "")
                        bg = rec.get("block group", "")
                        geoid = f"{s}{co}{tr}{bg}"
                        if geoid in merged_by_geoid:
                            merged_by_geoid[geoid].update(rec)
                        else:
                            merged_by_geoid[geoid] = rec

        return list(merged_by_geoid.values())

    def fetch_bay_area_block_groups(
        self,
        variable_codes: Sequence[str] | None = None,
    ) -> list[dict[str, str]]:
        """Fetch block groups for all 9 Bay Area counties."""
        codes = variable_codes or get_required_acs_variable_codes()
        return self.fetch_block_groups(
            state_fips="06",
            county_fips=sorted(BAY_AREA_COUNTIES.keys()),
            variable_codes=codes,
        )


def rows_to_bgrows(
    rows: Iterable[Mapping[str, str]], needed_vars: Sequence[str]
) -> list[BGRow]:
    """Convert raw ACS API dict rows to BGRow records keyed by 12-digit BG FIPS.

    For estimate/MOE coding:
    - The estimate codes (e.g. B01003_001E) are parsed as floats.
    - Companion MOE codes (B01003_001M) are parsed as floats when present.
    Missing, suppressed, or non-numeric values (e.g. -666666666) are skipped or set to 0.0.
    """
    out: dict[str, dict[str, tuple[float, float]]] = {}
    est_vars = {v for v in needed_vars if v.endswith("E")}
    moe_vars = {v for v in needed_vars if v.endswith("M")}
    moe_pairs: dict[str, str] = {e: e[:-1] + "M" for e in est_vars if (e[:-1] + "M") in moe_vars}

    for rec in rows:
        # Build 12-digit BG FIPS: state(2) + county(3) + tract(6) + bg(1)
        s = rec.get("state")
        co = rec.get("county")
        tr = rec.get("tract")
        bg = rec.get("block group")
        if not (s and co and tr and bg):
            continue
        bg_fips12 = f"{s}{co}{tr}{bg}"
        store = out.setdefault(bg_fips12, {})
        for e in est_vars:
            est_str = rec.get(e)
            if est_str is None or est_str == "" or est_str in ("-666666666", "-888888888", "-999999999", "null"):
                continue
            try:
                est_val = float(est_str)
            except ValueError:
                continue
            moe_code = moe_pairs.get(e)
            moe_val = 0.0
            if moe_code:
                m_str = rec.get(moe_code)
                if m_str is not None and m_str != "" and m_str not in ("-666666666", "-888888888", "-999999999", "null"):
                    try:
                        moe_val = float(m_str)
                    except ValueError:
                        moe_val = 0.0
            store[e] = (est_val, moe_val)
    return [BGRow(bg_fips12=k, values=v) for k, v in out.items()]


def relative_moe_flags(
    features: Mapping[str, tuple[float, float]], threshold: float = 0.5
) -> dict[str, bool]:
    """Flag features whose relative MOE exceeds the threshold (default 50%).

    Relative MOE is `moe / abs(estimate)` with a floor that zero/near-zero estimates
    are treated as high-uncertainty (flagged).
    """
    flags: dict[str, bool] = {}
    for name, (est, moe) in features.items():
        if est is None or moe is None:
            flags[name] = True
            continue
        if est == 0.0:
            flags[name] = True
            continue
        rel = abs(moe) / abs(est)
        flags[name] = rel >= threshold
    return flags
