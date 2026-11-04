#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

DATASETS="${DATASETS:-model_leeching}"
SEEDS="${SEEDS:-42}"
CONTAMINATION_RATIOS="${CONTAMINATION_RATIOS:-0,0.01,0.05,0.1}"

BATCH_SIZE="${BATCH_SIZE:-1500}"
REFERENCE_REPEATS="${REFERENCE_REPEATS:-20}"
NULL_SAMPLES="${NULL_SAMPLES:-1000}"
THRESHOLD_PERCENTILE="${THRESHOLD_PERCENTILE:-95}"
NORMAL_TRAIN_RATIO="${NORMAL_TRAIN_RATIO:-0.8}"
MIXED_ATTACKER_RATIOS="${MIXED_ATTACKER_RATIOS:-0.05,0.1}"
MIXED_BATCHES_PER_RATIO="${MIXED_BATCHES_PER_RATIO:-50}"
BENIGN_EVAL_BATCHES="${BENIGN_EVAL_BATCHES:-50}"
ATTACKER_EVAL_BATCHES="${ATTACKER_EVAL_BATCHES:-50}"

EMBEDDING_MODEL="${EMBEDDING_MODEL:-BAAI/bge-small-en-v1.5}"
QUERY_PREFIX="${QUERY_PREFIX:-}"
DEVICE="${DEVICE:-cuda}"
MMD_DEVICE="${MMD_DEVICE:-cuda}"
MMD_DTYPE="${MMD_DTYPE:-float32}"
NORMAL_SOURCE="${NORMAL_SOURCE:-dataset}"
GLOBAL_NORMAL_PATH="${GLOBAL_NORMAL_PATH:-data/global_normal/queries.jsonl}"

EXPERIMENT_ROOT="${EXPERIMENT_ROOT:-review_experiment/calibration_contamination}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${EXPERIMENT_ROOT}/outputs}"
CACHE_DIR="${CACHE_DIR:-review_experiment/cache/mmd_embeddings}"
LOG_ROOT="${LOG_ROOT:-${EXPERIMENT_ROOT}/logs}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "${OUTPUT_ROOT}" "${CACHE_DIR}" "${LOG_ROOT}"

dataset_items="${DATASETS//,/ }"
seed_items="${SEEDS//,/ }"

for dataset in ${dataset_items}; do
  for seed in ${seed_items}; do
    log_file="${LOG_ROOT}/${dataset}_seed${seed}_bs${BATCH_SIZE}.log"
    echo "Running calibration contamination sensitivity: dataset=${dataset}, seed=${seed}"
    cmd=(
      "${PYTHON_BIN}" review_experiment/calibration_contamination/calibration_contamination_sensitivity.py
      --dataset "${dataset}"
      --normal-source "${NORMAL_SOURCE}"
      --global-normal-path "${GLOBAL_NORMAL_PATH}"
      --embedding-model "${EMBEDDING_MODEL}"
      --query-prefix "${QUERY_PREFIX}"
      --mmd-device "${MMD_DEVICE}"
      --mmd-dtype "${MMD_DTYPE}"
      --batch-size "${BATCH_SIZE}"
      --reference-repeats "${REFERENCE_REPEATS}"
      --null-samples "${NULL_SAMPLES}"
      --threshold-percentile "${THRESHOLD_PERCENTILE}"
      --normal-train-ratio "${NORMAL_TRAIN_RATIO}"
      --contamination-ratios "${CONTAMINATION_RATIOS}"
      --mixed-attacker-ratios "${MIXED_ATTACKER_RATIOS}"
      --mixed-batches-per-ratio "${MIXED_BATCHES_PER_RATIO}"
      --benign-eval-batches "${BENIGN_EVAL_BATCHES}"
      --attacker-eval-batches "${ATTACKER_EVAL_BATCHES}"
      --seed "${seed}"
      --cache-dir "${CACHE_DIR}"
      --output-dir "${OUTPUT_ROOT}"
      --multi-kernel
    )
    if [[ -n "${DEVICE}" ]]; then
      cmd+=(--device "${DEVICE}")
    fi
    "${cmd[@]}" 2>&1 | tee "${log_file}"
  done
done
