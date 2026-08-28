"""ACS geography join helpers: block-group -> H3 cell via LODES V8 crosswalk (US-361).

The LODES V8 crosswalk (`<state>_xwalk.csv(.gz)`) ships block internal-point
lat/lng (`blklatdd`/`blklondd`) keyed by 15-digit 2020 block code `tabblk2020`.
Block-group FIPS is the first 12 digits. We derive a block-group centroid as the
mean of its member blocks' internal points, then map that point to an H3 cell.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple

import csv
import gzip
import h3

from src.export.national_builder import state_xwalk_url, download_to_cache
from src.spatial.acs_baseline import block_fips_to_bg


def _read_xwalk_rows(path: Path) -> Iterable[Tuple[str, float, float]]:
    """Yield (tabblk2020, lat, lng) rows from a LODES xwalk (gz or plain CSV)."""
    def _iter(reader):
        header = next(reader)
        try:
            idx_code = header.index("tabblk2020")
            idx_lat = header.index("blklatdd")
            idx_lng = header.index("blklondd")
        except ValueError as exc:
            raise ValueError(f"{path}: missing expected columns in header {header}") from exc
        for row in reader:
            try:
                code = row[idx_code]
                lat = float(row[idx_lat])
                lng = float(row[idx_lng])
            except Exception:
                continue
            yield code, lat, lng

    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            yield from _iter(reader)
    else:
        with path.open("rt", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            yield from _iter(reader)


def _bg_centroids_from_xwalk(path: Path) -> Dict[str, Tuple[float, float]]:
    """Compute block-group centroids from a LODES xwalk file."""
    sums: Dict[str, Tuple[float, float, int]] = defaultdict(lambda: (0.0, 0.0, 0))
    for tabblk, lat, lng in _read_xwalk_rows(path):
        try:
            bg = block_fips_to_bg(tabblk)
        except ValueError:
            continue
        s_lat, s_lng, n = sums[bg]
        sums[bg] = (s_lat + lat, s_lng + lng, n + 1)
    centroids: Dict[str, Tuple[float, float]] = {}
    for bg, (s_lat, s_lng, n) in sums.items():
        if n <= 0:
            continue
        centroids[bg] = (s_lat / n, s_lng / n)
    return centroids


@dataclass(frozen=True)
class BGToH3Resolver:
    """Resolve 12-digit 2020 BG FIPS -> H3 cell via LODES V8 crosswalk centroids."""

    resolution: int = 9
    cache_dir: Path = Path("data") / "lodes" / "xwalk"

    def build_for_states(self, states: Iterable[str]) -> Callable[[str], str]:
        """Return a callable `bg_fips12 -> h3_cell` for the given 2-letter states."""
        mapping: Dict[str, str] = {}
        for st in states:
            url = state_xwalk_url(st.lower())
            path = download_to_cache(url, self.cache_dir)
            cents = _bg_centroids_from_xwalk(path)
            for bg, (lat, lng) in cents.items():
                mapping[bg] = h3.latlng_to_cell(lat, lng, self.resolution)

        def _resolve(bg_fips12: str) -> str:
            cell = mapping.get(bg_fips12)
            if cell is None:
                # Unknown BG — map to an obviously invalid marker rather than raising.
                return ""
            return cell

        return _resolve

    @staticmethod
    def from_local_xwalks(
        paths: Iterable[Path], resolution: int = 9
    ) -> Callable[[str], str]:
        """Build a resolver from local xwalk CSV/CSV.GZ files (tests/fixtures path)."""
        cents: Dict[str, Tuple[float, float]] = {}
        for p in paths:
            cents.update(_bg_centroids_from_xwalk(p))
        mapping = {
            bg: h3.latlng_to_cell(lat, lng, resolution) for bg, (lat, lng) in cents.items()
        }

        def _resolve(bg_fips12: str) -> str:
            return mapping.get(bg_fips12, "")

        return _resolve

