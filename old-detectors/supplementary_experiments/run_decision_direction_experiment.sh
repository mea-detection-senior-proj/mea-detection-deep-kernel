#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

DEFAULT_DATASETS="model_leeching,Meaeq_AGNEWS,Meaeq_HATESPEECH,Meaeq_IMDB,Meaeq_SST-2,Query_efficent_med,ME_BERT_boolq_random,ME_BERT_boolq_wiki,ME_BERT_mnli_random,ME_BERT_mnli_wiki,ME_BERT_squad_random,ME_BERT_squad_wiki,ME_BERT_sst2_random,ME_BERT_sst2_wiki"
DATASETS="${DATASETS:-${DEFAULT_DATASETS}}"
METHODS="${METHODS:-PRADA SEAT CAP DATE}"
SIDES="${SIDES:-one-sided two-sided}"

BATCH_SIZE="${BATCH_SIZE:-1500}"
SEED="${SEED:-42}"
DEVICE="${DEVICE:-cuda}"
COMPUTE_DEVICE="${COMPUTE_DEVICE:-${DEVICE}}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-BAAI/bge-small-en-v1.5}"
QUERY_PREFIX="${QUERY_PREFIX:-}"

EXPERIMENT_ROOT="${EXPERIMENT_ROOT:-supplementary_experiments/decision_direction_experiment}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${EXPERIMENT_ROOT}/outputs}"
LOG_ROOT="${LOG_ROOT:-${EXPERIMENT_ROOT}/logs}"
CACHE_ROOT="${CACHE_ROOT:-${EXPERIMENT_ROOT}/cache}"

mkdir -p "${OUTPUT_ROOT}" "${LOG_ROOT}" "${CACHE_ROOT}"

dataset_items="${DATASETS//,/ }"

echo "Running one-sided/two-sided decision-direction experiment..."
echo "Datasets: ${DATASETS}"
echo "Methods: ${METHODS}"
echo "Sides: ${SIDES}"
echo "Output root: ${OUTPUT_ROOT}"
echo

run_one() {
  local method="$1"
  local side="$2"
  local dataset="$3"
  local method_lc
  local side_slug
  method_lc="$(echo "${method}" | tr '[:upper:]' '[:lower:]')"
  side_slug="${side}"

  local output_dir="${OUTPUT_ROOT}/${side_slug}/${method_lc}/${dataset}_bge_bs${BATCH_SIZE}"
  local cache_dir="${CACHE_ROOT}/${side_slug}/${method_lc}"
  local log_dir="${LOG_ROOT}/${side_slug}/${method_lc}"
  local log_file="${log_dir}/${dataset}_seed${SEED}_bs${BATCH_SIZE}.log"

  mkdir -p "${output_dir}" "${cache_dir}" "${log_dir}"

  echo "============================================================"
  echo "Method: ${method}"
  echo "Side: ${side}"
  echo "Dataset: ${dataset}"
  echo "Output dir: ${output_dir}"
  echo "============================================================"

  case "${method}" in
    PRADA)
      local tail
      [[ "${side}" == "one-sided" ]] && tail="upper" || tail="two-sided"
      DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${SEED}" \
      DEVICE="${DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
      EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
      TAIL="${tail}" CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
      bash PRADA/run_prada_detection.sh > "${log_file}" 2>&1
      ;;
    SEAT)
      local detection_tail
      [[ "${side}" == "one-sided" ]] && detection_tail="upper" || detection_tail="two-sided"
      DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${SEED}" \
      DEVICE="${DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
      EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
      DETECTION_TAIL="${detection_tail}" CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
      bash SEAT/run_seat_detection.sh > "${log_file}" 2>&1
      ;;
    CAP)
      local cap_tail
      [[ "${side}" == "one-sided" ]] && cap_tail="high" || cap_tail="two-sided"
      DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${SEED}" \
      DEVICE="${DEVICE}" EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
      TAIL="${cap_tail}" CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
      bash CAP/run_cap_detection.sh > "${log_file}" 2>&1
      ;;
    DATE)
      local date_side
      [[ "${side}" == "one-sided" ]] && date_side="upper" || date_side="two-sided"
      DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${SEED}" \
      DEVICE="${DEVICE}" TEST_SIDEDNESS="${date_side}" OUTPUT_DIR="${output_dir}" \
      bash DATE/run_date_detection.sh > "${log_file}" 2>&1
      ;;
    *)
      echo "Unknown method: ${method}" >&2
      return 1
      ;;
  esac
}

for side in ${SIDES}; do
  for method in ${METHODS}; do
    for dataset in ${dataset_items}; do
      [[ -z "${dataset}" ]] && continue
      run_one "${method}" "${side}" "${dataset}"
      echo
    done
  done
done

echo "Decision-direction experiment finished."
