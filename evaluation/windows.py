"""Evaluate every method on identical windows and reference draws."""
import numpy as np
import torch


def evaluate(methods, embeddings, calibration, test, target_fpr):
    calibration_rows, rows, thresholds = [], [], {}
    for name, detector in methods.items():
        def score(window):
            indices = torch.as_tensor(window.indices, device=embeddings.device)
            refs = torch.as_tensor(window.references, device=embeddings.device)
            return detector.score(embeddings, embeddings[indices], refs)

        null = np.asarray([score(window) for window in calibration])
        threshold = float(np.quantile(null, 1 - target_fpr, method="higher"))
        thresholds[name] = threshold
        calibration_rows.extend({"method": name, "window_id": i, "score": float(value), "threshold": threshold}
                                for i, value in enumerate(null))
        for i, window in enumerate(test):
            value = score(window)
            rows.append({"method": name, "split": window.split, "window_id": i,
                         "window_size": len(window.indices), "requested_ratio": window.requested_ratio,
                         "attacker_count": window.attacker_count,
                         "actual_ratio": window.attacker_count / len(window.indices),
                         "score": value, "threshold": threshold,
                         "p_value": float((1 + np.sum(null >= value)) / (len(null) + 1)),
                         "suspicious": int(value > threshold)})
    summary = []
    for method in methods:
        for split in dict.fromkeys(row["split"] for row in rows):
            selected = [r for r in rows if r["method"] == method and r["split"] == split]
            summary.append({"method": method, "split": split, "windows": len(selected),
                            "alerts": sum(r["suspicious"] for r in selected),
                            "detection_rate": float(np.mean([r["suspicious"] for r in selected]))})
    return rows, calibration_rows, summary, thresholds
