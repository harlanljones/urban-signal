"""Regenerate the pinned per-region golden counts (HX-B2).

Usage: ``cd apps/api && PYTHONPATH=. .venv/bin/python ../../scripts/measure_region_golden.py``

Rewrites ``apps/api/src/spatial/assets/region_golden_counts.json``. Run it only for a
deliberate coverage change (registry edit, anchor asset or bound change) and commit the
diff with the reason: ``test_region_golden`` fails on any unannounced drift.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.spatial.coverage_plan import plan_all

OUT = Path(__file__).resolve().parents[1] / "apps/api/src/spatial/assets/region_golden_counts.json"


def main() -> None:
    plans = plan_all()
    counts = {
        plan.region_id: {
            "golden": plan.golden_count,
            "owned": plan.owned_count,
            "measured": plan.measured_count,
            "in_anchor": plan.in_anchor_count,
        }
        for plan in plans.values()
    }
    document = {
        "total_owned": sum(c["owned"] for c in counts.values()),
        "regions": dict(sorted(counts.items())),
    }
    OUT.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
    print(f"{len(counts)} regions, {document['total_owned']} owned cells -> {OUT}")


if __name__ == "__main__":
    main()
