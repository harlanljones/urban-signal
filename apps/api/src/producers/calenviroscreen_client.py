"""CalEnviroScreen 5.0 — tract-level pollution/socioeconomic scores crosswalked to H3 res-8.

LEAF module — no spine edits.  Produces ``EnvironmentalStressReading`` covariate
records tagged to H3 res-8 cells destined for ``EnrichedH3Feature`` context.

The source is the CalEnviroScreen 5.0 CSV published on data.ca.gov
(verified live 2026-09-02, 9,106 rows, 70 columns).  The CSV carries census
tract GEOIDs but no coordinates; a pre-computed tract→centroid lookup
(``tract_centroids.json``, derived from the authoritative shapefile via
pyproj EPSG:3310 → EPSG:4326) provides the geometry for the H3 crosswalk.

Usage::

    client = CalEnviroScreenClient()
    readings = client.fetch()  # list[EnvironmentalStressReading]
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import h3
import httpx

from src.producers.environmental_stress_client import (
    EnvironmentalStressReading,
)

CES_CSV_URL = (
    "https://data.ca.gov/dataset/72b28c84-ceac-4886-9f71-d422470d2223/"
    "resource/c4e277e0-cf23-4a8f-b07e-c8544c5d3d2b/"
    "download/calenviroscreen50_070126.csv"
)

_CENTROIDS_PATH = Path(__file__).resolve().parent / "data" / "calenviroscreen_tract_centroids.json"


def _load_centroids() -> dict[str, tuple[float, float]]:
    """Load the tract→centroid lookup from the bundled JSON."""
    with open(_CENTROIDS_PATH, encoding="utf-8") as fh:
        raw: dict[str, list[float]] = json.load(fh)
    return {tract: (lat, lng) for tract, (lat, lng) in raw.items()}


def _resolve_tract_h3(tract: str, centroids: dict[str, tuple[float, float]]) -> dict[str, str | None] | None:
    """Return the H3 hierarchy for a census tract's centroid, or None."""
    point = centroids.get(tract)
    if point is None:
        return None
    lat, lng = point
    try:
        cell8 = h3.latlng_to_cell(lat, lng, 8)
        return {
            "h3_res7": h3.cell_to_parent(cell8, 7),
            "h3_res8": cell8,
            "h3_res9": h3.latlng_to_cell(lat, lng, 9),
        }
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> float | None:
    if val is None or str(val).strip() in ("", "NA", "null"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_csv_bytes(
    raw: bytes,
    centroids: dict[str, tuple[float, float]] | None = None,
    max_records: int | None = None,
) -> list[EnvironmentalStressReading]:
    """Parse the CES 5.0 CSV payload into H3-tagged stress readings.

    Each record carries the overall CalEnviroScreen score (``CIscore``) and
    its percentile, plus key indicator percentiles in ``extra``.
    """
    if centroids is None:
        centroids = _load_centroids()

    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    readings: list[EnvironmentalStressReading] = []

    for count, row in enumerate(reader):
        if max_records is not None and count >= max_records:
            break
        tract = str(row.get("tract", "")).strip().split(".")[0]
        if not tract:
            continue
        h3_tags = _resolve_tract_h3(tract, centroids)
        if h3_tags is None:
            continue

        ci_score = _safe_float(row.get("CIscore"))
        ci_pct = _safe_float(row.get("CIscoreP"))
        pollution_pct = _safe_float(row.get("PollutionP"))
        pop_char_pct = _safe_float(row.get("PopCharP"))

        lat_lng = centroids.get(tract)
        lat = lat_lng[0] if lat_lng else None
        lng = lat_lng[1] if lat_lng else None

        readings.append(
            EnvironmentalStressReading(
                source="calenviroscreen",
                metric="ci_score",
                value=ci_score if ci_score is not None else 0.0,
                unit="score",
                asset_id=tract,
                period_start=None,
                city_id=None,
                lat=lat,
                lng=lng,
                h3_res7=h3_tags["h3_res7"],
                h3_res8=h3_tags["h3_res8"],
                h3_res9=h3_tags["h3_res9"],
                extra={
                    "ci_score_pct": ci_pct,
                    "pollution_pct": pollution_pct,
                    "pop_char_pct": pop_char_pct,
                    "county": str(row.get("county", "")),
                    "ozone_pct": _safe_float(row.get("ozoneP")),
                    "pm_pct": _safe_float(row.get("pmP")),
                    "diesel_pct": _safe_float(row.get("dieselP")),
                    "traffic_pct": _safe_float(row.get("trafficP")),
                    "drinking_water_pct": _safe_float(row.get("drinkP")),
                    "lead_pct": _safe_float(row.get("leadP")),
                    "poverty_pct": _safe_float(row.get("povP")),
                    "unemployment_pct": _safe_float(row.get("unempP")),
                    "housing_burden_pct": _safe_float(row.get("housingBP")),
                    "asthma_pct": _safe_float(row.get("asthmaP")),
                    "low_birth_weight_pct": _safe_float(row.get("lbwP")),
                    "cardiovascular_disease_pct": _safe_float(row.get("cvdP")),
                    "diabetes_pct": _safe_float(row.get("diabetesP")),
                    "educational_attainment_pct": _safe_float(row.get("eduP")),
                    "linguistic_isolation_pct": _safe_float(row.get("lingP")),
                },
            )
        )
    return readings

class CalEnviroScreenClient:
    """Client for the CalEnviroScreen 5.0 CSV feed.

    Downloads the CES CSV from data.ca.gov and crosswalks tract-level scores
    onto H3 resolution-8 cells via a bundled centroid lookup.
    """

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        centroids: dict[str, tuple[float, float]] | None = None,
    ):
        self.http = http_client or httpx.Client(timeout=120.0, follow_redirects=True)
        self.centroids = centroids or _load_centroids()

    def fetch(
        self,
        url: str = CES_CSV_URL,
        max_records: int | None = None,
    ) -> list[EnvironmentalStressReading]:
        """Download the CES CSV and return H3-tagged covariate readings."""
        resp = self.http.get(url)
        resp.raise_for_status()
        return parse_csv_bytes(resp.content, self.centroids, max_records=max_records)