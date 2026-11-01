"""Known-attack feasibility pilot; not a replacement for a full research evaluation."""
import argparse
import copy
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from MMD_detection import mmd_detector_gpu as original
from pilot.protocol import PARTITIONS, digest, make_partitions, read_rows

original.np, original.torch = np, torch


def draw(pool, n, rng):
    if len(pool) < n:
        raise ValueError(f'Need {n} distinct queries in a pool, found {len(pool)}')
    return pool[torch.as_tensor(rng.choice(len(pool), n, replace=False), device=pool.device)]


def draw_reference_indices(pool, size, repeats, rng):
    if len(pool) < size:
        raise ValueError(f'Need {size} distinct queries in the reference pool')
    return torch.as_tensor(np.stack([rng.choice(len(pool), size, replace=False) for _ in range(repeats)]),
                           dtype=torch.long, device=pool.device)


def mmd(x, y, sigmas, network=None):
    def kernel(a, b):
        base = original.rbf_kernel_from_d2(original.squared_distances(a, b), sigmas)
        if network is None:
            return base
        a, b = network(a), network(b)
        learned = torch.exp(-original.squared_distances(a, b) / 2)
        return base * (0.1 + 0.9 * learned)
    xx, yy, xy = kernel(x, x), kernel(y, y), kernel(x, y)
    return ((xx.sum() - xx.diag().sum()) / (len(x) * (len(x)-1))
            + (yy.sum() - yy.diag().sum()) / (len(y) * (len(y)-1)) - 2 * xy.mean())


def mixed(benign, attack, size, ratio, rng):
    count = max(1, round(size * ratio))
    return torch.cat((draw(benign, size-count, rng), draw(attack, count, rng)))


def training_pair(benign, attack, size, ratio, rng):
    count = max(1, round(size * ratio))
    benign_pair = draw(benign, 2 * size - count, rng)
    return benign_pair[:size], torch.cat((benign_pair[size:], draw(attack, count, rng)))


def score(reference, window, sigmas, network):
    return mmd(reference, window, sigmas, network)


def repeated_score(pool, reference_indices, window, sigmas, network):
    return torch.stack([score(pool[index], window, sigmas, network) for index in reference_indices]).mean()


def standardized_mmd(values):
    """Feasibility proxy: mean mixed-window MMD divided by its variability."""
    return values.mean() / torch.sqrt(values.var(unbiased=False) + 1e-6)


