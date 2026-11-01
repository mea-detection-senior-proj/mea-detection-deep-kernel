from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from MeaeQ_adaptive.adaptive import mmd_gpu_local as mmd


TASK_DATASET_NAMES = {
    "AGNEWS": "Meaeq_AGNEWS",
    "HATESPEECH": "Meaeq_HATESPEECH",
    "IMDB": "Meaeq_IMDB",
    "SST-2": "Meaeq_SST-2",
}


def default_normal_path(args) -> Path:
    dataset = TASK_DATASET_NAMES.get(args.task_name, f"Meaeq_{args.task_name}")
    return Path(args.project_NLP_path).resolve().parents[1] / "data" / dataset / "normal" / "queries.jsonl"


def query_output_dir(args) -> Path:
    root = Path(args.root)
    prompt = args.prompt.replace(" ", "-")
    path = root / f"seed={args.seed}" / f"task_name={args.task_name}" / f"pool_data_source={args.pool_data_source}"
    path = path / f"pool_data_type={args.pool_data_type}" / f"prompt={prompt}" / f"pool_subsize={args.pool_subsize}"
    if args.method != "MeaeQ" and str(args.method).startswith("MeaeQ-"):
        path = path / f"method={args.method.replace(' ', '-')}"
    epsilon = "-1" if args.epsilon == -1 else str(args.epsilon)
    path = path / f"epsilon={epsilon}" / f"initial_sample_method={args.initial_sample_method}"
    path = path / f"initial_drk_model={args.initial_drk_model.replace(' ', '-')}" / f"query_num={args.query_num}"
    return path


