#!/usr/bin/env python3
"""Sensitivity study for MMD calibration/reference-pool contamination."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from MMD_detection import mmd_detector_gpu as mmd  # noqa: E402


def parse_ratio_list(text: str) -> list[float]:
    ratios = [float(item.strip()) for item in text.split(",") if item.strip()]
    for ratio in ratios:
        if not 0.0 <= ratio < 1.0:
            raise ValueError("contamination ratios must be in [0, 1)")
    return ratios


def parse_mixed_ratio_list(text: str) -> list[float]:
    ratios = [float(item.strip()) for item in text.split(",") if item.strip()]
    for ratio in ratios:
        if not 0.0 < ratio < 1.0:
            raise ValueError("mixed attacker ratios must be in (0, 1)")
    return ratios


def rate(metrics_by_split: dict, split: str) -> float:
    try:
        return float(metrics_by_split[split]["detection_rate"])
    except Exception:
        return float("nan")


def pct(value: float) -> float:
    return value * 100.0 if not math.isnan(value) else float("nan")


def make_contaminated_reference(
    clean_reference,
    attacker_reference,
    contamination_ratio: float,
    rng: np.random.Generator,
):
    pool_size = len(clean_reference)
    attacker_count = int(round(pool_size * contamination_ratio))
    attacker_count = min(attacker_count, pool_size)
    benign_count = pool_size - attacker_count

    benign_part = mmd.sample_batch(clean_reference, benign_count, rng) if benign_count else clean_reference[:0]
    attacker_part = (
        mmd.sample_batch(attacker_reference, attacker_count, rng)
        if attacker_count
        else attacker_reference[:0]
    )
    if mmd.torch is not None and mmd.torch.is_tensor(clean_reference):
        contaminated = mmd.torch.cat([benign_part, attacker_part], dim=0)
        perm = mmd.torch.as_tensor(
            rng.permutation(len(contaminated)),
            dtype=mmd.torch.long,
            device=contaminated.device,
        )
        contaminated = contaminated[perm]
    else:
        contaminated = np.concatenate([benign_part, attacker_part], axis=0)
        contaminated = contaminated[rng.permutation(len(contaminated))]
    return contaminated, benign_count, attacker_count


def evaluate_for_reference(
    z_reference,
    z_clean_reference,
    z_benign_test,
    z_attacker,
    args: argparse.Namespace,
    mixed_ratios: list[float],
    rng: np.random.Generator,
) -> tuple[list[mmd.BatchScore], dict]:
    sigma = mmd.median_bandwidth(z_reference, args.bandwidth_sample_size, rng)
    sigmas = [0.5 * sigma, sigma, 2.0 * sigma, 4.0 * sigma] if args.multi_kernel else [sigma]
    null_scores = mmd.build_null_distribution(
        z_b=z_reference,
        batch_size=args.batch_size,
        null_samples=args.null_samples,
        sigmas=sigmas,
        rng=rng,
    )
    threshold = float(np.percentile(null_scores, args.threshold_percentile))

    results: list[mmd.BatchScore] = []
    if args.benign_eval_batches > 0:
        results.extend(
            mmd.evaluate_random_stream(
                split="heldout_benign",
                label=0,
                z_stream=z_benign_test,
                z_b=z_reference,
                batch_size=args.batch_size,
                num_batches=args.benign_eval_batches,
                reference_repeats=args.reference_repeats,
                sigmas=sigmas,
                null_scores=null_scores,
                threshold=threshold,
                rng=rng,
            )
        )
    else:
        results.extend(
            mmd.evaluate_stream(
                split="heldout_benign",
                label=0,
                z_stream=z_benign_test,
                z_b=z_reference,
                batch_size=args.batch_size,
                drop_last=not args.keep_last_batch,
                reference_repeats=args.reference_repeats,
                sigmas=sigmas,
                null_scores=null_scores,
                threshold=threshold,
                rng=rng,
            )
        )

    if args.attacker_eval_batches > 0:
        results.extend(
            mmd.evaluate_random_stream(
                split="attacker",
                label=1,
                z_stream=z_attacker,
                z_b=z_reference,
                batch_size=args.batch_size,
                num_batches=args.attacker_eval_batches,
                reference_repeats=args.reference_repeats,
                sigmas=sigmas,
                null_scores=null_scores,
                threshold=threshold,
                rng=rng,
            )
        )
    else:
        results.extend(
            mmd.evaluate_stream(
                split="attacker",
                label=1,
                z_stream=z_attacker,
                z_b=z_reference,
                batch_size=args.batch_size,
                drop_last=not args.keep_last_batch,
                reference_repeats=args.reference_repeats,
                sigmas=sigmas,
                null_scores=null_scores,
                threshold=threshold,
                rng=rng,
            )
        )

    if mixed_ratios:
        results.extend(
            mmd.evaluate_mixed_stream(
                z_benign_stream=z_benign_test,
                z_attacker_stream=z_attacker,
                z_b=z_reference,
                batch_size=args.batch_size,
                attacker_ratios=mixed_ratios,
                batches_per_ratio=args.mixed_batches_per_ratio,
                reference_repeats=args.reference_repeats,
                sigmas=sigmas,
                null_scores=null_scores,
                threshold=threshold,
                rng=rng,
            )
        )

    clean_sigma = mmd.median_bandwidth(z_clean_reference, args.bandwidth_sample_size, rng)
    extra = {
        "threshold": threshold,
        "median_bandwidth": sigma,
        "clean_reference_median_bandwidth_probe": clean_sigma,
        "sigmas": sigmas,
        "null_score_mean": float(np.mean(null_scores)),
        "null_score_std": float(np.std(null_scores)),
        "null_score_min": float(np.min(null_scores)),
        "null_score_max": float(np.max(null_scores)),
    }
    return results, extra


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inject attacker queries into the MMD calibration pool and recompute thresholds."
    )
    parser.add_argument("--dataset", default="model_leeching")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--normal-source",
        choices=["dataset", "global"],
        default="dataset",
        help="Use the dataset normal split or the global benign pool.",
    )
    parser.add_argument("--global-normal-path", type=Path, default=Path("data/global_normal/queries.jsonl"))
    parser.add_argument("--normal-path", type=Path, default=None)
    parser.add_argument("--attacker-path", type=Path, default=None)
    parser.add_argument("--text-field", default="query")
    parser.add_argument("--embedding-model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--query-prefix", default="")
    parser.add_argument("--no-normalize-embeddings", action="store_true")
    parser.add_argument("--device", default=None)
    parser.add_argument(
        "--mmd-device",
        default=None,
        help="PyTorch device for MMD computation. Defaults to cuda when available, otherwise cpu.",
    )
    parser.add_argument(
        "--mmd-dtype",
        choices=["float32", "float64"],
        default="float32",
        help="Tensor dtype for GPU MMD computation.",
    )
    parser.add_argument("--encode-batch-size", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=1500)
    parser.add_argument("--reference-repeats", type=int, default=20)
    parser.add_argument("--null-samples", type=int, default=1000)
    parser.add_argument("--threshold-percentile", type=float, default=95.0)
    parser.add_argument("--normal-train-ratio", type=float, default=0.8)
    parser.add_argument("--bandwidth-sample-size", type=int, default=2000)
    parser.add_argument("--multi-kernel", action="store_true")
    parser.add_argument("--max-normal", type=int, default=None)
    parser.add_argument("--max-attacker", type=int, default=None)
    parser.add_argument("--contamination-ratios", default="0,0.01,0.05,0.1")
    parser.add_argument("--mixed-attacker-ratios", default="0.05,0.1")
    parser.add_argument("--mixed-batches-per-ratio", type=int, default=50)
    parser.add_argument("--benign-eval-batches", type=int, default=50)
    parser.add_argument("--attacker-eval-batches", type=int, default=50)
    parser.add_argument("--keep-last-batch", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cache-dir", type=Path, default=Path("review_experiment/cache/mmd_embeddings"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("review_experiment/calibration_contamination/outputs"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mmd.np = np
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("Missing dependency: torch. Install PyTorch to run the GPU MMD experiment.") from exc
    mmd.torch = torch

    if args.mmd_device is None:
        mmd_device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        mmd_device = args.mmd_device
    if str(mmd_device).startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(
            f"Requested --mmd-device {mmd_device}, but torch.cuda.is_available() is False"
        )
    mmd_dtype = torch.float64 if args.mmd_dtype == "float64" else torch.float32

    if not 0.0 < args.normal_train_ratio < 1.0:
        raise ValueError("--normal-train-ratio must be between 0 and 1")
    if args.batch_size < 2:
        raise ValueError("--batch-size must be at least 2")

    random.seed(args.seed)
    base_rng = np.random.default_rng(args.seed)

    resolved_dataset = args.dataset
    if args.normal_path is None and args.attacker_path is None and args.normal_source == "dataset":
        normal_path, attacker_path, resolved_dataset = mmd.default_dataset_paths(args.data_root, args.dataset)
    else:
        if args.attacker_path is not None:
            attacker_path = args.attacker_path
        else:
            attacker_path, resolved_dataset = mmd.default_attacker_path(args.data_root, args.dataset)
        if args.normal_path is not None:
            normal_path = args.normal_path
        elif args.normal_source == "global":
            normal_path = args.global_normal_path
        else:
            normal_path = args.data_root / resolved_dataset / "normal" / "queries.jsonl"
        if not normal_path.exists():
            raise FileNotFoundError(
                f"Missing normal queries: {normal_path}. Use --normal-source global for attacker-only datasets."
            )

    contamination_ratios = parse_ratio_list(args.contamination_ratios)
    mixed_ratios = parse_mixed_ratio_list(args.mixed_attacker_ratios)

    normal_queries = mmd.read_jsonl_queries(normal_path, args.text_field, args.max_normal)
    attacker_queries = mmd.read_jsonl_queries(attacker_path, args.text_field, args.max_attacker)
    base_rng.shuffle(normal_queries)
    base_rng.shuffle(attacker_queries)

    split_at = int(len(normal_queries) * args.normal_train_ratio)
    benign_pool_queries = normal_queries[:split_at]
    benign_test_queries = normal_queries[split_at:]
    if len(benign_pool_queries) < args.batch_size:
        raise ValueError("Benign reference pool is smaller than --batch-size")
    if len(benign_test_queries) < 2:
        raise ValueError("Held-out benign test stream has fewer than 2 queries")

    all_queries = benign_pool_queries + benign_test_queries + attacker_queries
    embeddings = mmd.embed_texts(
        all_queries,
        model_name=args.embedding_model,
        batch_size=args.encode_batch_size,
        device=args.device,
        prefix=args.query_prefix,
        normalize=not args.no_normalize_embeddings,
        cache_dir=args.cache_dir,
    )

    n_ref = len(benign_pool_queries)
    n_test = len(benign_test_queries)
    embeddings_t = torch.as_tensor(embeddings, dtype=mmd_dtype, device=mmd_device)
    z_clean_reference = embeddings_t[:n_ref]
    z_benign_test = embeddings_t[n_ref : n_ref + n_test]
    z_attacker = embeddings_t[n_ref + n_test :]

    output_dir = args.output_dir / f"{resolved_dataset}_seed{args.seed}_bs{args.batch_size}"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.csv"
    summary_rows = []
    clean_threshold = None

    for ratio in contamination_ratios:
        ratio_seed = args.seed + int(round(ratio * 1_000_000)) + 17
        rng = np.random.default_rng(ratio_seed)
        z_reference, clean_count, contaminated_count = make_contaminated_reference(
            clean_reference=z_clean_reference,
            attacker_reference=z_attacker,
            contamination_ratio=ratio,
            rng=rng,
        )
        results, extra = evaluate_for_reference(
            z_reference=z_reference,
            z_clean_reference=z_clean_reference,
            z_benign_test=z_benign_test,
            z_attacker=z_attacker,
            args=args,
            mixed_ratios=mixed_ratios,
            rng=rng,
        )
        if ratio == 0:
            clean_threshold = extra["threshold"]
        threshold_shift = (
            extra["threshold"] - clean_threshold
            if clean_threshold is not None
            else float("nan")
        )

        metrics = mmd.summarize(results)
        metrics_by_split = mmd.summarize_by_split(results)
        metadata = {
            "dataset": resolved_dataset,
            "data_root": str(args.data_root),
            "normal_source": args.normal_source,
            "global_normal_path": str(args.global_normal_path),
            "normal_path": str(normal_path),
            "attacker_path": str(attacker_path),
            "text_field": args.text_field,
            "embedding_model": args.embedding_model,
            "query_prefix": args.query_prefix,
            "normalize_embeddings": not args.no_normalize_embeddings,
            "mmd_device": str(mmd_device),
            "mmd_dtype": args.mmd_dtype,
            "batch_size": args.batch_size,
            "reference_repeats": args.reference_repeats,
            "null_samples": args.null_samples,
            "threshold_percentile": args.threshold_percentile,
            "threshold": extra["threshold"],
            "threshold_shift_from_clean": threshold_shift,
            "median_bandwidth": extra["median_bandwidth"],
            "sigmas": extra["sigmas"],
            "normal_queries": len(normal_queries),
            "clean_benign_pool_size": len(benign_pool_queries),
            "contaminated_reference_size": len(z_reference),
            "contamination_ratio_requested": ratio,
            "contamination_ratio_actual": contaminated_count / len(z_reference),
            "reference_clean_benign_count": clean_count,
            "reference_attacker_count": contaminated_count,
            "heldout_benign_size": len(benign_test_queries),
            "attacker_queries": len(attacker_queries),
            "mixed_attacker_ratios": mixed_ratios,
            "mixed_batches_per_ratio": args.mixed_batches_per_ratio,
            "benign_eval_batches": args.benign_eval_batches,
            "attacker_eval_batches": args.attacker_eval_batches,
            "seed": args.seed,
            "ratio_seed": ratio_seed,
            "metrics": metrics,
            "metrics_by_split": metrics_by_split,
            "null_score_mean": extra["null_score_mean"],
            "null_score_std": extra["null_score_std"],
            "null_score_min": extra["null_score_min"],
            "null_score_max": extra["null_score_max"],
        }

        ratio_name = f"contam_{ratio:.2%}".replace("%", "pct").replace(".", "p")
        ratio_dir = output_dir / ratio_name
        mmd.write_outputs(ratio_dir, results, metadata)

        fpr = rate(metrics_by_split, "heldout_benign")
        pure_tpr = rate(metrics_by_split, "attacker")
        mixed_tprs = [rate(metrics_by_split, f"mixed_{r:g}") for r in mixed_ratios]
        mixed_tprs_valid = [value for value in mixed_tprs if not math.isnan(value)]
        avg_mixed_tpr = (
            sum(mixed_tprs_valid) / len(mixed_tprs_valid) if mixed_tprs_valid else float("nan")
        )
        balanced_acc = (
            (avg_mixed_tpr + 1.0 - fpr) / 2.0
            if not math.isnan(avg_mixed_tpr) and not math.isnan(fpr)
            else float("nan")
        )
        row = {
            "dataset": resolved_dataset,
            "seed": args.seed,
            "contamination_ratio": ratio,
            "contamination_ratio_actual": contaminated_count / len(z_reference),
            "reference_attacker_count": contaminated_count,
            "threshold": extra["threshold"],
            "threshold_shift_from_clean": threshold_shift,
            "median_bandwidth": extra["median_bandwidth"],
            "benign_fpr": pct(fpr),
            "pure_tpr": pct(pure_tpr),
            "avg_mixed_tpr": pct(avg_mixed_tpr),
            "balanced_acc": pct(balanced_acc),
            "output_dir": str(ratio_dir),
            "metadata_path": str(ratio_dir / "metadata.json"),
        }
        for mixed_ratio, mixed_tpr in zip(mixed_ratios, mixed_tprs):
            row[f"{int(round(mixed_ratio * 100))}pct_tpr"] = pct(mixed_tpr)
        summary_rows.append(row)

    fields = [
        "dataset",
        "seed",
        "contamination_ratio",
        "contamination_ratio_actual",
        "reference_attacker_count",
        "threshold",
        "threshold_shift_from_clean",
        "median_bandwidth",
        "benign_fpr",
        "pure_tpr",
    ]
    fields.extend(f"{int(round(r * 100))}pct_tpr" for r in mixed_ratios)
    fields.extend(["avg_mixed_tpr", "balanced_acc", "output_dir", "metadata_path"])
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(json.dumps({"summary_path": str(summary_path), "rows": summary_rows}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

