"""Shared reference and mixed-window sampling."""
import numpy as np
import torch


def draw(pool, n, rng):
    if len(pool) < n:
        raise ValueError(f'Need {n} distinct queries in a pool, found {len(pool)}')
    return pool[torch.as_tensor(rng.choice(len(pool), n, replace=False), device=pool.device)]


def draw_reference_indices(pool, size, repeats, rng):
    if len(pool) < size:
        raise ValueError(f'Need {size} distinct queries in the reference pool')
    return torch.as_tensor(np.stack([rng.choice(len(pool), size, replace=False) for _ in range(repeats)]),
                           dtype=torch.long, device=pool.device)


def mixed(benign, attack, size, ratio, rng):
    count = max(1, round(size * ratio))
    return torch.cat((draw(benign, size-count, rng), draw(attack, count, rng)))


def training_pair(benign, attack, size, ratio, rng):
    count = max(1, round(size * ratio))
    benign_pair = draw(benign, 2 * size - count, rng)
    return benign_pair[:size], torch.cat((benign_pair[size:], draw(attack, count, rng)))