def _normalize(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    lo = float(np.min(values))
    hi = float(np.max(values))
    if hi - lo < 1e-12:
        return np.zeros_like(values)
    return (values - lo) / (hi - lo)


def _mmd_device(args) -> str:
    if args.adaptive_mmd_device == "cuda" and not torch.cuda.is_available():
        return "cpu"
    return args.adaptive_mmd_device


def _sigmas_from_reference(ref: torch.Tensor, args, rng: np.random.Generator) -> list[float]:
    base = mmd.median_bandwidth(ref, args.adaptive_bandwidth_sample_size, rng)
    return [base / 2.0, base, base * 2.0]


def _load_normal_queries(args, rng: np.random.Generator) -> tuple[list[str], Path, int]:
    normal_path = Path(args.adaptive_normal_path) if args.adaptive_normal_path else default_normal_path(args)
    pool_limit = None if args.adaptive_normal_pool_limit <= 0 else args.adaptive_normal_pool_limit
    normal_pool = mmd.read_jsonl_queries(normal_path, args.adaptive_text_field, pool_limit)
    sample_size = min(args.adaptive_reference_size, len(normal_pool))
    if sample_size < len(normal_pool):
        idx = rng.choice(len(normal_pool), size=sample_size, replace=False)
        normal_queries = [normal_pool[int(i)] for i in idx]
    else:
        normal_queries = normal_pool
    return normal_queries, normal_path, len(normal_pool)


def _embed_candidates_and_normal(candidates: list[str], args, rng: np.random.Generator):
    normal_queries, normal_path, normal_pool_size = _load_normal_queries(args, rng)
    cache_dir = Path(args.adaptive_cache_dir) if args.adaptive_cache_dir else None
    candidate_np = mmd.embed_texts(
        candidates,
        args.adaptive_embedding_model,
        args.adaptive_embed_batch_size,
        args.adaptive_embed_device,
        args.adaptive_query_prefix,
        True,
        cache_dir,
    )
    normal_np = mmd.embed_texts(
        normal_queries,
        args.adaptive_embedding_model,
        args.adaptive_embed_batch_size,
        args.adaptive_embed_device,
        args.adaptive_query_prefix,
        True,
        cache_dir,
    )
    device = _mmd_device(args)
    candidate_z = mmd.as_torch(candidate_np, device, args.adaptive_mmd_dtype)
    normal_z = mmd.as_torch(normal_np, device, args.adaptive_mmd_dtype)
    sigmas = _sigmas_from_reference(normal_z, args, rng)
    return candidate_z, normal_z, sigmas, normal_path, normal_pool_size, len(normal_queries)


def _sample_rows(z: torch.Tensor, size: int, rng: np.random.Generator) -> torch.Tensor:
    replace = len(z) < size
    idx = rng.choice(len(z), size=size, replace=replace)
    idx_t = torch.as_tensor(idx, dtype=torch.long, device=z.device)
    return z[idx_t]


def _build_null_scores(normal_z: torch.Tensor, batch_size: int, sigmas: list[float], args, rng: np.random.Generator) -> np.ndarray:
    scores = np.empty(args.adaptive_null_samples, dtype=np.float64)
    can_disjoint = len(normal_z) >= 2 * batch_size
    for i in range(args.adaptive_null_samples):
        if can_disjoint:
            idx = rng.choice(len(normal_z), size=2 * batch_size, replace=False)
            idx_t = torch.as_tensor(idx, dtype=torch.long, device=normal_z.device)
            z1 = normal_z[idx_t[:batch_size]]
            z2 = normal_z[idx_t[batch_size:]]
        else:
            z1 = _sample_rows(normal_z, batch_size, rng)
            z2 = _sample_rows(normal_z, batch_size, rng)
        scores[i] = mmd.mmd2_unbiased(z1, z2, sigmas)
    return scores


def _estimate_window_penalties(
    candidate_z: torch.Tensor,
    normal_z: torch.Tensor,
    sigmas: list[float],
    args,
    rng: np.random.Generator,
) -> np.ndarray:
    n = len(candidate_z)
    batch_size = max(2, min(args.adaptive_mmd_batch_size, n, len(normal_z)))
    windows = max(1, args.adaptive_penalty_windows)
    sums = np.zeros(n, dtype=np.float64)
    counts = np.zeros(n, dtype=np.float64)

    for _ in range(windows):
        c_idx = rng.choice(n, size=batch_size, replace=n < batch_size)
        b_idx = rng.choice(len(normal_z), size=batch_size, replace=len(normal_z) < batch_size)
        c_idx_t = torch.as_tensor(c_idx, dtype=torch.long, device=candidate_z.device)
        b_idx_t = torch.as_tensor(b_idx, dtype=torch.long, device=normal_z.device)
        score = mmd.mmd2_unbiased(candidate_z[c_idx_t], normal_z[b_idx_t], sigmas)
        for idx in c_idx:
            sums[int(idx)] += score
            counts[int(idx)] += 1.0

    missing = counts == 0
    if np.any(missing):
        global_score = float(np.mean(sums[counts > 0] / counts[counts > 0])) if np.any(counts > 0) else 0.0
        sums[missing] = global_score
        counts[missing] = 1.0
    return sums / counts


def _write_metadata(args, metadata: dict) -> None:
    output_path = query_output_dir(args) / "adaptive_metadata.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("adaptive metadata saved to:", output_path)


def select_regularized_queries(candidates: list[str], query_num: int, args) -> list[str]:
    if len(candidates) <= query_num:
        return candidates

    rng = np.random.default_rng(args.run_seed)
    candidate_z, normal_z, sigmas, normal_path, normal_pool_size, normal_reference_size = _embed_candidates_and_normal(
        candidates, args, rng
    )
    penalties = _estimate_window_penalties(candidate_z, normal_z, sigmas, args, rng)

    rank_utility = 1.0 - (np.arange(len(candidates), dtype=np.float64) / max(1, len(candidates) - 1))
    penalty_norm = _normalize(penalties)
    scores = rank_utility - args.adaptive_lambda * penalty_norm
    selected_idx = np.argsort(-scores)[:query_num]
    selected_idx = sorted(int(i) for i in selected_idx)
    selected = [candidates[i] for i in selected_idx]

    _write_metadata(args, {
        "method": args.method,
        "task_name": args.task_name,
        "query_num": query_num,
        "candidate_num": len(candidates),
        "selected_num": len(selected),
        "adaptive_lambda": args.adaptive_lambda,
        "adaptive_candidate_multiplier": args.adaptive_candidate_multiplier,
        "adaptive_normal_path": str(normal_path),
        "adaptive_normal_pool_size": normal_pool_size,
        "adaptive_reference_size": normal_reference_size,
        "adaptive_mmd_batch_size": args.adaptive_mmd_batch_size,
        "adaptive_penalty_windows": args.adaptive_penalty_windows,
        "adaptive_embedding_model": args.adaptive_embedding_model,
        "adaptive_sigmas": sigmas,
        "score_min": float(np.min(scores)),
        "score_max": float(np.max(scores)),
        "penalty_min": float(np.min(penalties)),
        "penalty_max": float(np.max(penalties)),
        "selected_indices": selected_idx,
    })
    return selected


def select_projection_queries(candidates: list[str], query_num: int, args) -> list[str]:
    if len(candidates) <= query_num:
        return candidates

    rng = np.random.default_rng(args.run_seed)
    candidate_z, normal_z, sigmas, normal_path, normal_pool_size, normal_reference_size = _embed_candidates_and_normal(
        candidates, args, rng
    )
    batch_size = max(2, min(args.adaptive_mmd_batch_size, len(candidate_z), len(normal_z)))
    null_scores = _build_null_scores(normal_z, batch_size, sigmas, args, rng)
    threshold = float(np.percentile(null_scores, args.adaptive_threshold_percentile))

    accepted: list[int] = []
    rejected_windows: list[dict] = []
    window_records: list[dict] = []
    window_id = 0
    for start in range(0, len(candidates), batch_size):
        idx = list(range(start, min(start + batch_size, len(candidates))))
        if len(idx) < 2:
            rejected_windows.append({"indices": idx, "score": float("inf"), "window_id": window_id})
            continue
        idx_t = torch.as_tensor(idx, dtype=torch.long, device=candidate_z.device)
        ref = _sample_rows(normal_z, len(idx), rng)
        score = mmd.mmd2_unbiased(candidate_z[idx_t], ref, sigmas)
        accepted_strict = score <= threshold
        record = {
            "window_id": window_id,
            "start": start,
            "size": len(idx),
            "score": float(score),
            "accepted_strict": bool(accepted_strict),
        }
        window_records.append(record)
        if accepted_strict:
            accepted.extend(idx)
        else:
            rejected_windows.append({"indices": idx, "score": float(score), "window_id": window_id})
        window_id += 1
        if len(accepted) >= query_num:
            break

    fallback_windows = []
    if len(accepted) < query_num:
        for item in sorted(rejected_windows, key=lambda x: x["score"]):
            accepted.extend(item["indices"])
            fallback_windows.append({"window_id": item["window_id"], "score": item["score"], "size": len(item["indices"])})
            if len(accepted) >= query_num:
                break

    selected_idx = sorted(accepted[:query_num])
    selected = [candidates[i] for i in selected_idx]
    strict_windows = [r for r in window_records if r["accepted_strict"]]

    _write_metadata(args, {
        "method": args.method,
        "task_name": args.task_name,
        "query_num": query_num,
        "candidate_num": len(candidates),
        "selected_num": len(selected),
        "adaptive_candidate_multiplier": args.adaptive_candidate_multiplier,
        "adaptive_normal_path": str(normal_path),
        "adaptive_normal_pool_size": normal_pool_size,
        "adaptive_reference_size": normal_reference_size,
        "adaptive_mmd_batch_size": batch_size,
        "adaptive_null_samples": args.adaptive_null_samples,
        "adaptive_threshold_percentile": args.adaptive_threshold_percentile,
        "adaptive_embedding_model": args.adaptive_embedding_model,
        "adaptive_sigmas": sigmas,
        "projection_threshold": threshold,
        "candidate_windows_scored": len(window_records),
        "accepted_strict_windows": len(strict_windows),
        "rejected_windows": len(rejected_windows),
        "fallback_windows": fallback_windows,
        "null_score_min": float(np.min(null_scores)),
        "null_score_max": float(np.max(null_scores)),
        "selected_indices": selected_idx,
        "window_records": window_records,
    })
    return selected