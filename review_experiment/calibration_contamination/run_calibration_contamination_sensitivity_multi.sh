#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

# Comma-separated or whitespace-separated dataset names.
# Examples:
#   DATASETS="model_leeching,Meaeq_AGNEWS,Query_efficent_med"
#   DATASETS="ME_BERT_boolq_wiki ME_BERT_squad_wiki"
DEFAULT_DATASETS="model_leeching,Meaeq_AGNEWS,Meaeq_HATESPEECH,Meaeq_IMDB,Meaeq_SST-2,Query_efficent_med,ME_BERT_boolq_random,ME_BERT_boolq_wiki,ME_BERT_mnli_random,ME_BERT_mnli_wiki,ME_BERT_squad_random,ME_BERT_squad_wiki,ME_BERT_sst2_random,ME_BERT_sst2_wiki"
DATASETS="${DATASETS:-${DEFAULT_DATASETS}}"

# Comma-separated or whitespace-separated seeds.
SEEDS="${SEEDS:-42}"

BATCH_SIZE="${BATCH_SIZE:-1500}"
MMD_DEVICE="${MMD_DEVICE:-cuda}"
MMD_DTYPE="${MMD_DTYPE:-float32}"

EXPERIMENT_ROOT="${EXPERIMENT_ROOT:-review_experiment/calibration_contamination}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${EXPERIMENT_ROOT}/outputs}"
LOG_ROOT="${LOG_ROOT:-${EXPERIMENT_ROOT}/logs}"
CACHE_DIR="${CACHE_DIR:-review_experiment/cache/mmd_embeddings}"

dataset_items="${DATASETS//,/ }"
seed_items="${SEEDS//,/ }"

mkdir -p "${OUTPUT_ROOT}" "${LOG_ROOT}" "${CACHE_DIR}"

echo "Running calibration contamination sensitivity for multiple datasets..."
echo "Datasets: ${DATASETS}"
echo "Seeds: ${SEEDS}"
echo "Output root: ${OUTPUT_ROOT}"
echo

for dataset in ${dataset_items}; do
  if [[ -z "${dataset}" ]]; then
    continue
  fi

  for seed in ${seed_items}; do
    if [[ -z "${seed}" ]]; then
      continue
    fi

    echo "============================================================"
    echo "Dataset: ${dataset}"
    echo "Seed: ${seed}"
    echo "Output root: ${OUTPUT_ROOT}"
    echo "============================================================"

    DATASETS="${dataset}" \
    SEEDS="${seed}" \
    BATCH_SIZE="${BATCH_SIZE}" \
    EXPERIMENT_ROOT="${EXPERIMENT_ROOT}" \
    OUTPUT_ROOT="${OUTPUT_ROOT}" \
    LOG_ROOT="${LOG_ROOT}" \
    CACHE_DIR="${CACHE_DIR}" \
    MMD_DEVICE="${MMD_DEVICE}" \
    MMD_DTYPE="${MMD_DTYPE}" \
    bash "${SCRIPT_DIR}/run_calibration_contamination_sensitivity.sh"

    echo
  done
done

echo "All requested calibration contamination sensitivity runs finished."
