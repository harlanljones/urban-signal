"""Spatial-Temporal Leakage Prevention: Rolling Walk-Forward Split with H3-7 Spatial Block Holdouts."""

from datetime import datetime
from typing import Generator, List, Set, Tuple
import numpy as np
import pandas as pd
from src.spatial.h3_indexer import H3SpatialIndexer


class SpatialTemporalHoldoutValidator:
    """Generates cross-validation folds strictly preventing spatial and temporal leakage.
    
    Guarantees:
        1. Temporal: Train set strictly precedes Test set in time (Walk-Forward).
        2. Spatial: Test set H3 cells belong to H3-7 parent hexagons completely excluded from Train.
    """

    def __init__(self, n_spatial_clusters: int = 5, min_train_months: int = 12):
        self.n_spatial_clusters = n_spatial_clusters
        self.min_train_months = min_train_months
        self.indexer = H3SpatialIndexer()

    def get_h3_7_parent(self, h3_cell: str) -> str:
        """Resolve parent H3-7 hexagon."""
        return self.indexer.get_parent(h3_cell, 7)

    def split(
        self,
        df: pd.DataFrame,
        time_col: str = "as_of_date",
        cell_col: str = "h3_index",
        test_window_months: int = 6,
    ) -> Generator[Tuple[np.ndarray, np.ndarray, Set[str]], None, None]:
        """Yields (train_indices, test_indices, held_out_h3_7_clusters) for each fold."""
        df_sorted = df.sort_values(time_col)
        dates = pd.to_datetime(df_sorted[time_col])

        # Attach parent H3-7 cluster
        parents = df_sorted[cell_col].apply(self.get_h3_7_parent)
        unique_parents = sorted(parents.unique())

        min_date = dates.min()
        max_date = dates.max()

        current_cutoff = min_date + pd.DateOffset(months=self.min_train_months)

        # Deterministic spatial fold assignments across unique H3-7 parent clusters
        parent_folds = {p: i % self.n_spatial_clusters for i, p in enumerate(unique_parents)}

        fold_idx = 0
        while current_cutoff + pd.DateOffset(months=test_window_months) <= max_date:
            test_cutoff = current_cutoff + pd.DateOffset(months=test_window_months)

            # Hold out one spatial cluster of H3-7 parents for this temporal fold
            held_out_cluster_id = fold_idx % self.n_spatial_clusters
            held_out_parents = {p for p, c in parent_folds.items() if c == held_out_cluster_id}

            train_mask = (dates < current_cutoff) & (~parents.isin(held_out_parents))
            test_mask = (dates >= current_cutoff) & (dates < test_cutoff) & (parents.isin(held_out_parents))

            train_idx = df_sorted.index[train_mask].to_numpy()
            test_idx = df_sorted.index[test_mask].to_numpy()

            if len(train_idx) > 0 and len(test_idx) > 0:
                yield train_idx, test_idx, held_out_parents

            current_cutoff = test_cutoff
            fold_idx += 1
