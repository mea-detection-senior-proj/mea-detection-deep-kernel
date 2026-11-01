#!/usr/bin/env bash
set -euo pipefail

# End-to-end query labeling + extraction runner.
#
# This script does NOT train the victim model. It assumes the task-specific
# victim checkpoint already exists, for example:
#   saved_model/SST-2-bert_base_uncased-victim-model.pkl
#
# If the checkpoint is missing, train the victim first, e.g.:
#   cd review_experiment/MeaeQ_adaptive/victim
#   TASK_NAME=SST-2 bash train_vic.sh
#
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

TASK_NAME="${TASK_NAME:-SST-2}"
METHOD="${METHOD:-MeaeQ}"  # MeaeQ, MeaeQ-regularized, or MeaeQ-projection
QUERY_NUMS="${QUERY_NUMS:-201}"
RUN_SEEDS="${RUN_SEEDS:-30}"

# Stage control list: set an item to 1 to run the stage, or 0 to skip it.
#   item 1: gen_query.sh        (generate queries and victim labels)
#   item 2: train_main_exper.sh (train extracted model and evaluate)
# Example:
#   RUN_STAGE_LIST="1 1" TASK_NAME=SST-2 QUERY_NUMS=201 bash shell/run_end_to_end.sh
RUN_STAGE_LIST="${RUN_STAGE_LIST:-0 1}"

VISIBLE_DEVICE="${VISIBLE_DEVICE:-0}"
VICTIM_MODEL_VERSION="${VICTIM_MODEL_VERSION:-bert_base_uncased}"
STEAL_MODEL_VERSION="${STEAL_MODEL_VERSION:-bert_base_uncased}"
VICTIM_MODEL_CHECKPOINT="${VICTIM_MODEL_CHECKPOINT:-${VICTIM_MODEL_VERSION}-victim-model.pkl}"
STEAL_MODEL_CHECKPOINT="${STEAL_MODEL_CHECKPOINT:-${STEAL_MODEL_VERSION}-steal-model.pkl}"
ONLY_QUERY="${ONLY_QUERY:-0}"
ADAPTIVE_LAMBDA="${ADAPTIVE_LAMBDA:-1.0}"

read -r RUN_QUERY_LABEL_DEFAULT RUN_TRAIN_DEFAULT <<< "${RUN_STAGE_LIST}"
RUN_QUERY_LABEL="${RUN_QUERY_LABEL:-${RUN_QUERY_LABEL_DEFAULT:-1}}"
RUN_TRAIN="${RUN_TRAIN:-${RUN_TRAIN_DEFAULT:-1}}"

common_env=(
  TASK_NAME="${TASK_NAME}"
  METHOD="${METHOD}"
  VISIBLE_DEVICE="${VISIBLE_DEVICE}"
  VICTIM_MODEL_VERSION="${VICTIM_MODEL_VERSION}"
  ADAPTIVE_LAMBDA="${ADAPTIVE_LAMBDA}"
)
if [[ -n "${QUERY_NUMS}" ]]; then
  common_env+=(QUERY_NUMS="${QUERY_NUMS}")
fi

train_env=(
  STEAL_MODEL_VERSION="${STEAL_MODEL_VERSION}"
  VICTIM_MODEL_CHECKPOINT="${VICTIM_MODEL_CHECKPOINT}"
  STEAL_MODEL_CHECKPOINT="${STEAL_MODEL_CHECKPOINT}"
)
if [[ -n "${RUN_SEEDS}" ]]; then
  train_env+=(RUN_SEEDS="${RUN_SEEDS}")
fi

echo "Running MeaeQ end-to-end pipeline"
echo "Project: ${PROJECT_ROOT}"
echo "Task: ${TASK_NAME}"
echo "Method: ${METHOD}"
echo "Query nums: ${QUERY_NUMS:-task defaults}"
echo "Run seeds: ${RUN_SEEDS:-train defaults}"
echo "Visible device: ${VISIBLE_DEVICE}"
echo "Adaptive lambda: ${ADAPTIVE_LAMBDA}"
echo "Run query+label: ${RUN_QUERY_LABEL}"
echo "Run train/eval: ${RUN_TRAIN}"
echo

if [[ "${RUN_QUERY_LABEL}" == "1" || "${RUN_QUERY_LABEL}" == "true" || "${RUN_QUERY_LABEL}" == "True" ]]; then
  echo "[1/2] Generating queries and victim labels"
  env "${common_env[@]}" ONLY_QUERY="${ONLY_QUERY}" bash "${SCRIPT_DIR}/gen_query.sh"
else
  echo "[1/2] Skipping query generation / victim labeling"
fi

if [[ "${RUN_TRAIN}" == "1" || "${RUN_TRAIN}" == "true" || "${RUN_TRAIN}" == "True" ]]; then
  echo "[2/2] Training extracted model and evaluating accuracy/agreement"
  env "${common_env[@]}" "${train_env[@]}" bash "${SCRIPT_DIR}/train_main_exper.sh"
else
  echo "[2/2] Skipping student training / evaluation"
fi

echo
echo "MeaeQ end-to-end pipeline finished."
echo "Logs, if training ran, are under: ${PROJECT_ROOT}/steal/model_steal/log"