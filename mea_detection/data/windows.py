"""Deterministic fixed-count windows; no replacement inside each draw."""
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class Window:
    split: str
    indices: np.ndarray
    references: np.ndarray
    attacker_count: int
    requested_ratio: float


def attacker_count(size, ratio):
    if not 0 <= ratio <= 1:
        raise ValueError("Ratio must be in [0, 1]")
    if ratio in (0, 1):
        return int(size * ratio)
    # Half-up; never silently turn a positive mixture into zero or a pure attack.
    return min(size - 1, max(1, math.floor(size * ratio + .5)))


def sample(pool, size, rng):
    if len(pool) < size:
        raise ValueError(f"Need {size} distinct rows; only {len(pool)} available")
    return np.asarray(rng.choice(pool, size=size, replace=False), dtype=np.int64)


def make_windows(benign, attack, reference, size, repeats, count, ratios, rng):
    if size < 2 or repeats < 1 or count < 1:
        raise ValueError("Window size >= 2 and positive repeats/count required")
    windows = []
    for ratio in ratios:
        n_attack = attacker_count(size, ratio)
        split = "heldout_benign" if ratio == 0 else "attacker" if ratio == 1 else f"mixed_{ratio:g}"
        for _ in range(count):
            indices = np.concatenate([sample(benign, size - n_attack, rng), sample(attack, n_attack, rng)])
            rng.shuffle(indices)
            refs = np.stack([sample(reference, size, rng) for _ in range(repeats)])
            windows.append(Window(split, indices, refs, n_attack, ratio))
    return windows
