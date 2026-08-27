"""Deterministic address geocoding with a Postgres-backed replay cache (ADR 0004).

Wave G1 substrate: converts address strings on coordinate-less municipal rows
into confidence-gated coordinates. Design contract, in priority order:

1. Deterministic and replayable — the Postgres cache is the guarantee, not an
   optimization. The first provider answer for a normalized address (including
   a definitive miss) is frozen forever keyed by a version-stamped hash, so a
   replay six months later resolves identically from the cache even if the
   underlying provider's data has drifted.
2. Self-hostable — backends target zero-marginal-cost substrates
   (:class:`CensusBatchBackend` over Census TIGER/Line addressbatch,
   :class:`NominatimBackend` against a self-hosted or public Nominatim).
3. Cached in Postgres — ``geocode_cache(address_hash → lat, lon, confidence,
   source)``.
4. Confidence-gated — results below the floor resolve to ``None`` so callers
   emit null H3 rather than a wrong cell. Gating happens at read time against
   the caller's floor; cached raw values are immutable.
"""

from __future__ import annotations

import hashlib
import re
import time
import typing
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

NORM_VERSION = "v2"

# Tokens that begin an apartment/unit suffix. v2 removes the designator plus
# its immediately following value token instead of truncating the whole tail:
# DC-style addresses place units MID-string ("7701 GEORGIA AVE NW, STE 102,
# Washington, DC"), where tail-truncation amputated the city context and
# turned resolvable addresses into misses (US-74 finding).
_UNIT_TOKENS = {"APT", "APARTMENT", "UNIT", "STE", "SUITE", "BLDG", "BUILDING", "FL", "FLOOR", "RM", "ROOM"}
_PUNCT_RE = re.compile(r"[^A-Z0-9 ]+")
_WS_RE = re.compile(r"\s+")
# A query that already names a state must not receive a context suffix —
# appending one corrupts legitimate out-of-jurisdiction premises addresses
# (US-74 finding: ~24% of DC license premises sit in MD/VA).
_STATE_RE = re.compile(
    r"\b(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|"
    r"MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|"
    r"WV|WI|WY|DC)\b"
)


def normalize_address(address: Any) -> str:
    """Deterministically canonicalize one address string for geocoding.

    Uppercase, punctuation folded to spaces, whitespace collapsed, unit
    designator + value pairs removed in place. Same input always yields the
    same output; the output is version-stamped when hashed (see
    :func:`address_hash`).
    """
    if not address:
        return ""
    # '#' always begins a unit suffix on US address lines, and it would not
    # survive punctuation folding as a recognizable token — split it first.
    upper = str(address).upper().split("#", 1)[0]
    cleaned = _PUNCT_RE.sub(" ", upper)
    cleaned = _WS_RE.sub(" ", cleaned).strip()
    tokens = cleaned.split(" ") if cleaned else []
    kept: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index > 0 and token in _UNIT_TOKENS:
            index += 2  # drop the designator and its value token
            continue
        kept.append(token)
        index += 1
    return " ".join(kept)


def address_hash(normalized: str) -> str:
    """Version-stamped content hash of a normalized address."""
    return hashlib.sha256(f"{NORM_VERSION}|{normalized}".encode()).hexdigest()


@dataclass(frozen=True)
class GeoPoint:
    """One geocoded coordinate with provenance."""

    lat: float
    lon: float
    confidence: float
    source: str


class PostgresGeocodeCache:
    """address_hash → coordinate cache; also persists definitive misses.

    A row with NULL lat/lon is a *frozen miss*: the provider definitively had
    nothing for this normalized address at cache time, and replays must keep
    getting "nothing" rather than silently re-resolving against drifted data.
    """

    DDL_POSTGRES = """
    CREATE TABLE IF NOT EXISTS geocode_cache (
        address_hash TEXT PRIMARY KEY,
        address_norm TEXT NOT NULL,
        lat DOUBLE PRECISION,
        lon DOUBLE PRECISION,
        confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
        source TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """

    DDL_SQLITE = """
    CREATE TABLE IF NOT EXISTS geocode_cache (
        address_hash TEXT PRIMARY KEY,
        address_norm TEXT NOT NULL,
        lat DOUBLE PRECISION,
        lon DOUBLE PRECISION,
        confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
        source TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """

    def __init__(self, uri_or_engine: str | Engine):
        self.engine = (
            create_engine(uri_or_engine, pool_pre_ping=True)
            if isinstance(uri_or_engine, str)
            else uri_or_engine
        )

    def ensure_table(self) -> None:
        is_sqlite = self.engine.dialect.name == "sqlite"
        ddl = self.DDL_SQLITE if is_sqlite else self.DDL_POSTGRES
        with self.engine.begin() as conn:
            conn.execute(text(ddl))

    def get(self, address_hash_value: str) -> GeoPoint | None | KeyError:
        """Return the frozen answer for a hash.

        Returns a :class:`GeoPoint`, ``None`` for a frozen miss, or
        :class:`KeyError` sentinel when the hash was never seen.
        """
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT lat, lon, confidence, source FROM geocode_cache "
                    "WHERE address_hash = :h"
                ),
                {"h": address_hash_value},
            ).fetchone()
        if row is None:
            return KeyError(address_hash_value)
        if row[0] is None or row[1] is None:
            return None
        return GeoPoint(lat=float(row[0]), lon=float(row[1]), confidence=float(row[2]), source=str(row[3]))

    def put_many(self, entries: Sequence[tuple[str, str, GeoPoint | None]]) -> None:
        """Freeze (hash, normalized, point-or-miss) rows idempotently."""
        if not entries:
            return
        params = [
            {
                "h": entry_hash,
                "n": normalized,
                "lat": point.lat if point else None,
                "lon": point.lon if point else None,
                "c": point.confidence if point else 0.0,
                "s": point.source if point else "none",
            }
            for entry_hash, normalized, point in entries
        ]
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO geocode_cache (address_hash, address_norm, lat, lon, confidence, source) "
                    "VALUES (:h, :n, :lat, :lon, :c, :s) "
                    "ON CONFLICT (address_hash) DO NOTHING"
                ),
                params,
            )

    def flush(self) -> None:
        """Remove every cached row (determinism acceptance runs only)."""
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM geocode_cache"))


