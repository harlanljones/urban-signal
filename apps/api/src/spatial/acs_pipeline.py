"""Pilot ACS neighborhood indicators end-to-end assembly (US-361).

This composes:
- ACSClient (live fetch or fixture-provided rows)
- BG → H3 resolver (via LODES xwalk centroids)
- Block-group → H3 aggregation with MOE propagation
- Relative-MOE flagging
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.spatial.acs_baseline import BGRow, H3Baseline, aggregate_blockgroup_to_h3
from src.spatial.acs_client import (
    ACSClient,
    ENV_API_KEY,
    relative_moe_flags,
    rows_to_bgrows,
    variables_for_features,
)
from src.spatial.acs_join import BGToH3Resolver
from src.spatial.city_registry import CityId, REGISTRY


@dataclass
class ACSPipelineConfig:
    """Configuration for a pilot ACS pull."""

    feature_names: Optional[Sequence[str]] = None
    h3_resolution: int = 9


def ingest_city_from_rows(
    rows: Iterable[Mapping[str, str]],
    bg_to_h3: Callable[[str], str],
    config: ACSPipelineConfig | None = None,
) -> List[H3Baseline]:
    """Assemble H3 baselines from pre-fetched ACS rows and a BG→H3 resolver."""
    cfg = config or ACSPipelineConfig()
    needed = variables_for_features(cfg.feature_names)
    bg_rows: List[BGRow] = rows_to_bgrows(rows, needed)
    return aggregate_blockgroup_to_h3(bg_rows, bg_to_h3, cfg.feature_names)


def ingest_city_live(
    city: CityId,
    state_fips: str,
    county_fips: Sequence[str],
    feature_names: Optional[Sequence[str]] = None,
    api_key: Optional[str] = None,
) -> List[H3Baseline]:
    """Live end-to-end ingest for one city (ACS pull + BG→H3 + aggregation).

    - You must pass a Census API key or set CENSUS_API_KEY in the environment.
    - Joins BG to H3 via LODES V8 crosswalks for the city's state.
    """
    # Verify city exists and fetch its bbox (to filter hexes later if needed).
    if city not in REGISTRY:
        raise ValueError(f"Unknown city id {city}")
    needed = variables_for_features(feature_names)
    client = ACSClient(api_key=api_key)
    rows = client.fetch_block_groups(state_fips, county_fips, needed)
    resolver = BGToH3Resolver(resolution=9)
    bg_to_h3 = resolver.build_for_states([_state_from_fips(state_fips)])
    return ingest_city_from_rows(rows, bg_to_h3, ACSPipelineConfig(feature_names=feature_names))


def _state_from_fips(state_fips: str) -> str:
    """Map numeric FIPS to two-letter code for the LODES URL helper. Minimal mapping for pilot."""
    fips_to_st = {
        "01": "al",
        "02": "ak",
        "04": "az",
        "05": "ar",
        "06": "ca",
        "08": "co",
        "09": "ct",
        "10": "de",
        "11": "dc",
        "12": "fl",
        "13": "ga",
        "15": "hi",
        "16": "id",
        "17": "il",
        "18": "in",
        "19": "ia",
        "20": "ks",
        "21": "ky",
        "22": "la",
        "23": "me",
        "24": "md",
        "25": "ma",
        "26": "mi",
        "27": "mn",
        "28": "ms",
        "29": "mo",
        "30": "mt",
        "31": "ne",
        "32": "nv",
        "33": "nh",
        "34": "nj",
        "35": "nm",
        "36": "ny",
        "37": "nc",
        "38": "nd",
        "39": "oh",
        "40": "ok",
        "41": "or",
        "42": "pa",
        "44": "ri",
        "45": "sc",
        "46": "sd",
        "47": "tn",
        "48": "tx",
        "49": "ut",
        "50": "vt",
        "51": "va",
        "53": "wa",
        "54": "wv",
        "55": "wi",
        "56": "wy",
    }
    code = fips_to_st.get(state_fips)
    if not code:
        raise ValueError(f"State FIPS {state_fips!r} not recognized for pilot mapping.")
    return code


__all__ = [
    "ACSPipelineConfig",
    "ingest_city_from_rows",
    "ingest_city_live",
    "relative_moe_flags",
]

