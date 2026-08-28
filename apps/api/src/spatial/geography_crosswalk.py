"""Geography crosswalk for aggregate market series (US-363 §1.1).

The one shared reusable asset the sweep asks for: metro/city name and CBSA
code -> ``city_id``, plus ZIP/ZCTA -> centroid -> H3 res7/8/9. ``parcel_join``
does not provide this — it resolves parcels inside one city — and every
series source (Zillow ZIP/metro, FHFA metro/ZIP, HUD SAFMR ZIP, ACS ZCTA) is
keyed by a geography name or code rather than a point.

**Source choice.** The sweep suggests HUD's USPS ZIP crosswalk. HUD's bulk
API is token-gated (``huduser.gov/hudapi/public/usps`` returns 401 without a
Bearer token, verified 2026-08-28), which would make the crosswalk — a
dependency of every series feed — fail closed on a missing secret. The Census
Gazetteer files are the same public-domain geography with **no key at all**:

  * ``2024_Gaz_zcta_national.zip`` — 33,791 ZCTAs with ``INTPTLAT``/
    ``INTPTLONG`` internal-point centroids (1.0 MB, verified 200 live
    2026-08-28).
  * ``2024_Gaz_cbsa_national.zip`` — 935 CBSAs with ``GEOID`` (the CBSA code),
    ``NAME`` and a centroid (46 KB, verified 200 live).

**Metro names do not match across publishers, and exact matching silently
loses most metros.** The 2024 Gazetteer carries the 2023 OMB delineations
while Zillow's research CSVs still ship the older titles, so the same place is
written two different ways (verified 2026-08-28):

    Gazetteer  Houston-Pasadena-The Woodlands, TX Metro Area
    Zillow     Houston-The Woodlands-Sugar Land, TX
    Gazetteer  New York-Newark-Jersey City, NY-NJ Metro Area
    Zillow     New York, NY
    Gazetteer  Chicago-Naperville-Elgin, IL-IN Metro Area
    Zillow     Chicago-Naperville-Elgin, IL-IN-WI

Matching therefore tries the full normalized name first and falls back to
(primary city, first state) — the two parts that survive every redelineation.
Collisions on that key are logged and left unresolved rather than guessed.

Both are fetched once and cached on disk; nothing here calls the network when
the cache is warm, and every lookup is pure once loaded.

**Resolution rule.** A geography belongs to a registered city when its
internal point falls inside that city's ``metro_bbox``. Bboxes can overlap
(Prince George's inside the DC metro, Aurora inside Denver's), so a point
inside more than one resolves to the **smallest** containing bbox — the more
specific registration — and the tie is recorded rather than silently
arbitrary. A geography inside none resolves to ``None``: a national series
row outside every registered metro is dropped, not attached to the nearest
city.
"""

from __future__ import annotations

import io
import logging
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

GAZETTEER_YEAR = "2024"
ZCTA_GAZETTEER_URL = (
    f"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    f"{GAZETTEER_YEAR}_Gazetteer/{GAZETTEER_YEAR}_Gaz_zcta_national.zip"
)
CBSA_GAZETTEER_URL = (
    f"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    f"{GAZETTEER_YEAR}_Gazetteer/{GAZETTEER_YEAR}_Gaz_cbsa_national.zip"
)
# US-363 §1.4: NFIP claim coordinates are privacy-truncated to 0.1 degrees —
# roughly 11 km, far coarser than a res-8 hexagon — so claims must be tagged
# through `censusGeoid` instead. This is the tract centroid table that makes
# that possible (2.4 MB, verified 200 live 2026-08-28).
TRACT_GAZETTEER_URL = (
    f"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    f"{GAZETTEER_YEAR}_Gazetteer/{GAZETTEER_YEAR}_Gaz_tracts_national.zip"
)
# FEMA disaster declarations are county-level (fipsStateCode + fipsCountyCode)
# with no point at all. 3,222 counties, 138 KB, verified 200 live 2026-08-28.
COUNTY_GAZETTEER_URL = (
    f"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    f"{GAZETTEER_YEAR}_Gazetteer/{GAZETTEER_YEAR}_Gaz_counties_national.zip"
)

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "crosswalk"


@dataclass(frozen=True)
class GeographyPoint:
    """An internal point for one geography, with its identifiers."""

    geography_id: str
    geography_level: str  # "zip" | "metro"
    name: str
    latitude: float
    longitude: float


def _cache_dir() -> Path:
    override = os.environ.get("URBAN_CROSSWALK_CACHE_DIR")
    return Path(override) if override else DEFAULT_CACHE_DIR


