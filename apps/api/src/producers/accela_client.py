"""Shared client for public Accela REST/ArcGIS surfaces.

Accela deployments commonly expose their public records through an ArcGIS
FeatureServer facade. Reusing the hardened ArcGIS pagination and geometry
handling keeps city-specific integrations small while allowing a DatasetSpec
to identify the upstream as ``accela``.
"""

from src.producers.arcgis_client import ArcGISClient


class AccelaClient(ArcGISClient):
    """Accela-compatible paginating client with ArcGIS REST semantics."""
