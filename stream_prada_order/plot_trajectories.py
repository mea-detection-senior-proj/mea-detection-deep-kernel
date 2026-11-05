"""Render descriptive trajectories of the preselected permutation-zero examples."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main(path):
    metadata = json.loads((path / 'metadata.json').read_text(encoding='utf-8'))
    examples = json.loads((path / 'example_traces.json').read_text())
    calibration = json.loads((path / 'calibration.json').read_text())
    cfg = metadata['config']
    fig, axes = plt.subplots(len(examples), 3, figsize=(14, 9), constrained_layout=True)
    for i, (ratio, traces) in enumerate(examples.items()):
        for name, trace in traces.items():
            axes[i, 0].plot(np.arange(2, cfg['stream_length']+1), trace['distances'], label=name, alpha=.8, linewidth=.9)
            axes[i, 1].plot(trace['w_steps'], trace['w'], label=name)
            members = set(trace['growing'])
            sizes = np.cumsum([idx in members for idx in trace['query_indices']])
            axes[i, 2].plot(np.arange(1, cfg['stream_length']+1), sizes, label=name)
        axes[i, 1].axhline(calibration['delta'], linestyle='--', color='black', label='Common W threshold')
        for j, ylabel in enumerate(['Minimum L2 distance', 'Shapiro-Wilk W', 'Growing set size']):
            axes[i, j].axvline(cfg['benign_prefix']+1, linestyle=':', color='gray')
            axes[i, j].set(xlabel='Query index', ylabel=ylabel, title=f'Requested attack ratio {float(ratio):.0%}')
    axes[0, 1].legend(fontsize=8)
    fig.suptitle('Permutation 0 examples, selected before outcomes; dotted line = common attack onset')
    fig.savefig(path / 'example_trajectories.png', dpi=170)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    main(parser.parse_args().results)
