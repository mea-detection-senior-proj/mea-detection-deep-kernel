"""Run the predefined known-attack pilot and collect descriptive rates."""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('pilot/outputs/main_model_leeching_repeats20'))
    p.add_argument('--device', default='cuda')
    p.add_argument('--embedding-model', default='pilot/cache/bge-small-en-v1.5')
    p.add_argument('--reference-repeats', type=int, default=20)
    p.add_argument('--dataset', default='model_leeching')
    args = p.parse_args()
    output = (ROOT / args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in (1, 20, 42):
        for window in (250, 500):
            run_dir = output / f'seed_{seed}_window_{window}'
            if run_dir.exists() and any(run_dir.iterdir()):
                raise FileExistsError(f'Refusing to overwrite run: {run_dir}')
            run_dir.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, '-u', 'pilot/deep_kernel_pilot.py', '--dataset', args.dataset,
                   '--device', args.device, '--embedding-model', args.embedding_model,
                   '--seed', str(seed), '--window', str(window), '--epochs', '20', '--steps', '8',
                   '--validation-windows', '32', '--calibration-windows', '200', '--test-windows', '100',
                   '--reference-repeats', str(args.reference_repeats),
                   '--output', str(run_dir)]
            print(f'Starting seed={seed} window={window}; log: {run_dir / "run.log"}', flush=True)
            with (run_dir / 'run.log').open('w', encoding='utf-8') as log:
                result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
            if result.returncode:
                raise RuntimeError(f'Run failed ({result.returncode}); see {run_dir / "run.log"}')
            metadata = json.loads((run_dir / 'metadata.json').read_text(encoding='utf-8'))
            for method, rates in metadata['rates'].items():
                rows.append({'dataset': args.dataset, 'seed': seed, 'window': window, 'method': method,
                             'fpr': rates['benign'], 'tpr_5pct': rates['mixed_0.05'],
                             'tpr_10pct': rates['mixed_0.1'],
                             'best_epoch': metadata['training']['best_epoch'],
                             'output': str(run_dir)})
            with (output / 'runs.csv').open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            print(f'Completed seed={seed} window={window}: {metadata["rates"]}', flush=True)
    print(f'Wrote {output / "runs.csv"}', flush=True)


if __name__ == '__main__':
    main()
