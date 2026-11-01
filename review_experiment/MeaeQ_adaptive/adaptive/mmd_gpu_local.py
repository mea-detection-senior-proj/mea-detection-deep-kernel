from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import torch


def read_jsonl_queries(path: Path, text_field: str = "query", limit: int | None = None) -> list[str]:
    queries: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} is not valid JSON") from exc
            text = row.get(text_field)
            if not isinstance(text, str) or not text.strip():
                continue
            queries.append(text.strip())
            if limit is not None and len(queries) >= limit:
                break
    if not queries:
        raise ValueError(f"No usable '{text_field}' strings found in {path}")
    return queries


def cache_key(texts: list[str], model_name: str, prefix: str, normalize: bool) -> str:
    h = hashlib.sha256()
    h.update(model_name.encode("utf-8"))
    h.update(b"\0")
    h.update(prefix.encode("utf-8"))
    h.update(b"\0")
    h.update(str(normalize).encode("ascii"))
    h.update(b"\0")
    for text in texts:
        h.update(text.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:24]


def embed_texts(
    texts: list[str],
    model_name: str,
    batch_size: int,
    device: str | None,
    prefix: str = "",
    normalize: bool = True,
    cache_dir: Path | None = None,
) -> np.ndarray:
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{cache_key(texts, model_name, prefix, normalize)}.npy"
        if cache_path.exists():
            return np.load(cache_path)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit("Missing dependency: sentence-transformers") from exc

    kwargs = {}
    if device:
        kwargs["device"] = device
    model = SentenceTransformer(model_name, **kwargs)
    encoded = model.encode(
        [prefix + text for text in texts],
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )
    embeddings = np.asarray(encoded, dtype=np.float32)
    if cache_dir is not None:
        np.save(cache_path, embeddings)
    return embeddings


def as_torch(x: np.ndarray, device: str, dtype: str = "float32") -> torch.Tensor:
    torch_dtype = torch.float64 if dtype == "float64" else torch.float32
    return torch.as_tensor(x, dtype=torch_dtype, device=torch.device(device))


def squared_distances(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    x_norm = torch.sum(x * x, dim=1, keepdim=True)
    y_norm = torch.sum(y * y, dim=1, keepdim=True).T
    d2 = x_norm + y_norm - 2.0 * (x @ y.T)
    return torch.clamp(d2, min=0.0)


def median_bandwidth(z: torch.Tensor, sample_size: int, rng: np.random.Generator) -> float:
    n = len(z)
    if n < 2:
        raise ValueError("Need at least two embeddings to estimate bandwidth")
    idx = rng.choice(n, size=min(sample_size, n), replace=False)
    idx_t = torch.as_tensor(idx, dtype=torch.long, device=z.device)
    d2 = squared_distances(z[idx_t], z[idx_t])
    tri = torch.triu_indices(len(idx), len(idx), offset=1, device=z.device)
    positive = d2[tri[0], tri[1]][d2[tri[0], tri[1]] > 0]
    if positive.numel() == 0:
        return 1.0
    return float(torch.sqrt(torch.median(positive)).detach().cpu().item())


def rbf_kernel_from_d2(d2: torch.Tensor, sigmas: Iterable[float]) -> torch.Tensor:
    kernels = []
    for sigma in sigmas:
        sigma = max(float(sigma), 1e-12)
        kernels.append(torch.exp(-d2 / (2.0 * sigma * sigma)))
    return torch.stack(kernels, dim=0).mean(dim=0)


def mmd2_unbiased(x: torch.Tensor, y: torch.Tensor, sigmas: list[float]) -> float:
    m, n = len(x), len(y)
    if m < 2 or n < 2:
        raise ValueError("Unbiased MMD requires both batches to contain at least 2 samples")
    k_xx = rbf_kernel_from_d2(squared_distances(x, x), sigmas)
    k_yy = rbf_kernel_from_d2(squared_distances(y, y), sigmas)
    k_xy = rbf_kernel_from_d2(squared_distances(x, y), sigmas)
    xx = (torch.sum(k_xx) - torch.trace(k_xx)) / (m * (m - 1))
    yy = (torch.sum(k_yy) - torch.trace(k_yy)) / (n * (n - 1))
    xy = torch.sum(k_xy) / (m * n)
    return float((xx + yy - 2.0 * xy).detach().cpu().item())