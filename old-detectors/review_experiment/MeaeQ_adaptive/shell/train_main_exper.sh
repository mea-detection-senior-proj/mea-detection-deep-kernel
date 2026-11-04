#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}/steal/model_steal"

if [[ -n "${RUN_SEEDS:-}" ]]; then
  read -r -a run_seed_arr <<< "${RUN_SEEDS//,/ }"
else
  run_seed_arr=(30 31 32 33 34 35 36 37 38 39)
fi

task_name="${TASK_NAME:-IMDB}" # SST-2, IMDB, AGNEWS, HATESPEECH
method="${METHOD:-MeaeQ}" # MeaeQ, MeaeQ-regularized, MeaeQ-projection; also supports RS/TRF/DRC/random baselines
visible_device="${VISIBLE_DEVICE:-0}"
vic_model="${VICTIM_MODEL_VERSION:-bert_base_uncased}"
steal_model="${STEAL_MODEL_VERSION:-bert_base_uncased}"
vic_model_ck="${VICTIM_MODEL_CHECKPOINT:-${vic_model}-victim-model.pkl}"
steal_model_ck="${STEAL_MODEL_CHECKPOINT:-${steal_model}-steal-model.pkl}"

if [[ -n "${QUERY_NUMS:-}" ]]; then
  read -r -a query_num_arr <<< "${QUERY_NUMS//,/ }"
elif [[ "${task_name}" == "HATESPEECH" ]]; then
  query_num_arr=(191 382 574)
elif [[ "${task_name}" == "SST-2" ]]; then
  query_num_arr=(201 335 536)
elif [[ "${task_name}" == "IMDB" ]]; then
  query_num_arr=(120 200 320)
elif [[ "${task_name}" == "AGNEWS" ]]; then
  query_num_arr=(360 600 960)
else
  echo "Unknown TASK_NAME=${task_name}" >&2
  exit 1
fi

# Task defaults.
tokenize_max_length_default=128
batch_size_default=32
optimizer_default="adam"
learning_rate_default="3e-5"
weight_decay_default="1e-4"
num_epochs_default=10
num_labels_default=-1
weighted_cross_entropy_default=False

if [[ "${task_name}" == "SST-2" ]]; then
  num_labels_default=2
elif [[ "${task_name}" == "IMDB" ]]; then
  num_labels_default=2
  weighted_cross_entropy_default=True
elif [[ "${task_name}" == "AGNEWS" ]]; then
  tokenize_max_length_default=256
  batch_size_default=16
  learning_rate_default="5e-5"
  weight_decay_default=0
  num_labels_default=4
  weighted_cross_entropy_default=True
elif [[ "${task_name}" == "HATESPEECH" ]]; then
  num_labels_default=2
fi

tokenize_max_length="${TOKENIZE_MAX_LENGTH:-${tokenize_max_length_default}}"
batch_size="${BATCH_SIZE:-${batch_size_default}}"
optimizer="${OPTIMIZER:-${optimizer_default}}"
learning_rate="${LEARNING_RATE:-${learning_rate_default}}"
weight_decay="${WEIGHT_DECAY:-${weight_decay_default}}"
num_epochs="${NUM_EPOCHS:-${num_epochs_default}}"
num_labels="${NUM_LABELS:-${num_labels_default}}"
weighted_cross_entropy="${WEIGHTED_CROSS_ENTROPY:-${weighted_cross_entropy_default}}"

pool_data_source_default="wiki"
pool_data_type_default="None"
prompt_default="None"
pool_subsize_default=-1
epsilon_default=-1
initial_sample_method_default="None"
initial_drk_model_default="None"
al_sample_batch_num_default=-1
al_sample_method_default="None"

if [[ "${method}" == "RS" ]]; then
  pool_data_type_default="whole"
  initial_sample_method_default="WIKI"
elif [[ "${method}" == "sub-RS" ]]; then
  pool_data_type_default="random_subset"
  if [[ "${task_name}" == "SST-2" || "${task_name}" == "IMDB" ]]; then
    pool_subsize_default=1766
  elif [[ "${task_name}" == "AGNEWS" ]]; then
    pool_subsize_default=212630
  elif [[ "${task_name}" == "HATESPEECH" ]]; then
    pool_subsize_default=1561
  fi
  initial_sample_method_default="WIKI"
elif [[ "${method}" == "random-sst2" ]]; then
  pool_data_source_default="sst2"
  pool_data_type_default="whole"
  initial_sample_method_default="random_sentence"
elif [[ "${method}" == "random-imdb" ]]; then
  pool_data_source_default="imdb"
  pool_data_type_default="whole"
  initial_sample_method_default="random_sentence"
