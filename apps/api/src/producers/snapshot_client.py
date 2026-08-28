"""SnapshotClient — live state feeds with no watermark (US-363 §1.2).

GBFS station feeds change state **in place**. There is no watermark column,
no row id that survives a change, and no publication of installs or removals:
the only way to see that a dock appeared is to hold the previous station set
and diff against it. That makes this a different archetype from
``PaginatingClient`` — poll, snapshot, diff, persist — and it fits any
attribute-poor point feed that republishes its whole state each cycle (LA's
small-cell layer `7dww-jq9x` is the next candidate).

Verified live 2026-08-28 against Citi Bike (``bkn``): GBFS **2.3**, ``ttl`` 60,
**2,508** stations, and ``station_information`` / ``station_status`` id spaces
matching exactly (2,508 of 2,508). **98** stations report ``is_installed: 0``
— the documented pre-activation quirk, and the reason a raw station-set diff
is not enough on its own.

Dialect handling follows ``gbfs_versions`` where published and otherwise
reads the envelope's ``version``; v1.1, v2.3 and v3.0 differ in where the
feed list lives (``data.<lang>.feeds`` vs ``data.feeds``) and in whether
``capacity`` is guaranteed.

**The state store is the product.** No public archive of GBFS
``station_information`` history exists, so the accumulated station set is
itself an asset, not a cache: it is what makes install/removal dates
recoverable at all.

Licensing is enforced at the config layer, not here: only the Lyft-operated
pool is registered, because Lyft's Data License Agreement permits product use
while barring re-hosting of the raw feed, and Lime/Bird/Spin/Bolt/Veo carry
internal-non-commercial-only terms with 10-minute retention limits.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

STATION_INFORMATION = "station_information"
STATION_STATUS = "station_status"

# Operator sentinels seen in the wild that mean "unknown", not a number.
DOCK_SENTINELS = frozenset({999999, 99999, -1})


@dataclass
class StationRecord:
    """One station as we hold it in the state store."""

    station_id: str
    name: Optional[str] = None
    short_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    capacity: Optional[int] = None
    first_seen: str = ""
    last_seen: str = ""
    is_installed: Optional[int] = None

    def to_json(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "name": self.name,
            "short_name": self.short_name,
            "lat": self.lat,
            "lon": self.lon,
            "capacity": self.capacity,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "is_installed": self.is_installed,
        }

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "StationRecord":
        return cls(
            station_id=str(payload.get("station_id", "")),
            name=payload.get("name"),
            short_name=payload.get("short_name"),
            lat=payload.get("lat"),
            lon=payload.get("lon"),
            capacity=payload.get("capacity"),
            first_seen=payload.get("first_seen", ""),
            last_seen=payload.get("last_seen", ""),
            is_installed=payload.get("is_installed"),
        )


@dataclass
class SnapshotDiff:
    """What one poll changed."""

    added: List[StationRecord] = field(default_factory=list)
    removed: List[StationRecord] = field(default_factory=list)
    unchanged: int = 0
    dlq: List[Tuple[str, str]] = field(default_factory=list)  # (station_id, reason)


SUPPORTED_GBFS_VERSIONS = ("3.0", "2.3", "1.1")
STATUS_NUMERIC_FIELDS = (
    "num_bikes_available",
    "num_docks_available",
    "num_bikes_disabled",
    "num_docks_disabled",
)
STATUS_SENTINELS = DOCK_SENTINELS | {86400}


class GbfsDialectError(RuntimeError):
    """The feed does not look like any GBFS version we can read."""


class EmptySnapshotError(RuntimeError):
    """The feed answered with an empty station set.

    Treated as a failed poll rather than a valid snapshot of "no stations".
    Lyft publishes a live-but-empty `dca` stub alongside the real Capital
    Bikeshare system (`dca-cabi`), and it answers 200 with
    ``{"data": {"stations": []}}`` and a fresh ``last_updated`` (verified
    2026-08-28). Seeding the state store from that, then polling a feed that
    later populates, would stamp an install event on all 866 stations at once.
    An empty answer means "ask again", never "they all vanished".
    """


class SnapshotClient:
    """Polls a GBFS system, diffs its station set, and persists the state."""

    def __init__(self, state_dir: Optional[str] = None, timeout_seconds: float = 30.0):
        from src.config import settings

        self.state_dir = Path(state_dir or settings.gbfs_state_dir)
        self.timeout = timeout_seconds
        self.last_status_snapshot: Optional[Tuple[str, List[Dict[str, Any]]]] = None

    # ----------------------------------------------------------------- #
    # transport                                                          #
    # ----------------------------------------------------------------- #
    def _get_json(self, url: str) -> Any:
        import httpx

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            return resp.json()

    # ----------------------------------------------------------------- #
    # discovery                                                          #
    # ----------------------------------------------------------------- #
    @staticmethod
    def resolve_feeds(discovery: Dict[str, Any], base_url: str | None = None) -> Dict[str, str]:
        """Map feed name -> URL from a GBFS document of any supported dialect."""
        data = discovery.get("data")
        if not isinstance(data, dict):
            raise GbfsDialectError("discovery document has no `data` object")

        feeds = data.get("feeds")
        if feeds is None:
            for value in data.values():
                if isinstance(value, dict) and isinstance(value.get("feeds"), list):
                    feeds = value["feeds"]
                    break
        if not isinstance(feeds, list):
            raise GbfsDialectError(
                f"no feed list under data or data.<lang> (keys: {sorted(data)[:6]})"
            )

        resolved = {}
        for entry in feeds:
            if isinstance(entry, dict) and entry.get("name") and entry.get("url"):
                url = str(entry["url"])
                resolved[str(entry["name"])] = urljoin(base_url, url) if base_url else url
        if STATION_INFORMATION not in resolved:
            raise GbfsDialectError(
                f"system publishes no {STATION_INFORMATION} feed (has: {sorted(resolved)})"
            )
        return resolved

    @staticmethod
    def _version_links(payload: Dict[str, Any], base_url: str) -> List[Tuple[str, str]]:
        """Extract supported GBFS version-document links from either dialect."""
        links: List[Tuple[str, str]] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                versions = value.get("versions")
                if isinstance(versions, list):
                    for entry in versions:
                        if isinstance(entry, dict) and entry.get("version") and entry.get("url"):
                            links.append((str(entry["version"]), urljoin(base_url, str(entry["url"]))))
                feeds = value.get("feeds")
                if isinstance(feeds, list):
                    for entry in feeds:
                        if (
                            isinstance(entry, dict)
                            and entry.get("name") == "gbfs_versions"
                            and entry.get("url")
                        ):
                            links.append(("", urljoin(base_url, str(entry["url"]))))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(payload.get("data"))
        return links

    @staticmethod
    def _version_rank(version: str) -> int:
        try:
            return SUPPORTED_GBFS_VERSIONS.index(version)
        except ValueError:
            return len(SUPPORTED_GBFS_VERSIONS)

    def discover(self, discovery_url: str) -> Tuple[Dict[str, str], str]:
        """Fetch the highest supported document advertised by ``gbfs_versions``."""
        root = self._get_json(discovery_url)
        if not isinstance(root, dict):
            raise GbfsDialectError("discovery response is not a JSON object")

        candidates = self._version_links(root, discovery_url)
        expanded: List[Tuple[str, str]] = list(candidates)
        for declared_version, url in candidates:
            if declared_version in SUPPORTED_GBFS_VERSIONS:
                continue
            versions_doc = self._get_json(url)
            if isinstance(versions_doc, dict):
                expanded.extend(self._version_links(versions_doc, url))

        supported = [entry for entry in expanded if entry[0] in SUPPORTED_GBFS_VERSIONS]
        if supported:
            # SUPPORTED_GBFS_VERSIONS is ordered newest-to-oldest.
            version, document_url = min(supported, key=lambda entry: self._version_rank(entry[0]))
            selected = self._get_json(document_url)
            if isinstance(selected, dict):
                return self.resolve_feeds(selected, document_url), version

        version = str(root.get("version") or "")
        return self.resolve_feeds(root, discovery_url), version

    # ----------------------------------------------------------------- #
    # parsing                                                            #
    # ----------------------------------------------------------------- #
    @staticmethod
    def parse_stations(
        information: Dict[str, Any],
        status: Optional[Dict[str, Any]] = None,
        now: Optional[str] = None,
    ) -> Tuple[Dict[str, StationRecord], List[Tuple[str, str]]]:
        """Turn one poll into a station set, plus rows routed to the DLQ.

        Rejected to the DLQ rather than admitted with a guess:

        * a station with no id, or with no usable coordinate;
        * a coordinate at exactly (0, 0) — the null-island placeholder some
          free-floating systems emit for a system-wide "virtual station";
        * a dock count carrying an operator sentinel (999999 and friends).

        ``is_installed: 0`` is **not** a DLQ case. It is a real, documented
        pre-activation state (98 of Citi Bike's 2,508 stations on
        2026-08-28), and it is precisely the signal that a station is about to
        exist — dropping it would discard the leading indicator this feed is
        registered for. It is carried on the record instead.
        """
        stamp = now or datetime.now(UTC).isoformat()
        stations: Dict[str, StationRecord] = {}
        dlq: List[Tuple[str, str]] = []

        status_by_id: Dict[str, Dict[str, Any]] = {}
        if status:
            for row in (status.get("data") or {}).get("stations") or []:
                sid = str(row.get("station_id") or "").strip()
                if sid:
                    status_by_id[sid] = row

        for row in (information.get("data") or {}).get("stations") or []:
            sid = str(row.get("station_id") or "").strip()
            if not sid:
                dlq.append(("", "station_information row carries no station_id"))
                continue
            lat, lon = row.get("lat"), row.get("lon")
            if lat is None or lon is None:
                dlq.append((sid, "station has no coordinate"))
                continue
            try:
                lat_f, lon_f = float(lat), float(lon)
            except (TypeError, ValueError):
                dlq.append((sid, f"uncoercible coordinate ({lat!r}, {lon!r})"))
                continue
            if lat_f == 0.0 and lon_f == 0.0:
                dlq.append((sid, "null-island placeholder coordinate"))
                continue

            capacity = row.get("capacity")
            if isinstance(capacity, (int, float)) and int(capacity) in DOCK_SENTINELS:
                capacity = None
            elif capacity is not None:
                try:
                    capacity = int(capacity)
                except (TypeError, ValueError):
                    capacity = None

            live = status_by_id.get(sid, {})
            stations[sid] = StationRecord(
                station_id=sid,
                name=row.get("name"),
                short_name=row.get("short_name"),
                lat=lat_f,
                lon=lon_f,
                capacity=capacity,
                first_seen=stamp,
                last_seen=stamp,
                is_installed=live.get("is_installed"),
            )
        return stations, dlq

    @staticmethod
    def parse_status(
        status: Optional[Dict[str, Any]],
        stations: Dict[str, StationRecord],
        snapshot_ts: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Normalize one station-status snapshot for the private state archive.

        Status rows are retained by source snapshot timestamp rather than
        overwritten. Unknown station ids and malformed rows are omitted: the
        station-information snapshot is the authoritative spatial inventory.
        Operator sentinels are represented as null so they cannot contaminate
        availability or turnover aggregates.
        """
        if not status:
            stamp = snapshot_ts or datetime.now(UTC).isoformat()
            return stamp, []

        raw_timestamp = status.get("last_updated")
        if raw_timestamp is None:
            raw_timestamp = (status.get("data") or {}).get("last_updated")
        if raw_timestamp is not None and str(raw_timestamp).strip():
            try:
                stamp = datetime.fromtimestamp(float(raw_timestamp), UTC).isoformat()
            except (TypeError, ValueError, OverflowError, OSError):
                stamp = str(raw_timestamp)
        else:
            stamp = snapshot_ts or datetime.now(UTC).isoformat()

        from src.spatial.h3_indexer import H3SpatialIndexer

        rows: List[Dict[str, Any]] = []
        for raw in (status.get("data") or {}).get("stations") or []:
            if not isinstance(raw, dict):
                continue
            station_id = str(raw.get("station_id") or "").strip()
            station = stations.get(station_id)
            if not station or station.lat is None or station.lon is None:
                continue

            row: Dict[str, Any] = {
                "station_id": station_id,
                "snapshot_ts": stamp,
                "latitude": station.lat,
                "longitude": station.lon,
                "is_installed": raw.get("is_installed"),
                "is_renting": raw.get("is_renting"),
                "is_returning": raw.get("is_returning"),
            }
            for field_name in STATUS_NUMERIC_FIELDS:
                value = raw.get(field_name)
                if value is not None:
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        value = None
                if value in STATUS_SENTINELS:
                    value = None
                row[field_name] = value

            last_reported = raw.get("last_reported")
            if last_reported is not None:
                try:
                    last_reported = int(last_reported)
                except (TypeError, ValueError):
                    last_reported = None
            row["last_reported"] = None if last_reported in STATUS_SENTINELS else last_reported
            row.update(H3SpatialIndexer.get_multi_res_hierarchy(station.lat, station.lon))
            rows.append(row)
        return stamp, rows

    # ----------------------------------------------------------------- #
    # state store                                                        #
    # ----------------------------------------------------------------- #
    def state_path(self, system_id: str) -> Path:
        return self.state_dir / f"{system_id}.json"

    def load_state(self, system_id: str) -> Dict[str, StationRecord]:
        path = self.state_path(system_id)
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Unreadable GBFS state %s: %s — treating as empty", path, exc)
            return {}
        return {
            sid: StationRecord.from_json(row)
            for sid, row in (payload.get("stations") or {}).items()
        }

    def load_status_snapshots(self, system_id: str) -> List[Dict[str, Any]]:
        """Load the normalized status archive for one GBFS system."""
        path = self.state_path(system_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return []
        archive = payload.get("status_snapshots") or {}
        return list(archive.values()) if isinstance(archive, dict) else []

    def save_state(
        self,
        system_id: str,
        stations: Dict[str, StationRecord],
        status_snapshot: Optional[Tuple[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        path = self.state_path(system_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        prior: Dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text())
                if isinstance(loaded, dict):
                    prior = loaded
            except (OSError, json.JSONDecodeError):
                logger.warning("Replacing unreadable GBFS state %s", path)

        archive = prior.get("status_snapshots") or {}
        if not isinstance(archive, dict):
            archive = {}
        if status_snapshot is not None:
            snapshot_ts, rows = status_snapshot
            archive[f"station_status:{snapshot_ts}"] = {
                "system_id": system_id,
                "feed": STATION_STATUS,
                "snapshot_ts": snapshot_ts,
                "rows": rows,
            }

        payload = {
            "system_id": system_id,
            "saved_at": datetime.now(UTC).isoformat(),
            "stations": {sid: rec.to_json() for sid, rec in stations.items()},
            "status_snapshots": archive,
        }
        # Write-then-rename: a torn state file would look like a system that
        # lost every station and emit thousands of spurious removals.
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(payload))
        temp.replace(path)

    # ----------------------------------------------------------------- #
    # diff                                                               #
    # ----------------------------------------------------------------- #
    @staticmethod
    def diff(
        previous: Dict[str, StationRecord],
        current: Dict[str, StationRecord],
    ) -> SnapshotDiff:
        """Diff two station sets.

        **A first poll produces no events.** With no prior state every station
        looks new, which would stamp thousands of install events on the day we
        happened to start polling. The first poll seeds the store instead; the
        install date of a pre-existing station is simply not knowable from a
        feed that publishes no history.
        """
        if not previous:
            return SnapshotDiff(added=[], removed=[], unchanged=len(current))

        added = [rec for sid, rec in current.items() if sid not in previous]
        removed = [rec for sid, rec in previous.items() if sid not in current]
        unchanged = len(current) - len(added)
        return SnapshotDiff(added=added, removed=removed, unchanged=unchanged)

    @staticmethod
    def merge_state(
        previous: Dict[str, StationRecord],
        current: Dict[str, StationRecord],
    ) -> Dict[str, StationRecord]:
        """Carry ``first_seen`` forward for stations we already knew about."""
        merged: Dict[str, StationRecord] = {}
        for sid, rec in current.items():
            prior = previous.get(sid)
            if prior is not None and prior.first_seen:
                rec.first_seen = prior.first_seen
            merged[sid] = rec
        return merged

    # ----------------------------------------------------------------- #
    # poll                                                               #
    # ----------------------------------------------------------------- #
    def poll(self, system_id: str, discovery_url: str) -> Tuple[SnapshotDiff, Dict[str, StationRecord], str]:
        """One cycle: discover, fetch, parse, diff. Does not persist.

        Raises ``EmptySnapshotError`` when the system answers with no
        stations — see that class for why an empty answer is a failed poll
        rather than a mass removal.
        """
        feeds, version = self.discover(discovery_url)
        information = self._get_json(feeds[STATION_INFORMATION])
        status = self._get_json(feeds[STATION_STATUS]) if STATION_STATUS in feeds else None

        current, dlq = self.parse_stations(information, status)
        if not current:
            raise EmptySnapshotError(
                f"{system_id}: station_information returned no usable stations "
                f"({len(dlq)} rows rejected) — refusing to seed or overwrite state"
            )
        self.last_status_snapshot = self.parse_status(status, current)
        previous = self.load_state(system_id)
        result = self.diff(previous, current)
        result.dlq = dlq
        merged = self.merge_state(previous, current)
        logger.info(
            "GBFS %s (v%s): %d stations, +%d/-%d, %d to DLQ",
            system_id,
            version or "?",
            len(current),
            len(result.added),
            len(result.removed),
            len(dlq),
        )
        return result, merged, version