def _download(url: str, dest: Path) -> Path:
    """Fetch a Gazetteer zip once. Callers with a warm cache never get here."""
    import httpx

    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Fetching Census Gazetteer %s", url)
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest


def _read_gazetteer(payload: bytes) -> Iterable[Dict[str, str]]:
    """Yield rows from a Gazetteer zip.

    The files are tab-separated with every line right-padded to a fixed width,
    so both header and value cells must be stripped; a naive split leaves
    ``INTPTLONG`` carrying eighty trailing spaces and every float parse fails.
    """
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name = archive.namelist()[0]
        text = archive.read(name).decode("utf-8", "replace")
    lines = text.splitlines()
    if not lines:
        return
    header = [cell.strip() for cell in lines[0].split("\t")]
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = [cell.strip() for cell in line.split("\t")]
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        yield dict(zip(header, cells))


class GeographyCrosswalk:
    """ZCTA / CBSA -> city_id and H3, loaded once from the Census Gazetteer."""

    def __init__(self, cache_dir: Optional[Path] = None, offline: bool = False):
        self.cache_dir = Path(cache_dir) if cache_dir else _cache_dir()
        self.offline = offline
        self._zctas: Optional[Dict[str, GeographyPoint]] = None
        self._cbsas: Optional[Dict[str, GeographyPoint]] = None
        self._cbsa_by_name: Optional[Dict[str, str]] = None
        self._cbsa_by_primary: Optional[Dict[Tuple[str, str], str]] = None
        self._tracts: Optional[Dict[str, GeographyPoint]] = None
        self._tract_stems_cache: Optional[Dict[str, List[GeographyPoint]]] = None
        self._counties: Optional[Dict[str, GeographyPoint]] = None
        self._city_bboxes: Optional[list[tuple[str, Dict[str, float], float]]] = None

    # ----------------------------------------------------------------- #
    # loading                                                            #
    # ----------------------------------------------------------------- #
    def _payload(self, url: str, filename: str) -> bytes:
        path = self.cache_dir / filename
        if path.exists():
            return path.read_bytes()
        if self.offline:
            raise FileNotFoundError(
                f"crosswalk cache miss for {filename} and offline=True — "
                f"prime the cache with GeographyCrosswalk().load() while online"
            )
        _download(url, path)
        return path.read_bytes()

    def _load_zctas(self) -> Dict[str, GeographyPoint]:
        if self._zctas is not None:
            return self._zctas
        table: Dict[str, GeographyPoint] = {}
        for row in _read_gazetteer(
            self._payload(ZCTA_GAZETTEER_URL, f"{GAZETTEER_YEAR}_Gaz_zcta_national.zip")
        ):
            geoid = row.get("GEOID", "")
            lat, lng = row.get("INTPTLAT"), row.get("INTPTLONG")
            if not geoid or not lat or not lng:
                continue
            try:
                table[geoid] = GeographyPoint(geoid, "zip", geoid, float(lat), float(lng))
            except ValueError:
                continue
        self._zctas = table
        return table

    def _load_cbsas(self) -> Dict[str, GeographyPoint]:
        if self._cbsas is not None:
            return self._cbsas
        table: Dict[str, GeographyPoint] = {}
        by_name: Dict[str, str] = {}
        by_primary: Dict[Tuple[str, str], str] = {}
        ambiguous: set[Tuple[str, str]] = set()
        for row in _read_gazetteer(
            self._payload(CBSA_GAZETTEER_URL, f"{GAZETTEER_YEAR}_Gaz_cbsa_national.zip")
        ):
            geoid = row.get("GEOID", "")
            name = row.get("NAME", "")
            lat, lng = row.get("INTPTLAT"), row.get("INTPTLONG")
            if not geoid or not lat or not lng:
                continue
            try:
                table[geoid] = GeographyPoint(geoid, "metro", name, float(lat), float(lng))
            except ValueError:
                continue
            by_name[normalize_metro_name(name)] = geoid
            key = metro_primary_key(name)
            if key:
                collision = by_primary.get(key)
                if collision and collision != geoid:
                    ambiguous.add(key)
                by_primary[key] = geoid
        for key in ambiguous:
            # Two CBSAs share a (primary city, first state) key. Guessing
            # between them would attach a metro series to the wrong market, so
            # the key is dropped and the caller falls back to no match.
            logger.warning("Ambiguous CBSA primary key %r — dropped from the fallback index", key)
            by_primary.pop(key, None)
        self._cbsas = table
        self._cbsa_by_name = by_name
        self._cbsa_by_primary = by_primary
        return table

    def _load_tracts(self) -> Dict[str, GeographyPoint]:
        if self._tracts is not None:
            return self._tracts
        table: Dict[str, GeographyPoint] = {}
        for row in _read_gazetteer(
            self._payload(TRACT_GAZETTEER_URL, f"{GAZETTEER_YEAR}_Gaz_tracts_national.zip")
        ):
            geoid = row.get("GEOID", "")
            lat, lng = row.get("INTPTLAT"), row.get("INTPTLONG")
            if not geoid or not lat or not lng:
                continue
            try:
                table[geoid] = GeographyPoint(geoid, "tract", geoid, float(lat), float(lng))
            except ValueError:
                continue
        self._tracts = table
        return table

    def _load_counties(self) -> Dict[str, GeographyPoint]:
        if self._counties is not None:
            return self._counties
        table: Dict[str, GeographyPoint] = {}
        for row in _read_gazetteer(
            self._payload(COUNTY_GAZETTEER_URL, f"{GAZETTEER_YEAR}_Gaz_counties_national.zip")
        ):
            geoid = row.get("GEOID", "")
            lat, lng = row.get("INTPTLAT"), row.get("INTPTLONG")
            if not geoid or not lat or not lng:
                continue
            try:
                table[geoid] = GeographyPoint(
                    geoid, "county", row.get("NAME", geoid), float(lat), float(lng)
                )
            except ValueError:
                continue
        self._counties = table
        return table

    def county_point(self, fips: Any) -> Optional[GeographyPoint]:
        """Look up a county centroid from a 5-digit state+county FIPS code."""
        text = "".join(ch for ch in str(fips or "") if ch.isdigit())
        if len(text) < 5:
            return None
        return self._load_counties().get(text[:5])

    def city_for_county_fips(self, fips: Any) -> Optional[str]:
        """Registered city whose metro bbox contains a county's internal point.

        Coarser than the ZIP path by construction — a county can span several
        markets, or none. It exists for the one feed that publishes nothing
        finer (FEMA disaster declarations), and a county whose centroid falls
        outside every registered metro resolves to ``None`` rather than being
        attached to a neighbour.
        """
        point = self.county_point(fips)
        return self.city_for_point(point.latitude, point.longitude) if point else None

    def load(self, tracts: bool = False, counties: bool = False) -> "GeographyCrosswalk":
        """Prime both tables (and the on-disk cache). Safe to call repeatedly."""
        self._load_zctas()
        self._load_cbsas()
        if tracts:
            self._load_tracts()
        if counties:
            self._load_counties()
        return self

    # ----------------------------------------------------------------- #
    # city resolution                                                    #
    # ----------------------------------------------------------------- #
    def _bboxes(self) -> list[tuple[str, Dict[str, float], float]]:
        """Registered metro bboxes with their area, smallest-first."""
        if self._city_bboxes is not None:
            return self._city_bboxes
        from src.spatial.city_registry import REGISTRY

        boxes: list[tuple[str, Dict[str, float], float]] = []
        for cid, reg in REGISTRY.items():
            bbox = reg.metro_bbox
            area = (bbox["max_lat"] - bbox["min_lat"]) * (bbox["max_lng"] - bbox["min_lng"])
            boxes.append((cid.value, bbox, area))
        boxes.sort(key=lambda item: (item[2], item[0]))
        self._city_bboxes = boxes
        return boxes

    def city_for_point(self, lat: float, lng: float) -> Optional[str]:
        """Smallest registered metro bbox containing the point, else None.

        Smallest-first matters: Prince George's sits inside the DC metro bbox
        and Aurora inside Denver's, so a first-match-wins scan over an
        unordered registry would hand the same ZIP to a different city
        depending on dict order.
        """
        for city_id, bbox, _area in self._bboxes():
            if (
                bbox["min_lat"] <= lat <= bbox["max_lat"]
                and bbox["min_lng"] <= lng <= bbox["max_lng"]
            ):
                return city_id
        return None

    def city_for_zip(self, zcta: str) -> Optional[str]:
        point = self.zip_point(zcta)
        return self.city_for_point(point.latitude, point.longitude) if point else None

    def city_for_cbsa(self, cbsa_code: str) -> Optional[str]:
        """Resolve a CBSA code to a registered city.

        **Not** by centroid containment. A CBSA spans whole counties, so its
        internal point sits well outside the tighter bbox we register a metro
        with — Seattle-Tacoma-Bellevue's centroid lands in the Cascades, east
        of Seattle's ``metro_bbox`` entirely, and Denver's and DC's do the
        same. Containment is right for a ZIP (small, inside one market) and
        wrong for a CBSA.

        The CBSA's *primary city* is the reliable link instead: it is exactly
        the name the registry's alias table already resolves. Centroid
        containment stays as a second pass for the cases where a CBSA's lead
        city is not itself a registered market but its centroid still lands
        inside one.
        """
        point = self._load_cbsas().get(str(cbsa_code).strip())
        if point is None:
            return None
        return self._city_for_geography_point(point)

    def _city_for_geography_point(self, point: GeographyPoint) -> Optional[str]:
        from src.spatial.city_registry import normalize_city

        key = metro_primary_key(point.name)
        if key:
            override = METRO_NAME_OVERRIDES.get(key)
            if override:
                return override
            resolved = normalize_city(key[0])
            if resolved is not None:
                return resolved.value
        return self.city_for_point(point.latitude, point.longitude)

    def city_for_metro_name(self, name: str) -> Optional[str]:
        """Resolve a publisher's metro label to a registered city.

        Tries the label's own primary city first, so a metro we register but
        whose CBSA title leads with a different city still resolves, then
        falls through to the CBSA lookup.
        """
        from src.spatial.city_registry import normalize_city

        key = metro_primary_key(name)
        if key:
            override = METRO_NAME_OVERRIDES.get(key)
            if override:
                return override
            resolved = normalize_city(key[0])
            if resolved is not None:
                return resolved.value
        code = self.cbsa_code_for_name(name)
        return self.city_for_cbsa(code) if code else None

    # ----------------------------------------------------------------- #
    # lookups                                                            #
    # ----------------------------------------------------------------- #
    def zip_point(self, zcta: str) -> Optional[GeographyPoint]:
        """Look up a ZCTA centroid, tolerating ZIP+4 and unpadded input."""
        return self._load_zctas().get(normalize_zcta(zcta))

    def cbsa_code_for_name(self, name: str) -> Optional[str]:
        """Match a publisher's metro label to a CBSA GEOID.

        Zillow writes ``"Houston-The Woodlands-Sugar Land, TX"``; the
        Gazetteer writes ``"Houston-The Woodlands-Sugar Land, TX Metro Area"``.
        Both normalize to the same key.
        """
        self._load_cbsas()
        assert self._cbsa_by_name is not None and self._cbsa_by_primary is not None
        exact = self._cbsa_by_name.get(normalize_metro_name(name))
        if exact:
            return exact
        key = metro_primary_key(name)
        return self._cbsa_by_primary.get(key) if key else None

    def _tract_stems(self) -> Dict[str, List[GeographyPoint]]:
        """Tracts indexed by their 9-character state+county+tract-base prefix."""
        if self._tract_stems_cache is not None:
            return self._tract_stems_cache
        stems: Dict[str, List[GeographyPoint]] = {}
        for geoid, point in self._load_tracts().items():
            stems.setdefault(geoid[:9], []).append(point)
        self._tract_stems_cache = stems
        return stems

    def tract_point(self, geoid: Any) -> Optional[GeographyPoint]:
        """Look up a tract centroid from a FEMA ``censusGeoid``.

        FEMA publishes a 12-character **block group** id (``482012227001``);
        the tract is its first 11 characters. Two things make a bare dict
        lookup insufficient:

        * **Tracts split between censuses.** Harris County's ``48201222700``
          became ``48201222701`` and ``48201222702`` in the 2020 tabulation,
          and a claim filed under the old id matches neither. A split tract's
          children partition their parent, so any child's centroid lies inside
          the old tract — the fallback takes the first child by GEOID, which
          is deterministic and always inside the right county.
        * **Id length varies.** Block, block-group and bare tract ids all
          appear across FEMA entities; everything is normalized to 11 digits.

        Returns ``None`` rather than a guess when neither path matches, so the
        caller can fall back to the ZIP centroid or the DLQ.
        """
        text = "".join(ch for ch in str(geoid or "") if ch.isdigit())
        if len(text) < 11:
            return None
        tract = text[:11]
        exact = self._load_tracts().get(tract)
        if exact is not None:
            return exact
        children = self._tract_stems().get(tract[:9])
        if not children:
            return None
        return sorted(children, key=lambda p: p.geography_id)[0]

    def city_for_tract(self, geoid: Any) -> Optional[str]:
        point = self.tract_point(geoid)
        return self.city_for_point(point.latitude, point.longitude) if point else None

    def tract_to_h3(self, geoid: Any, indexer: Any) -> Dict[str, Optional[str]]:
        """Tract centroid -> H3 hierarchy.

        A centroid tag, like ``zip_to_h3``: a tract is much larger than a
        res-9 hexagon, so this places the tract's signal on one cell rather
        than claiming the loss occurred there. It is still far better than the
        0.1-degree-truncated coordinate FEMA publishes, which cannot even
        place a claim in the right city reliably.
        """
        point = self.tract_point(geoid)
        if point is None:
            return {"h3_res7": None, "h3_res8": None, "h3_res9": None}
        return indexer.get_multi_res_hierarchy(point.latitude, point.longitude)

    def zip_to_h3(self, zcta: str, indexer: Any) -> Dict[str, Optional[str]]:
        """ZCTA centroid -> the multi-resolution H3 hierarchy.

        A ZCTA is far larger than a res-9 hexagon, so this is a *centroid*
        tag: the covariate it carries applies to the whole ZIP and is joined
        onto the cell the centroid lands in. It is not a claim that the ZIP's
        rent was measured in that hexagon.
        """
        point = self.zip_point(zcta)
        if point is None:
            return {"h3_res7": None, "h3_res8": None, "h3_res9": None}
        return indexer.get_multi_res_hierarchy(point.latitude, point.longitude)


