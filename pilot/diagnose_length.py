"""Length-only diagnostic on the pilot's exact sampled windows."""
import csv
import json
from pathlib import Path

import numpy as np

from pilot.protocol import make_partitions, read_rows


def draw(pool, n, rng):
    return pool[rng.choice(len(pool), n, replace=False)]


def run(seed, window, partitions):
    _, _, _, calibration_seed, test_seed = np.random.SeedSequence(seed).spawn(5)
    cal_rng, test_rng = np.random.default_rng(calibration_seed), np.random.default_rng(test_seed)
    pool = {f'{label}_{part}': np.array([len(r['query']) for r in rows])
            for part, labels in partitions.items() for label, rows in labels.items()}
    bt, bc, be = (pool[f'benign_{part}'] for part in ('train', 'calibration', 'test'))
    ae = pool['attack_test']
    # Mirror the exact order and RNG calls in deep_kernel_pilot.py.
    cal = [(draw(bt, window, cal_rng), draw(bc, window, cal_rng)) for _ in range(200)]
    windows = [('benign', draw(be, window, test_rng)) for _ in range(100)]
    for ratio in (.05, .1):
        count = max(1, round(window * ratio))
        for _ in range(100):
            w = np.concatenate((draw(be, window-count, test_rng), draw(ae, count, test_rng)))
            windows.append((f'mixed_{ratio:g}', w))
    refs = [draw(bt, window, test_rng) for _ in windows]
    calibration_scores = [np.mean(w) - np.mean(ref) for ref, w in cal]
    threshold = float(np.quantile(calibration_scores, .95))
    values = [(label, float(np.mean(w) - np.mean(ref))) for (label, w), ref in zip(windows, refs)]
    rates = {label: float(np.mean([s > threshold for name, s in values if name == label]))
             for label in ('benign', 'mixed_0.05', 'mixed_0.1')}
    return rates, threshold


def main():
    data = Path('data/model_leeching')
    normal, attack = (read_rows(data / label / 'queries.jsonl') for label in ('normal', 'attacker'))
    output = Path('pilot/outputs/length_diagnostic')
    output.mkdir(parents=True, exist_ok=True)
    results, split_stats = [], []
    for seed in (1, 20, 42):
        partitions, audit = make_partitions(normal, attack, seed)
        for part, groups in partitions.items():
            for label, rows in groups.items():
                lengths = np.array([len(row['query']) for row in rows])
                split_stats.append({'seed': seed, 'partition': part, 'label': label,
                                    'n': len(lengths), 'mean_chars': float(lengths.mean()),
                                    'median_chars': float(np.median(lengths))})
        for window in (250, 500):
            rates, threshold = run(seed, window, partitions)
            results.append({'seed': seed, 'window': window, 'threshold_chars': threshold,
                            'fpr': rates['benign'], 'tpr_5pct': rates['mixed_0.05'],
                            'tpr_10pct': rates['mixed_0.1']})
    for name, rows in [('runs.csv', results), ('split_lengths.csv', split_stats)]:
        with (output / name).open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
