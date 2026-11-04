"""Serialization of selected frozen detector state."""
import torch

from .kernels.deep import DeepKernelMMD
from mea_detection.identity import code_identity


def save_detector(path, model, config, lock_id, base_bandwidth):
    torch.save({"format": "mea-detection-deep-v1", "code": code_identity()["pipeline_source_sha256"],
                "state_dict": model.state_dict(), "input_dim": model.network[0].in_features,
                "config": config, "initial_base_bandwidth": base_bandwidth, "lock_id": lock_id}, path)


def load_detector(checkpoint_path, device="cpu", expected_lock_id=None):
    """Replay a compatible selected state; historical checkpoints are not rewritten."""
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if checkpoint.get("format") != "mea-detection-deep-v1" or checkpoint.get("code") != code_identity()["pipeline_source_sha256"]:
        raise ValueError("Incompatible checkpoint source identity; create a new run")
    if expected_lock_id is not None and checkpoint["lock_id"] != expected_lock_id:
        raise ValueError("Checkpoint protocol lock differs")
    config = checkpoint["config"]
    model = DeepKernelMMD(checkpoint["input_dim"], checkpoint["initial_base_bandwidth"],
                          config["hidden_dim"], config["feature_dim"])
    model.to(device=device, dtype=checkpoint["state_dict"]["log_base_bandwidth"].dtype)
    model.load_state_dict(checkpoint["state_dict"])
    return model.eval().requires_grad_(False)
