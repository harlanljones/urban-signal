"""Export the MapLibre dashboard HTML into the Workers static assets directory.

Keeps src/serving/dashboard.py as the single source of truth for UI markup;
run before `wrangler dev` / `wrangler deploy`:

    python scripts/export_dashboard.py
"""

import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.serving.dashboard import get_dashboard_html


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "apps" / "dashboard" / "public"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"
    out_file.write_text(get_dashboard_html(), encoding="utf-8")
    print(f"Wrote {out_file} ({out_file.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
