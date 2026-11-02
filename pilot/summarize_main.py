"""Validate the completed six-run experiment and write descriptive summaries."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

METHODS = ('rbf', 'multi_rbf', 'deep_kernel')
METRICS = ('fpr', 'tpr_5pct', 'tpr_10pct')


def result_table(rows):
    labels = {'rbf': 'RBF', 'multi_rbf': 'Multi-RBF', 'deep_kernel': 'Deep Kernel'}
    lines = ['| Method | Dataset | Seed | Window | FPR | TPR 5% | TPR 10% |',
             '|---|---|---:|---:|---:|---:|---:|']
    for row in rows:
        values = ' | '.join(f'{float(row[m]):.0%}' for m in METRICS)
        lines.append(f"| {labels[row['method']]} | {row.get('dataset', 'model_leeching')} | {row['seed']} | {row['window']} | {values} |")
    return lines


def summarize(root, dataset='model_leeching'):
    rows, training = [], []
    for seed in (1, 20, 42):
        manifests = []
        for window in (250, 500):
            folder = root / f'seed_{seed}_window_{window}'
            meta = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
            args = meta['arguments']
            expected = dict(seed=seed, window=window, dataset=dataset,
                            reference_repeats=20, epochs=20, steps=8, train_window=100,
                            validation_windows=32, calibration_windows=200, test_windows=100,
                            max_per_class=None)
            for key, value in expected.items():
                if args[key] != value:
                    raise ValueError(f'{folder}: unexpected {key}={args[key]}')
            for key in ('id', 'normalized_text', 'attack_context'):
                if meta['audit'][f'cross_partition_{key}_collisions'] != 0:
                    raise ValueError(f'{folder}: partition overlap')
            manifests.append(meta['split_sha256'])
            with (folder / 'scores.csv').open(newline='', encoding='utf-8') as stream:
                scores = list(csv.DictReader(stream))
            with (folder / 'calibration_scores.csv').open(newline='', encoding='utf-8') as stream:
                calibration = list(csv.DictReader(stream))
            for method in METHODS:
                rates = {}
                for split, metric in zip(('benign', 'mixed_0.05', 'mixed_0.1'), METRICS):
                    selected = [r for r in scores if r['method'] == method and r['split'] == split]
                    if len(selected) != 100 or not all(np.isfinite(float(r['score'])) for r in selected):
                        raise ValueError(f'{folder}: invalid test scores')
                    if len({r['window_id'] for r in selected}) != 100:
                        raise ValueError(f'{folder}: duplicate test window IDs')
                    if any(int(r['detected']) != int(float(r['score']) > meta['thresholds'][method])
                           for r in selected):
                        raise ValueError(f'{folder}: inconsistent detection decisions')
                    rates[metric] = float(np.mean([int(r['detected']) for r in selected]))
                    if not np.isclose(rates[metric], meta['rates'][method][split]):
                        raise ValueError(f'{folder}: inconsistent reported rates')
                cal = [float(r['score']) for r in calibration if r['method'] == method]
                if len(cal) != 200 or not np.isfinite(cal).all():
                    raise ValueError(f'{folder}: invalid calibration scores')
                if not np.isclose(np.quantile(cal, .95), meta['thresholds'][method]):
                    raise ValueError(f'{folder}: inconsistent threshold')
                rows.append(dict(dataset=dataset, seed=seed, window=window, method=method, **rates,
                                 threshold=meta['thresholds'][method],
                                 actual_attack_5pct=meta['actual_attack_fractions']['0.05'],
                                 actual_attack_10pct=meta['actual_attack_fractions']['0.1']))
            for item in meta['training']['history']:
                training.append(dict(seed=seed, window=window, **item))
        if manifests[0] != manifests[1]:
            raise ValueError(f'Seed {seed}: splits differ between window sizes')
    aggregates = []
    for window in (250, 500):
        for method in METHODS:
            subset = [r for r in rows if r['window'] == window and r['method'] == method]
            record = dict(window=window, method=method)
            for metric in METRICS:
                values = [r[metric] for r in subset]
                record.update({f'{metric}_mean': float(np.mean(values)),
                               f'{metric}_min': min(values), f'{metric}_max': max(values)})
            aggregates.append(record)
    for filename, records in [('validated_runs.csv', rows), ('summary.csv', aggregates),
                              ('training_history.csv', training)]:
        with (root / filename).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    chart(root, rows, aggregates, dataset)
    training_chart(root, training)
    lines = [f'# Deep Kernel MMD: {dataset}', '', *result_table(rows), '',
             'Six runs; seeds 1, 20, 42; frozen BGE-small; grouped splits (see metadata for policy);',
             '20 references per calibration/test window; 200 calibration windows;',
             '100 test windows per condition; method-specific 95th-percentile thresholds.', '',
             '## Mean and range across seeds', '',
             '| Method | Window | FPR | TPR 5% | TPR 10% |',
             '|---|---:|---:|---:|---:|']
    for row in aggregates:
        cells = [f"{row[m+'_mean']:.1%} ({row[m+'_min']:.1%}–{row[m+'_max']:.1%})" for m in METRICS]
        lines.append(f"| {row['method']} | {row['window']} | " + ' | '.join(cells) + ' |')
    lines += ['', '![Rates by seed and window](rates.svg)', '', '## Checkpoint selection', '',
              '| Seed | Window | Best epoch | Validation before | Validation selected |',
              '|---:|---:|---:|---:|---:|']
    for seed in (1, 20, 42):
        for window in (250, 500):
            meta = json.loads((root / f'seed_{seed}_window_{window}' / 'metadata.json').read_text())
            t = meta['training']
            lines.append(f"| {seed} | {window} | {t['best_epoch']} | {t['initial_validation_objective']:.4f} | {t['best_validation_objective']:.4f} |")
    lines += ['', '![Training and validation objectives](training.svg)', '', '## Interpretation limits', '',
              '- These are descriptive known-attack results, not an unseen-family evaluation.',
              '- Ranges across seeds are not confidence intervals. Sampled windows overlap.',
              '- A 95th-percentile calibration threshold does not guarantee 5% held-out FPR.',
              '- Compare TPR alongside FPR; unequal FPR does not establish superiority at equal FPR.',
              '- The learned kernel uses attack labels during training; fixed kernels do not.',
              '- Length/format differences in this dataset limit semantic interpretations.',
              '- Training uses the existing exploratory signal-to-noise proxy.',
              '- At window 250, nominal 5% is 12/250 = 4.8%; other tested mixtures are exact.',
              '- Test scores were not used to select checkpoints or thresholds.', '',
              '- Additional SST-2 datasets have synthetic row IDs and no recoverable source-passage IDs; ID/text grouping does not establish source independence.',
              'Full per-seed rates: validated_runs.csv. Training trajectories: training_history.csv.',
              'Each run folder includes scores, calibration scores, split hashes, settings and weights.']
    (root / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


def chart(root, rows, aggregates, dataset='model_leeching'):
    """Export a standalone SVG with all seeds and mean/range; no extra dependencies."""
    colors = {'rbf': '#2563eb', 'multi_rbf': '#d97706', 'deep_kernel': '#15803d'}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="650" viewBox="0 0 1120 650">',
           '<rect width="1120" height="650" fill="white"/>',
           '<g font-family="Arial,sans-serif" fill="#172033">',
           f'<text x="30" y="30" font-size="22">{dataset}: mean, range and individual seeds</text>']
    for col, (metric, label) in enumerate(zip(METRICS, ('Benign FPR', 'TPR at 5% attack', 'TPR at 10% attack'))):
        left = 65 + col * 365
        svg.append(f'<text x="{left}" y="85" font-size="18">{label}</text>')
        for tick in range(0, 101, 20):
            y = 510 - tick * 3.7
            svg.append(f'<path d="M{left},{y}h300" stroke="#e2e8f0"/><text x="{left-8}" y="{y+4}" text-anchor="end" font-size="12">{tick}%</text>')
        if metric == 'fpr':
            svg.append(f'<path d="M{left},{510-5*3.7}h300" stroke="#dc2626" stroke-dasharray="5 4"/>')
        for group, window in enumerate((250, 500)):
            center = left + 75 + group * 150
            svg.append(f'<text x="{center}" y="540" text-anchor="middle" font-size="14">{window} queries</text>')
            for offset, method in zip((-35, 0, 35), METHODS):
                x, color = center + offset, colors[method]
                agg = next(a for a in aggregates if a['window'] == window and a['method'] == method)
                low, high, mean = [510 - agg[metric + suffix] * 370 for suffix in ('_min', '_max', '_mean')]
                svg.append(f'<path d="M{x},{low}V{high}M{x-5},{low}h10M{x-5},{high}h10" stroke="{color}" stroke-width="2"/>')
                subset = [r for r in rows if r['window'] == window and r['method'] == method]
                for jitter, row in zip((-7, 0, 7), subset):
                    svg.append(f'<circle cx="{x+jitter}" cy="{510-row[metric]*370}" r="4" fill="white" stroke="{color}"/>')
                svg.append(f'<rect x="{x-4}" y="{mean-4}" width="8" height="8" fill="{color}"/>')
    for index, method in enumerate(METHODS):
        x = 100 + index * 260
        svg.append(f'<rect x="{x}" y="580" width="12" height="12" fill="{colors[method]}"/><text x="{x+20}" y="591" font-size="15">{method}</text>')
    svg.append('<text x="30" y="630" font-size="13">Squares: means. Circles: seeds 1, 20, 42. Lines: min–max (not confidence intervals). Red dashed: 5% target FPR.</text></g></svg>')
    (root / 'rates.svg').write_text('\n'.join(svg), encoding='utf-8')


def training_chart(root, records):
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="720">',
           '<rect width="1100" height="720" fill="white"/>',
           '<g font-family="Arial,sans-serif" fill="#172033">',
           '<text x="30" y="30" font-size="22">Deep Kernel: training and validation objectives</text>']
    for row, window in enumerate((250, 500)):
        for col, seed in enumerate((1, 20, 42)):
            items = [r for r in records if r['window'] == window and r['seed'] == seed]
            left, top = 65 + col * 355, 100 + row * 285
            values = [-r['loss'] for r in items] + [r['validation_objective'] for r in items]
            low, high = min(values), max(values)
            span = max(high - low, .01)
            low, high = low - span * .1, high + span * .1
            svg.append(f'<text x="{left}" y="{top-20}" font-size="16">Seed {seed}, window {window}</text>')
            for fraction in (0, .5, 1):
                y = top + 190 * (1-fraction)
                value = low + (high-low)*fraction
                svg.append(f'<path d="M{left},{y}h270" stroke="#e2e8f0"/><text x="{left-5}" y="{y+4}" text-anchor="end" font-size="11">{value:.2f}</text>')
            for key, color in (('loss', '#2563eb'), ('validation_objective', '#15803d')):
                points = []
                for item in items:
                    value = -item[key] if key == 'loss' else item[key]
                    points.append(f"{left+(item['epoch']-1)/19*270:.2f},{top+190*(high-value)/(high-low):.2f}")
                svg.append(f'<polyline points="{" ".join(points)}" stroke="{color}" fill="none" stroke-width="2"/>')
            svg.append(f'<text x="{left}" y="{top+210}" font-size="12">Epoch 1</text><text x="{left+220}" y="{top+210}" font-size="12">Epoch 20</text>')
    svg.append('<text x="40" y="670" font-size="15" fill="#2563eb">Blue: training objective (negative loss)</text><text x="510" y="670" font-size="15" fill="#15803d">Green: fixed validation objective</text>')
    svg.append('<text x="40" y="700" font-size="12">Panels use separate vertical scales. Objective values are exploratory proxies, not measured detection power.</text></g></svg>')
    (root / 'training.svg').write_text('\n'.join(svg), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--dataset', default='model_leeching')
    args = parser.parse_args()
    summarize(args.root, args.dataset)
