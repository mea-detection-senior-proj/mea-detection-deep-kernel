#!/usr/bin/env bash
set -euo pipefail

# Convenience entry point for reproducing the paper experiments.
# Use EXPERIMENTS to run a subset, e.g.
#   EXPERIMENTS="main adaptive contamination" bash run_all_paper_experiments.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

DEFAULT_DATASETS="model_leeching,Meaeq_AGNEWS,Meaeq_HATESPEECH,Meaeq_IMDB,Meaeq_SST-2,Query_efficent_med,ME_BERT_boolq_random,ME_BERT_boolq_wiki,ME_BERT_mnli_random,ME_BERT_mnli_wiki,ME_BERT_squad_random,ME_BERT_squad_wiki,ME_BERT_sst2_random,ME_BERT_sst2_wiki"
DATASETS="${DATASETS:-${DEFAULT_DATASETS}}"
SEEDS="${SEEDS:-1 20 42}"
DEVICE="${DEVICE:-cuda}"
MMD_DEVICE="${MMD_DEVICE:-${DEVICE}}"
COMPUTE_DEVICE="${COMPUTE_DEVICE:-${DEVICE}}"
BATCH_SIZE="${BATCH_SIZE:-1500}"

EXPERIMENTS="${EXPERIMENTS:-main original_protocol adaptive contamination encoder_sensitivity batch_threshold_sensitivity decision_direction runtime mmd_reference_repeats mmd_null_samples}"

run_if_selected() {
  local name="$1"
  shift
  if [[ " ${EXPERIMENTS} " != *" ${name} "* ]]; then
    return 0
  fi

  echo
  echo "################################################################################"
  echo "Running paper experiment group: ${name}"
  echo "################################################################################"
  "$@"
}

run_if_selected main \
  env DATASETS="${DATASETS}" SEEDS="${SEEDS}" BATCH_SIZE="${BATCH_SIZE}" \
    DEVICE="${DEVICE}" MMD_DEVICE="${MMD_DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
    bash new_main_experiment/run_new_main_experiment.sh

run_if_selected original_protocol \
  env DATASETS="${DATASETS}" DEVICE="${DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" bash -c '
    set -euo pipefail
    DATASET="${DATASETS}" DEVICE="${DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
      OUTPUT_ROOT="PRADA/stream_outputs" bash PRADA/run_prada_stream_detection.sh
    DATASETS="${DATASETS}" DEVICE="${DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
      OUTPUT_ROOT="SEAT/original_outputs" bash SEAT/run_seat_original_detection_multi.sh
    DATASETS="${DATASETS}" DEVICE="${DEVICE}" \
      OUTPUT_ROOT="CAP/original_outputs" bash CAP/run_cap_original_detection_multi.sh
    DATASETS="${DATASETS}" DEVICE="${DEVICE}" \
      OUTPUT_ROOT="DATE/original_outputs" bash DATE/run_date_original_detection_multi.sh
    DATASETS="${DATASETS}" DEVICE="${DEVICE}" \
      OUTPUT_ROOT="Mahalanobis/sample_outputs" bash Mahalanobis/run_mahalanobis_sample_detection_multi.sh
  '

run_if_selected adaptive \
  env SEED="${ADAPTIVE_SEED:-42}" BATCH_SIZE="${BATCH_SIZE}" DEVICE="${DEVICE}" MMD_DEVICE="${MMD_DEVICE}" \
    bash review_experiment/MeaeQ_adaptive/run_adaptive_mmd_evaluation.sh

run_if_selected contamination \
  env DATASETS="${DATASETS}" SEEDS="${CONTAMINATION_SEEDS:-42}" BATCH_SIZE="${BATCH_SIZE}" MMD_DEVICE="${MMD_DEVICE}" \
    bash review_experiment/calibration_contamination/run_calibration_contamination_sensitivity_multi.sh

run_if_selected encoder_sensitivity \
  env DATASETS="${DATASETS}" SEEDS="${ENCODER_SEEDS:-42}" BATCH_SIZE="${BATCH_SIZE}" DEVICE="${DEVICE}" MMD_DEVICE="${MMD_DEVICE}" \
    bash supplementary_experiments/run_mmd_embedding_model_experiment.sh

run_if_selected batch_threshold_sensitivity \
  env BATCH_SIZE="${BATCH_SIZE}" DEVICE="${DEVICE}" MMD_DEVICE="${MMD_DEVICE}" \
    bash MMD_detection/run_mmd_sensitivity_gpu.sh

run_if_selected decision_direction \
  env DATASETS="${DATASETS}" SEED="${DECISION_DIRECTION_SEED:-42}" BATCH_SIZE="${BATCH_SIZE}" DEVICE="${DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
    bash supplementary_experiments/run_decision_direction_experiment.sh

run_if_selected runtime \
  env DATASET="${RUNTIME_DATASET:-model_leeching}" SEED="${RUNTIME_SEED:-42}" BATCH_SIZE="${BATCH_SIZE}" \
    DEVICE="${DEVICE}" MMD_DEVICE="${MMD_DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
    bash supplementary_experiments/run_cold_cache_wallclock.sh

run_if_selected mmd_reference_repeats \
  env DATASETS="${REFERENCE_REPEAT_DATASETS:-model_leeching}" SEEDS="${REFERENCE_REPEAT_SEEDS:-42}" BATCH_SIZE="${BATCH_SIZE}" \
    DEVICE="${DEVICE}" MMD_DEVICE="${MMD_DEVICE}" \
    bash supplementary_experiments/run_mmd_reference_repeats_experiment.sh

run_if_selected mmd_null_samples \
  env DATASETS="${NULL_SAMPLE_DATASETS:-model_leeching}" SEEDS="${NULL_SAMPLE_SEEDS:-42}" BATCH_SIZE="${BATCH_SIZE}" \
    DEVICE="${DEVICE}" MMD_DEVICE="${MMD_DEVICE}" \
    bash supplementary_experiments/run_mmd_null_samples_experiment.sh

echo
echo "Selected paper experiment groups finished."
