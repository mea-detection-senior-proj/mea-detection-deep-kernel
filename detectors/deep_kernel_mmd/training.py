"""Train on pure attacker pairs; select checkpoint only on fixed validation pairs."""
import copy
import math

import numpy as np
import torch

from detectors.mmd.detector import median_bandwidth

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


def power_objective(model, x, y, regularizer):
    """Eq. 2 numerator and Eq. 5 regularized asymptotic variance (not /n).

    H includes diagonals for the variance V-statistic; exclude them only from
    the paired U-statistic numerator. This is not variance across traffic windows.
    """
    if len(x) != len(y) or len(x) < 2 or regularizer <= 0:
        raise ValueError("Need equal-size batches >= 2 and positive regularization")
    xy = model.kernel(x, y)
    h = model.kernel(x, x) + model.kernel(y, y) - xy - xy.T
    numerator = (h.sum() - h.diagonal().sum()) / (len(x) * (len(x) - 1))
    variance = 4 * h.mean(1).var(unbiased=False)
    return numerator / torch.sqrt(variance + regularizer), numerator, variance


def draw_pair(benign, attack, size, rng):
    if len(benign) < size or len(attack) < size:
        raise ValueError("Insufficient distinct training/validation queries")
    return (benign[torch.as_tensor(rng.choice(len(benign), size, replace=False), device=benign.device)],
            attack[torch.as_tensor(rng.choice(len(attack), size, replace=False), device=attack.device)])


def fit_kernel(model, benign_train, attack_train, benign_validation, attack_validation, config, seed):
    """No reference/calibration/test data is accepted by this training interface."""
    config = validate_training(config)
    init_rng, train_rng, validation_rng = [np.random.default_rng(s) for s in np.random.SeedSequence([seed, 7]).spawn(3)]
    with torch.no_grad():
        sigma = median_bandwidth(model.network(benign_train), 512, init_rng)
        model.log_feature_bandwidth.fill_(math.log(sigma))
    pairs = [draw_pair(benign_validation, attack_validation, config["window_size"], validation_rng)
             for _ in range(config["validation_pairs"])]

    def validate():
        model.eval()
        with torch.no_grad():
            value = float(torch.stack([power_objective(model, x, y, config["variance_regularizer"])[0]
                                       for x, y in pairs]).mean())
        if not math.isfinite(value):
            raise RuntimeError("Non-finite validation objective")
        return value

    initial = best = validate()
    best_epoch, best_state, history = 0, copy.deepcopy(model.state_dict()), []
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"])
    for epoch in range(1, config["epochs"] + 1):
        model.train()
        losses, gradients = [], []
        for _ in range(config["steps_per_epoch"]):
            x, y = draw_pair(benign_train, attack_train, config["window_size"], train_rng)
            objective, _, _ = power_objective(model, x, y, config["variance_regularizer"])
            loss = -objective
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), config["gradient_clip"])
            if not torch.isfinite(loss) or not torch.isfinite(norm):
                raise RuntimeError("Non-finite training loss/gradient")
            optimizer.step()
            losses.append(float(loss.detach()))
            gradients.append(float(norm))
        quality = validate()
        history.append({"epoch": epoch, "loss": float(np.mean(losses)), "gradient_norm": float(np.mean(gradients)),
                        "validation_objective": quality})
        print(f"  epoch {epoch}: loss={np.mean(losses):.5f}, validation={quality:.5f}", flush=True)
        if quality > best:
            best, best_epoch, best_state = quality, epoch, copy.deepcopy(model.state_dict())
    model.load_state_dict(best_state)
    model.eval().requires_grad_(False)
    return {"initial_validation_objective": initial, "best_validation_objective": best, "best_epoch": best_epoch,
            "selection": "maximum mean pure-pair validation objective, including epoch zero",
            "history": history, "config": config, "kernel_parameters": model.parameters_metadata()}
