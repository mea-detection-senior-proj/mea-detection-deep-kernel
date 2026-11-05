"""Render a blocked resource assessment from existing evidence without rerunning."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(path):
    gate = json.loads((path / 'gate.json').read_text(encoding='utf-8'))
    parity = json.loads((path / 'parity.json').read_text(encoding='utf-8'))
    if gate['status'] != 'blocked_projection' or (path / 'calibration.json').exists():
        raise ValueError('This helper supports the initial five-stream projection stop only')
    assessment = {
        'status': 'blocked_resource_projection', 'gate': gate,
        'completed_real_query_parity_streams': len(parity),
        'calibration_streams_executed': 5, 'calibration_scores_persisted': False,
        'threshold': None, 'detection_rates': None, 'held_out_benign_fpr': None,
        'alert_changes': None, 'detection_delays': None, 'peak_ram_bytes': None,
        'peak_gpu_bytes': None,
        'note': 'Stopped before completing calibration or any mixed-order/benign evaluation. '
                'Null means unmeasured. No statistical outcome is inferred from preflight parity checks.'}
    (path / 'assessment.json').write_text(json.dumps(assessment, indent=2), encoding='utf-8')
    fig, ax = plt.subplots(figsize=(7, 3), constrained_layout=True)
    ax.barh(['Elapsed to gate', 'Projected full run (2x safety)'],
            [gate['elapsed_seconds']/60, gate['projected_total_seconds']/60],
            color=['#377eb8', '#e68632'])
    ax.axvline(gate['gate_seconds']/60, color='#b2182b', linestyle='--', label='20-minute limit')
    ax.set(xlabel='Minutes', title='Resource gate: stopped before outcome evaluation', xlim=(0, 24))
    ax.legend()
    fig.savefig(path / 'resource_gate.png', dpi=170)
    plt.close(fig)
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(path.iterdir()) if p.is_file() and p.name != 'artifact_hashes.json'}
    (path / 'artifact_hashes.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    main(parser.parse_args().results)
