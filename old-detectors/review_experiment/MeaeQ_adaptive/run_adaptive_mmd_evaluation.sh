#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

# Adaptive-evasion evaluation used for the camera-ready paper.
# The three datasets correspond to original MeaeQ, MMD-regularized MeaeQ,
# and projection-style MeaeQ query sets on SST-2.
DATASETS="${DATASETS:-Meaeq_SST-2,Meaeq_SST-2_regularized,Meaeq_SST-2_projection}"

BATCH_SIZE="${BATCH_SIZE:-1500}"
SEED="${SEED:-42}"
DEVICE="${DEVICE:-cuda}"
MMD_DEVICE="${MMD_DEVICE:-${DEVICE}}"
MMD_DTYPE="${MMD_DTYPE:-float32}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-BAAI/bge-small-en-v1.5}"
QUERY_PREFIX="${QUERY_PREFIX:-}"
REFERENCE_REPEATS="${REFERENCE_REPEATS:-20}"
NULL_SAMPLES="${NULL_SAMPLES:-1000}"
THRESHOLD_PERCENTILE="${THRESHOLD_PERCENTILE:-95}"
MIXED_ATTACKER_RATIOS="${MIXED_ATTACKER_RATIOS:-0.05,0.1,0.25,0.5}"
MIXED_BATCHES_PER_RATIO="${MIXED_BATCHES_PER_RATIO:-50}"
BENIGN_EVAL_BATCHES="${BENIGN_EVAL_BATCHES:-50}"
ATTACKER_EVAL_BATCHES="${ATTACKER_EVAL_BATCHES:-50}"

OUTPUT_ROOT="${OUTPUT_ROOT:-review_experiment/MeaeQ_adaptive/MMD_result}"
CACHE_DIR="${CACHE_DIR:-review_experiment/MeaeQ_adaptive/cache/mmd_embeddings}"
LOG_ROOT="${LOG_ROOT:-review_experiment/MeaeQ_adaptive/logs}"

mkdir -p "${OUTPUT_ROOT}" "${CACHE_DIR}" "${LOG_ROOT}"

dataset_items="${DATASETS//,/ }"

echo "Running adaptive MeaeQ MMD evaluation..."
echo "Datasets: ${DATASETS}"
echo "Seed: ${SEED}"
echo "Output root: ${OUTPUT_ROOT}"
echo

for dataset in ${dataset_items}; do
  if [[ -z "${dataset}" ]]; then
    continue
  fi

  output_dir="${OUTPUT_ROOT}/${dataset}_bge_bs${BATCH_SIZE}"
  log_file="${LOG_ROOT}/${dataset}_seed${SEED}_bs${BATCH_SIZE}.log"

  echo "============================================================"
  echo "Dataset: ${dataset}"
  echo "Output dir: ${output_dir}"
  echo "Log file: ${log_file}"
  echo "============================================================"

  DATASET="${dataset}" \
  BATCH_SIZE="${BATCH_SIZE}" \
  SEED="${SEED}" \
  DEVICE="${DEVICE}" \
  MMD_DEVICE="${MMD_DEVICE}" \
  MMD_DTYPE="${MMD_DTYPE}" \
  EMBEDDING_MODEL="${EMBEDDING_MODEL}" \
  QUERY_PREFIX="${QUERY_PREFIX}" \
  REFERENCE_REPEATS="${REFERENCE_REPEATS}" \
  NULL_SAMPLES="${NULL_SAMPLES}" \
  THRESHOLD_PERCENTILE="${THRESHOLD_PERCENTILE}" \
  MIXED_ATTACKER_RATIOS="${MIXED_ATTACKER_RATIOS}" \
  MIXED_BATCHES_PER_RATIO="${MIXED_BATCHES_PER_RATIO}" \
  BENIGN_EVAL_BATCHES="${BENIGN_EVAL_BATCHES}" \
  ATTACKER_EVAL_BATCHES="${ATTACKER_EVAL_BATCHES}" \
  CACHE_DIR="${CACHE_DIR}" \
  OUTPUT_DIR="${output_dir}" \
  bash MMD_detection/run_mmd_detection_gpu.sh > "${log_file}" 2>&1

  echo
done

echo "Adaptive MeaeQ MMD evaluation finished."
