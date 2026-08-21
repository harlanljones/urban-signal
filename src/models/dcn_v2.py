"""18-Month Macro Horizon: Multi-Scale Deep & Cross Network (DCN-v2) Ensemble.

Estimates the probability of >15% structural commercial/residential appreciation outperformance over macro horizons.
"""

from typing import List
import torch
import torch.nn as nn
import torch.nn.functional as F


class CrossNetworkV2(nn.Module):
    """DCN-v2 Cross Network layer with matrix multiplications for bounded feature crossing.
    
    Formula: x_{l+1} = x_0 * (W_l * x_l + b_l) + x_l
    """

    def __init__(self, in_features: int, num_layers: int = 3):
        super().__init__()
        self.num_layers = num_layers
        self.weights = nn.ParameterList([
            nn.Parameter(torch.randn(in_features, in_features) * 0.01)
            for _ in range(num_layers)
        ])
        self.biases = nn.ParameterList([
            nn.Parameter(torch.zeros(in_features))
            for _ in range(num_layers)
        ])

    def forward(self, x0: torch.Tensor) -> torch.Tensor:
        xl = x0
        for w, b in zip(self.weights, self.biases):
            # Matrix multiplication followed by elementwise multiplication with x0
            xl_w = F.linear(xl, w, b)
            xl = x0 * xl_w + xl
        return xl


class MultiScaleDCNv2(nn.Module):
    """Multi-Scale Deep & Cross Network ensemble for macro 18-month outperformance classification."""

    def __init__(
        self,
        in_features: int = 12,
        cross_layers: int = 3,
        deep_hidden_dims: List[int] = None,
        dropout: float = 0.15,
    ):
        super().__init__()
        deep_dims = deep_hidden_dims or [64, 32]

        self.cross_net = CrossNetworkV2(in_features, num_layers=cross_layers)

        # Deep component
        deep_layers: List[nn.Module] = []
        prev_dim = in_features
        for dim in deep_dims:
            deep_layers.extend([
                nn.Linear(prev_dim, dim),
                nn.BatchNorm1d(dim),
                nn.SiLU(),
                nn.Dropout(dropout),
            ])
            prev_dim = dim
        self.deep_net = nn.Sequential(*deep_layers)

        # Final combination head
        combined_dim = in_features + deep_dims[-1]
        self.head = nn.Sequential(
            nn.Linear(combined_dim, 16),
            nn.SiLU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),  # Probability of >15% outperformance
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Args:
            x: Input feature tensor [batch_size, in_features]
        Returns:
            prob: [batch_size, 1] macro outperformance probability
        """
        x_cross = self.cross_net(x)
        x_deep = self.deep_net(x)

        combined = torch.cat([x_cross, x_deep], dim=-1)
        prob = self.head(combined)
        return prob
