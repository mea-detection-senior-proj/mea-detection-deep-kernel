"""Fit and freeze a kernel using fixed validation windows."""
import copy

import torch

from .sampling import training_pair
from .evaluation import score


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


