"""Fixed-kernel MMD; callers supply embeddings and reference draws."""
from dataclasses import dataclass
import math

import torch


def squared_distances(x, y):
    return (x.square().sum(-1, keepdim=True) + y.square().sum(-1).unsqueeze(-2)
            - 2 * x @ y.transpose(-1, -2)).clamp_min(0)


def median_bandwidth(reference, sample_size, rng):
    if len(reference) < 2 or sample_size < 2:
        raise ValueError("Bandwidth estimation needs at least two samples")
    indices = torch.as_tensor(rng.choice(len(reference), min(len(reference), sample_size), replace=False),
                              device=reference.device)
    distances = squared_distances(reference[indices], reference[indices])
    pairs = torch.triu_indices(len(indices), len(indices), 1, device=reference.device)
    positive = distances[pairs[0], pairs[1]]
    positive = positive[positive > 0]
    return float(positive.median().sqrt()) if len(positive) else 1.0


def rbf_kernel(x, y, bandwidths):
    d2 = squared_distances(x, y)
    return torch.stack([torch.exp(-d2 / (2 * sigma**2)) for sigma in bandwidths]).mean(0)


def mmd2_unbiased(x, y, bandwidths):
    if len(x) < 2 or len(y) < 2:
        raise ValueError("Unbiased MMD requires at least two samples per set")
    xx, yy, xy = rbf_kernel(x, x, bandwidths), rbf_kernel(y, y, bandwidths), rbf_kernel(x, y, bandwidths)
    return ((xx.sum() - xx.diagonal().sum()) / (len(x) * (len(x) - 1))
            + (yy.sum() - yy.diagonal().sum()) / (len(y) * (len(y) - 1)) - 2 * xy.mean())


def mean_reference_mmd(reference_pool, window, reference_indices, kernel):
    """Batch reference draws without changing the mean-of-MMD statistic."""
    if reference_indices.ndim != 2 or len(reference_indices) < 1:
        raise ValueError("Expected one or more reference-index rows")
    reference = reference_pool[reference_indices]
    m, n = reference.shape[-2], len(window)
    if min(m, n) < 2:
        raise ValueError("Unbiased MMD requires at least two samples per set")
    xx, yy, xy = kernel(reference, reference), kernel(window, window), kernel(reference, window)
    values = ((xx.sum((-2, -1)) - xx.diagonal(dim1=-2, dim2=-1).sum(-1)) / (m * (m - 1))
              + (yy.sum() - yy.diagonal().sum()) / (n * (n - 1)) - 2 * xy.mean((-2, -1)))
    score = float(values.mean())
    if not math.isfinite(score):
        raise ValueError("Non-finite MMD score")
    return score


@dataclass(frozen=True)
class MMDDetector:
    bandwidths: tuple[float, ...]

    def __post_init__(self):
        if not self.bandwidths or any(not math.isfinite(s) or s <= 0 for s in self.bandwidths):
            raise ValueError("Bandwidths must be finite and positive")

    @torch.no_grad()
    def score(self, reference_pool, window, reference_indices):
        """Average the same statistic across explicit reference draws in every phase."""
        return mean_reference_mmd(reference_pool, window, reference_indices,
                                  lambda x, y: rbf_kernel(x, y, self.bandwidths))
