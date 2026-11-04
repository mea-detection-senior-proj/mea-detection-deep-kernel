"""Count distinct queries needed by evaluation windows and training pairs."""
from mea_detection.data.windows import attacker_count


def evaluation_capacity(sizes, size, ratio):
    if size < 2:
        raise ValueError("Window size >= 2 required")
    na = attacker_count(size, ratio)
    needs = {"reference_benign": size, "calibration_benign": size,
             "test_benign": size, "test_attack": na}
    pools = {"reference_benign": sizes["reference"]["benign"],
             "calibration_benign": sizes["calibration"]["benign"],
             "test_benign": sizes["test"]["benign"], "test_attack": sizes["test"]["attack"]}
    # Benign-only testing is required even for a pure-attack condition.
    shortages = [f"{key}: {pools[key]} < {need}" for key, need in needs.items() if pools[key] < need]
    bounds = []
    if na:
        bounds.append(pools["test_attack"] // na)
    if size > na:
        bounds.append(pools["test_benign"] // (size - na))
    return {"window_size": size, "requested_ratio": ratio, "attacker_count": na, "actual_ratio": na / size,
            "supported": not shortages, "shortages": "; ".join(shortages),
            "benign_disjoint_test_windows_row_bound": pools["test_benign"] // size,
            "condition_disjoint_test_windows_row_bound": min(bounds),
            "disjoint_calibration_windows_row_bound": pools["calibration_benign"] // size}


def require_evaluation_capacity(sizes, window_sizes, ratios):
    for size in window_sizes:
        for ratio in [0, *ratios]:
            capacity = evaluation_capacity(sizes, size, ratio)
            if not capacity["supported"]:
                raise ValueError(f"evaluation window {size}: {capacity['shortages']}")


def training_capacity(sizes, size, ratio=1.):
    na = attacker_count(size, ratio)
    shortages = []
    for part in ("train", "validation"):
        for label, need in (("benign", 2 * size - na), ("attack", na)):
            if sizes[part][label] < need:
                shortages.append(f"{part}_{label}: {sizes[part][label]} < {need}")
    return {"training_window_size": size, "training_mode": "pure" if ratio == 1 else "mixed",
            "requested_ratio": ratio, "attacker_count": na,
            "supported": not shortages, "shortages": "; ".join(shortages)}


def require_training_capacity(sizes, size):
    capacity = training_capacity(sizes, size)
    if not capacity["supported"]:
        raise ValueError(f"Insufficient data for pure training size {size}: {capacity['shortages']}")
