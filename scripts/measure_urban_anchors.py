"""Measure Urban Anchor cardinality and polyfill budgets (HX-A1; DG-1/2/3 evidence).

Usage: ``cd apps/api && PYTHONPATH=. .venv/bin/python ../../scripts/measure_urban_anchors.py``
"""

from __future__ import annotations

import time
from collections import Counter

from src.spatial.city_registry import REGISTRY
from src.spatial.urban_anchors import (
    anchor_cells,
    anchors_intersecting,
    detail_resolution,
    load_anchors,
)


def main() -> None:
    anchors = load_anchors()
    print(f"anchors: {len(anchors)}")
    per_metro: dict[str, tuple[str, ...]] = {
        cid.value: anchors_intersecting(reg.metro_bbox) for cid, reg in REGISTRY.items()
    }
    print("anchors per metro bbox:", sorted(Counter(len(v) for v in per_metro.values()).items()))
    metros_per_anchor: Counter[str] = Counter(a for v in per_metro.values() for a in v)
    print("metros per anchor:", sorted(Counter(metros_per_anchor.values()).items()))
    touched = set(metros_per_anchor)
    print(f"anchors intersecting any metro bbox: {len(touched)}")
    start = time.perf_counter()
    totals = {7: 0, 8: 0, 9: 0}
    touched_totals = {7: 0, 8: 0, 9: 0}
    for anchor_id in anchors:
        n7 = len(anchor_cells(anchor_id, 7))
        totals[7] += n7
        totals[8] += n7 * 7
        totals[9] += n7 * 49
        if anchor_id in touched:
            for res, mult in ((7, 1), (8, 7), (9, 49)):
                touched_totals[res] += n7 * mult
    print(f"res-7 polyfill wall time (all anchors): {time.perf_counter() - start:.1f}s")
    print("cells at uniform res, all anchors:", totals)
    print("cells at uniform res, metro-touching anchors:", touched_totals)
    adaptive = 0
    classes: Counter[int] = Counter()
    for anchor_id, anchor in anchors.items():
        res = detail_resolution(anchor)
        classes[res] += 1
        adaptive += len(anchor_cells(anchor_id, 7)) * 7 ** (res - 7)
    print("anchor classes (detail res -> count):", sorted(classes.items()))
    print(f"cells at adaptive detail resolution, all anchors: {adaptive}")


if __name__ == "__main__":
    main()
