#!/usr/bin/env python3
from pathlib import Path

METHODS = ["MMD", "Mahalanobis", "PRADA", "SEAT", "CAP", "DATE"]
DATASETS = [
    "model_leeching",
    "Meaeq_AGNEWS",
    "Meaeq_HATESPEECH",
    "Meaeq_IMDB",
    "Meaeq_SST-2",
    "Query_efficent_med",
    "ME_BERT_boolq_random",
    "ME_BERT_boolq_wiki",
    "ME_BERT_mnli_random",
    "ME_BERT_mnli_wiki",
    "ME_BERT_squad_random",
    "ME_BERT_squad_wiki",
    "ME_BERT_sst2_random",
    "ME_BERT_sst2_wiki",
]
SEEDS = ["1", "20", "42"]
BATCH_SIZE = "1500"


def main() -> None:
    root = Path("new_main_experiment/outputs")
    done = []
    missing = []

    for method in METHODS:
        method_dir = method.lower()
        for seed in SEEDS:
            for dataset in DATASETS:
                metadata = root / method_dir / f"{dataset}_seed{seed}_bs{BATCH_SIZE}" / "metadata.json"
                if metadata.exists() and metadata.stat().st_size > 0:
                    done.append((method, dataset, seed))
                else:
                    missing.append((method, dataset, seed))

    expected = len(METHODS) * len(DATASETS) * len(SEEDS)
    print(f"expected={expected} done={len(done)} missing={len(missing)}")

    for method in METHODS:
        method_missing = [item for item in missing if item[0] == method]
        print(f"\n{method}: done={len(DATASETS) * len(SEEDS) - len(method_missing)}/42 missing={len(method_missing)}")
        for seed in SEEDS:
            datasets = [dataset for _, dataset, item_seed in method_missing if item_seed == seed]
            if datasets:
                print(f"  seed {seed}: {', '.join(datasets)}")

    print("\nResume commands by method:")
    for method in METHODS:
        if any(item[0] == method for item in missing):
            print(f"METHODS={method} bash new_main_experiment/run_new_main_experiment.sh")


if __name__ == "__main__":
    main()
