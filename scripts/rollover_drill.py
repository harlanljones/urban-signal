"""US-70: annual New Year rollover drill for year-sliced feeds (roadmap §8.2).

Frozen-clock check that every year-sliced feed (DC permits/311, Boston 311,
Baltimore 311, + any added later) has a layer/resource mapping for the target
year. Run it in staging every December 15 against the NEXT year's Jan 2:

    python scripts/rollover_drill.py --frozen-date 2027-01-02

Exits nonzero (loudly) if any feed lacks a mapping — risk R3's failure mode.
The fix is the manual fallback runbook: append the year's endpoint in
``DatasetSpec.extra["endpoint_by_year"]``, restart the scheduler job, verify
with a newest-row probe.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.producers.rollover import RolloverDrillError, drill_rollover


def upcoming_jan_2() -> date:
    """The next Jan 2 after today — the frozen-clock target for the drill."""
    today = datetime.now(UTC).date()
    candidate = date(today.year, 1, 2)
    return candidate if today < candidate else date(today.year + 1, 1, 2)


def parse_frozen_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frozen-date",
        type=parse_frozen_date,
        default=upcoming_jan_2(),
        help="Frozen-clock date the scheduler is simulated at (default: next Jan 2)",
    )
    args = parser.parse_args()

    try:
        checks = drill_rollover(args.frozen_date)
    except RolloverDrillError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps([asdict(check) for check in checks], indent=2))
    print(
        f"ROLLOVER_DRILL_GREEN: {len(checks)} year-sliced feed(s) resolve for "
        f"{args.frozen_date.year}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())