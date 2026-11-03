"""Run a Deep Kernel MMD experiment from JSON configuration and CLI overrides."""
import argparse
import json
from pathlib import Path

from .datasets.registry import get_dataset, load_dataset


def main(argv=None):
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config", type=Path)
    bootstrap.add_argument("--dataset-config", type=Path)
    known, _ = bootstrap.parse_known_args(argv)
    p = argparse.ArgumentParser(description=__doc__, parents=[bootstrap])
    p.add_argument('--dataset', default=None)
    p.add_argument('--data-root', type=Path, default=Path('data'))
    p.add_argument('--output', type=Path, default=Path('pilot/outputs/known_attack'))
    p.add_argument('--device', default='cpu')
    p.add_argument('--embedding-model', default='BAAI/bge-small-en-v1.5')
    p.add_argument('--window', type=int, default=250)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--epochs', type=int, default=20)
    p.add_argument('--steps', type=int, default=8)
    p.add_argument('--validation-windows', type=int, default=32)
    p.add_argument('--train-window', type=int, default=100)
    p.add_argument('--calibration-windows', type=int, default=200)
    p.add_argument('--test-windows', type=int, default=100)
    p.add_argument('--reference-repeats', type=int, default=1,
                   help='Number of benign references averaged per window, in calibration and test')
    p.add_argument('--max-per-class', type=int, default=None)

    p.add_argument('--cache-dir', type=Path, default=Path('pilot/cache'))
    if known.config:
        defaults = json.loads(known.config.read_text(encoding='utf-8'))
        allowed = {action.dest for action in p._actions} - {'help', 'config', 'dataset_config'}
        unknown = set(defaults) - allowed
        if unknown:
            p.error(f'Unknown experiment settings: {sorted(unknown)}')
        for action in p._actions:
            if action.dest in defaults and action.type is not None:
                defaults[action.dest] = action.type(defaults[action.dest])
        p.set_defaults(**defaults)
    args = p.parse_args(argv)
    if min(args.window, args.train_window) < 2 or min(args.epochs, args.calibration_windows, args.test_windows, args.reference_repeats) < 1 or min(args.steps, args.validation_windows) < 2:
        p.error('window sizes, steps and validation windows must be >= 2; other counts must be positive')
    if args.max_per_class is not None and args.max_per_class < 1:
        p.error('--max-per-class must be positive')
    try:
        spec = load_dataset(args.dataset_config) if args.dataset_config else get_dataset(args.dataset or 'model_leeching')
        if args.dataset is not None and args.dataset != spec.name:
            p.error('--dataset and --dataset-config names disagree')
    except ValueError as exc:
        p.error(str(exc))
    args.dataset = spec.name
    from .experiment import run
    run(args, spec)
