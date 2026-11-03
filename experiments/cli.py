"""Command-line inputs; unspecified flags never override JSON settings."""
import argparse
from pathlib import Path

from experiments.configuration import load_config


def parse_config(argv=None):
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS,
                                     description="Prepare shared windows, run selected MMD methods and write a report.")
    parser.add_argument("--config", type=Path, help="Optional JSON defaults; explicitly supplied flags take precedence")
    dataset = parser.add_mutually_exclusive_group()
    dataset.add_argument("--dataset", help="Folder name under --data-root, containing normal/queries.jsonl and attacker/queries.jsonl")
    dataset.add_argument("--dataset-config", help=argparse.SUPPRESS)
    for name in ("device", "embedding-model", "embedding-revision", "query-prefix", "data-root", "cache-dir", "output", "protocol-lock"):
        parser.add_argument(f"--{name}")
    parser.add_argument("--dtype", choices=("float32", "float64"))
    parser.add_argument("--methods", nargs="+", choices=("rbf", "multi_rbf", "deep_kernel"))
    windows = parser.add_mutually_exclusive_group()
    windows.add_argument("--window", type=int, help="One evaluation window size; does not change train-window")
    windows.add_argument("--window-sizes", nargs="+", type=int)
    seeds = parser.add_mutually_exclusive_group()
    seeds.add_argument("--seed", type=int)
    seeds.add_argument("--seeds", nargs="+", type=int)
    for name in ("reference-repeats", "calibration-windows", "test-windows", "encode-batch-size", "bandwidth-sample-size"):
        parser.add_argument(f"--{name}", type=int)
    parser.add_argument("--attacker-ratios", type=float, nargs="+", help="Fractions, e.g. 0.01 0.05 0.1 1")
    parser.add_argument("--target-fpr", type=float, help="Calibration target as a fraction, e.g. 0.05")
    parser.add_argument("--train-window", type=int)
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the plan without loading an encoder or writing files")
    values = vars(parser.parse_args(argv))
    config_path = values.pop("config", None)
    dry_run = values.pop("dry_run", False)
    for singular, plural in (("window", "window_sizes"), ("seed", "seeds")):
        if singular in values:
            values[plural] = [values.pop(singular)]
    training = {}
    for flag, field in (("train_window", "window_size"), ("epochs", "epochs"), ("learning_rate", "learning_rate")):
        if flag in values:
            training[field] = values.pop(flag)
    if training:
        values["training"] = training
    try:
        return parser, load_config(config_path, values), dry_run
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
