"""Liu et al. (ICML 2020), Eq. 1, on frozen sentence embeddings."""
import math

import torch
from torch import nn

from .fixed import mean_reference_mmd, squared_distances


class DeepKernelMMD(nn.Module):
    def __init__(self, input_dim, base_bandwidth, hidden_dim=128, feature_dim=64):
        super().__init__()
        if base_bandwidth <= 0:
            raise ValueError("Base bandwidth must be positive")
        self.network = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, feature_dim))
        self.log_base_bandwidth = nn.Parameter(torch.tensor(math.log(base_bandwidth)))
        self.log_feature_bandwidth = nn.Parameter(torch.tensor(0.))
        self.epsilon_logit = nn.Parameter(torch.tensor(math.log(.1 / .9)))

    def kernel(self, x, y):
        base = torch.exp(-squared_distances(x, y) / (2 * self.log_base_bandwidth.exp().square()))
        features = torch.exp(-squared_distances(self.network(x), self.network(y))
                             / (2 * self.log_feature_bandwidth.exp().square()))
        epsilon = self.epsilon_logit.sigmoid()
        return ((1 - epsilon) * features + epsilon) * base

    @torch.no_grad()
    def score(self, reference_pool, window, reference_indices):
        if self.training:
            raise ValueError("Freeze/evaluate the kernel before scoring held-out data")
        return mean_reference_mmd(reference_pool, window, reference_indices, self.kernel)

    def parameters_metadata(self):
        return {"base_bandwidth": float(self.log_base_bandwidth.detach().exp()),
                "feature_bandwidth": float(self.log_feature_bandwidth.detach().exp()),
                "epsilon": float(self.epsilon_logit.detach().sigmoid())}
