"""Context reference builder: per-hex density/covariate inputs (US-380).

Four national context layers — FRA highway-rail grade crossings (+ Form 57
incidents), IMLS public-library outlets, NCES EDGE postsecondary campuses,
HRSA health-center sites — folded into per-hex reference values destined for
``EnrichedH3Feature`` covariates / reference tables. This is the
context_observations covariate idiom (parse → site records → per-hex fold)
minus Kafka: these are stock measurements of a place, not dated events, so
nothing here emits on a topic. IMLS branch YoY churn becomes
``AnchorInstitutionEvent`` in a later stream (US-375 owns that schema).

Idioms inherited from ``context_observations_producer``:

* absence is dropped, never coerced to 0.0 where a mean would see it —
  ``aadt_mean`` averages only crossings that publish an AADT, and a hex with
  none reports ``None``, not 0;
* a row with no defensible coordinate goes geocode-pending (``needs_geocode``
  records, returned for the existing geocode pipeline) — no ad-hoc geocoder,
  and the HRSA address-suppressed family (state ``'XX'``, blank X/Y) never
  gets a guessed coordinate;
* H3 tagging is ``H3SpatialIndexer.get_multi_res_hierarchy`` (injected so
  tests can stub it).

``city_id`` resolution is spine — ``GeographyCrosswalk.city_for_point`` is
injected as ``city_for_point(lat, lng) -> str | None`` and rows outside every
registered metro keep their reference value with ``city_id=None`` (the
national stock is the point of these layers).

The canonical FRA row is ``objectid`` (fully distinct, 242,124 of 242,124
live): the FRA business key ``crossing`` duplicates (242,109 distinct) with
rows identical apart from objectid, so the builder keeps ``min(objectid)``
per crossing — byte-deterministic.

The pydantic shapes here are leaf-local decisions awaiting a spine home
(same convention as ``anchor_events_spec.py``): the spine delta in
``.streams/us380-context.md`` carries the exact classes so transcription is
mechanical.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from src.producers.field_maps_energy_benchmark import to_float

SOURCE_FRA_CROSSINGS = 'fra_crossings'
SOURCE_FRA_INCIDENTS = 'fra_incidents'
SOURCE_IMLS_LIBRARIES = 'imls_libraries'
SOURCE_NCES_POSTSEC = 'nces_postsec'
SOURCE_HRSA_SITES = 'hrsa_sites'

EDGE_POSTSEC_UNITID = 0
EDGE_POSTSEC_NAME = 1
EDGE_POSTSEC_STREET = 2
EDGE_POSTSEC_CITY = 3
EDGE_POSTSEC_STATE = 4
EDGE_POSTSEC_ZIP = 5
EDGE_POSTSEC_LAT = 10
EDGE_POSTSEC_LON = 11
EDGE_POSTSEC_YEAR = 20

CLINIC_OPENING_WINDOW_DAYS = 365


def _field(row, *names):
    """Read the first present variant of a column (verbatim or normalized)."""
    for name in names:
        if name in row and row[name] is not None and str(row[name]).strip():
            return str(row[name]).strip()
    return None
def _coords(lat=None, lng=None):
    """Parse a coordinate pair, dropping null island like the producer does."""
    lat_f = to_float(lat)
    lng_f = to_float(lng)
    if lat_f is None or lng_f is None:
        return (None, None)
    if lat_f == 0.0 and lng_f == 0.0:
        return (None, None)
    return (lat_f, lng_f)


def _geom_point_coords(the_geom=None):
    """Extract (lat, lng) from a Socrata GeoJSON point (coordinates are [lng, lat])."""
    if not isinstance(the_geom, dict):
        return (None, None)
    coords = the_geom.get('coordinates')
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return (None, None)
    lng_f = to_float(coords[0])
    lat_f = to_float(coords[1])
    return (lat_f, lng_f)


def _text(value=None):
    """Render a raw cell as trimmed text; blank and absent cells are None."""
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


class _SiteRef(BaseModel):
    """One sited context asset pending per-hex aggregation."""
    source: str = ''
    site_id: str = ''
    name: str | None = None
    address: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    h3_res7: str | None = None
    h3_res8: str | None = None
    h3_res9: str | None = None
    needs_geocode: bool = False
    city_id: str | None = None


class CrossingRef(_SiteRef):
    """One canonical FRA grade crossing (deduped to min(objectid))."""
    objectid: str = ''
    day_thru_trains: float = 0
    night_thru_trains: float = 0
    aadt: float | None = None
    aadt_year: str | None = None


class LibraryRef(_SiteRef):
    """One IMLS public-library outlet."""
    geostatus: str | None = None
    geomtype: str | None = None


class CampusRef(_SiteRef):
    """One NCES EDGE postsecondary institution (main campus by construction)."""
    school_year: str | None = None


class ClinicRef(_SiteRef):
    """One HRSA health-center service delivery site."""
    site_added_date: date | None = None


class HexContextReference(BaseModel):
    """Per-hex context covariates destined for ``EnrichedH3Feature``.

    Counts are per res-9 hex; at fixed cell area a count is the density
    input (denominators, when wanted, are applied downstream). Fields a
    source does not measure stay 0/None so four source folds merge additively.
    """
    city_id: str | None = Field(default=None)
    h3_res7: str = Field(...)
    h3_res8: str = Field(...)
    h3_res9: str = Field(..., description='Aggregation key')
    crossing_density: int = Field(default=0, description='Canonical grade crossings in hex')
    rail_thru_trains: float = Field(default=0, description="Sum of DAYTHRU+NGHTTHRU across the hex's crossings")
    aadt_mean: float | None = Field(default=None, description='Mean AADT over crossings that publish one — never zero-filled')
    incident_count: int = Field(default=0, description='Form 57 incidents attached via gradecrossingid')
    library_density: int = Field(default=0, description='IMLS library outlets in hex')
    campus_presence: int = Field(default=0, description='EDGE postsecondary institutions in hex')
    clinic_density: int = Field(default=0, description='HRSA service delivery sites in hex')
    clinic_openings_365d: int = Field(default=0, description="Sites whose 'Site Added to Scope' date is inside the window")


class ContextReferenceBuilder:
    """Parse the four context sources into site records and per-hex folds."""

    def __init__(
        self,
        indexer: Callable[[float, float], dict[str, str]] | None = None,
        city_for_point: Callable[[float, float], str | None] | None = None,
    ):
        self.indexer = indexer
        self.city_for_point = city_for_point

    def _tag(self, record: _SiteRef, lat: float | None = None, lng: float | None = None) -> None:
        """Tag a record with coordinates, H3 hierarchy, and city_id."""
        record.latitude = lat
        record.longitude = lng
        if lat is not None and lng is not None:
            if self.indexer is not None:
                h3 = self.indexer(lat, lng)
                record.h3_res7 = h3.get('h3_res7')
                record.h3_res8 = h3.get('h3_res8')
                record.h3_res9 = h3.get('h3_res9')
            if self.city_for_point is not None:
                record.city_id = self.city_for_point(lat, lng)
        else:
            record.needs_geocode = True

    def _sited(self, records: list[_SiteRef] | None) -> list[_SiteRef]:
        """Filter to records that have valid H3 tags."""
        if not records:
            return []
        return [r for r in records if r.h3_res9 is not None]

    def geocode_pending_rows(self, records: list[_SiteRef] | None) -> list[dict[str, Any]]:
        """Render the geocode-pending subset for the existing geocode pipeline."""
        pending = []
        for record in (records or []):
            if not record.needs_geocode:
                continue
            pending.append({
                'source': record.source,
                'site_id': record.site_id,
                'name': record.name,
                'address': record.address,
                'city': record.city,
                'state': record.state,
                'zipcode': record.zipcode,
                'latitude': record.latitude,
                'longitude': record.longitude,
            })
        return pending

    def load_fra_crossings(self, rows: list[dict[str, Any]] | None = None) -> list[CrossingRef]:
        """Dedup by the FRA crossing number keeping min(objectid), then tag.

        Socrata publishes native latitude/longitude plus a GeoJSON the_geom;
        the native pair is preferred, the_geom is the fallback.
        """
        canonical: dict[str, dict[str, Any]] = {}
        for row in (rows or []):
            crossing_id = _field(row, 'crossing', 'crossing_number')
            if not crossing_id:
                continue
            objectid = _field(row, 'objectid')
            if crossing_id in canonical:
                existing = canonical[crossing_id]
                existing_oid = _field(existing, 'objectid')
                if objectid and existing_oid and objectid < existing_oid:
                    canonical[crossing_id] = row
            else:
                canonical[crossing_id] = row

        records: list[CrossingRef] = []
        for crossing_id, row in canonical.items():
            lat = to_float(_field(row, 'latitude', 'latitude_x', 'lat'))
            lng = to_float(_field(row, 'longitude', 'longitude_y', 'lon'))
            if lat is None or lng is None:
                lat, lng = _geom_point_coords(row.get('the_geom'))

            record = CrossingRef(
                source=SOURCE_FRA_CROSSINGS,
                site_id=crossing_id,
                objectid=str(_field(row, 'objectid') or ''),
                day_thru_trains=to_float(_field(row, 'day_thru_trains', 'daythru')) or 0,
                night_thru_trains=to_float(_field(row, 'night_thru_trains', 'ngththru')) or 0,
                aadt=to_float(_field(row, 'aadt')),
                aadt_year=_field(row, 'aadt_year', 'aadtyear'),
                name=_text(_field(row, 'crossing_name', 'crossingname')),
                address=_text(_field(row, 'street', 'streetaddress')),
                city=_text(_field(row, 'city')),
                state=_text(_field(row, 'state', 'statecode')),
                zipcode=_text(_field(row, 'zip', 'zipcode')),
            )
            self._tag(record, lat, lng)
            records.append(record)
        return records

    def load_fra_incidents(self, rows: list[dict[str, Any]] | None = None) -> dict[str, int]:
        """Count Form 57 incidents per crossing (join key gradecrossingid)."""
        counts: dict[str, int] = {}
        for row in (rows or []):
            crossing = _field(row, 'gradecrossingid')
            if not crossing:
                continue
            counts[crossing] = counts.get(crossing, 0) + 1
        return counts

    
    def aggregate_crossings(
        self,
        records: list[CrossingRef] | None = None,
        incidents_by_crossing: dict[str, int] | None = None,
    ) -> tuple[dict[str, HexContextReference], dict[str, tuple[float, int]]]:
        """Fold crossings into per-hex density, through-train volume and AADT.

        Returns ``(folds, aadt_weights)``: per hex, the sum and count of the
        AADT values actually reported, so ``merge_hex_rows`` can recombine
        exact weighted means instead of averaging averages.
        """
        if incidents_by_crossing is None:
            incidents_by_crossing = {}
        folds: dict[str, HexContextReference] = {}
        aadt_weights: dict[str, tuple[float, int]] = {}

        for record in (records or []):
            if record.h3_res9 is None:
                continue
            key = record.h3_res9
            if key not in folds:
                folds[key] = HexContextReference(
                    city_id=record.city_id,
                    h3_res7=record.h3_res7 or '',
                    h3_res8=record.h3_res8 or '',
                    h3_res9=record.h3_res9,
                )
            elif record.city_id and not folds[key].city_id:
                folds[key].city_id = record.city_id

            folds[key].crossing_density += 1
            folds[key].rail_thru_trains += (record.day_thru_trains or 0) + (record.night_thru_trains or 0)
            folds[key].incident_count += incidents_by_crossing.get(record.site_id, 0)

            if record.aadt is not None:
                current_sum, current_count = aadt_weights.get(key, (0.0, 0))
                aadt_weights[key] = (current_sum + record.aadt, current_count + 1)

        return folds, aadt_weights

    def load_libraries(self, rows: list[dict[str, Any]] | None = None) -> list[LibraryRef]:
        """Tag IMLS outlets; address-only rows go geocode-pending, not guessed."""
        records: list[LibraryRef] = []
        for row in (rows or []):
            lib_id = _field(row, 'LIBID')
            if not lib_id:
                continue
            lat, lng = _coords(_field(row, 'LATITUDE'), _field(row, 'LONGITUD'))
            record = LibraryRef(
                source=SOURCE_IMLS_LIBRARIES,
                site_id=lib_id,
                name=_text(_field(row, 'LIBNAME')),
                address=_text(_field(row, 'ADDRESS')),
                city=_text(_field(row, 'CITY')),
                state=_text(_field(row, 'STABR')),
                zipcode=_text(_field(row, 'ZIP')),
                geostatus=_text(_field(row, 'GEOSTATUS')),
                geomtype=_text(_field(row, 'GEOMTYPE')),
            )
            self._tag(record, lat, lng)
            records.append(record)
        return records

    def aggregate_libraries(self, records: list[LibraryRef] | None = None) -> dict[str, HexContextReference]:
        """Fold library records into per-hex density."""
        folds: dict[str, HexContextReference] = {}
        for record in (records or []):
            if record.h3_res9 is None:
                continue
            key = record.h3_res9
            if key not in folds:
                folds[key] = HexContextReference(
                    city_id=record.city_id,
                    h3_res7=record.h3_res7 or '',
                    h3_res8=record.h3_res8 or '',
                    h3_res9=record.h3_res9,
                )
            elif record.city_id and not folds[key].city_id:
                folds[key].city_id = record.city_id
            folds[key].library_density += 1
        return folds

    
    def load_postsec(self, lines: list[str] | None = None) -> list[CampusRef]:
        """Parse the headerless pipe-delimited EDGE file positionally."""
        records: list[CampusRef] = []
        for line in (lines or []):
            line = line.strip()
            if not line:
                continue
            parts = line.split('|')
            if len(parts) <= EDGE_POSTSEC_YEAR:
                continue
            unitid = parts[EDGE_POSTSEC_UNITID].strip()
            if not unitid:
                continue
            lat, lng = _coords(parts[EDGE_POSTSEC_LAT], parts[EDGE_POSTSEC_LON])

            name = parts[EDGE_POSTSEC_NAME].strip() if len(parts) > EDGE_POSTSEC_NAME and parts[EDGE_POSTSEC_NAME].strip() else None
            address = parts[EDGE_POSTSEC_STREET].strip() if len(parts) > EDGE_POSTSEC_STREET and parts[EDGE_POSTSEC_STREET].strip() else None
            city = parts[EDGE_POSTSEC_CITY].strip() if len(parts) > EDGE_POSTSEC_CITY and parts[EDGE_POSTSEC_CITY].strip() else None
            state = parts[EDGE_POSTSEC_STATE].strip() if len(parts) > EDGE_POSTSEC_STATE and parts[EDGE_POSTSEC_STATE].strip() else None
            zipcode = parts[EDGE_POSTSEC_ZIP].strip() if len(parts) > EDGE_POSTSEC_ZIP and parts[EDGE_POSTSEC_ZIP].strip() else None
            school_year = parts[EDGE_POSTSEC_YEAR].strip() if len(parts) > EDGE_POSTSEC_YEAR and parts[EDGE_POSTSEC_YEAR].strip() else None

            record = CampusRef(
                source=SOURCE_NCES_POSTSEC,
                site_id=unitid,
                name=name,
                address=address,
                city=city,
                state=state,
                zipcode=zipcode,
                school_year=school_year,
            )
            self._tag(record, lat, lng)
            records.append(record)
        return records

    def aggregate_campuses(self, records: list[CampusRef] | None = None) -> dict[str, HexContextReference]:
        """Fold campus records into per-hex presence."""
        folds: dict[str, HexContextReference] = {}
        for record in (records or []):
            if record.h3_res9 is None:
                continue
            key = record.h3_res9
            if key not in folds:
                folds[key] = HexContextReference(
                    city_id=record.city_id,
                    h3_res7=record.h3_res7 or '',
                    h3_res8=record.h3_res8 or '',
                    h3_res9=record.h3_res9,
                )
            elif record.city_id and not folds[key].city_id:
                folds[key].city_id = record.city_id
            folds[key].campus_presence += 1
        return folds

    
    def load_hrsa(self, rows: list[dict[str, Any]] | None = None) -> list[ClinicRef]:
        """Tag HRSA sites; blank X/Y (the state-'XX' suppressed family) pend."""
        records: list[ClinicRef] = []
        for row in (rows or []):
            site_id = _field(row, 'BPHC Assigned Number', 'bphc_assigned_number')
            if not site_id:
                site_id = _field(row, 'Health Center Number', 'health_center_number')
            if not site_id:
                continue

            lat, lng = _coords(
                _field(row, 'Geocoding Artifact Address Primary Y Coordinate',
                       'geocoding_artifact_address_primary_y_coordinate'),
                _field(row, 'Geocoding Artifact Address Primary X Coordinate',
                       'geocoding_artifact_address_primary_x_coordinate'),
            )
            record = ClinicRef(
                source=SOURCE_HRSA_SITES,
                site_id=site_id,
                name=_text(_field(row, 'Site Name')),
                address=_text(_field(row, 'Site Address')),
                city=_text(_field(row, 'Site City')),
                state=_text(_field(row, 'Site State Abbreviation')),
                zipcode=_text(_field(row, 'Site Postal Code')),
                site_added_date=self._parse_site_added(
                    _field(row, 'Site Added to Scope this Date', 'site_added_to_scope_this_date')
                ),
            )
            self._tag(record, lat, lng)
            records.append(record)
        return records

    @staticmethod
    def _parse_site_added(value: str | None = None) -> date | None:
        """Parse HRSA 'Site Added to Scope' date (MM/DD/YYYY)."""
        if not value:
            return None
        try:
            return datetime.strptime(str(value).strip(), '%m/%d/%Y').replace(tzinfo=UTC).date()
        except ValueError:
            return None
    
    def aggregate_clinics(
        self,
        records: list[ClinicRef] | None = None,
        as_of: date | None = None,
    ) -> dict[str, HexContextReference]:
        """Fold clinic density plus the recent site-scope openings."""
        if as_of is None:
            as_of = date.today()
        folds: dict[str, HexContextReference] = {}
        for record in (records or []):
            if record.h3_res9 is None:
                continue
            key = record.h3_res9
            if key not in folds:
                folds[key] = HexContextReference(
                    city_id=record.city_id,
                    h3_res7=record.h3_res7 or '',
                    h3_res8=record.h3_res8 or '',
                    h3_res9=record.h3_res9,
                )
            elif record.city_id and not folds[key].city_id:
                folds[key].city_id = record.city_id

            folds[key].clinic_density += 1
            if (record.site_added_date is not None
                    and as_of - record.site_added_date <= timedelta(days=CLINIC_OPENING_WINDOW_DAYS)):
                folds[key].clinic_openings_365d += 1
        return folds

    def merge_hex_rows(
        self,
        *folds: dict[str, HexContextReference] | tuple[dict[str, HexContextReference], dict[str, tuple[float, int]]],
    ) -> dict[str, HexContextReference]:
        """Union per-source folds into one reference row per hex.

        Counts add; when a fold carries AADT weights (the crossing fold's
        second element) the means recombine exactly as
        ``sum(aadt) / count(reporting crossings)`` — never an average of
        averages; a hex no fold gave AADT for reports ``None``; a ``None``
        city_id never overwrites a resolved one.
        """
        merged: dict[str, HexContextReference] = {}
        aadt_sums: dict[str, tuple[float, int]] = {}

        for fold in folds:
            if isinstance(fold, tuple):
                fold_dict, aadt_weights = fold
            else:
                fold_dict = fold
                aadt_weights = None

            for key, ref in (fold_dict or {}).items():
                if key not in merged:
                    merged[key] = ref.model_copy(deep=True)
                else:
                    merged[key].crossing_density += ref.crossing_density
                    merged[key].rail_thru_trains += ref.rail_thru_trains
                    merged[key].incident_count += ref.incident_count
                    merged[key].library_density += ref.library_density
                    merged[key].campus_presence += ref.campus_presence
                    merged[key].clinic_density += ref.clinic_density
                    merged[key].clinic_openings_365d += ref.clinic_openings_365d
                    if merged[key].city_id is None and ref.city_id is not None:
                        merged[key].city_id = ref.city_id

            if aadt_weights:
                for key, (aadt_sum, aadt_count) in aadt_weights.items():
                    existing_sum, existing_count = aadt_sums.get(key, (0.0, 0))
                    aadt_sums[key] = (existing_sum + aadt_sum, existing_count + aadt_count)

        for key, (aadt_sum, aadt_count) in aadt_sums.items():
            if key in merged and aadt_count > 0:
                merged[key].aadt_mean = aadt_sum / aadt_count

        return merged

    def build_reference_table(
        self,
        crossings: list[CrossingRef] | None = None,
        libraries: list[LibraryRef] | None = None,
        campuses: list[CampusRef] | None = None,
        clinics: list[ClinicRef] | None = None,
        incidents_by_crossing: dict[str, int] | None = None,
        as_of: date | None = None,
    ) -> dict[str, HexContextReference]:
        """One call: fold all four sources into the merged per-hex table."""
        crossing_folds = self.aggregate_crossings(crossings, incidents_by_crossing)
        return self.merge_hex_rows(
            crossing_folds,
            self.aggregate_libraries(libraries),
            self.aggregate_campuses(campuses),
            self.aggregate_clinics(clinics, as_of=as_of),
        )


