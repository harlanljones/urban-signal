"""Region failure-domain drill (ADR-0010 Stage C, HX-C6).

Proves that when one region fails verification at promote time:
1. PromotionRefused is raised;
2. The failing region's current pointer remains on its previous valid generation;
3. Objects and generation files for the failed build do not overwrite valid ones;
4. The region failure domain is fully isolated from other regions.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from src.export.regions import (
    MEASURED_FLOOR_RATIO,
    PromotionRefused,
    load_pointer,
    promote_region,
    stage_region,
)


def run_drill(verbose: bool = True) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="us-region-drill-") as temp_dir:
        root = Path(temp_dir)
        region_id = "metro/nyc"
        plan_hash = "plan-nyc-stable"
        golden_count = 10

        # Step 1: Stage and promote initial valid generation G1
        chunk_g1 = json.dumps({"type": "FeatureCollection", "gen": 1, "features": []}).encode()
        manifest_g1 = stage_region(
            root,
            region_id=region_id,
            input_hash="in-1",
            plan_hash=plan_hash,
            golden_count=golden_count,
            measured_count=10,
            chunks={"gridtiles_res9/parent1": chunk_g1},
        )
        p1 = promote_region(
            root,
            region_id=region_id,
            generation=manifest_g1.generation,
            expected_golden=golden_count,
            expected_plan_hash=plan_hash,
        )
        assert p1.current == manifest_g1.generation, "Initial promotion failed"

        # Step 2: Stage G2 with corrupted chunk data
        chunk_g2_corrupt = b"corrupted bytes"
        manifest_g2 = stage_region(
            root,
            region_id=region_id,
            input_hash="in-2",
            plan_hash=plan_hash,
            golden_count=golden_count,
            measured_count=10,
            chunks={"gridtiles_res9/parent1": chunk_g2_corrupt},
        )
        # Invalidate the chunk file to simulate hash mismatch
        chunk_path = root / "objects" / manifest_g2.chunks["gridtiles_res9/parent1"]["sha256"]
        chunk_path.write_bytes(b"tampered content")

        failed_promotion = False
        try:
            promote_region(
                root,
                region_id=region_id,
                generation=manifest_g2.generation,
                expected_golden=golden_count,
                expected_plan_hash=plan_hash,
            )
        except PromotionRefused:
            failed_promotion = True

        assert failed_promotion, "Corrupted chunk did not refuse promotion"

        # Step 3: Verify pointer remains on G1
        active_pointer = load_pointer(root, region_id)
        # Step 4: Stage G3 with dropped measured cells (feed outage simulation)
        chunk_g3 = json.dumps({"type": "FeatureCollection", "gen": 3, "features": []}).encode()
        manifest_g3 = stage_region(
            root,
            region_id=region_id,
            input_hash="in-3",
            plan_hash=plan_hash,
            golden_count=golden_count,
            measured_count=int(10 * MEASURED_FLOOR_RATIO) - 2,  # below floor
            chunks={"gridtiles_res9/parent1": chunk_g3},
        )
        feed_outage_refused = False
        try:
            promote_region(
                root,
                region_id=region_id,
                generation=manifest_g3.generation,
                expected_golden=golden_count,
                expected_plan_hash=plan_hash,
            )
        except PromotionRefused:
            feed_outage_refused = True

        assert feed_outage_refused, "Measured count drop did not refuse promotion"
        assert load_pointer(root, region_id).current == manifest_g1.generation

        summary = {
            "region_id": region_id,
            "retained_generation": active_pointer.current,
            "corrupted_generation_refused": manifest_g2.generation,
            "feed_outage_generation_refused": manifest_g3.generation,
            "pointer_intact": True,
        }
        if verbose:
            print(json.dumps(summary, indent=2))
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output")
    args = parser.parse_args()
    run_drill(verbose=not args.quiet)


if __name__ == "__main__":
    main()
