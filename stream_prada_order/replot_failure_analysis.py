"""Regenerate Phase A figures from saved diagnostics without BGE/PRADA replay."""
import argparse
import csv
import gzip
import json
from pathlib import Path

import failure_analysis as fa


def main(args):
    fa.require(not args.output.exists(),'Refusing to overwrite plot directory')
    manifest=json.loads((args.diagnostics/'artifact_hashes.json').read_text())
    for name,h in manifest.items():
        fa.require(fa.sha(args.diagnostics/name)==h,f'Input artifact mismatch: {name}')
    analysis=json.loads((args.diagnostics/'analysis.json').read_text())
    with (args.diagnostics/'stream_source_features.csv').open(encoding='utf-8') as f:
        stream_rows=list(csv.DictReader(f))
    for row in stream_rows:
        row['score']=float(row['score'])
    traces={k:json.loads(gzip.decompress((args.diagnostics/f'{k}_replay_traces.json.gz').read_bytes()))
            for k in ('calibration','benign')}
    with (args.diagnostics/'horizon_diagnostics.csv').open(encoding='utf-8') as f:
        horizons=list(csv.DictReader(f))
    for row in horizons:
        row['horizon']=int(row['horizon'])
        row['mean_kept_shapiro_samples']=float(row['mean_kept_shapiro_samples']) if row['mean_kept_shapiro_samples'] else None
    with (args.diagnostics/'marginal_cumulative.csv').open(encoding='utf-8') as f:
        marginal=list(csv.DictReader(f))
    for row in marginal:
        row['query']=int(row['query'])
        row['marginal_rate']=float(row['marginal_rate'])
        row['cumulative_rate']=float(row['cumulative_rate'])
    args.output.mkdir(parents=True)
    fa.diagnostic_plots(args.output,analysis,stream_rows,traces,horizons,marginal)
    for name in ('score_distributions_composition.png','benign_timing_length.png','prefix_confounding.png'):
        fa.require(fa.sha(args.output/name)==manifest[name],f'Rendered plot differs: {name}')
    print('All three plots reproduced byte-for-byte; no encoder/detector execution')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diagnostics',type=Path,default=fa.ROOT/'stream_prada_order/diagnostics/phase_a')
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
