"""Unit tests for Uber H3 spatial indexing and graph builder."""

import pytest
import torch
from src.spatial.geo_utils import is_in_nyc_metro, point_to_wkt
from src.spatial.graph_builder import H3HexGraphBuilder
from src.spatial.h3_indexer import H3SpatialIndexer


def test_h3_multi_res_hierarchy(sample_nyc_coords):
    indexer = H3SpatialIndexer()
    soho = sample_nyc_coords["soho"]

    hierarchy = indexer.get_multi_res_hierarchy(soho["lat"], soho["lng"])
    assert "h3_res7" in hierarchy
    assert "h3_res8" in hierarchy
    assert "h3_res9" in hierarchy

    # Verify parent relationship
    res9 = hierarchy["h3_res9"]
    res8 = hierarchy["h3_res8"]
    res7 = hierarchy["h3_res7"]

    assert indexer.get_parent(res9, 8) == res8
    assert indexer.get_parent(res8, 7) == res7


def test_h3_centroid_and_boundary(sample_nyc_coords):
    indexer = H3SpatialIndexer()
    williamsburg = sample_nyc_coords["williamsburg"]

    cell = indexer.latlng_to_h3(williamsburg["lat"], williamsburg["lng"], resolution=9)
    lat, lng = indexer.h3_to_latlng(cell)

    assert abs(lat - williamsburg["lat"]) < 0.01
    assert abs(lng - williamsburg["lng"]) < 0.01

    boundary = indexer.h3_to_boundary(cell, geojson_format=True)
    assert len(boundary) >= 6  # Hexagon has 6 vertices


def test_k_ring_neighbors(sample_nyc_coords):
    indexer = H3SpatialIndexer()
    lic = sample_nyc_coords["lic"]
    cell = indexer.latlng_to_h3(lic["lat"], lic["lng"], resolution=8)

    ring1 = indexer.get_k_ring_neighbors_only(cell, k=1)
    assert len(ring1) == 6  # Standard planar hexagonal neighborhood has 6 neighbors

    disk1 = indexer.get_k_ring(cell, k=1)
    assert len(disk1) == 7  # Center + 6 neighbors


def test_dynamic_spatial_fallback():
    indexer = H3SpatialIndexer()
    cell_res9 = indexer.latlng_to_h3(40.7128, -74.0060, resolution=9)

    # High density -> keeps Res 9
    eff_cell, res = indexer.dynamic_spatial_fallback(cell_res9, sample_count=10, min_density_threshold=5)
    assert res == 9
    assert eff_cell == cell_res9

    # Low density -> falls back to Res 8
    eff_cell, res = indexer.dynamic_spatial_fallback(cell_res9, sample_count=2, min_density_threshold=5)
    assert res == 8
    assert eff_cell == indexer.get_parent(cell_res9, 8)

    # Zero density -> falls back to Res 7
    eff_cell, res = indexer.dynamic_spatial_fallback(cell_res9, sample_count=0, min_density_threshold=5)
    assert res == 7
    assert eff_cell == indexer.get_parent(cell_res9, 7)


def test_hex_graph_builder(sample_nyc_coords):
    indexer = H3SpatialIndexer()
    builder = H3HexGraphBuilder(resolution=8)
    soho_cell = indexer.latlng_to_h3(sample_nyc_coords["soho"]["lat"], sample_nyc_coords["soho"]["lng"], resolution=8)

    cells = list(indexer.get_k_ring(soho_cell, k=2))
    edge_index, edge_weight, cell_to_idx = builder.build_graph_from_cells(cells, include_2nd_ring=True)

    assert edge_index.shape[0] == 2
    assert edge_index.shape[1] > len(cells)  # Edges connecting neighbors
    assert len(cell_to_idx) == len(cells)

    # Normalized Laplacian test
    laplacian = builder.compute_normalized_laplacian(edge_index, num_nodes=len(cells))
    assert laplacian.shape == (len(cells), len(cells))
    assert torch.all(torch.isfinite(laplacian))


def test_geo_utils(sample_nyc_coords):
    soho = sample_nyc_coords["soho"]
    assert is_in_nyc_metro(soho["lat"], soho["lng"])
    assert not is_in_nyc_metro(34.0522, -118.2437)  # Los Angeles should be False

    wkt = point_to_wkt(soho["lat"], soho["lng"])
    assert wkt.startswith("POINT(-74.003000 40.723300)")