elif [[ "${method}" == "TRF" ]]; then
  pool_data_type_default="reduced_subset_by_prompt"
  if [[ "${task_name}" == "SST-2" || "${task_name}" == "IMDB" ]]; then
    prompt_default="This is a movie review."
  elif [[ "${task_name}" == "AGNEWS" ]]; then
    prompt_default="This is a news."
  elif [[ "${task_name}" == "HATESPEECH" ]]; then
    prompt_default="This is a hate speech"
  fi
  epsilon_default=0.95
  initial_sample_method_default="random_sentence"
elif [[ "${method}" == "DRC" ]]; then
  pool_data_type_default="random_subset"
  if [[ "${task_name}" == "SST-2" || "${task_name}" == "IMDB" ]]; then
    pool_subsize_default=1766
  elif [[ "${task_name}" == "AGNEWS" ]]; then
    pool_subsize_default=212630
  elif [[ "${task_name}" == "HATESPEECH" ]]; then
    pool_subsize_default=1561
  fi
  initial_sample_method_default="data_reduction_kmeans"
  initial_drk_model_default="bart-large-mnli"
elif [[ "${method}" == "MeaeQ" || "${method}" == "MeaeQ-regularized" || "${method}" == "MeaeQ-projection" ]]; then
  pool_data_type_default="reduced_subset_by_prompt"
  if [[ "${task_name}" == "SST-2" || "${task_name}" == "IMDB" ]]; then
    prompt_default="This is a movie review."
  elif [[ "${task_name}" == "AGNEWS" ]]; then
    prompt_default="This is a news."
  elif [[ "${task_name}" == "HATESPEECH" ]]; then
    prompt_default="This is a hate speech"
  fi
  epsilon_default=0.95
  initial_sample_method_default="data_reduction_kmeans"
  initial_drk_model_default="bart-large-mnli"
elif [[ "${method}" == "AL-RS" ]]; then
  pool_data_type_default="random_subset"
  pool_subsize_default=30000
  initial_sample_method_default="random_sentence"
  al_sample_batch_num_default=20
  al_sample_method_default="random"
elif [[ "${method}" == "AL-US" ]]; then
  pool_data_type_default="random_subset"
  pool_subsize_default=30000
  initial_sample_method_default="random_sentence"
  al_sample_batch_num_default=20
  al_sample_method_default="uncertainty"
fi

pool_data_source="${POOL_DATA_SOURCE:-${pool_data_source_default}}"
pool_data_type="${POOL_DATA_TYPE:-${pool_data_type_default}}"
prompt="${PROMPT:-${prompt_default}}"
pool_subsize="${POOL_SUBSIZE:-${pool_subsize_default}}"
epsilon="${EPSILON:-${epsilon_default}}"
initial_sample_method="${INITIAL_SAMPLE_METHOD:-${initial_sample_method_default}}"
initial_drk_model="${INITIAL_DRK_MODEL:-${initial_drk_model_default}}"
al_sample_batch_num="${AL_SAMPLE_BATCH_NUM:-${al_sample_batch_num_default}}"
al_sample_method="${AL_SAMPLE_METHOD:-${al_sample_method_default}}"

for query_num in "${query_num_arr[@]}"; do
  for run_seed in "${run_seed_arr[@]}"; do
    echo "Training extracted model: task=${task_name}, method=${method}, query_num=${query_num}, run_seed=${run_seed}"
    python original_steal.py \
      --victim_model_version "${vic_model}" \
      --victim_model_checkpoint "${vic_model_ck}" \
      --steal_model_version "${steal_model}" \
      --steal_model_checkpoint "${steal_model_ck}" \
      --task_name "${task_name}" \
      --visible_device "${visible_device}" \
      --weighted_cross_entropy "${weighted_cross_entropy}" \
      --tokenize_max_length "${tokenize_max_length}" \
      --batch_size "${batch_size}" \
      --optimizer "${optimizer}" \
      --learning_rate "${learning_rate}" \
      --weight_decay "${weight_decay}" \
      --num_epochs "${num_epochs}" \
      --num_labels "${num_labels}" \
      --run_seed "${run_seed}" \
      --query_num "${query_num}" \
      --method "${method}" \
      --pool_data_type "${pool_data_type}" \
      --prompt "${prompt}" \
      --pool_subsize "${pool_subsize}" \
      --epsilon "${epsilon}" \
      --initial_sample_method "${initial_sample_method}" \
      --initial_drk_model "${initial_drk_model}" \
      --al_sample_batch_num "${al_sample_batch_num}" \
      --al_sample_method "${al_sample_method}" \
      --pool_data_source "${pool_data_source}"
  done
done