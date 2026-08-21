"""Graph builder for Uber H3 hexagonal spatial adjacency lattices."""

from typing import Dict, List, Optional, Set, Tuple
import numpy as np
import torch
import h3
from src.spatial.h3_indexer import H3SpatialIndexer


class H3HexGraphBuilder:
    """Constructs spatial graph topologies over H3 discrete global grids for GNN message passing."""

    def __init__(self, resolution: int = 8):
        self.resolution = resolution
        self.indexer = H3SpatialIndexer()

    def build_graph_from_cells(
        self,
        h3_cells: List[str],
        include_2nd_ring: bool = False,
        self_loops: bool = True,
    ) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, int]]:
        """Build node-to-index mapping and PyTorch Geometric edge_index / edge_weights.
        
        Returns:
            edge_index: torch.LongTensor of shape [2, num_edges]
            edge_weight: torch.FloatTensor of shape [num_edges]
            cell_to_idx: dict mapping h3_index string -> integer node index
        """
        cell_set: Set[str] = set(h3_cells)
        cell_list = sorted(list(cell_set))
        cell_to_idx = {cell: i for i, cell in enumerate(cell_list)}

        edges_src: List[int] = []
        edges_dst: List[int] = []
        edge_weights: List[float] = []

        for cell in cell_list:
            u = cell_to_idx[cell]

            if self_loops:
                edges_src.append(u)
                edges_dst.append(u)
                edge_weights.append(1.0)

            # 1st-ring adjacent neighbors (distance = 1 hex)
            ring_1 = self.indexer.get_k_ring_neighbors_only(cell, k=1)
            for neighbor in ring_1:
                if neighbor in cell_to_idx:
                    v = cell_to_idx[neighbor]
                    edges_src.append(u)
                    edges_dst.append(v)
                    edge_weights.append(1.0)  # Primary spatial adjacency

            # 2nd-ring neighbors (distance = 2 hexes, decayed weight)
            if include_2nd_ring:
                ring_2 = self.indexer.get_k_ring_neighbors_only(cell, k=2)
                for neighbor in ring_2:
                    if neighbor in cell_to_idx:
                        v = cell_to_idx[neighbor]
                        edges_src.append(u)
                        edges_dst.append(v)
                        edge_weights.append(0.5)  # Secondary decayed adjacency

        edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
        edge_weight = torch.tensor(edge_weights, dtype=torch.float32)

        return edge_index, edge_weight, cell_to_idx

    def compute_normalized_laplacian(
        self,
        edge_index: torch.Tensor,
        num_nodes: int,
    ) -> torch.Tensor:
        """Compute the symmetrically normalized graph adjacency matrix: D^{-1/2} A D^{-1/2}."""
        # Convert edge_index to dense adjacency
        adj = torch.zeros((num_nodes, num_nodes), dtype=torch.float32)
        adj[edge_index[0], edge_index[1]] = 1.0

        # Degree matrix
        deg = torch.sum(adj, dim=1)
        deg_inv_sqrt = torch.pow(deg, -0.5)
        deg_inv_sqrt[torch.isinf(deg_inv_sqrt)] = 0.0

        d_mat = torch.diag(deg_inv_sqrt)
        norm_adj = torch.mm(torch.mm(d_mat, adj), d_mat)
        return norm_adj

    def generate_nyc_submarket_graph(
        self,
        center_lat: float = 40.7128,
        center_lng: float = -74.0060,
        radius_k: int = 15,
    ) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, int]]:
        """Generate a complete hexagonal graph patch around a metropolitan anchor."""
        origin_cell = self.indexer.latlng_to_h3(center_lat, center_lng, self.resolution)
        cells = list(self.indexer.get_k_ring(origin_cell, k=radius_k))
        return self.build_graph_from_cells(cells, include_2nd_ring=True)
