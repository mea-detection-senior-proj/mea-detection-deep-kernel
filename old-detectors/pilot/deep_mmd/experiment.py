"""Single-dataset experiment: split, encode, fit, calibrate, evaluate, save."""
import csv
import json
import time
from pathlib import Path

import numpy as np
import torch

from .datasets.protocol import PARTITIONS, digest, make_partitions, read_rows
from .embeddings import embed_texts
from .kernels import median_bandwidth
from .models import build_feature_network
from .training import fit_kernel
from .evaluation import evaluate


def run(args, spec):
    if args.output.exists() and any(p.name != "run.log" for p in args.output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite nonempty output: {args.output}")
    started = time.perf_counter()
    bandwidth_rng, train_rng, validation_rng, calibration_rng, test_rng = [np.random.default_rng(s) for s in np.random.SeedSequence(args.seed).spawn(5)]
    torch.manual_seed(args.seed)
    normal_path, attack_path = spec.paths(args.data_root)
    normal = read_rows(normal_path, args.max_per_class, spec=spec)
    attack = read_rows(attack_path, args.max_per_class, spec=spec)
    partitions, audit = make_partitions(normal, attack, args.seed, args.dataset, spec=spec)
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
    embeddings = embed_texts(canonical_text, args.embedding_model, 64, args.device, '', True, args.cache_dir)
    order = np.asarray([positions[text] for text in all_text])
    all_z = torch.as_tensor(embeddings[order], dtype=torch.float32, device=args.device)
    sizes = [len(g) for g in groups]
    bt, bv, bc, be, at, av, _ac, ae = torch.split(all_z, sizes)
    sigma = median_bandwidth(bt, 2000, bandwidth_rng)
    sigmas = [sigma / 2, sigma, sigma * 2, sigma * 4]
    network = build_feature_network(all_z.shape[1]).to(args.device)
    training = fit_kernel(network, bt, at, bv, av, sigmas, args.train_window, args.epochs,
                          args.steps, args.validation_windows, train_rng, validation_rng)
    methods = {'rbf': ([sigma], None), 'multi_rbf': (sigmas, None), 'deep_kernel': (sigmas, network)}
    results, calibration_results, thresholds = evaluate(
        methods, bt, bc, be, ae, args.window, args.reference_repeats,
        args.calibration_windows, args.test_windows, calibration_rng, test_rng)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'scores.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0])); writer.writeheader(); writer.writerows(results)
    with (args.output / 'calibration_scores.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(calibration_results[0])); writer.writeheader(); writer.writerows(calibration_results)
    summary = {m: {s: float(np.mean([r['detected'] for r in results if r['method']==m and r['split']==s])) for s in ['benign','mixed_0.05','mixed_0.1']} for m in methods}
    manifest = {name: [{'id_sha256': digest(row['id']), 'text_sha256': digest(row['query'])} for row in rows_by_name[name]] for name in names}
    metadata = {'protocol_version': 'source-grouped-v3-matched-reference-repeats', 'arguments': {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()}, 'software': {'torch': torch.__version__, 'numpy': np.__version__, 'cuda': torch.version.cuda}, 'sizes': dict(zip(names, sizes)), 'audit': audit, 'sigma': sigma, 'thresholds': thresholds, 'rates': summary, 'training': training, 'split_sha256': manifest}
    metadata['elapsed_seconds'] = time.perf_counter() - started
    metadata['dataset_spec'] = spec.to_dict()
    if spec.grouping_policy != 'id-text-attack-context':
        metadata['protocol_version'] = 'id-text-grouped-v1-matched-reference-repeats'
    metadata['actual_attack_fractions'] = {str(r): max(1, round(args.window * r)) / args.window for r in (.05, .1)}
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    torch.save(network.state_dict(), args.output / 'deep_kernel.pt')
    print(json.dumps(summary, indent=2))
