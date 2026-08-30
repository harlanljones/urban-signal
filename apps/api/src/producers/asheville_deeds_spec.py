"""DatasetSpec-shaped plain dicts for the Buncombe County (NC) property roll
as Asheville DEEDS supplement (US-399).

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold; the per-city placement is documented in
``.streams/us399-asheville-deeds.md`` ("Spine delta").

Source: Buncombe County GIS Property layer (``FeatureServer/1``), 135,239
polygon parcels, ``geometryType: esriGeometryPolygon``, ``objectIdField:
"objectid"``, ``maxRecordCount: 2000``.  WGS84 geometry via ``outSR=4326``.

LABEL: Roll-grade (last sale per parcel), snapshot cadence, not an event
stream.  ``SalePrice`` is zeroed on every row; price is reconstructed client-
side as ``Stamps × 500`` (NC excise stamps, $1.00 per $500 or fraction).
``Instrument`` / ``Reason`` filter for non-arm's-length transactions is
documented in the field map module.

Native polygon → H3 direct via the ArcGIS client's centroid extraction.
"""

from src.config import settings
from src.producers.field_maps_asheville_deeds import ASHEVILLE_DEEDS_FIELD_MAP

ASHEVILLE_DEEDS_ENDPOINT = (
    "https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/1"
)

ASHEVILLE_DEEDS_SPEC: dict = {
    "endpoint": ASHEVILLE_DEEDS_ENDPOINT,
    "platform": "arcgis",
    "watermark_col": "DeedDate",
    "watermark_type": "text",
    "watermark_format": "%Y%m%d",
    "id_keys": ["PIN", "objectid"],
    "topic": settings.topic_deeds,
    "interval_seconds": 86400.0,
    "producer_key": "deeds",
    "expected_cadence_days": 7,
    "ingestion_mode": "snapshot",
    "oid_field": "objectid",
    "max_record_count": 2000,
    "needs_geocode": False,
    "field_map": ASHEVILLE_DEEDS_FIELD_MAP,
}