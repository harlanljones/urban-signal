"""Uber H3 discrete global grid spatial indexer and multi-resolution hierarchy engine."""

from typing import Dict, List, Optional, Set, Tuple
import h3


class H3SpatialIndexer:
    """Manages multi-resolution Uber H3 grid operations for urban real estate forecasting."""

    # Approximate nominal cell areas in km² for Uber H3
    CELL_AREAS_KM2: Dict[int, float] = {
        7: 5.16129336,   # ~5.16 km² (Macro district)
        8: 0.73732760,   # ~0.74 km² (Neighborhood submarket)
        9: 0.10533251,   # ~0.10 km² (Micro block/parcel catalyst)
        10: 0.01504750,  # ~0.015 km² (Individual lot)
    }

    @staticmethod
    def latlng_to_h3(lat: float, lng: float, resolution: int = 9) -> str:
        """Convert WGS84 coordinate pair to an H3 cell index string."""
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
            raise ValueError(f"Invalid coordinates: lat={lat}, lng={lng}")
        return h3.latlng_to_cell(lat, lng, resolution)

    @classmethod
    def get_multi_res_hierarchy(cls, lat: float, lng: float) -> Dict[str, str]:
        """Compute Res 7, Res 8, and Res 9 H3 indexes for a given coordinate."""
        res9 = cls.latlng_to_h3(lat, lng, resolution=9)
        res8 = h3.cell_to_parent(res9, 8)
        res7 = h3.cell_to_parent(res9, 7)
        return {
            "h3_res7": res7,
            "h3_res8": res8,
            "h3_res9": res9,
        }

    @staticmethod
    def h3_to_latlng(h3_index: str) -> Tuple[float, float]:
        """Return the centroid (latitude, longitude) of an H3 cell."""
        return h3.cell_to_latlng(h3_index)

    @staticmethod
    def h3_to_boundary(h3_index: str, geojson_format: bool = False) -> List[Tuple[float, float]]:
        """Return the polygon boundary vertices of an H3 cell.
        
        If geojson_format is True, coordinates are [lng, lat].
        Otherwise [lat, lng].
        """
        boundary = h3.cell_to_boundary(h3_index)
        if geojson_format:
            return [[lng, lat] for lat, lng in boundary]
        return list(boundary)

    @staticmethod
    def get_k_ring(h3_index: str, k: int = 1) -> Set[str]:
        """Return all neighbor cells within distance k of the origin cell (including origin)."""
        return set(h3.grid_disk(h3_index, k))

    @staticmethod
    def get_k_ring_neighbors_only(h3_index: str, k: int = 1) -> Set[str]:
        """Return only the hollow ring of neighbor cells at exact distance k."""
        return set(h3.grid_ring(h3_index, k))

    @classmethod
    def get_cell_area_km2(cls, resolution: int) -> float:
        """Get the nominal area in km² for a given H3 resolution."""
        return cls.CELL_AREAS_KM2.get(resolution, h3.cell_area(cls.latlng_to_h3(40.7128, -74.0060, resolution), unit='km^2'))

    @staticmethod
    def get_parent(h3_index: str, parent_res: int) -> str:
        """Get parent cell at a coarser resolution."""
        return h3.cell_to_parent(h3_index, parent_res)

    @staticmethod
    def get_children(h3_index: str, child_res: int) -> List[str]:
        """Get child cells at a finer resolution."""
        return list(h3.cell_to_children(h3_index, child_res))

    @classmethod
    def dynamic_spatial_fallback(
        cls,
        h3_res9_index: str,
        sample_count: int,
        min_density_threshold: int = 5,
    ) -> Tuple[str, int]:
        """Dynamic spatial fallback for low-density outer rings / suburban tracts.
        
        If Res 9 event density < min_density_threshold, falls back to Res 8 parent.
        If Res 8 density is also sparse, falls back to Res 7 macro parent.
        Returns: (effective_h3_index, effective_resolution)
        """
        if sample_count >= min_density_threshold:
            return h3_res9_index, 9

        parent_8 = cls.get_parent(h3_res9_index, 8)
        if sample_count >= 1:
            return parent_8, 8

        parent_7 = cls.get_parent(h3_res9_index, 7)
        return parent_7, 7
