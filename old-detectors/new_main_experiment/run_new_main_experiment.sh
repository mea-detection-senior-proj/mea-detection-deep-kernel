#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

DEFAULT_DATASETS="model_leeching,Meaeq_AGNEWS,Meaeq_HATESPEECH,Meaeq_IMDB,Meaeq_SST-2,Query_efficent_med,ME_BERT_boolq_random,ME_BERT_boolq_wiki,ME_BERT_mnli_random,ME_BERT_mnli_wiki,ME_BERT_squad_random,ME_BERT_squad_wiki,ME_BERT_sst2_random,ME_BERT_sst2_wiki"
DATASETS="${DATASETS:-${DEFAULT_DATASETS}}"
SEEDS="${SEEDS:-1 20 42}"
METHODS="${METHODS:-MMD Mahalanobis PRADA SEAT PseudoEnergy CAP DATE}"

BATCH_SIZE="${BATCH_SIZE:-1500}"
DEVICE="${DEVICE:-cuda}"
MMD_DEVICE="${MMD_DEVICE:-${DEVICE}}"
COMPUTE_DEVICE="${COMPUTE_DEVICE:-${DEVICE}}"

EMBEDDING_MODEL="${EMBEDDING_MODEL:-BAAI/bge-small-en-v1.5}"
QUERY_PREFIX="${QUERY_PREFIX:-}"
MMD_REFERENCE_REPEATS="${MMD_REFERENCE_REPEATS:-20}"
MMD_NULL_SAMPLES="${MMD_NULL_SAMPLES:-1000}"

EXPERIMENT_ROOT="${EXPERIMENT_ROOT:-new_main_experiment}"
RESULT_ROOT="${RESULT_ROOT:-${EXPERIMENT_ROOT}/results}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${EXPERIMENT_ROOT}/outputs}"
CACHE_ROOT="${CACHE_ROOT:-${EXPERIMENT_ROOT}/cache}"
LOG_ROOT="${LOG_ROOT:-${EXPERIMENT_ROOT}/logs}"
ROW_ROOT="${ROW_ROOT:-${RESULT_ROOT}/rows}"

FORCE="${FORCE:-0}"
PARALLEL_METHODS="${PARALLEL_METHODS:-1}"
MAX_METHOD_JOBS="${MAX_METHOD_JOBS:-0}"
DATE_CHECKPOINT_WARMUP="${DATE_CHECKPOINT_WARMUP:-1}"

DATE_MODEL_NAME="${DATE_MODEL_NAME:-google/electra-small-discriminator}"
DATE_GENERATOR="${DATE_GENERATOR:-learned}"
DATE_GENERATOR_MODEL_NAME="${DATE_GENERATOR_MODEL_NAME:-google/electra-small-generator}"

SUMMARY_CSV="${SUMMARY_CSV:-${RESULT_ROOT}/new_main_experiment_runs_bs${BATCH_SIZE}.csv}"
OVERALL_CSV="${OVERALL_CSV:-${RESULT_ROOT}/new_main_experiment_overall_bs${BATCH_SIZE}.csv}"

