"""Feature network; preserve layer indices for historical checkpoints."""
from torch import nn


def build_feature_network(input_dim, hidden_dim=128, output_dim=32):
    return nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(),
                         nn.Linear(hidden_dim, output_dim))
