#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}/steal/model_steal"

task_name="${TASK_NAME:-HATESPEECH}" # SST-2, IMDB, AGNEWS, HATESPEECH
method="${METHOD:-MeaeQ}" # MeaeQ, MeaeQ-regularized, MeaeQ-projection; also supports RS/TRF/DRC/random baselines
visible_device="${VISIBLE_DEVICE:-0}"
victim_model_version="${VICTIM_MODEL_VERSION:-bert_base_uncased}"
bart_large_mnli_path="${BART_LARGE_MNLI_PATH:-../../pretrained_model/bart_large_mnli}"
only_query="${ONLY_QUERY:-0}"

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

if [[ "${task_name}" == "SST-2" ]]; then
  num_labels_default=2
elif [[ "${task_name}" == "IMDB" ]]; then
  num_labels_default=2
elif [[ "${task_name}" == "AGNEWS" ]]; then
  tokenize_max_length_default=256
  batch_size_default=16
  learning_rate_default="5e-5"
  num_labels_default=4
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

pool_data_source_default="wiki"
pool_data_type_default="None"
prompt_default="None"
pool_subsize_default=-1
epsilon_default=-1
initial_sample_method_default="None"
initial_drk_model_default="None"

if [[ "${method}" == "RS" ]]; then
  pool_data_type_default="whole"
  initial_sample_method_default="RS"
elif [[ "${method}" == "sub-RS" ]]; then
  pool_data_type_default="random_subset"
  if [[ "${task_name}" == "SST-2" || "${task_name}" == "IMDB" ]]; then
    pool_subsize_default=1766
  elif [[ "${task_name}" == "AGNEWS" ]]; then
    pool_subsize_default=212630
  elif [[ "${task_name}" == "HATESPEECH" ]]; then
    pool_subsize_default=1561
  fi
  initial_sample_method_default="RS"
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
fi

pool_data_source="${POOL_DATA_SOURCE:-${pool_data_source_default}}"
pool_data_type="${POOL_DATA_TYPE:-${pool_data_type_default}}"
prompt="${PROMPT:-${prompt_default}}"
pool_subsize="${POOL_SUBSIZE:-${pool_subsize_default}}"
epsilon="${EPSILON:-${epsilon_default}}"
initial_sample_method="${INITIAL_SAMPLE_METHOD:-${initial_sample_method_default}}"
initial_drk_model="${INITIAL_DRK_MODEL:-${initial_drk_model_default}}"

adaptive_candidate_multiplier="${ADAPTIVE_CANDIDATE_MULTIPLIER:-5}"
adaptive_lambda="${ADAPTIVE_LAMBDA:-1.0}"
adaptive_normal_path="${ADAPTIVE_NORMAL_PATH:-}"
adaptive_reference_size="${ADAPTIVE_REFERENCE_SIZE:-1500}"
adaptive_normal_pool_limit="${ADAPTIVE_NORMAL_POOL_LIMIT:-10000}"
adaptive_text_field="${ADAPTIVE_TEXT_FIELD:-query}"
adaptive_embedding_model="${ADAPTIVE_EMBEDDING_MODEL:-BAAI/bge-small-en-v1.5}"
adaptive_embed_batch_size="${ADAPTIVE_EMBED_BATCH_SIZE:-64}"
adaptive_embed_device="${ADAPTIVE_EMBED_DEVICE:-cuda}"
adaptive_query_prefix="${ADAPTIVE_QUERY_PREFIX:-}"
adaptive_cache_dir="${ADAPTIVE_CACHE_DIR:-${PROJECT_ROOT}/../cache/meaeq_adaptive_embeddings}"
adaptive_mmd_device="${ADAPTIVE_MMD_DEVICE:-cuda}"
adaptive_mmd_dtype="${ADAPTIVE_MMD_DTYPE:-float32}"
adaptive_mmd_batch_size="${ADAPTIVE_MMD_BATCH_SIZE:-64}"
adaptive_penalty_windows="${ADAPTIVE_PENALTY_WINDOWS:-200}"
adaptive_bandwidth_sample_size="${ADAPTIVE_BANDWIDTH_SAMPLE_SIZE:-1000}"
adaptive_null_samples="${ADAPTIVE_NULL_SAMPLES:-200}"
adaptive_threshold_percentile="${ADAPTIVE_THRESHOLD_PERCENTILE:-95}"

for query_num in "${query_num_arr[@]}"; do
  echo "Generating/labelling queries: task=${task_name}, method=${method}, query_num=${query_num}, only_query=${only_query}"
  cmd=(
    python gen_query.py
    --victim_model_version "${victim_model_version}"
    --task_name "${task_name}"
    --visible_device "${visible_device}"
    --tokenize_max_length "${tokenize_max_length}"
    --num_labels "${num_labels}"
    --query_num "${query_num}"
    --method "${method}"
    --pool_data_type "${pool_data_type}"
    --prompt "${prompt}"
    --pool_subsize "${pool_subsize}"
    --epsilon "${epsilon}"
    --initial_sample_method "${initial_sample_method}"
    --initial_drk_model "${initial_drk_model}"
    --bart_large_mnli_path "${bart_large_mnli_path}"
    --pool_data_source "${pool_data_source}"
    --adaptive_candidate_multiplier "${adaptive_candidate_multiplier}"
    --adaptive_lambda "${adaptive_lambda}"
    --adaptive_normal_path "${adaptive_normal_path}"
    --adaptive_reference_size "${adaptive_reference_size}"
    --adaptive_normal_pool_limit "${adaptive_normal_pool_limit}"
    --adaptive_text_field "${adaptive_text_field}"
    --adaptive_embedding_model "${adaptive_embedding_model}"
    --adaptive_embed_batch_size "${adaptive_embed_batch_size}"
    --adaptive_embed_device "${adaptive_embed_device}"
    --adaptive_query_prefix "${adaptive_query_prefix}"
    --adaptive_cache_dir "${adaptive_cache_dir}"
    --adaptive_mmd_device "${adaptive_mmd_device}"
    --adaptive_mmd_dtype "${adaptive_mmd_dtype}"
    --adaptive_mmd_batch_size "${adaptive_mmd_batch_size}"
    --adaptive_penalty_windows "${adaptive_penalty_windows}"
    --adaptive_bandwidth_sample_size "${adaptive_bandwidth_sample_size}"
    --adaptive_null_samples "${adaptive_null_samples}"
    --adaptive_threshold_percentile "${adaptive_threshold_percentile}"
  )
  if [[ "${only_query}" == "1" || "${only_query}" == "true" || "${only_query}" == "True" ]]; then
    cmd+=(--only_query)
  fi
  "${cmd[@]}"
done