"""Calibrate each method and evaluate on shared windows and references."""
import numpy as np
import torch

from .kernels import mmd
from .sampling import draw, draw_reference_indices, mixed


def score(reference, window, sigmas, network):
    return mmd(reference, window, sigmas, network)


def repeated_score(pool, reference_indices, window, sigmas, network):
    return torch.stack([score(pool[index], window, sigmas, network) for index in reference_indices]).mean()




def evaluate(methods, benign_reference, benign_calibration, benign_test, attack_test,
             window_size, reference_repeats, calibration_windows, test_windows,
             calibration_rng, test_rng):
    results = []
    thresholds = {}
    calibration_results = []
    with torch.no_grad():
        # Reference queries come from training pool; calibration windows are separate.
        calibration = [(draw_reference_indices(benign_reference, window_size, reference_repeats, calibration_rng),
                        draw(benign_calibration, window_size, calibration_rng)) for _ in range(calibration_windows)]
        windows = [('benign', draw(benign_test, window_size, test_rng)) for _ in range(test_windows)]
        for ratio in (.05, .10):
            windows += [(f'mixed_{ratio:g}', mixed(benign_test, attack_test, window_size, ratio, test_rng)) for _ in range(test_windows)]
        refs = [draw_reference_indices(benign_reference, window_size, reference_repeats, test_rng) for _ in windows]
        for method, (bandwidths, model) in methods.items():
            print(f'Evaluating {method}: calibration ({reference_repeats} references/window)', flush=True)
            cal = [repeated_score(benign_reference, indices, w, bandwidths, model).item() for indices, w in calibration]
            threshold = float(np.quantile(cal, .95))
            thresholds[method] = threshold
            calibration_results.extend({'method': method, 'window_id': i, 'score': value,
                                        'threshold': threshold} for i, value in enumerate(cal))
            for i, ((label, window), indices) in enumerate(zip(windows, refs)):
                if i % 50 == 0:
                    print(f'{method}: test window {i}/{len(windows)}', flush=True)
                value = repeated_score(benign_reference, indices, window, bandwidths, model).item()
                results.append({'method': method, 'split': label, 'window_id': i, 'score': value, 'threshold': threshold, 'detected': int(value > threshold)})
    return results, calibration_results, thresholds
