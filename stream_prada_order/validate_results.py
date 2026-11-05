"""Validate evidence and paired schedules; optionally package CSVs losslessly.

No encoder is loaded and no detector experiment is rerun by this command.
"""
import argparse
import csv
import gzip
import hashlib
import io
import itertools
import json
from pathlib import Path

import numpy as np
import experiment as exp


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_artifact(path):
    if path.exists():
        return path.read_bytes()
    return gzip.decompress(path.with_suffix(path.suffix + '.gz').read_bytes())


def table(path):
    return list(csv.DictReader(io.StringIO(read_artifact(path).decode('utf-8'))))


def flag(value):
    require(value in ('True', 'False'), 'Malformed Boolean')
    return value == 'True'


def same(a, b, label):
    require(np.allclose(a, b, rtol=0, atol=1e-12), label)


def validate(path, pack=False):
    manifest = json.loads((path / 'artifact_hashes.json').read_text(encoding='utf-8'))
    for name, expected in manifest.items():
        data = read_artifact(path / name)
        require(hashlib.sha256(data).hexdigest() == expected, f'Artifact hash mismatch: {name}')
    metadata = json.loads((path / 'metadata.json').read_text(encoding='utf-8'))
    cfg = metadata['config']
    require(metadata['status'] == 'completed', 'Not a completed experiment')
    require(metadata['branch'] == 'experiment/stream-prada-order', 'Wrong evidence branch')
    for name, expected in metadata['source_files_sha256'].items():
        require(exp.sha(exp.ROOT / name) == expected, f'Executed source drift: {name}')
    for name in ('cross_partition_id_collisions', 'cross_partition_normalized_text_collisions',
                 'cross_partition_attack_context_collisions'):
        require(metadata['split_audit'][name] == 0, 'Split audit failure')
    pools = metadata['pool_query_sha256']
    require(not (set(pools['calibration']) & (set(pools['benign']) | set(pools['attack']))),
            'Calibration text leakage')
    require(not (set(pools['benign']) & set(pools['attack'])), 'Cross-label text collision')
    calibration = json.loads((path / 'calibration.json').read_text())
    threshold = calibration['p95_threshold']
    same(threshold, np.percentile(calibration['scores'], 95), 'P95 mismatch')
    same(calibration['delta'], 1-threshold, 'Delta mismatch')
    require(len(calibration['scores']) == cfg['calibration_streams'], 'Incomplete calibration')
    for name in ['gate.json'] + [f'pilot_gate_ratio_{ratio}.json' for ratio in cfg['attack_ratios']]:
        gate = json.loads((path / name).read_text())
        require(gate['status'] == 'passed' and gate['gate_seconds'] == cfg['resource_gate_seconds']
                and gate['projected_total_seconds'] <= gate['gate_seconds'], f'Failed gate: {name}')
    require(metadata['total_seconds'] < cfg['resource_gate_seconds'], 'Elapsed budget exceeded')
    rows = table(path / 'stream_scores.csv')
    paired = table(path / 'paired_differences.csv')
    benign = table(path / 'benign_scores.csv')
    summary = json.loads((path / 'summary.json').read_text())
    n = cfg['permutations']
    expected_count = len(cfg['attack_ratios']) * 3 * n
    require(len(rows) == expected_count == metadata['stream_count'], 'Incomplete evaluation')
    require(len(paired) == expected_count, 'Incomplete paired differences')
    require(len(benign) == cfg['benign_eval_streams'], 'Incomplete benign evaluation')
    index = {(float(r['requested_ratio']), int(r['permutation']), r['ordering']): r for r in rows}
    require(len(index) == len(rows), 'Duplicate schedule key')
    nb = metadata['pool_sizes']['benign']
    onset = cfg['benign_prefix'] + 1
    for ri, ratio in enumerate(cfg['attack_ratios']):
        rng = np.random.default_rng(cfg['seed'] + 100 + ri)
        count = round(cfg['stream_length'] * ratio)
        b = rng.permutation(nb)[:cfg['stream_length']-count]
        a = nb + rng.permutation(metadata['pool_sizes']['attack'])[:count]
        prefix, tail = b[:cfg['benign_prefix']], b[cfg['benign_prefix']:]
        seeds = np.random.SeedSequence([cfg['seed'], ri, 400]).spawn(n)
        for permutation, seed in enumerate(seeds):
            orders = exp.make_orders(prefix, tail, a, np.random.default_rng(seed))
            for name, order in orders.items():
                row = index[(ratio, permutation, name)]
                require(row['order_sha256'] == hashlib.sha256(order.astype('<i8').tobytes()).hexdigest(),
                        'Schedule reconstruction mismatch')
                require(np.array_equal(order[:cfg['benign_prefix']], prefix), 'Changed prefix')
                require(order[onset-1] >= nb and int(np.sum(order >= nb)) == count, 'Attack onset/count mismatch')
                require(set(order) == set(np.concatenate([b, a])), 'Changed membership')
                same(float(row['attack_ratio']), count/cfg['stream_length'], 'Effective fraction mismatch')
                same(float(row['min_w']), 1-float(row['score']), 'Score-W mismatch')
                has_alert = flag(row['alert'])
                require(has_alert == bool(row['first_alert']), 'First alert mismatch')
                if has_alert:
                    first = int(row['first_alert'])
                    require(102 <= first <= cfg['stream_length'], 'Warmup/end violation')
                    require(float(row['min_w']) < 1-threshold, 'Strict alert threshold violation')
                    require(flag(row['prefix_false_alarm']) == (first < onset), 'Prefix alarm mismatch')
                else:
                    require(float(row['min_w']) >= 1-threshold, 'Missed strict threshold crossing')
                expected_delay = '' if not has_alert or flag(row['prefix_false_alarm']) else str(int(row['first_alert'])-onset)
                require(row['delay_queries'] == expected_delay, 'Incorrect/censored delay')
    for row in paired:
        ratio = next(r for r in cfg['attack_ratios'] if round(cfg['stream_length']*r)/cfg['stream_length'] == float(row['attack_ratio']))
        x, y = (index[(ratio, int(row['permutation']), row[name])] for name in ('a', 'b'))
        require(flag(row['changed_alert']) == (flag(x['alert']) != flag(y['alert'])), 'Paired alert mismatch')
        same(float(row['score_delta_b_minus_a']), float(y['score'])-float(x['score']), 'Paired score mismatch')
        require(int(row['growing_size_delta_b_minus_a']) == int(y['growing_size'])-int(x['growing_size']), 'Growth delta mismatch')
    require(len({(float(r['attack_ratio']),int(r['permutation']),r['a'],r['b']) for r in paired}) == len(paired), 'Duplicate pairs')
    same(summary['threshold'], threshold, 'Summary threshold mismatch')
    fp = sum(flag(r['alert']) for r in benign)
    for row in benign:
        require(flag(row['alert']) == (1-float(row['score']) < 1-threshold), 'Benign threshold mismatch')
    require(summary['held_out_benign']['alerts'] == fp, 'Benign count mismatch')
    same(summary['held_out_benign']['fpr'], fp/len(benign), 'FPR mismatch')
    same(summary['held_out_benign']['wilson95_conditional'], exp.wilson(fp,len(benign)), 'FPR interval mismatch')
    for group in summary['detection']:
        rs = [r for r in rows if float(r['attack_ratio']) == group['attack_ratio'] and r['ordering'] == group['ordering']]
        k = sum(flag(r['alert']) for r in rs)
        require(group['streams'] == len(rs) == n and group['alerts'] == k, 'Summary detection counts')
        same(group['rate'], k/n, 'Summary rate mismatch')
        same(group['wilson95_conditional'], exp.wilson(k,n), 'Detection interval mismatch')
        same(group['mean_score'], np.mean([float(r['score']) for r in rs]), 'Mean score mismatch')
        same(group['mean_growing_size'], np.mean([int(r['growing_size']) for r in rs]), 'Mean growth mismatch')
        delays = [int(r['delay_queries']) for r in rs if r['delay_queries']]
        require(group['detected_nonprefix'] == len(delays), 'Delay denominator mismatch')
        require(group['right_censored'] == len(rs)-k, 'Censor denominator mismatch')
        require(group['prefix_false_alarms'] == sum(flag(r['prefix_false_alarm']) for r in rs), 'Prefix false alarm count')
        if delays:
            same(group['median_delay_detected_queries'], np.median(delays), 'Median delay mismatch')
        else:
            require(group['median_delay_detected_queries'] is None, 'Unmeasured delay must be null')
    for group in summary['paired']:
        ds = [r for r in paired if float(r['attack_ratio'])==group['attack_ratio'] and r['a']==group['a'] and r['b']==group['b']]
        changed = sum(flag(r['changed_alert']) for r in ds)
        require(group['pairs'] == len(ds) == n and group['changed_alerts'] == changed, 'Changed-alert counts')
        same(group['changed_percent'],100*changed/n,'Changed percentage mismatch')
        same(group['changed_wilson95_conditional'],exp.wilson(changed,n),'Changed interval mismatch')
        for key in ('distance_mae','w_mae','growing_symmetric_difference','growing_size_delta_b_minus_a'):
            same(group['mean_'+key],np.mean([float(r[key]) for r in ds]),'Paired mean mismatch')
    examples = json.loads((path / 'example_traces.json').read_text())
    for ratio, traces in examples.items():
        for name,result in traces.items():
            row = index[(float(ratio),0,name)]
            require(len(result['distances']) == cfg['stream_length']-1, 'History length')
            require(result['w_steps'] == list(range(102,cfg['stream_length']+1)), 'W test schedule')
            same(result['score'],float(row['score']),'Example score mismatch')
            require(exp.alert(result,threshold)==flag(row['alert']),'Example alert mismatch')
        for a,b in itertools.combinations(exp.ORDERS,2):
            x,y=traces[a],traces[b]
            pair=next(r for r in paired if float(r['attack_ratio'])==float(index[(float(ratio),0,a)]['attack_ratio'])
                      and r['permutation']=='0' and r['a']==a and r['b']==b)
            same(float(pair['distance_mae']),np.mean(np.abs(np.array(x['distances'])-y['distances'])),'History MAE mismatch')
            same(float(pair['w_mae']),np.mean(np.abs(np.array(x['w'])-y['w'])),'W MAE mismatch')
            require(int(pair['growing_symmetric_difference'])==len(set(x['growing'])^set(y['growing'])),'Growing membership mismatch')
    archives = {}
    if pack:
        for name in manifest:
            if name.endswith('.csv'):
                data = read_artifact(path / name)
                packed = gzip.compress(data, mtime=0)
                destination = path / (name + '.gz')
                require(not destination.exists() or destination.read_bytes()==packed, 'Refusing to overwrite different archive')
                destination.write_bytes(packed)
                require(gzip.decompress(packed)==data,'Lossless archive roundtrip failed')
                archives[destination.name] = {'sha256':hashlib.sha256(packed).hexdigest(),
                    'uncompressed_name':name,'uncompressed_sha256':hashlib.sha256(data).hexdigest(),
                    'bytes':len(packed),'uncompressed_bytes':len(data)}
        exp.json_write(path / 'archives.json', archives)
    elif (path / 'archives.json').exists():
        archives=json.loads((path / 'archives.json').read_text())
        for name,info in archives.items():
            packed=(path/name).read_bytes()
            require(hashlib.sha256(packed).hexdigest()==info['sha256'],'Archive hash mismatch')
            require(hashlib.sha256(gzip.decompress(packed)).hexdigest()==info['uncompressed_sha256'],'Archive content mismatch')
    report={'status':'passed','stream_rows':len(rows),'paired_rows':len(paired),'benign_streams':len(benign),
            'calibration_streams':len(calibration['scores']),'schedule_hashes_reconstructed':len(rows),
            'artifact_hashes_verified':len(manifest),'source_hashes_verified':len(metadata['source_files_sha256']),
            'archives_verified':len(archives),'note':'Audit of saved evidence; no new queries or detector runs.'}
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    parser.add_argument('--pack',action='store_true')
    parser.add_argument('--audit-output',type=Path)
    args=parser.parse_args()
    report=validate(args.results,args.pack)
    if args.audit_output:
        require(not args.audit_output.exists(),'Refusing to overwrite audit')
        exp.json_write(args.audit_output,report)
