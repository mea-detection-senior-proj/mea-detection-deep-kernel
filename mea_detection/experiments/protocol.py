"""Protocol compatibility policy independent of file handling."""

import numpy as np

from mea_detection.data.datasets import split_rows
from mea_detection.data.capacity import require_evaluation_capacity
from mea_detection.data.windows import make_windows

LOCK_KEYS = ("data_root", "embedding_model", "embedding_revision", "query_prefix", "dtype",
             "seeds", "window_sizes", "attacker_ratios", "reference_repeats", "calibration_windows",
             "test_windows", "target_fpr", "bandwidth_sample_size")


def protocol_settings(config):
    selector = {"dataset": config["dataset"]} if config.get("dataset") else {"dataset_config": config["dataset_config"]}
    return {**selector, **{key: config[key] for key in LOCK_KEYS}}


def validate_settings(metadata, config):
    requested = protocol_settings(config)
    # Old locks retain their embedded dataset snapshot; no old JSON file is needed.
    if config.get("dataset") and "dataset_config" in metadata["settings"] and config["dataset"] == metadata["dataset"]["name"]:
        requested.pop("dataset")
        requested["dataset_config"] = metadata["settings"]["dataset_config"]
    keys = set(requested) | set(metadata["settings"])
    differences = [f"{key}: requested={requested.get(key)!r}, locked={metadata['settings'].get(key)!r}"
                   for key in sorted(keys) if requested.get(key) != metadata["settings"].get(key)]
    if differences:
        raise ValueError("Experiment settings differ from the locked evaluation protocol:\n" + "\n".join(differences)
                         + "\nUse a new protocol lock for these settings.")


def partition_plans(config, spec, benign, attack):
    plans = [(seed, *split_rows(benign, attack, seed, spec["grouping_policy"])) for seed in config["seeds"]]
    for seed, _, audit, _ in plans:
        try:
            require_evaluation_capacity(audit["sizes"], config["window_sizes"], config["attacker_ratios"])
        except ValueError as exc:
            raise ValueError(f"Dataset {spec['name']}, seed {seed}, {exc}") from exc
    return plans


def evaluation_draws(config, pools, seed, size):
    cal_rng, test_rng = [np.random.default_rng(s) for s in np.random.SeedSequence([seed, size, 1]).spawn(2)]
    calibration = make_windows(pools["calibration"]["benign"], [], pools["reference"]["benign"], size,
                               config["reference_repeats"], config["calibration_windows"], [0], cal_rng)
    test = make_windows(pools["test"]["benign"], pools["test"]["attack"], pools["reference"]["benign"], size,
                        config["reference_repeats"], config["test_windows"], [0] + config["attacker_ratios"], test_rng)
    return calibration, test
