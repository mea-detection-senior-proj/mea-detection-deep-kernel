"""Compatibility entry point; implementation lives in pilot.deep_mmd."""
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pilot.deep_mmd.cli import main
from pilot.deep_mmd.sampling import draw, draw_reference_indices, mixed, training_pair
from pilot.deep_mmd.kernels import mmd
from pilot.deep_mmd.evaluation import score, repeated_score
from pilot.deep_mmd.training import standardized_mmd, fit_kernel

if __name__ == '__main__':
    main()