def normalize_zcta(value: Any) -> str:
    """Canonicalize a ZIP/ZCTA to the Gazetteer's zero-padded 5-digit form."""
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.split("-", 1)[0]  # ZIP+4 -> ZIP
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return ""
    return digits[:5].zfill(5)


def normalize_metro_name(value: Any) -> str:
    """Fold a metro label to a comparable key.

    Strips the Gazetteer's ``Metro Area`` / ``Micro Area`` suffix, collapses
    whitespace, and case-folds, so a publisher's label and the Gazetteer's
    name meet in the middle.
    """
    text = str(value or "").strip().lower()
    for suffix in (" metro area", " micro area", " metropolitan statistical area"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return " ".join(text.split())


# CBSA-title spellings the registry's alias table does not carry, keyed by
# (primary city, first state) so they cannot collide across states.
#
# These live here rather than in the spine ALIASES table because each is a
# CBSA-title artifact, not a city alias, and two of them are genuinely
# ambiguous as bare aliases: "washington" is also a state, and "miami" is also
# the Miami, OK micro area (CBSA 33060) — the state half is what makes them
# safe. Verified against the 2024 Gazetteer 2026-08-28.
METRO_NAME_OVERRIDES: Dict[Tuple[str, str], str] = {
    ("washington", "dc"): "washington_dc",   # CBSA 47900
    ("miami", "fl"): "miami_dade",           # CBSA 33100 (NOT 33060, Miami OK)
    ("boise city", "id"): "boise",           # CBSA 14260
    ("st. louis", "mo"): "st_louis",         # CBSA 41180
    ("columbus", "ga"): "columbus_ga",       # CBSA 17980; distinct from Columbus, OH
}

# Registered markets with no CBSA of their own — they are submarkets inside a
# larger metro's CBSA (Fort Worth and Aurora inside Dallas-Fort Worth and
# Denver-Aurora; Prince George's inside Washington-Arlington-Alexandria).
# Metro-level series cannot address them and should not be forced to: they
# receive coverage through ZIP-level series instead, where centroid
# containment picks the smaller, more specific bbox.
CBSA_SUBMARKET_CITIES = frozenset({"fort_worth", "aurora", "prince_georges"})


def metro_primary_key(value: Any) -> Optional[Tuple[str, str]]:
    """(primary city, first state) for a metro label, or None if unparseable.

    ``"Houston-Pasadena-The Woodlands, TX Metro Area"`` and
    ``"Houston-The Woodlands-Sugar Land, TX"`` both key to
    ``("houston", "tx")``. The primary city and the first state are the only
    parts of a CBSA title that survive OMB redelineations.
    """
    text = normalize_metro_name(value)
    if "," not in text:
        return None
    place, _, states = text.rpartition(",")
    city = place.split("-", 1)[0].strip()
    state = states.strip().split("-", 1)[0].strip()
    if not city or not state:
        return None
    return (city, state)


_DEFAULT: Optional[GeographyCrosswalk] = None


def default_crosswalk() -> GeographyCrosswalk:
    """Process-wide crosswalk instance (loads lazily, caches on disk)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = GeographyCrosswalk()
    return _DEFAULT
