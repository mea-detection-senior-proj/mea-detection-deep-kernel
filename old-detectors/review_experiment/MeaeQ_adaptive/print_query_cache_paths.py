#!/usr/bin/env python3
"""Dry-run MeaeQ query cache paths without importing model code.

This mirrors shell/gen_query.sh plus utils.tools path construction so you can
check whether the slow query-generation stage should hit existing cache files.
"""

from __future__ import annotations

import os
from pathlib import Path


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return default if value in (None, "") else int(value)


def task_query_nums(task_name: str) -> list[int]:
    query_nums = os.environ.get("QUERY_NUMS")
    if query_nums:
        return [int(x) for x in query_nums.replace(",", " ").split()]
    if task_name == "HATESPEECH":
        return [191, 382, 574]
    if task_name == "SST-2":
        return [201, 335, 536]
    if task_name == "IMDB":
        return [120, 200, 320]
    if task_name == "AGNEWS":
        return [360, 600, 960]
    raise ValueError(f"Unknown TASK_NAME={task_name}")


def method_defaults(task_name: str, method: str) -> dict[str, object]:
    defaults: dict[str, object] = {
        "pool_data_source": "wiki",
        "pool_data_type": "None",
        "prompt": "None",
        "pool_subsize": -1,
        "epsilon": -1.0,
        "initial_sample_method": "None",
        "initial_drk_model": "None",
    }

    if method == "RS":
        defaults["pool_data_type"] = "whole"
        defaults["initial_sample_method"] = "RS"
    elif method == "sub-RS":
        defaults["pool_data_type"] = "random_subset"
        defaults["pool_subsize"] = 212630 if task_name == "AGNEWS" else 1561 if task_name == "HATESPEECH" else 1766
        defaults["initial_sample_method"] = "RS"
    elif method == "random-sst2":
        defaults["pool_data_source"] = "sst2"
        defaults["pool_data_type"] = "whole"
        defaults["initial_sample_method"] = "random_sentence"
    elif method == "random-imdb":
        defaults["pool_data_source"] = "imdb"
        defaults["pool_data_type"] = "whole"
        defaults["initial_sample_method"] = "random_sentence"
    elif method == "TRF":
        defaults["pool_data_type"] = "reduced_subset_by_prompt"
        defaults["prompt"] = prompt_for_task(task_name)
        defaults["epsilon"] = 0.95
        defaults["initial_sample_method"] = "random_sentence"
    elif method == "DRC":
        defaults["pool_data_type"] = "random_subset"
        defaults["pool_subsize"] = 212630 if task_name == "AGNEWS" else 1561 if task_name == "HATESPEECH" else 1766
        defaults["initial_sample_method"] = "data_reduction_kmeans"
        defaults["initial_drk_model"] = "bart-large-mnli"
    elif method in ("MeaeQ", "MeaeQ-regularized", "MeaeQ-projection"):
        defaults["pool_data_type"] = "reduced_subset_by_prompt"
        defaults["prompt"] = prompt_for_task(task_name)
        defaults["epsilon"] = 0.95
        defaults["initial_sample_method"] = "data_reduction_kmeans"
        defaults["initial_drk_model"] = "bart-large-mnli"
    return defaults


def prompt_for_task(task_name: str) -> str:
    if task_name in ("SST-2", "IMDB"):
        return "This is a movie review."
    if task_name == "AGNEWS":
        return "This is a news."
    if task_name == "HATESPEECH":
        return "This is a hate speech"
    return "None"


def path_part(prefix: str, value: object) -> str:
    normalized = str(value).replace(' ', '-')
    if prefix == "prompt":
        normalized = normalized.replace('.', '')
    return f"{prefix}={normalized}"


def main() -> None:
    project_root = Path(__file__).resolve().parent
    root = Path(env("QUERY_POOL_ROOT", str(project_root / "steal" / "query_and_pool")))

    task_name = env("TASK_NAME", "HATESPEECH")
    method = env("METHOD", "MeaeQ")
    seed = env_int("SEED", 56)
    defaults = method_defaults(task_name, method)

    pool_data_source = env("POOL_DATA_SOURCE", str(defaults["pool_data_source"]))
    pool_data_type = env("POOL_DATA_TYPE", str(defaults["pool_data_type"]))
    prompt = env("PROMPT", str(defaults["prompt"]))
    pool_subsize = env_int("POOL_SUBSIZE", int(defaults["pool_subsize"]))
    epsilon = float(env("EPSILON", str(defaults["epsilon"])))
    initial_sample_method = env("INITIAL_SAMPLE_METHOD", str(defaults["initial_sample_method"]))
    initial_drk_model = env("INITIAL_DRK_MODEL", str(defaults["initial_drk_model"]))

    pool_dir = root / path_part("seed", seed) / path_part("task_name", task_name) / path_part("pool_data_source", pool_data_source) / path_part("pool_data_type", pool_data_type) / path_part("prompt", prompt) / path_part("pool_subsize", pool_subsize)

    print("MeaeQ gen_query cache dry-run")
    print(f"project_root: {project_root}")
    print(f"task_name: {task_name}")
    print(f"method: {method}")
    print(f"seed: {seed}  (gen_query cache seed; RUN_SEEDS is for training)")
    print(f"query_nums: {task_query_nums(task_name)}")
    print(f"pool_data_source: {pool_data_source}")
    print(f"pool_data_type: {pool_data_type}")
    print(f"prompt: {prompt}")
    print(f"pool_subsize: {pool_subsize}")
    print()

    pool_sentence = pool_dir / "pool_data_sentence.pickle"
    pool_pb = pool_dir / "pool_data_pb.pickle"
    print("Pool cache:")
    for p in (pool_sentence, pool_pb):
        print(f"  {p}  exists={p.exists()}")
    print()

    print("Final query caches:")
    for query_num in task_query_nums(task_name):
        query_dir = pool_dir
        if method != "MeaeQ" and method.startswith("MeaeQ-"):
            query_dir = query_dir / path_part("method", method)
        query_dir = query_dir / path_part("epsilon", epsilon) / path_part("initial_sample_method", initial_sample_method) / path_part("initial_drk_model", initial_drk_model) / path_part("query_num", query_num)
        for p in (query_dir / "query_content.pickle", query_dir / "query_label.pickle"):
            print(f"  {p}  exists={p.exists()}")


if __name__ == "__main__":
    main()