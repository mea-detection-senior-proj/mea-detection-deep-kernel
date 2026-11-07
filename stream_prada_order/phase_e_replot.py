"""Regenerate Phase E figures using published numeric artifacts only."""
import argparse
import json
from pathlib import Path
import time

import phase_e_audit as audit
from phase_e_plots import plots


def main(results,output):
    e=audit.e; e.d.require(not output.exists(),'Refusing to overwrite figures')
    started=time.perf_counter(); verified=audit.audit(results)
    meta=json.loads((results/'metadata.json').read_text(encoding='utf-8')); cfg=meta['config']
    records=audit.read_gz(e.ROOT/cfg['phase_d_run']/'development_traces.json.gz')
    features=audit.read_gz(results/'query_metadata.json.gz'); growth=audit.read_gz(results/'growth_paths.json.gz')
    fit=json.loads((results/'fit_parameters.json').read_text(encoding='utf-8'))
    summary=audit.read_gz(results/'summary.json.gz'); assoc=json.loads((results/'associations.json').read_text(encoding='utf-8'))
    output.mkdir(parents=True)
    plots(output,records,features,growth,fit,cfg,summary,assoc)
    hashes={p.name:e.fb.sha(p) for p in output.glob('*.png')}
    e.d.write(output/'provenance.json',{'source_sha256':e.fb.sha(__file__),'plot_source_sha256':e.fb.sha(e.HERE/'phase_e_plots.py'),
        'input_artifact_manifest_sha256':e.fb.sha(results/'artifact_hashes.json'),'seconds':time.perf_counter()-started,
        'raw_queries_required':False,'encoder_runs':0,'audit_status':verified['status'],
        'matches_original_bytes':{name:h==e.fb.sha(results/name) for name,h in hashes.items()}})
    e.d.write(output/'artifact_hashes.json',{p.name:e.fb.sha(p) for p in output.iterdir() if p.is_file()})
    print(json.dumps({'figures':hashes,'original_bytes_match':all(h==e.fb.sha(results/name) for name,h in hashes.items())},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); main(args.results,args.output)