mkdir -p "${RESULT_ROOT}" "${OUTPUT_ROOT}" "${CACHE_ROOT}" "${LOG_ROOT}" "${ROW_ROOT}"
rm -f "${ROW_ROOT}"/*.csv

write_header() {
  printf "method,dataset,seed,batch_size,embedding_model,query_prefix,mmd_reference_repeats,mmd_null_samples,benign_fpr,5pct_tpr,10pct_tpr,25pct_tpr,50pct_tpr,100pct_tpr,avg_tpr,balanced_acc,output_dir,metadata_path,log_file,status\n"
}

write_header > "${SUMMARY_CSV}"

ensure_date_checkpoints() {
  if [[ "${DATE_CHECKPOINT_WARMUP}" != "1" ]]; then
    return 0
  fi
  if [[ " ${METHODS} " != *" DATE "* ]]; then
    return 0
  fi

  echo "Checking DATE HuggingFace checkpoints before DATE runs..."
  python3 - <<PY
from transformers import AutoModel, AutoModelForMaskedLM, AutoTokenizer

model_name = "${DATE_MODEL_NAME}"
generator = "${DATE_GENERATOR}"
generator_model_name = "${DATE_GENERATOR_MODEL_NAME}"

def ensure_tokenizer_and_model(name, model_cls=None):
    try:
        AutoTokenizer.from_pretrained(name, use_fast=True, local_files_only=True)
        if model_cls is not None:
            model_cls.from_pretrained(name, local_files_only=True)
        print(f"[local] {name}")
    except Exception:
        print(f"[download] {name}")
        AutoTokenizer.from_pretrained(name, use_fast=True)
        if model_cls is not None:
            model_cls.from_pretrained(name)

ensure_tokenizer_and_model(model_name, AutoModel)
if generator == "learned":
    ensure_tokenizer_and_model(generator_model_name, AutoModelForMaskedLM)
PY
}

append_summary() {
  local method="$1"
  local dataset="$2"
  local seed="$3"
  local output_dir="$4"
  local log_file="$5"
  local status="$6"
  local row_file="${ROW_ROOT}/${method}_${dataset}_seed${seed}.csv"

  python3 - <<PY > "${row_file}"
import csv
import json
import math
import sys
from pathlib import Path

method = ${method@Q}
dataset = ${dataset@Q}
seed = ${seed@Q}
batch_size = ${BATCH_SIZE@Q}
embedding_model = ${EMBEDDING_MODEL@Q} if method != "DATE" else "N/A"
query_prefix = ${QUERY_PREFIX@Q} if method != "DATE" else "N/A"
mmd_reference_repeats = ${MMD_REFERENCE_REPEATS@Q} if method == "MMD" else "N/A"
mmd_null_samples = ${MMD_NULL_SAMPLES@Q} if method == "MMD" else "N/A"
output_dir = ${output_dir@Q}
metadata_path = str(Path(output_dir) / "metadata.json")
log_file = ${log_file@Q}
status = ${status@Q}

def rate(by_split, key):
    try:
        return float(by_split[key]["detection_rate"]) * 100.0
    except Exception:
        return float("nan")

row = {
    "method": method,
    "dataset": dataset,
    "seed": seed,
    "batch_size": batch_size,
    "embedding_model": embedding_model,
    "query_prefix": query_prefix,
    "mmd_reference_repeats": mmd_reference_repeats,
    "mmd_null_samples": mmd_null_samples,
    "benign_fpr": "nan",
    "5pct_tpr": "nan",
    "10pct_tpr": "nan",
    "25pct_tpr": "nan",
    "50pct_tpr": "nan",
    "100pct_tpr": "nan",
    "avg_tpr": "nan",
    "balanced_acc": "nan",
    "output_dir": output_dir,
    "metadata_path": metadata_path,
    "log_file": log_file,
    "status": status,
}

path = Path(metadata_path)
if path.exists() and status == "0":
    meta = json.loads(path.read_text(encoding="utf-8"))
    by = meta.get("metrics_by_split", {})
    fpr = rate(by, "heldout_benign")
    tprs = {
        "5pct_tpr": rate(by, "mixed_0.05"),
        "10pct_tpr": rate(by, "mixed_0.1"),
        "25pct_tpr": rate(by, "mixed_0.25"),
        "50pct_tpr": rate(by, "mixed_0.5"),
        "100pct_tpr": rate(by, "attacker"),
    }
    vals = [v for v in tprs.values() if not math.isnan(v)]
    avg = sum(vals) / len(vals) if vals else float("nan")
    bal = (avg + 100.0 - fpr) / 2.0 if not math.isnan(avg) and not math.isnan(fpr) else float("nan")
    row["benign_fpr"] = f"{fpr:.6f}"
    row["avg_tpr"] = f"{avg:.6f}"
    row["balanced_acc"] = f"{bal:.6f}"
    row.update({k: f"{v:.6f}" for k, v in tprs.items()})

writer = csv.DictWriter(sys.stdout, fieldnames=[
    "method", "dataset", "seed", "batch_size", "embedding_model", "query_prefix",
    "mmd_reference_repeats", "mmd_null_samples", "benign_fpr", "5pct_tpr",
    "10pct_tpr", "25pct_tpr", "50pct_tpr", "100pct_tpr", "avg_tpr",
    "balanced_acc", "output_dir", "metadata_path", "log_file", "status",
])
writer.writerow(row)
PY
}

combine_results() {
  write_header > "${SUMMARY_CSV}"
  if compgen -G "${ROW_ROOT}/*.csv" >/dev/null; then
    cat "${ROW_ROOT}"/*.csv >> "${SUMMARY_CSV}"
  fi
}

write_overall() {
  python3 - <<PY
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

summary = Path(${SUMMARY_CSV@Q})
overall = Path(${OVERALL_CSV@Q})
metrics = ["benign_fpr", "5pct_tpr", "10pct_tpr", "25pct_tpr", "50pct_tpr", "100pct_tpr", "avg_tpr", "balanced_acc"]
rows = []
if summary.exists():
    with summary.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("status") == "0"]

groups = defaultdict(list)
for row in rows:
    groups[row["method"]].append(row)

fields = ["method", "runs"]
for metric in metrics:
    fields += [f"{metric}_mean", f"{metric}_std"]

with overall.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for method in sorted(groups):
        group = groups[method]
        out = {"method": method, "runs": str(len(group))}
        for metric in metrics:
            vals = []
            for row in group:
                try:
                    val = float(row[metric])
                except Exception:
                    val = float("nan")
                if not math.isnan(val):
                    vals.append(val)
            out[f"{metric}_mean"] = f"{statistics.mean(vals):.6f}" if vals else "nan"
            out[f"{metric}_std"] = f"{statistics.stdev(vals):.6f}" if len(vals) > 1 else ("0.000000" if vals else "nan")
        writer.writerow(out)
PY
}

run_method() {
  local method="$1"
  local dataset="$2"
  local seed="$3"
  local method_lc
  method_lc="$(echo "${method}" | tr '[:upper:]' '[:lower:]')"

  local run_id="${method_lc}/${dataset}_seed${seed}_bs${BATCH_SIZE}"
  local output_dir="${OUTPUT_ROOT}/${run_id}"
  local cache_dir="${CACHE_ROOT}/${method_lc}"
  local log_dir="${LOG_ROOT}/${method_lc}"
  local log_file="${log_dir}/${dataset}_seed${seed}_bs${BATCH_SIZE}.log"
  local metadata_path="${output_dir}/metadata.json"

  mkdir -p "${output_dir}" "${cache_dir}" "${log_dir}"

  if [[ "${FORCE}" != "1" && -f "${metadata_path}" ]]; then
    echo "Skipping existing run: ${method} ${dataset} seed=${seed}"
    append_summary "${method}" "${dataset}" "${seed}" "${output_dir}" "${log_file}" "0"
    return 0
  fi

  echo "============================================================"
  echo "Method: ${method}"
  echo "Dataset: ${dataset}"
  echo "Seed: ${seed}"
  echo "Output dir: ${output_dir}"
  echo "Log file: ${log_file}"
  if [[ "${method}" != "DATE" ]]; then
    echo "Embedding model: ${EMBEDDING_MODEL}"
    echo "Query prefix: ${QUERY_PREFIX}"
  fi
  if [[ "${method}" == "MMD" ]]; then
    echo "MMD reference repeats: ${MMD_REFERENCE_REPEATS}"
    echo "MMD null samples: ${MMD_NULL_SAMPLES}"
  fi
  echo "============================================================"

  set +e
  case "${method}" in
    MMD)
      env DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${seed}" \
        DEVICE="${DEVICE}" MMD_DEVICE="${MMD_DEVICE}" \
        EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
        REFERENCE_REPEATS="${MMD_REFERENCE_REPEATS}" NULL_SAMPLES="${MMD_NULL_SAMPLES}" \
        CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
        bash MMD_detection/run_mmd_detection_gpu.sh > "${log_file}" 2>&1
      ;;
    Mahalanobis)
      env DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${seed}" \
        DEVICE="${DEVICE}" EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
        CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
        bash Mahalanobis/run_mahalanobis_detection.sh > "${log_file}" 2>&1
      ;;
    PRADA)
      env DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${seed}" \
        DEVICE="${DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
        EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
        CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
        bash PRADA/run_prada_detection.sh > "${log_file}" 2>&1
      ;;
    SEAT)
      env DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${seed}" \
        DEVICE="${DEVICE}" COMPUTE_DEVICE="${COMPUTE_DEVICE}" \
        EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
        CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
        bash SEAT/run_seat_detection.sh > "${log_file}" 2>&1
      ;;
    PseudoEnergy)
      env DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${seed}" \
        DEVICE="${DEVICE}" EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
        SCORE_MODE="two_sided" CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
        bash PseudoEnergy/run_pseudo_energy_detection.sh > "${log_file}" 2>&1
      ;;
    CAP)
      env DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${seed}" \
        DEVICE="${DEVICE}" EMBEDDING_MODEL="${EMBEDDING_MODEL}" QUERY_PREFIX="${QUERY_PREFIX}" \
        CACHE_DIR="${cache_dir}" OUTPUT_DIR="${output_dir}" \
        bash CAP/run_cap_detection.sh > "${log_file}" 2>&1
      ;;
    DATE)
      env DATASET="${dataset}" BATCH_SIZE="${BATCH_SIZE}" SEED="${seed}" \
        DEVICE="${DEVICE}" OUTPUT_DIR="${output_dir}" \
        MODEL_NAME="${DATE_MODEL_NAME}" GENERATOR="${DATE_GENERATOR}" \
        GENERATOR_MODEL_NAME="${DATE_GENERATOR_MODEL_NAME}" \
        bash DATE/run_date_detection.sh > "${log_file}" 2>&1
      ;;
    *)
      echo "Unknown method: ${method}" > "${log_file}"
      false
      ;;
  esac
  local status="$?"
  set -e

  append_summary "${method}" "${dataset}" "${seed}" "${output_dir}" "${log_file}" "${status}"

  if [[ "${status}" != "0" ]]; then
    echo "Run failed: ${method} ${dataset} seed=${seed}. See ${log_file}" >&2
    return "${status}"
  fi
}

running_method_jobs() {
  jobs -rp | wc -l
}

wait_for_method_slot() {
  if [[ "${MAX_METHOD_JOBS}" -le 0 ]]; then
    return 0
  fi
  while [[ "$(running_method_jobs)" -ge "${MAX_METHOD_JOBS}" ]]; do
    sleep 2
  done
}

run_method_suite() {
  local method="$1"
  local seed
  local raw_dataset
  local dataset

  for seed in ${SEEDS}; do
    for raw_dataset in ${dataset_items}; do
      dataset="$(echo "${raw_dataset}" | xargs)"
      [[ -z "${dataset}" ]] && continue
      run_method "${method}" "${dataset}" "${seed}"
    done
  done
}

echo "Running new main experiment..."
echo "Datasets: ${DATASETS}"
echo "Seeds: ${SEEDS}"
echo "Methods: ${METHODS}"
echo "Parallel methods: ${PARALLEL_METHODS}"
if [[ "${PARALLEL_METHODS}" == "1" ]]; then
  echo "Max method jobs: ${MAX_METHOD_JOBS} (0 means all methods at once)"
fi
echo "Embedding model: ${EMBEDDING_MODEL}"
echo "MMD reference repeats: ${MMD_REFERENCE_REPEATS}"
echo "MMD null samples: ${MMD_NULL_SAMPLES}"
echo "Summary CSV: ${SUMMARY_CSV}"
echo

ensure_date_checkpoints

dataset_items="${DATASETS//,/ }"
failed=0

if [[ "${PARALLEL_METHODS}" == "1" ]]; then
  pids=()
  for method in ${METHODS}; do
    wait_for_method_slot
    run_method_suite "${method}" &
    pids+=("$!")
  done

  for pid in "${pids[@]}"; do
    if ! wait "${pid}"; then
      failed=1
    fi
  done
else
  for method in ${METHODS}; do
    if ! run_method_suite "${method}"; then
      failed=1
      combine_results
      write_overall
      exit 1
    fi
  done
fi

combine_results
write_overall

if [[ "${failed}" != "0" ]]; then
  echo "At least one run failed. Check logs in ${LOG_ROOT}." >&2
  exit 1
fi

echo
echo "Finished new main experiment."
echo "Run summary: ${SUMMARY_CSV}"
echo "Overall summary: ${OVERALL_CSV}"