def fit_kernel(network, benign_train, attack_train, benign_validation,
               attack_validation, sigmas, train_window, epochs, steps,
               validation_windows, train_rng, validation_rng):
    """Select an epoch only from fixed validation pairs; test data is not accepted."""
    if steps < 2 or validation_windows < 2:
        raise ValueError('At least two training and validation windows are required')
    validation_pairs = [training_pair(benign_validation, attack_validation, train_window, .1, validation_rng)
                        for _ in range(validation_windows)]
    optimizer = torch.optim.Adam(network.parameters(), lr=0.001, weight_decay=0.0001)

    def validation_score():
        network.eval()
        with torch.no_grad():
            values = torch.stack([score(ref, window, sigmas, network) for ref, window in validation_pairs])
            quality = standardized_mmd(values)
            if not torch.isfinite(quality):
                raise RuntimeError('Non-finite validation objective')
            return quality.item()

    initial_quality = validation_score()
    best, best_epoch = initial_quality, 0
    best_state = copy.deepcopy(network.state_dict())
    history = []
    for epoch in range(epochs):
        network.train()
        pairs = [training_pair(benign_train, attack_train, train_window, .1, train_rng) for _ in range(steps)]
        values = torch.stack([score(reference, window, sigmas, network) for reference, window in pairs])
        loss = -standardized_mmd(values)
        optimizer.zero_grad()
        loss.backward()
        gradient = torch.nn.utils.clip_grad_norm_(network.parameters(), 10.0)
        if not torch.isfinite(loss) or not torch.isfinite(gradient):
            raise RuntimeError('Non-finite training loss or gradient')
        optimizer.step()
        quality = validation_score()
        history.append({'epoch': epoch + 1, 'loss': loss.item(), 'gradient_norm': gradient.item(),
                        'validation_objective': quality})
        if quality > best:
            best, best_epoch = quality, epoch + 1
            best_state = copy.deepcopy(network.state_dict())
        print(f'epoch {epoch+1}: loss={loss.item():.4f} gradient={gradient.item():.4f} val={quality:.4f}', flush=True)
    network.load_state_dict(best_state)
    network.eval()
    network.requires_grad_(False)
    return {'initial_validation_objective': initial_quality, 'best_validation_objective': best,
            'best_epoch': best_epoch, 'history': history}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', default='model_leeching')
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
    args = p.parse_args()
    if min(args.window, args.train_window) < 2 or min(args.epochs, args.calibration_windows, args.test_windows, args.reference_repeats) < 1 or min(args.steps, args.validation_windows) < 2:
        p.error('window sizes, steps and validation windows must be >= 2; other counts must be positive')
    bandwidth_rng, train_rng, validation_rng, calibration_rng, test_rng = [np.random.default_rng(s) for s in np.random.SeedSequence(args.seed).spawn(5)]
    torch.manual_seed(args.seed)
    if args.dataset.lower() != 'model_leeching':
        p.error('Source grouping is validated only for model_leeching; inspect other datasets before use')
    normal_path, attack_path, _ = original.default_dataset_paths(args.data_root, args.dataset)
    normal = read_rows(normal_path, args.max_per_class)
    attack = read_rows(attack_path, args.max_per_class)
    partitions, audit = make_partitions(normal, attack, args.seed)
    names = [f'{label}_{part}' for label in ('benign', 'attack') for part in PARTITIONS]
    rows_by_name = {f'{label}_{part}': partitions[part][label] for label in ('benign', 'attack') for part in PARTITIONS}
    groups = [[row['query'] for row in rows_by_name[name]] for name in names]
    for name, group in zip(names, groups):
        print(f'{name}: {len(group)} unique queries', flush=True)
    sizes_by_name = dict(zip(names, map(len, groups)))
    needed = {'benign_train': max(args.window, 2 * args.train_window - round(args.train_window * .1)),
              'benign_validation': 2 * args.train_window - round(args.train_window * .1),
              'benign_calibration': args.window, 'benign_test': args.window,
              'attack_train': max(1, round(args.train_window * .1)),
              'attack_validation': max(1, round(args.train_window * .1)),
              'attack_test': max(1, round(args.window * .1))}
    insufficient = {name: {'available': sizes_by_name[name], 'required': count}
                    for name, count in needed.items() if sizes_by_name[name] < count}
    if insufficient:
        raise ValueError(f'Insufficient source-grouped data: {insufficient}')
    all_text = sum(groups, [])
    # Embeddings depend on the query and encoder, not on the partition seed.
    # Stable order allows the same cached embeddings to serve every split.
    canonical_text = sorted(all_text)
    positions = {text: i for i, text in enumerate(canonical_text)}
    embeddings = original.embed_texts(canonical_text, args.embedding_model, 64, args.device, '', True, Path('pilot/cache'))
    order = np.asarray([positions[text] for text in all_text])
    all_z = torch.as_tensor(embeddings[order], dtype=torch.float32, device=args.device)
    sizes = [len(g) for g in groups]
    bt, bv, bc, be, at, av, _ac, ae = torch.split(all_z, sizes)
    sigma = original.median_bandwidth(bt, 2000, bandwidth_rng)
    sigmas = [sigma / 2, sigma, sigma * 2, sigma * 4]
    network = nn.Sequential(nn.Linear(all_z.shape[1], 128), nn.ReLU(), nn.Linear(128, 32)).to(args.device)
    training = fit_kernel(network, bt, at, bv, av, sigmas, args.train_window, args.epochs,
                          args.steps, args.validation_windows, train_rng, validation_rng)
    methods = {'rbf': ([sigma], None), 'multi_rbf': (sigmas, None), 'deep_kernel': (sigmas, network)}
    results = []
    thresholds = {}
    calibration_results = []
    with torch.no_grad():
        # Reference queries come from training pool; calibration windows are separate.
        calibration = [(draw_reference_indices(bt, args.window, args.reference_repeats, calibration_rng),
                        draw(bc, args.window, calibration_rng)) for _ in range(args.calibration_windows)]
        windows = [('benign', draw(be, args.window, test_rng)) for _ in range(args.test_windows)]
        for ratio in (.05, .10):
            windows += [(f'mixed_{ratio:g}', mixed(be, ae, args.window, ratio, test_rng)) for _ in range(args.test_windows)]
        refs = [draw_reference_indices(bt, args.window, args.reference_repeats, test_rng) for _ in windows]
        for method, (bandwidths, model) in methods.items():
            cal = [repeated_score(bt, indices, w, bandwidths, model).item() for indices, w in calibration]
            threshold = float(np.quantile(cal, .95))
            thresholds[method] = threshold
            calibration_results.extend({'method': method, 'window_id': i, 'score': value,
                                        'threshold': threshold} for i, value in enumerate(cal))
            for i, ((label, window), indices) in enumerate(zip(windows, refs)):
                value = repeated_score(bt, indices, window, bandwidths, model).item()
                results.append({'method': method, 'split': label, 'window_id': i, 'score': value, 'threshold': threshold, 'detected': int(value > threshold)})
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'scores.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0])); writer.writeheader(); writer.writerows(results)
    with (args.output / 'calibration_scores.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(calibration_results[0])); writer.writeheader(); writer.writerows(calibration_results)
    summary = {m: {s: float(np.mean([r['detected'] for r in results if r['method']==m and r['split']==s])) for s in ['benign','mixed_0.05','mixed_0.1']} for m in methods}
    manifest = {name: [{'id_sha256': digest(row['id']), 'text_sha256': digest(row['query'])} for row in rows_by_name[name]] for name in names}
    metadata = {'protocol_version': 'source-grouped-v3-matched-reference-repeats', 'arguments': {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()}, 'software': {'torch': torch.__version__, 'numpy': np.__version__, 'cuda': torch.version.cuda}, 'sizes': dict(zip(names, sizes)), 'audit': audit, 'sigma': sigma, 'thresholds': thresholds, 'rates': summary, 'training': training, 'split_sha256': manifest}
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    torch.save(network.state_dict(), args.output / 'deep_kernel.pt')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