class NominatimBackend:
    """Nominatim /search backend (self-hosted URL or the public instance).

    Nominatim exposes no numeric accuracy score, so confidence is derived from
    corroboration: a result whose display name contains the leading house
    number of the query corroborates a rooftop-level match (0.95); anything
    else is treated as area-level guesswork (0.5, below every sane floor).
    """

    def __init__(
        self,
        base_url: str = "https://nominatim.openstreetmap.org",
        user_agent: str = "urban-signal-geocoder/1.0",
        min_interval_seconds: float = 1.1,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.min_interval = min_interval_seconds
        self.timeout = timeout
        self._last_call = 0.0
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
        )

    def geocode(self, normalized: str) -> GeoPoint | None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()
        response = self._client.get(
            f"{self.base_url}/search",
            params={"format": "jsonv2", "limit": 1, "addressdetails": 0, "q": normalized},
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        best = results[0]
        lat = float(best["lat"])
        lon = float(best["lon"])
        house_number = normalized.split(" ", 1)[0] if normalized else ""
        corroborated = bool(house_number) and house_number in str(best.get("display_name", "")).upper()
        confidence = 0.95 if corroborated else 0.5
        return GeoPoint(lat=lat, lon=lon, confidence=confidence, source=f"nominatim:{best.get('osm_type', '?')}")


class CensusBatchBackend:
    """Census TIGER/Line addressbatch backend (≤1000 addresses per call).

    Match statuses map conservatively: Exact→1.0, Tie→0.5 (ambiguous), any
    Non_Exact spelling→0.7, No_Match→miss. The public endpoint requires no
    key; the same API shape is what a self-hosted TIGER stack serves.
    """

    STATUS_CONFIDENCE: typing.ClassVar[dict[str, float]] = {
        "exact": 1.0,
        "tie": 0.5,
        "non_exact": 0.7,
        "non-exact": 0.7,
    }

    def __init__(self, base_url: str = "https://geocoding.services.census.gov", benchmark: str = "Public_AR_Current", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.benchmark = benchmark
        self.timeout = timeout

    def geocode_many(self, ids_and_addresses: Sequence[tuple[str, str]]) -> dict[str, GeoPoint | None]:
        import csv
        import io

        csv_body = io.StringIO()
        writer = csv.writer(csv_body)
        for row_id, normalized in ids_and_addresses:
            writer.writerow([row_id, normalized])
        response = httpx.post(
            f"{self.base_url}/geocoder/locations/addressbatch",
            params={"benchmark": self.benchmark},
            files={"addressFile": ("addresses.csv", csv_body.getvalue().encode(), "text/csv")},
            timeout=self.timeout,
        )
        response.raise_for_status()
        resolved: dict[str, GeoPoint | None] = {}
        for row in csv.reader(io.StringIO(response.text)):
            if not row or not row[0]:
                continue
            row_id, status, coords = row[0], row[2].strip(), row[4]
            confidence = self.STATUS_CONFIDENCE.get(status.lower())
            if confidence is None or not coords or "(" not in coords:
                resolved[row_id] = None
                continue
            lon_text, lat_text = coords.strip('() ').split(",")
            resolved[row_id] = GeoPoint(float(lat_text), float(lon_text), confidence, f"census:{status}")
        return resolved

    def geocode(self, normalized: str) -> GeoPoint | None:
        return self.geocode_many([("1", normalized)]).get("1")


class CensusBackend:
    """Census TIGER/Line onelineaddress backend (per-address).

    TIGER range interpolation covers every US street segment — including
    addresses OSM has never mapped — which is why it is the plan's named
    substrate. A returned match is an interpolated address-range hit:
    confidence 1.0. Empty ``addressMatches`` is a definitive miss.
    """

    def __init__(
        self,
        base_url: str = "https://geocoding.geo.census.gov",
        benchmark: str = "Public_AR_Current",
        min_interval_seconds: float = 0.3,
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.benchmark = benchmark
        self.min_interval = min_interval_seconds
        self.timeout = timeout
        self._last_call = 0.0

    def geocode(self, normalized: str) -> GeoPoint | None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()
        response = httpx.get(
            f"{self.base_url}/geocoder/locations/onelineaddress",
            params={"address": normalized, "benchmark": self.benchmark, "format": "json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        matches = response.json().get("result", {}).get("addressMatches") or []
        if not matches:
            return None
        best = matches[0]
        coords = best["coordinates"]
        return GeoPoint(float(coords["y"]), float(coords["x"]), 1.0, "census:tiger")


class Geocoder:
    """Cache-first facade; the only class callers should touch."""

    def __init__(
        self,
        cache: PostgresGeocodeCache,
        backend: Any,
        confidence_floor: float = 0.9,
    ):
        self.cache = cache
        self.backend = backend
        self.confidence_floor = confidence_floor

    def geocode(self, address: Any) -> GeoPoint | None:
        """Resolve one address; never raises on provider failure.

        Provider errors degrade to an uncached None (the next call retries);
        only definitive provider answers are frozen into the cache.
        """
        normalized = normalize_address(address)
        if not normalized:
            return None
        digest = address_hash(normalized)
        cached = self.cache.get(digest)
        if not isinstance(cached, KeyError):
            return self._gate(cached)
        try:
            point = self.backend.geocode(normalized)
        except Exception:  # noqa: BLE001  # provider outages must not kill enrichment
            return None
        self.cache.put_many([(digest, normalized, point)])
        return self._gate(point)

    def geocode_many(self, addresses: Iterable[Any]) -> list[GeoPoint | None]:
        """Resolve many addresses cache-first; misses go to the backend once.

        Backends exposing ``geocode_many`` (e.g. Census batches) are used for
        the unresolved set; otherwise falls back to rate-limited sequential
        :meth:`geocode` calls.
        """
        normalized_list = [normalize_address(address) for address in addresses]
        results: list[GeoPoint | None] = [None] * len(normalized_list)
        pending: list[tuple[int, str, str]] = []
        for index, normalized in enumerate(normalized_list):
            if not normalized:
                continue
            digest = address_hash(normalized)
            cached = self.cache.get(digest)
            if isinstance(cached, KeyError):
                pending.append((index, digest, normalized))
            else:
                results[index] = self._gate(cached)
        if not pending:
            return results
        batch_backend = getattr(self.backend, "geocode_many", None)
        if batch_backend is None:
            for index, _digest, normalized in pending:
                results[index] = self.geocode(normalized)
            return results
        try:
            answers = batch_backend([(digest, normalized) for _index, digest, normalized in pending])
            self.cache.put_many(
                [(digest, normalized, answers.get(digest)) for _index, digest, normalized in pending]
            )
        except Exception:  # noqa: BLE001  # leave uncached; next run retries
            return results
        for index, digest, _normalized in pending:
            cached = self.cache.get(digest)
            if not isinstance(cached, KeyError):
                results[index] = self._gate(cached)
        return results

    def _gate(self, point: GeoPoint | None) -> GeoPoint | None:
        if point is None or point.confidence < self.confidence_floor:
            return None
        return point


_geocoder_singleton: Geocoder | None = None


def get_geocoder() -> Geocoder:
    """Process-wide cache-first geocoder built from settings (lazy singleton)."""
    global _geocoder_singleton
    if _geocoder_singleton is None:
        from src.config import settings

        cache = PostgresGeocodeCache(settings.postgres_uri)
        cache.ensure_table()
        if settings.geocode_backend == "census":
            backend = CensusBackend()
        else:
            backend = NominatimBackend(base_url=settings.nominatim_base_url)
        _geocoder_singleton = Geocoder(
            cache,
            backend,
            confidence_floor=settings.geocode_confidence_floor,
        )
    return _geocoder_singleton


def geocode_row_if_declared(
    city_id: str,
    feed_value: str,
    address: Any,
    context: str | None = None,
) -> tuple[float, float] | None:
    """Resolve coordinates for rows of specs that declare ``needs_geocode``.

    Returns ``(lat, lon)`` above the confidence floor, else ``None`` — both
    for undeclared feeds and for failures, so producers fall through to their
    existing coordinate-less behavior unchanged. Never raises.
    """
    try:
        from src.spatial.city_registry import FeedType, get_dataset, normalize_city

        cid = normalize_city(city_id)
        if cid is None:
            return None
        spec = get_dataset(cid, FeedType(feed_value))
        if not spec.needs_geocode:
            return None
        if not isinstance(address, str) or len(address.strip()) < 6:
            return None
        query = address.strip()
        suffix = spec.geocode_context
        if suffix and suffix.upper() not in query.upper() and not _STATE_RE.search(query.upper()):
            query = f"{query}, {suffix}"
        point = get_geocoder().geocode(query)
        return (point.lat, point.lon) if point else None
    except Exception:  # noqa: BLE001  # geocoding must never kill parsing
        return None
