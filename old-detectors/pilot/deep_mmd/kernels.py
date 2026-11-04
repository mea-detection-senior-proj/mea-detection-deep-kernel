"""Differentiable fixed/deep kernels and unbiased MMD statistics."""
import torch


def squared_distances(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    x_norm = torch.sum(x * x, dim=1, keepdim=True)
    y_norm = torch.sum(y * y, dim=1, keepdim=True).T
    d2 = x_norm + y_norm - 2.0 * (x @ y.T)
    return torch.clamp(d2, min=0.0)


def median_bandwidth(z: torch.Tensor, sample_size: int, rng: object) -> float:
    n = len(z)
    if n < 2:
        raise ValueError("Need at least two benign embeddings to estimate bandwidth")
    idx = rng.choice(n, size=min(sample_size, n), replace=False)
    idx_t = torch.as_tensor(idx, dtype=torch.long, device=z.device)
    d2 = squared_distances(z[idx_t], z[idx_t])
    tri = torch.triu_indices(len(idx), len(idx), offset=1, device=z.device)
    upper = d2[tri[0], tri[1]]
    positive = upper[upper > 0]
    if positive.numel() == 0:
        return 1.0
    return float(torch.sqrt(torch.median(positive)).detach().cpu().item())


def rbf_kernel_from_d2(d2: torch.Tensor, sigmas: list[float]) -> torch.Tensor:
    kernels = []
    for sigma in sigmas:
        sigma = max(float(sigma), 1e-12)
        kernels.append(torch.exp(-d2 / (2.0 * sigma * sigma)))
    return torch.stack(kernels, dim=0).mean(dim=0)


def mmd(x, y, sigmas, network=None):
    def kernel(a, b):
        base = rbf_kernel_from_d2(squared_distances(a, b), sigmas)
        if network is None:
            return base
        a, b = network(a), network(b)
        learned = torch.exp(-squared_distances(a, b) / 2)
        return base * (0.1 + 0.9 * learned)
    xx, yy, xy = kernel(x, x), kernel(y, y), kernel(x, y)
    return ((xx.sum() - xx.diag().sum()) / (len(x) * (len(x)-1))
            + (yy.sum() - yy.diag().sum()) / (len(y) * (len(y)-1)) - 2 * xy.mean())


