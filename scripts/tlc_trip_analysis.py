"""Run the read-only NYC TLC trip-record prototype (US-362).

Examples:
    python scripts/tlc_trip_analysis.py --year 2025 --month 1 \
      --yellow-path /data/yellow_tripdata_2025-01.parquet \
      --hvfhv-path /data/fhvhv_tripdata_2025-01.parquet \
      --zones-path /data/taxi_zone_lookup.csv --output /tmp/tlc-report.json

Without explicit trip paths the command reads the official TLC CloudFront URLs.
Use ``--row-limit`` for a bounded smoke test; omit it for a full monthly run.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.features.tlc_trip_analysis import (
    TLC_ZONE_LOOKUP_URL,
    DatasetInput,
    analyze_month,
    load_benchmarks,
    trip_url,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True, help="TLC publication year")
    parser.add_argument("--month", type=int, required=True, help="TLC publication month")
    parser.add_argument("--yellow-path", help="local Yellow Parquet path or override URL")
    parser.add_argument("--hvfhv-path", help="local HVFHV Parquet path or override URL")
    parser.add_argument(
        "--zones-path",
        default=TLC_ZONE_LOOKUP_URL,
        help="local taxi_zone_lookup.csv path or official URL",
    )
    parser.add_argument("--top-n", type=int, default=20, help="number of zones/OD pairs in report")
    parser.add_argument(
        "--row-limit",
        type=int,
        help="optional bounded sample size per dataset; omit for the full month",
    )
    parser.add_argument(
        "--benchmarks",
        type=Path,
        help="optional JSON object with expected totals keyed by yellow/hvfhv",
    )
    parser.add_argument("--output", type=Path, help="write report JSON to this path")
    args = parser.parse_args()

    datasets = [
        DatasetInput("yellow", args.yellow_path or trip_url("yellow", args.year, args.month)),
        DatasetInput("hvfhv", args.hvfhv_path or trip_url("hvfhv", args.year, args.month)),
    ]
    report = analyze_month(
        datasets,
        args.zones_path,
        top_n=args.top_n,
        row_limit=args.row_limit,
        benchmarks=load_benchmarks(args.benchmarks),
    )
    report["generated_at"] = datetime.now(UTC).isoformat()
    report["period"] = f"{args.year:04d}-{args.month:02d}"
    rendered = json.dumps(report, indent=2, default=str) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"report written: {args.output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
