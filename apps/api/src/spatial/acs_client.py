"""Census ACS 5-year API client and helpers (US-361 pilot).

- Targets ACS 2020–2024 5-year (`/data/2024/acs/acs5`) by default.
- Fetches block-group rows for one or more counties (state + county FIPS).
- Returns BGRow records consumable by `aggregate_blockgroup_to_h3`.

Live fetch requires a Census API key provided in environment variable
`CENSUS_API_KEY`. Tests run on fixtures without network access.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import httpx

from src.spatial.acs_baseline import ACS_BASELINE_FEATURES, BGRow

DEFAULT_DATASET = "https://api.census.gov/data/2024/acs/acs5"
ENV_API_KEY = "CENSUS_API_KEY"


def variables_for_features(feature_names: Optional[Sequence[str]] = None) -> List[str]:
    """Return the set of ACS variable codes needed for the given baseline features.

    Includes both estimate and MOE fields for sum features; ratio features contribute
    numerator and denominator estimate codes; median-approx features contribute only
    the median estimate and its "weight" proxy if the catalog specifies one.
    """
    names = feature_names or list(ACS_BASELINE_FEATURES.keys())
    vars_set: set[str] = set()
    for name in names:
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
            # weight_var is a proxy; include it if present
            if f.weight_var:
                vars_set.add(f.weight_var)
    # GEO dimension columns
    vars_set.update(("state", "county", "tract", "block group"))
    return sorted(vars_set)


@dataclass(frozen=True)
class ACSClient:
    """Thin ACS Data API client for `acs5` block-group pulls."""

    api_key: Optional[str] = None
    base_url: str = DEFAULT_DATASET
    timeout_s: float = 60.0

    def _require_key(self) -> str:
        key = self.api_key or os.getenv(ENV_API_KEY) or ""
        if not key:
            raise RuntimeError(
                "Missing Census API key. Set CENSUS_API_KEY in the environment to enable live fetch."
            )
        return key

    def fetch_block_groups(
        self,
        state_fips: str,
        county_fips: Iterable[str],
        variable_codes: Sequence[str],
    ) -> List[Dict[str, str]]:
        """Fetch block-group rows for the given state and counties.

        Returns a list of dicts with keys matching the requested `variable_codes` plus
        the geography dimensions: `state`, `county`, `tract`, `block group`.
        """
        key = self._require_key()
        headers = {"User-Agent": "urban-signal-acs-client"}
        out: List[Dict[str, str]] = []
        # Census API caps the `get` list (~50 vars). Our catalog stays under the cap.
        get_param = ",".join(variable_codes)
        with httpx.Client(timeout=self.timeout_s, headers=headers, follow_redirects=True) as client:
            for cty in county_fips:
                params = {
                    "get": get_param,
                    "for": "block group:*",
                    "in": f"state:{state_fips} county:{cty}",
                    "key": key,
                }
                resp = client.get(self.base_url, params=params)
                # When unauthorized/missing key, Census returns an HTML page with "Missing Key"
                resp.raise_for_status()
                data = resp.json()
                if not data or not isinstance(data, list) or not data[0]:
                    continue
                header = data[0]
                for row in data[1:]:
                    record = {col: val for col, val in zip(header, row)}
                    out.append(record)
        return out


def rows_to_bgrows(
    rows: Iterable[Mapping[str, str]], needed_vars: Sequence[str]
) -> List[BGRow]:
    """Convert raw ACS API dict rows to BGRow records keyed by 12-digit BG FIPS.

    For estimate/MOE coding:
    - The estimate codes (e.g. B01003_001E) are parsed as floats.
    - Companion MOE codes (B01003_001M) are parsed as floats when present.
    Missing or non-numeric values are skipped for that variable.
    """
    out: Dict[str, Dict[str, Tuple[float, float]]] = {}
    est_vars = {v for v in needed_vars if v.endswith("E")}
    moe_vars = {v for v in needed_vars if v.endswith("M")}
    moe_pairs: Dict[str, str] = {e: e[:-1] + "M" for e in est_vars if (e[:-1] + "M") in moe_vars}
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
            if est_str is None or est_str == "" or est_str == "-666666666":
                continue
            try:
                est_val = float(est_str)
            except ValueError:
                continue
            moe_code = moe_pairs.get(e)
            moe_val = 0.0
            if moe_code:
                m_str = rec.get(moe_code)
                if m_str is not None and m_str != "":
                    try:
                        moe_val = float(m_str)
                    except ValueError:
                        moe_val = 0.0
            store[e] = (est_val, moe_val)
    return [BGRow(bg_fips12=k, values=v) for k, v in out.items()]


def relative_moe_flags(
    features: Mapping[str, Tuple[float, float]], threshold: float = 0.5
) -> Dict[str, bool]:
    """Flag features whose relative MOE exceeds the threshold (default 50%).

    Relative MOE is `moe / abs(estimate)` with a floor that zero/near-zero estimates
    are treated as high-uncertainty (flagged).
    """
    flags: Dict[str, bool] = {}
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

