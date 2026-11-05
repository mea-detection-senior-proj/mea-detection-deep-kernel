"""Paired offline ordering experiment; no model/API queries and no training.

The trace loop follows PRADA/prada_stream_detector.py (MIT, Shuze Liu et al.).
Only its distance lookup is accelerated using a shared frozen pairwise matrix.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import warnings

import numpy as np
from scipy.stats import shapiro

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pilot'))
sys.path.insert(0, str(ROOT / 'PRADA'))
import protocol
import prada_detector as base

base.np = np
ORDERS = ('random', 'clustered', 'interleaved')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8', newline='\n')


def source_file_hashes(paths):
    return {str(Path(p).resolve().relative_to(ROOT)): sha(p) for p in paths}


def make_orders(prefix, benign, attack, rng):
    prefix, benign, attack = [np.asarray(x, dtype=int) for x in (prefix, benign, attack)]
    all_ids = np.concatenate([prefix, benign, attack])
    if len(attack) == 0 or len(set(all_ids)) != len(all_ids):
        raise ValueError('Need attacks and disjoint unique query membership')
    # Within-label permutations are paired across all three scheduling rules.
    b, a = rng.permutation(benign), rng.permutation(attack)
    tail = np.concatenate([a[1:], b])
    random_order = np.concatenate([prefix, a[:1], rng.permutation(tail)])
    clustered = np.concatenate([prefix, a, b])
    length = len(a) + len(b)
    positions = np.floor(np.arange(len(a)) * length / len(a)).astype(int)
    interleaved = np.empty(length, dtype=int)
    mask = np.zeros(length, dtype=bool)
    mask[positions] = True
    interleaved[mask], interleaved[~mask] = a, b
    return dict(zip(ORDERS, (random_order, clustered, np.concatenate([prefix, interleaved]))))


def trace(matrix, order):
    order = np.asarray(order, dtype=int)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or not np.isfinite(matrix).all():
        raise ValueError('Nonfinite or nonsquare distance matrix')
    if len(order) < 1 or order.min() < 0 or order.max() >= len(matrix):
        raise ValueError('Invalid stream indices')
    growing = [int(order[0])]
    dg, distances, thresholds, ws, steps = [0.0], [], [0.0], [], []
    threshold = 0.0
    for step, idx in enumerate(order[1:], 2):
        d = float(np.min(matrix[idx, growing]))
        distances.append(d)
        if d > threshold:
            growing.append(int(idx))
            dg.append(d)
            threshold = max(threshold, float(np.mean(dg) - np.std(dg)))
        thresholds.append(threshold)
        if len(distances) > 100:
            values = base.trim_outliers_3sigma(np.asarray(distances, dtype=np.float64))
            # Frozen protocol length <= 5000: no stochastic Shapiro subsampling.
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                w = float(shapiro(values).statistic)
            if not np.isfinite(w):
                raise ValueError('Invalid Shapiro statistic')
            ws.append(w)
            steps.append(step)
    return {'growing': growing, 'distances': distances, 'thresholds': thresholds,
            'w': ws, 'w_steps': steps, 'score': float(1 - min([1.0] + ws))}


def first_alert(result, threshold):
    # Exactly the reference's strict W < delta comparison.
    return next((s for s, w in zip(result['w_steps'], result['w']) if w < 1 - threshold), None)


def alert(result, threshold):
    return first_alert(result, threshold) is not None


def project_seconds(elapsed, per_stream, remaining_streams, gate, safety=2.0):
    return elapsed + safety * per_stream * remaining_streams


def wilson(k, n):
    if n == 0:
        return None
    p, z = k / n, 1.959963984540054
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    half = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return [float(center - half), float(center + half)]


def write_csv(path, rows):
    with Path(path).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def draw_graphs(out, rows, differences, benign, threshold):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    ratios = sorted(set(r['attack_ratio'] for r in rows))
    for name in ORDERS:
        groups = [[r for r in rows if r['ordering'] == name and r['attack_ratio'] == ratio] for ratio in ratios]
        rates = [np.mean([r['alert'] for r in g]) for g in groups]
        axes[0].plot(ratios, rates, marker='o', label=name)
        axes[1].plot(ratios, [np.mean([r['score'] for r in g]) for g in groups], marker='o', label=name)
    axes[0].set(ylabel='Conditional detection rate', xlabel='Attack fraction', ylim=(-.03, 1.03))
    axes[1].axhline(threshold, color='black', linestyle='--', label='Benign P95')
    axes[1].set(ylabel='Mean maximum score (1 - min W)', xlabel='Attack fraction')
    axes[2].hist([r['score'] for r in benign], bins=20)
    axes[2].axvline(threshold, color='red', linestyle='--')
    axes[2].set(xlabel='Held-out benign maximum score', ylabel='Streams')
    axes[0].legend(); axes[1].legend(fontsize=8)
    fig.savefig(out / 'rates_scores_fpr.png', dpi=170)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    labels = [f'{a}/{b}' for a, b in itertools.combinations(ORDERS, 2)]
    for ax, metric, title in zip(axes, ['distance_mae', 'w_mae', 'growing_symmetric_difference'],
                                  ['Distance history MAE', 'Shapiro W trajectory MAE', 'Growing set symmetric difference']):
        groups = [[r[metric] for r in differences if f"{r['a']}/{r['b']}" == label] for label in labels]
        ax.boxplot(groups, tick_labels=labels, showfliers=False)
        ax.tick_params(axis='x', labelrotation=20)
        ax.set_title(title)
    fig.savefig(out / 'paired_differences.png', dpi=170)
    plt.close(fig)


def run(args):
    started = time.perf_counter()
    import psutil
    import torch
    import scipy
    import sentence_transformers
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(1)
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    if branch != 'experiment/stream-prada-order':
        raise RuntimeError('Wrong branch: experiment must remain isolated')
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    if cfg['stream_length'] > 5000 or cfg['stream_length'] <= 102 or cfg['benign_prefix'] < 102:
        raise ValueError('Invalid frozen protocol dimensions')
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite an existing run')
    args.output.mkdir(parents=True)
    out = args.output
    gate = cfg['resource_gate_seconds']
    def deadline():
        if time.perf_counter() - started >= gate:
            json_write(out / 'gate.json', {'status': 'blocked_elapsed_gate', 'elapsed_seconds': time.perf_counter()-started})
            raise RuntimeError(f'{gate}-second resource gate reached; approval required')
    reference = ROOT / 'PRADA/prada_stream_detector.py'
    ref_blob = subprocess.check_output(['git', 'hash-object', str(reference)], text=True).strip()
    if ref_blob != cfg['reference_blob']:
        raise ValueError('Reference blob drift')
    paths = [args.data_root / label / 'queries.jsonl' for label in ('normal', 'attacker')]
    hashes = [sha(p) for p in paths]
    if hashes != [cfg['normal_sha256'], cfg['attacker_sha256']]:
        raise ValueError('Dataset hash drift')
    model_path = args.model_root / cfg['model_revision']
    model_files = {str(p.relative_to(model_path)): sha(p) for p in sorted(model_path.rglob('*')) if p.is_file()}
    if not model_files or 'model.safetensors' not in model_files:
        raise ValueError('Missing frozen local model')
    parts, audit = protocol.make_partitions(*(protocol.read_rows(p) for p in paths), cfg['seed'])
    rng = np.random.default_rng(cfg['seed'] + 1)
    pools = {}
    for key, part, label in [('calibration', 'calibration', 'benign'), ('benign', 'test', 'benign'), ('attack', 'test', 'attack')]:
        source = parts[part][label]
        pools[key] = [source[i] for i in rng.permutation(len(source))[:cfg['pool_limit']]]
        if len(pools[key]) < cfg['stream_length']:
            raise ValueError('Insufficient unique actual queries')
    all_rows = sum(pools.values(), [])
    text_hashes = [hashlib.sha256(protocol.normalize(r['query']).encode()).hexdigest() for r in all_rows]
    ncal, nb = len(pools['calibration']), len(pools['benign'])
    matrix_estimate = 4*(ncal*ncal + (len(all_rows)-ncal)**2)
    available = psutil.virtual_memory().available
    if matrix_estimate * 4 > available:
        raise RuntimeError('Pairwise memory preflight failed')
    if not torch.cuda.is_available():
        raise RuntimeError('Frozen GPU encoding configuration requires CUDA')
    gpu_free, gpu_total = torch.cuda.mem_get_info()
    if gpu_free < 1024**3:
        raise RuntimeError('Less than 1 GiB free GPU memory')
    torch.cuda.reset_peak_memory_stats()
    os.environ['HF_HUB_OFFLINE'] = '1'
    model = SentenceTransformer(str(model_path), device='cuda', local_files_only=True)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    if model.max_seq_length != cfg['max_seq_length']:
        raise ValueError('Encoder maximum sequence length drift')
    embedding_start = time.perf_counter()
    with torch.inference_mode():
        embeddings = model.encode([r['query'] for r in all_rows], batch_size=cfg['embedding_batch_size'],
                                  normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True)
    embedding_seconds = time.perf_counter() - embedding_start
    if not np.isfinite(embeddings).all():
        raise ValueError('Invalid encoder output')
    norms = np.linalg.norm(embeddings, axis=1)
    if not np.allclose(norms, 1, atol=1e-5):
        raise ValueError('Embeddings are not normalized')
    # CPU float32 cdist matches reference precomputed mode; reuse values per cohort.
    tensors = [torch.from_numpy(embeddings[:ncal]), torch.from_numpy(embeddings[ncal:])]
    matrices = [torch.cdist(z, z).numpy() for z in tensors]
    cal_matrix, eval_matrix = matrices
    metadata = {'config': cfg, 'config_sha256': sha(args.config), 'branch': branch,
                'base_main': subprocess.check_output(['git', 'rev-parse', 'main'], text=True).strip(),
                'source_hashes': {str(p): h for p, h in zip(paths, hashes)}, 'model_files_sha256': model_files,
                'pool_query_sha256': {k: [hashlib.sha256(protocol.normalize(r['query']).encode()).hexdigest() for r in v] for k,v in pools.items()},
                'split_audit': audit, 'pool_sizes': {k: len(v) for k,v in pools.items()},
                'environment': {'python': sys.version, 'platform': platform.platform(), 'numpy': np.__version__,
                                'scipy': scipy.__version__, 'torch': torch.__version__, 'sentence_transformers': sentence_transformers.__version__,
                                'gpu': torch.cuda.get_device_name(), 'cuda': torch.version.cuda},
                'embedding_sha256': hashlib.sha256(embeddings.tobytes()).hexdigest(),
                'embedding_seconds': embedding_seconds, 'matrix_estimate_bytes': matrix_estimate,
                'available_ram_bytes': available, 'free_gpu_bytes_before': gpu_free,
                'source_files_sha256': source_file_hashes([Path(__file__), args.config, ROOT/'pilot/protocol.py', ROOT/'PRADA/prada_detector.py', reference]),
                'interpretation': 'Simulated offline schedules; fixed sets per ratio, conditional permutation uncertainty; no chronological API claims.'}
    json_write(out / 'metadata.json', metadata)
    # Real-embedding parity is a hard gate before calibration/evaluation.
    import prada_stream_detector as official
    official.np, official.torch, official.base.np = np, torch, np
    parity = []
    for seed in range(3):
        indices = np.random.default_rng(cfg['seed'] + seed).choice(len(tensors[1]), cfg['stream_length'], replace=False)
        actual = trace(eval_matrix, indices)
        expected = official.prada_stream_trace(embeddings[ncal:][indices], 'l2', 'cpu', .99, 100, 5000, 1, True, False, np.random.default_rng(0))
        error = float(np.max(np.abs(np.array(actual['w']) - expected[4])))
        if error > 2e-5 or len(actual['growing']) != expected[3] or first_alert(actual, .01) != (None if expected[1] < 0 else expected[1]):
            raise RuntimeError('Real-query reference parity failed')
        parity.append({'seed': seed, 'max_w_abs_error': error, 'growing_size': expected[3], 'alert_step': expected[1]})
    json_write(out / 'parity.json', parity)
    deadline()
    # All runs fully score after alarms; maximum score and trajectories remain comparable.
    cal_rng = np.random.default_rng(cfg['seed'] + 2)
    cal_scores = []
    timings = []
    for i in range(cfg['calibration_streams']):
        deadline()
        t = time.perf_counter()
        ids = cal_rng.choice(ncal, cfg['stream_length'], replace=False)
        cal_scores.append(trace(cal_matrix, ids)['score'])
        timings.append(time.perf_counter() - t)
        if i == 4:
            remaining = cfg['calibration_streams']-5 + cfg['benign_eval_streams'] + 3*len(cfg['attack_ratios'])*cfg['permutations']
            projected = project_seconds(time.perf_counter()-started, max(timings), remaining, gate, cfg['projection_safety_factor'])
            json_write(out/'gate.json', {'status': 'passed' if projected <= gate else 'blocked_projection', 'projected_total_seconds': projected,
                                       'gate_seconds': gate, 'elapsed_seconds': time.perf_counter()-started, 'benchmark_max_stream_seconds': max(timings)})
            if projected > gate:
                raise RuntimeError(f'Projected total exceeds {gate}-second gate; approval required')
    threshold = float(np.percentile(cal_scores, 95))
    json_write(out/'calibration.json', {'scores': cal_scores, 'p95_threshold': threshold, 'delta': 1-threshold})
    benign = []
    benign_rng = np.random.default_rng(cfg['seed'] + 3)
    for i in range(cfg['benign_eval_streams']):
        deadline()
        result = trace(eval_matrix, benign_rng.choice(nb, cfg['stream_length'], replace=False))
        benign.append({'stream': i, 'score': result['score'], 'alert': alert(result, threshold)})
    rows, differences, examples = [], [], {}
    for ri, ratio in enumerate(cfg['attack_ratios']):
        rng_set = np.random.default_rng(cfg['seed'] + 100 + ri)
        count = round(cfg['stream_length'] * ratio)
        b = rng_set.permutation(nb)[:cfg['stream_length']-count]
        a = nb + rng_set.permutation(len(pools['attack']))[:count]
        prefix, tail_b = b[:cfg['benign_prefix']], b[cfg['benign_prefix']:]
        if len(prefix) != cfg['benign_prefix']:
            raise ValueError('Attack ratio leaves insufficient prefix')
        seeds = np.random.SeedSequence([cfg['seed'], ri, 400]).spawn(cfg['permutations'])
        for permutation, seed in enumerate(seeds):
            deadline()
            orders = make_orders(prefix, tail_b, a, np.random.default_rng(seed))
            results = {}
            for name, order in orders.items():
                t = time.perf_counter()
                result = trace(eval_matrix, order)
                elapsed = time.perf_counter() - t
                results[name] = result
                first = first_alert(result, threshold)
                onset = cfg['benign_prefix'] + 1
                prealarm = first is not None and first < onset
                post = next((step for step,w in zip(result['w_steps'],result['w']) if step >= onset and w < 1-threshold), None)
                rows.append({'attack_ratio': count/cfg['stream_length'], 'requested_ratio': ratio, 'permutation': permutation,
                             'ordering': name, 'score': result['score'], 'min_w': 1-result['score'], 'alert': first is not None,
                             'first_alert': first, 'prefix_false_alarm': prealarm, 'post_onset_crossing': post,
                             'delay_queries': None if prealarm or first is None else first-onset,
                             'growing_size': len(result['growing']), 'distance_mean': float(np.mean(result['distances'])),
                             'distance_std': float(np.std(result['distances'])), 'runtime_seconds': elapsed,
                             'order_sha256': hashlib.sha256(order.astype('<i8').tobytes()).hexdigest()})
            for left, right in itertools.combinations(ORDERS, 2):
                x,y = results[left], results[right]
                differences.append({'attack_ratio': count/cfg['stream_length'], 'permutation': permutation, 'a': left, 'b': right,
                                    'changed_alert': alert(x,threshold) != alert(y,threshold), 'score_delta_b_minus_a': y['score']-x['score'],
                                    'growing_size_delta_b_minus_a': len(y['growing'])-len(x['growing']),
                                    'growing_symmetric_difference': len(set(x['growing']) ^ set(y['growing'])),
                                    'distance_mae': float(np.mean(np.abs(np.array(x['distances'])-y['distances']))),
                                    'w_mae': float(np.mean(np.abs(np.array(x['w'])-y['w'])))})
            if permutation == 0:
                examples[str(ratio)] = {k: {**v, 'query_indices': orders[k].tolist()} for k,v in results.items()}
            if permutation + 1 == cfg['pilot_permutations']:
                total_rows = len(rows)
                rate = max(timings + [r['runtime_seconds'] for r in rows])
                remaining = 3*len(cfg['attack_ratios'])*cfg['permutations'] - total_rows
                projected = project_seconds(time.perf_counter()-started, rate, remaining, gate, cfg['projection_safety_factor'])
                json_write(out/f'pilot_gate_ratio_{ratio}.json', {'pilot_permutations': permutation+1, 'projected_total_seconds': projected, 'gate_seconds': gate,
                                                              'status': 'passed' if projected <= gate else 'blocked_projection'})
                if projected > gate:
                    write_csv(out/'partial_stream_scores.csv', rows)
                    raise RuntimeError(f'Pilot projects beyond {gate}-second gate; approval required')
            if (permutation+1) % 100 == 0:
                print(f'ratio={ratio}: {permutation+1}/{cfg["permutations"]}, elapsed={time.perf_counter()-started:.1f}s', flush=True)
    write_csv(out/'stream_scores.csv', rows)
    write_csv(out/'paired_differences.csv', differences)
    write_csv(out/'benign_scores.csv', benign)
    json_write(out/'example_traces.json', examples)
    summary = {'threshold': threshold, 'held_out_benign': {'alerts': sum(r['alert'] for r in benign), 'streams': len(benign),
               'fpr': float(np.mean([r['alert'] for r in benign])), 'wilson95_conditional': wilson(sum(r['alert'] for r in benign), len(benign))},
               'detection': [], 'paired': [], 'caveats': ['Fixed query membership per ratio; permutations are not independent query cohorts.',
               'Benign streams reuse a held-out query pool: interval is conditional Monte Carlo uncertainty, not population FPR uncertainty.',
               'Delay is conditional on detected streams without prefix alarms; nondetections are right censored at stream end.',
               'Source grouping follows repository pilot protocol; no new detector, causal mechanism, or novelty claim.']}
    for ratio in sorted(set(r['attack_ratio'] for r in rows)):
        for name in ORDERS:
            rs = [r for r in rows if r['attack_ratio']==ratio and r['ordering']==name]
            detected = sum(r['alert'] for r in rs)
            delays = [r['delay_queries'] for r in rs if r['delay_queries'] is not None]
            summary['detection'].append({'attack_ratio':ratio, 'ordering':name,'alerts':detected,'streams':len(rs),
                    'rate':detected/len(rs),'wilson95_conditional':wilson(detected,len(rs)),
                    'prefix_false_alarms':sum(r['prefix_false_alarm'] for r in rs),
                    'mean_score':float(np.mean([r['score'] for r in rs])), 'mean_growing_size':float(np.mean([r['growing_size'] for r in rs])),
                    'detected_nonprefix':len(delays),'right_censored':sum(not r['alert'] for r in rs),
                    'median_delay_detected_queries':float(np.median(delays)) if delays else None})
        for a,b in itertools.combinations(ORDERS,2):
            ds=[r for r in differences if r['attack_ratio']==ratio and r['a']==a and r['b']==b]
            changed=sum(r['changed_alert'] for r in ds)
            delta=np.array([r['score_delta_b_minus_a'] for r in ds])
            summary['paired'].append({'attack_ratio':ratio,'a':a,'b':b,'changed_alerts':changed,'pairs':len(ds),
                  'changed_percent':100*changed/len(ds),'changed_wilson95_conditional':wilson(changed,len(ds)),
                  'mean_score_delta_b_minus_a':float(delta.mean()),
                  'score_delta_percentile95':np.quantile(delta,[.025,.975]).tolist(),
                  **{f'mean_{k}':float(np.mean([r[k] for r in ds])) for k in ('distance_mae','w_mae','growing_symmetric_difference','growing_size_delta_b_minus_a')}})
    draw_graphs(out,rows,differences,benign,threshold)
    metadata.update({'total_seconds':time.perf_counter()-started,'process_peak_working_set_bytes':psutil.Process().memory_info().peak_wset,
                     'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'gpu_peak_reserved_bytes':torch.cuda.max_memory_reserved(),
                     'status':'completed','stream_count':len(rows)})
    json_write(out/'metadata.json',metadata)
    json_write(out/'summary.json',summary)
    json_write(out/'artifact_hashes.json',{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='artifact_hashes.json'})
    print(json.dumps({'status':'completed','seconds':metadata['total_seconds'],'fpr':summary['held_out_benign'],'threshold':threshold}),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path(__file__).with_name('config.json'))
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--model-root',type=Path,default=Path.home()/'.cache/huggingface/hub/models--BAAI--bge-small-en-v1.5/snapshots')
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
