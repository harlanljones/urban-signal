"""poi_diff_producer — release-delta POI churn -> ``poi_change`` (US-363 §1.3).

Business move-in/out is the best derived signal we have, and outside the
handful of metros with a municipal license feed there is nothing to derive it
from. Foursquare publishes an explicit, machine-readable churn channel
nationally, monthly, under Apache 2.0 — this reads it.

**A new archetype, not a ``PaginatingClient``.** There is no watermark and no
query interface: a release is a set of Parquet partitions, and the unit of
work is "the delta between release N-1 and release N".

**The source moved.** The anonymous S3 bucket the sweep recorded
(``fsq-os-places-us-east-1``) now holds only ``LICENSE.txt`` and
``NOTICE.txt``; every release partition is gone. Foursquare moved the dataset
to a **gated Hugging Face repo** — anonymous download returns 401, access is
auto-granted on request — keeping the layout intact (verified 2026-08-28):

    release/dt=<date>/places/parquet/places-*.zstd.parquet
    release/dt=<date>/deltas/parquet/deltas-*.zstd.parquet
    release/dt=<date>/categories/parquet/categories.zstd.parquet

21 releases exist; the latest is ``dt=2026-08-11`` with 10 delta partitions.
The repo listing is public, so release discovery works without a token; the
partitions themselves need ``HF_TOKEN``.

**Delta files carry three columns only** — ``fsq_place_id``, ``action``
(add|update|remove|merge) and ``redirect`` (the surviving id for a merge).
Every attribute the event needs (coordinates, name, categories,
``date_closed``, ``unresolved_flags``) comes from joining those ids against
the release's ``places`` partitions. That join is the expensive half of the
job and the reason the producer stages files rather than streaming them.

**Naive added/removed counts are GERS-matcher noise**, so classification is
deliberately conservative: an ``add`` is an opening, a ``remove`` is a
closing, a ``merge`` is a *database* event carried at reduced confidence, and
an ``update`` only becomes a closing when the place itself says so
(``date_closed`` set, or ``closed`` among ``unresolved_flags``). Event dates
are release dates, and that detection-date bias is documented rather than
hidden: FSQ's own ``date_closed`` is "the date the POI was marked as closed in
our database", which their docs are explicit does not mean the day it closed.

Parquet is read through DuckDB, which the feature pipeline already depends on;
pyarrow is not installed in this environment and is not worth adding for one
reader.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

POI_OPENED = "poi_opened"
POI_CLOSED = "poi_closed"

ACTION_ADD = "add"
ACTION_UPDATE = "update"
ACTION_REMOVE = "remove"
ACTION_MERGE = "merge"

# Confidence by evidence strength. A merge is a database operation — one
# record absorbed into another — and only sometimes a real closing, so it
# never carries the same weight as an explicit removal.
CONFIDENCE = {
    ACTION_ADD: 1.0,
    ACTION_REMOVE: 0.9,
    ACTION_MERGE: 0.4,
    ACTION_UPDATE: 0.6,
}

# `unresolved_flags` are Placemaker-reported quality issues awaiting
# corroboration. `closed` is a soft closing signal; the rest mean the record
# should not be treated as a real, public, distinct venue at all.
FLAG_CLOSED = "closed"
DISQUALIFYING_FLAGS = frozenset({"duplicate", "delete", "privatevenue", "inappropriate"})

# Foursquare's documented non-commercial category exclusion list (38 ids).
#
# DELIBERATELY EMPTY, and the producer refuses to run in strict mode while it
# is. The ids are published in the release's own `categories` partition, which
# is behind the same gate as the data; populating this from a guess would be
# worse than failing, because the failure mode is using categories we are not
# licensed to use commercially. Fill it from the categories partition on the
# first authenticated run and drop `strict_licensing=False` from any caller.
NON_COMMERCIAL_CATEGORY_IDS: frozenset[str] = frozenset()

# Source precedence for cross-source dedup (§1.3 step 5). Cross-source
# identity resolution (name + phone + geohash) is explicitly deferred; this
# only decides which source wins for the same native id.
SOURCE_PRECEDENCE = ("fsq", "overture", "atp", "osm")

_RELEASE_RE = re.compile(r"release/dt=(\d{4}-\d{2}-\d{2})/")


class PoiSourceError(RuntimeError):
    """The POI release channel is unreachable or unusable as declared."""


@dataclass(frozen=True)
class Release:
    """One published release and the partition paths it contains."""

    release_id: str  # the dt= value, e.g. 2026-08-11
    delta_paths: List[str]
    place_paths: List[str]
    category_paths: List[str]

    @property
    def release_date(self) -> date:
        return date.fromisoformat(self.release_id)


def parse_releases(sibling_paths: Iterable[str]) -> Dict[str, Release]:
    """Group a repo file listing into releases.

    The listing is public even though the files are gated, so release
    discovery — including "is there a new release?" — works with no token.
    """
    buckets: Dict[str, Dict[str, List[str]]] = {}
    for path in sibling_paths:
        match = _RELEASE_RE.match(path)
        if not match:
            continue
        kind = path.split("/")[2] if len(path.split("/")) > 2 else ""
        if not path.endswith(".parquet"):
            continue
        buckets.setdefault(match.group(1), {}).setdefault(kind, []).append(path)

    releases: Dict[str, Release] = {}
    for release_id, kinds in buckets.items():
        releases[release_id] = Release(
            release_id=release_id,
            delta_paths=sorted(kinds.get("deltas", [])),
            place_paths=sorted(kinds.get("places", [])),
            category_paths=sorted(kinds.get("categories", [])),
        )
    return releases


def select_latest_release(releases: Dict[str, Release], after: Optional[str] = None) -> Optional[Release]:
    """Newest release strictly after ``after``, or None when we are current.

    A release with no delta partitions is skipped rather than treated as "no
    churn": the first release in the repo has no predecessor to diff against,
    and a partial upload should not be mistaken for a quiet month.
    """
    candidates = [
        rel
        for rid, rel in releases.items()
        if rel.delta_paths and (after is None or rid > after)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.release_id)


def classify(
    action: Optional[str],
    date_closed: Any = None,
    unresolved_flags: Optional[Sequence[str]] = None,
    redirect: Optional[str] = None,
) -> Tuple[Optional[str], float]:
    """(event_type, confidence) for one delta row joined to its place.

    Returns ``(None, 0.0)`` for rows that are not evidence of churn — the
    common case for ``update``, which mostly means an attribute was
    refreshed.
    """
    act = (action or "").strip().lower()
    flags = {str(f).strip().lower() for f in (unresolved_flags or [])}

    if flags & DISQUALIFYING_FLAGS:
        # Duplicate/deleted/private/inappropriate records are not venues whose
        # opening or closing means anything about a neighborhood.
        return None, 0.0

    if act in {ACTION_ADD, "create", "open", "opened"}:
        return POI_OPENED, CONFIDENCE[ACTION_ADD]
    if act in {ACTION_REMOVE, "delete", "close", "closed", "redirect"}:
        return POI_CLOSED, CONFIDENCE[ACTION_REMOVE]
    if act == ACTION_MERGE:
        # Only a merge that actually names a survivor is a merge; one without
        # a redirect is an unexplained disappearance, which is a removal.
        return POI_CLOSED, CONFIDENCE[ACTION_MERGE] if redirect else CONFIDENCE[ACTION_REMOVE]
    if act == ACTION_UPDATE:
        if date_closed or FLAG_CLOSED in flags:
            confidence = CONFIDENCE[ACTION_UPDATE]
            if FLAG_CLOSED in flags and not date_closed:
                # An unresolved flag is by definition not yet corroborated.
                confidence *= 0.5
            return POI_CLOSED, confidence
        return None, 0.0
    return None, 0.0


def category_of(place: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """(category_id, category_label) — the first of each, or (None, None)."""

    def first(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value or None
        try:
            items = list(value)
        except TypeError:
            return None
        return str(items[0]) if items else None

    return first(place.get("fsq_category_ids")), first(place.get("fsq_category_labels"))


class PoiDiffProducer:
    """Turns a POI release delta into ``PoiChangeEvent``s."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        crosswalk: Any = None,
        strict_licensing: bool = True,
        *,
        indexer: Any = None,
        kafka_producer: Any = None,
    ):
        from src.config import settings
        from src.producers.base_producer import BaseKafkaProducer
        from src.spatial.h3_indexer import H3SpatialIndexer

        self.settings = settings
        self.producer = kafka_producer or BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=Path(__file__).parent.parent
            / "schemas"
            / "avro"
            / "poi_change_event.avsc",
            dlq_topic=settings.topic_dlq,
        )
        # The interlock gate resolves a spec's platform to a same-named
        # attribute on its producer; this feed's platform is `hf_parquet`.
        self.hf_parquet = self
        from src.producers.socrata_client import SocrataClient

        self.socrata = SocrataClient()
        self.spatial_indexer = indexer or H3SpatialIndexer()
        self.strict_licensing = strict_licensing
        self._crosswalk = crosswalk

    def build_events(self, rows: Iterable[Dict[str, Any]]) -> List[Any]:
        """Build events from decoded rows without acquiring release files.

        Each row must contain a release date (``release_date``, ``release_id``
        or ``dt``). This seam intentionally accepts ordinary mappings so tests
        and callers do not need DuckDB, pyarrow, or Hugging Face credentials.
        """
        events: List[Any] = []
        for row in rows:
            raw_release = row.get("release_date") or row.get("release_id") or row.get("dt")
            if raw_release is None:
                continue
            release_id = str(raw_release)
            if release_id.startswith("dt="):
                release_id = release_id[3:]
            if isinstance(raw_release, datetime):
                release_id = raw_release.date().isoformat()
            try:
                date.fromisoformat(release_id)
            except ValueError:
                try:
                    release_id = datetime.fromisoformat(release_id.replace("Z", "+00:00")).date().isoformat()
                except ValueError:
                    continue
            event = self.build_event(row, Release(release_id, [], [], []))
            if event is not None:
                events.append(event)
        return events

    @property
    def crosswalk(self):
        if self._crosswalk is None:
            from src.spatial.geography_crosswalk import default_crosswalk

            self._crosswalk = default_crosswalk()
        return self._crosswalk

    # ----------------------------------------------------------------- #
    # licensing gate                                                     #
    # ----------------------------------------------------------------- #
    def check_licensing(self) -> None:
        """Refuse to run commercially until the exclusion list is populated.

        Foursquare excludes 38 category ids from commercial use. Running
        without that list is not a degraded run, it is an unlicensed one, so
        this fails closed. ``strict_licensing=False`` exists for tests and for
        an explicitly non-commercial exploration, and says so in the log.
        """
        if NON_COMMERCIAL_CATEGORY_IDS:
            return
        if self.strict_licensing:
            raise PoiSourceError(
                "NON_COMMERCIAL_CATEGORY_IDS is empty: Foursquare excludes 38 category "
                "ids from commercial use and they must be loaded from the release's "
                "`categories` partition before a commercial run. Pass "
                "strict_licensing=False only for non-commercial exploration."
            )
        logger.warning(
            "Running with an empty non-commercial category exclusion list — "
            "non-commercial use only."
        )

    def is_licensed(self, category_id: Optional[str]) -> bool:
        return not (category_id and category_id in NON_COMMERCIAL_CATEGORY_IDS)

    # ----------------------------------------------------------------- #
    # release discovery                                                  #
    # ----------------------------------------------------------------- #
    def list_releases(self) -> Dict[str, Release]:
        """List the repo's releases. Public — no token needed."""
        import httpx

        url = f"{self.settings.fsq_places_api_base}/api/datasets/{self.settings.fsq_places_repo}"
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:
            raise PoiSourceError(f"cannot list {url}: {exc}") from exc
        siblings = [s.get("rfilename", "") for s in payload.get("siblings", [])]
        if not siblings:
            raise PoiSourceError(
                f"{url} returned no file listing — the repo layout changed again"
            )
        return parse_releases(siblings)

    def _token(self) -> str:
        token = os.environ.get("HF_TOKEN")
        if not token:
            raise PoiSourceError(
                "HF_TOKEN is unset. Foursquare OS Places moved to a gated Hugging Face "
                "repo (anonymous download returns 401); request access on the dataset "
                "page and export a read token."
            )
        return token

    def download(self, path: str, dest_dir: Path) -> Path:
        """Fetch one partition into ``dest_dir``. Requires HF_TOKEN."""
        import httpx

        repo = self.settings.fsq_places_repo
        url = f"{self.settings.fsq_places_api_base}/datasets/{repo}/resolve/main/{path}"
        dest = dest_dir / Path(path).name
        dest_dir.mkdir(parents=True, exist_ok=True)
        headers = {"Authorization": f"Bearer {self._token()}"}
        try:
            with httpx.Client(timeout=300.0, follow_redirects=True) as client:
                with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    with dest.open("wb") as fh:
                        for chunk in resp.iter_bytes():
                            fh.write(chunk)
        except Exception as exc:
            raise PoiSourceError(f"cannot download {path}: {exc}") from exc
        return dest

    # ----------------------------------------------------------------- #
    # state                                                              #
    # ----------------------------------------------------------------- #
    def state_path(self) -> Path:
        return Path(self.settings.poi_state_dir) / "last_release.json"

    def last_release(self) -> Optional[str]:
        path = self.state_path()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text()).get("release_id")
        except (OSError, json.JSONDecodeError):
            return None

    def record_release(self, release_id: str, event_count: int) -> None:
        path = self.state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(
                {
                    "release_id": release_id,
                    "events": event_count,
                    "processed_at": datetime.now(UTC).isoformat(),
                }
            )
        )
        temp.replace(path)

    # ----------------------------------------------------------------- #
    # join                                                               #
    # ----------------------------------------------------------------- #
    @staticmethod
    def join_deltas_to_places(
        delta_files: Sequence[Path],
        place_files: Sequence[Path],
        bboxes: Sequence[Dict[str, float]],
    ) -> List[Dict[str, Any]]:
        """Join delta ids to place attributes, filtered to registered metros.

        The bbox filter is pushed into the query rather than applied in Python:
        a release covers the whole planet and we care about ~62 metros, so
        filtering after materializing every joined row would move two orders of
        magnitude more data than necessary.
        """
        import duckdb

        if not delta_files or not place_files:
            return []

        con = duckdb.connect()
        deltas = ", ".join(f"'{p}'" for p in delta_files)
        places = ", ".join(f"'{p}'" for p in place_files)
        bbox_clause = " OR ".join(
            f"(p.latitude BETWEEN {b['min_lat']} AND {b['max_lat']} AND "
            f"p.longitude BETWEEN {b['min_lng']} AND {b['max_lng']})"
            for b in bboxes
        ) or "FALSE"

        rows = con.execute(
            f"""
            SELECT d.fsq_place_id, d.action, d.redirect,
                   p.name, p.latitude, p.longitude, p.address, p.locality, p.region,
                   p.postcode, p.date_closed, p.fsq_category_ids, p.fsq_category_labels,
                   p.unresolved_flags
            FROM read_parquet([{deltas}]) d
            LEFT JOIN read_parquet([{places}]) p USING (fsq_place_id)
            WHERE p.fsq_place_id IS NULL OR ({bbox_clause})
            """
        ).fetchall()
        columns = [
            "fsq_place_id", "action", "redirect", "name", "latitude", "longitude",
            "address", "locality", "region", "postcode", "date_closed",
            "fsq_category_ids", "fsq_category_labels", "unresolved_flags",
        ]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    # ----------------------------------------------------------------- #
    # event building                                                     #
    # ----------------------------------------------------------------- #
    def build_event(self, row: Dict[str, Any], release: Release) -> Optional[Any]:
        """One joined row -> a ``PoiChangeEvent``, or None when it is not churn."""
        from src.schemas.models import PoiChangeEvent

        poi_id = str(row.get("fsq_place_id") or row.get("place_id") or row.get("id") or "").strip()
        if not poi_id:
            return None

        event_type, confidence = classify(
            row.get("action"),
            date_closed=row.get("date_closed"),
            unresolved_flags=row.get("unresolved_flags"),
            redirect=row.get("redirect"),
        )
        if event_type is None:
            return None

        lat, lon = row.get("latitude"), row.get("longitude")
        if lat is None or lon is None:
            return None
        try:
            lat_f, lon_f = float(lat), float(lon)
        except (TypeError, ValueError):
            return None
        if lat_f == 0.0 and lon_f == 0.0:
            return None

        category_id, category_label = category_of(row)
        category_id = category_id or row.get("category_id") or row.get("fsq_category_id")
        category_label = category_label or row.get("category") or row.get("category_name")
        if not self.is_licensed(category_id):
            return None

        city_id = self.crosswalk.city_for_point(lat_f, lon_f)
        if city_id is None:
            return None

        h3 = self.spatial_indexer.get_multi_res_hierarchy(lat_f, lon_f)
        from src.spatial.geo_utils import get_division_for_coordinate

        # Event date is the RELEASE date, not `date_closed`. Foursquare's own
        # documentation says `date_closed` is "the date the POI was marked as
        # closed in our database", which is not the day it closed; using it
        # would dress a detection date up as ground truth.
        event_date = datetime.combine(release.release_date, datetime.min.time(), tzinfo=UTC)

        return PoiChangeEvent(
            city_id=city_id,
            poi_id=poi_id,
            source="fsq",
            event_type=event_type,
            name=row.get("name"),
            category=category_label,
            category_id=category_id,
            confidence=confidence,
            release_id=f"dt={release.release_id}",
            action=str(row.get("action") or "") or None,
            borough=get_division_for_coordinate(lat_f, lon_f, city_id=city_id),
            address=row.get("address"),
            latitude=lat_f,
            longitude=lon_f,
            event_date=event_date,
            h3_res7=h3["h3_res7"],
            h3_res8=h3["h3_res8"],
            h3_res9=h3["h3_res9"],
            ingested_at=datetime.now(UTC),
        )

    @staticmethod
    def dedup(events: Sequence[Any]) -> List[Any]:
        """Collapse to one event per (source, native id), best source wins."""
        rank = {source: index for index, source in enumerate(SOURCE_PRECEDENCE)}
        best: Dict[str, Any] = {}
        for event in events:
            existing = best.get(event.poi_id)
            if existing is None:
                best[event.poi_id] = event
                continue
            if rank.get(event.source, 99) < rank.get(existing.source, 99):
                best[event.poi_id] = event
        return list(best.values())

    # ----------------------------------------------------------------- #
    # run                                                                #
    # ----------------------------------------------------------------- #
    def run_stream(self, work_dir: Optional[str] = None, limit: Optional[int] = None) -> int:
        """Process the newest unprocessed release."""
        import tempfile

        self.check_licensing()

        releases = self.list_releases()
        release = select_latest_release(releases, after=self.last_release())
        if release is None:
            logger.info("POI deltas: already current at release %s", self.last_release())
            return 0

        from src.spatial.city_registry import REGISTRY

        bboxes = [reg.metro_bbox for reg in REGISTRY.values()]

        staging = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="fsq-"))
        delta_files = [self.download(p, staging / "deltas") for p in release.delta_paths]
        place_files = [self.download(p, staging / "places") for p in release.place_paths]

        rows = self.join_deltas_to_places(delta_files, place_files, bboxes)
        events = [e for e in (self.build_event(row, release) for row in rows) if e is not None]
        events = self.dedup(events)
        if limit is not None:
            events = events[:limit]

        unlocatable = sum(
            1 for row in rows if row.get("latitude") is None and row.get("action") != ACTION_UPDATE
        )
        for row_id in range(unlocatable):
            self.producer.route_to_dlq(
                failed_topic=self.settings.topic_poi_change,
                key=f"fsq:{release.release_id}:unlocatable:{row_id}",
                payload={"release": release.release_id},
                error_msg="delta id has no matching place row — no geometry to tag",
            )

        for event in events:
            self.producer.produce(
                topic=self.settings.topic_poi_change,
                key=f"{event.city_id}:fsq:{event.poi_id}",
                payload=event,
            )
        self.producer.flush()
        self.record_release(release.release_id, len(events))
        logger.info(
            "POI release dt=%s: %d joined rows -> %d events (%d unlocatable)",
            release.release_id,
            len(rows),
            len(events),
            unlocatable,
        )
        return len(events)


def parse_fsq_delta_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    crosswalk: Any = None,
    indexer: Any = None,
) -> List[Any]:
    """Public row/iterable adapter for fixture-driven FSQ delta parsing."""
    producer = PoiDiffProducer(
        crosswalk=crosswalk,
        indexer=indexer,
        kafka_producer=object(),
        strict_licensing=False,
    )
    return producer.build_events(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Foursquare OS Places delta producer")
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--non-commercial",
        action="store_true",
        help="run without the category exclusion list (non-commercial use only)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    PoiDiffProducer(strict_licensing=not args.non_commercial).run_stream(
        work_dir=args.work_dir, limit=args.limit
    )
