"""Per-city field-mapping support for the shared municipal row parsers.

Every city's feed spells its columns differently — Seattle's ArcGIS layer says
`PIN`/`SaleDate`, LA spells longitude `lon`, NOLA says `issuedate`. Historically
each new spelling grew another `or row.get(...)` term in the shared parsers;
with a fourth city needing non-trivial spellings that chain-of-fallbacks
approached unmaintainable (see docs/research/
new-orleans-austin-verification.md, "Refactor trigger assessment").

Instead, a city declares its spellings as data alongside its feed spec:

    DatasetSpec(
        ...,
        field_map={
            "job_id": ["numstring"],
            "latitude": ["location_1.latitude"],   # dotted = nested container
        },
    )

Parsers consult the map for the resolved city BEFORE their generic fallback
chains, so maps are purely additive overrides and chains remain the defaults
for cities that declare nothing. Value semantics match the chains exactly:
falsy values (empty strings, None) fall through to the next candidate.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.spatial.city_registry import FeedType


def first_mapped(
    row: dict[str, Any],
    field_map: dict[str, list[str]],
    *canonical: str,
) -> Any:
    """Return ``row[first candidate key present]`` for the first canonical
    field with candidates, or None. Dotted keys index one nested container."""
    for name in canonical:
        for key in field_map.get(name, []):
            if "." in key:
                head, _, tail = key.partition(".")
                container = row.get(head)
                if isinstance(container, dict) and container.get(tail):
                    return container[tail]
            elif row.get(key):
                return row[key]
    return None


def resolve_field_map(city_value: str, feed: "FeedType") -> dict[str, list[str]]:
    """Look up one city's field map for one feed, degrading to empty.

    Unknown city identifiers and registered cities lacking the feed (LA has no
    DEEDS dataset, for instance) both yield ``{}``, so autodetected rows parse
    through bare chains exactly as before the mapping table existed.
    """
    from src.spatial.city_registry import get_dataset, normalize_city

    norm = normalize_city(city_value)
    if norm is None:
        return {}
    try:
        spec = get_dataset(norm, feed)
    except KeyError:
        return {}
    field_map = spec.field_map
    return field_map if isinstance(field_map, dict) else {}
