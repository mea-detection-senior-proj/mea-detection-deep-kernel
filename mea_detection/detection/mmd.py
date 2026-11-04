"""Fixed-kernel MMD; callers supply embeddings and reference draws."""
from dataclasses import dataclass
import math

import torch


from .kernels.fixed import rbf_kernel, mean_reference_mmd


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
