"""12-Month Horizon: Spatio-Temporal Graph Neural Network (ST-GNN) in PyTorch.

Models spatial price diffusion across adjacent H3 hexagonal nodes with GCN message passing and GRU temporal recurrence.
"""

from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class HexGCNLayer(nn.Module):
    """Hexagonal Graph Convolutional layer with normalized adjacency message passing."""

    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features, bias=False)
        self.bias = nn.Parameter(torch.zeros(out_features))

    def forward(self, x: torch.Tensor, norm_adj: torch.Tensor) -> torch.Tensor:
        """Args:
            x: Node features [num_nodes, in_features]
            norm_adj: Normalized adjacency matrix [num_nodes, num_nodes]
        """
        # Message passing: A_hat * X * W + b
        ax = torch.mm(norm_adj, x)
        out = self.linear(ax) + self.bias
        return F.silu(out)


class SpatioTemporalGNN(nn.Module):
    """Spatio-Temporal Graph Neural Network combining HexGCN spatial layers with GRU temporal recurrence.
    
    Input shape: [batch_seq_len, num_nodes, in_features]
    Output shape: [num_nodes, 1] (12-month delta appreciation)
    """

    def __init__(
        self,
        in_features: int = 12,
        hidden_dim: int = 64,
        spatial_layers: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.in_features = in_features
        self.hidden_dim = hidden_dim

        # Spatial convolution layers
        self.gcn1 = HexGCNLayer(in_features, hidden_dim)
        self.gcn2 = HexGCNLayer(hidden_dim, hidden_dim)

        # Temporal GRU recurrence
        self.gru = nn.GRUCell(hidden_dim, hidden_dim)

        # Prediction head
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
        )

    def forward(
        self,
        x_seq: torch.Tensor,
        norm_adj: torch.Tensor,
        h_prev: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass over sequence of time steps.
        
        Args:
            x_seq: [seq_len, num_nodes, in_features]
            norm_adj: [num_nodes, num_nodes]
            h_prev: [num_nodes, hidden_dim] (optional initial hidden state)
            
        Returns:
            pred: [num_nodes, 1] predicted 12-month appreciation delta
            h_final: [num_nodes, hidden_dim] final recurrent state
        """
        num_nodes = x_seq.shape[1]

        if h_prev is None:
            h_prev = torch.zeros((num_nodes, self.hidden_dim), device=x_seq.device, dtype=x_seq.dtype)

        h_t = h_prev
        for x_t in torch.unbind(x_seq, dim=0):
            # Spatial message passing across hexagonal lattice
            s1 = self.gcn1(x_t, norm_adj)
            s2 = self.gcn2(s1, norm_adj)

            # Temporal update
            h_t = self.gru(s2, h_t)

        pred = self.head(h_t)
        return pred, h_t
