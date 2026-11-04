"""Accepted pure-training settings and input validation."""
import math

DEFAULT_TRAINING = {"mode": "pure", "window_size": 100, "epochs": 30, "steps_per_epoch": 16,
                    "validation_pairs": 32, "learning_rate": .001, "weight_decay": .0001,
                    "variance_regularizer": 1e-8, "gradient_clip": 10., "hidden_dim": 128, "feature_dim": 64}


def validate_training(supplied):
    if not isinstance(supplied, dict) or set(supplied) - set(DEFAULT_TRAINING):
        raise ValueError("Invalid training config keys")
    config = {**DEFAULT_TRAINING, **supplied}
    if config["mode"] != "pure":
        raise ValueError("This first comparison supports pure training only")
    for key in ("window_size", "epochs", "steps_per_epoch", "validation_pairs", "hidden_dim", "feature_dim"):
        if type(config[key]) is not int or config[key] < (2 if key == "window_size" else 1):
            raise ValueError(f"Invalid training count: {key}")
    for key in ("learning_rate", "variance_regularizer", "gradient_clip", "weight_decay"):
        value = config[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < (0 if key == "weight_decay" else 1e-15):
            raise ValueError(f"Invalid training value: {key}")
    return config


