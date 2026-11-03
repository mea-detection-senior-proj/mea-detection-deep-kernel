"""Audit local data and fixed-count window capacity without loading an encoder."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

from data_pipeline.datasets import PARTITIONS, context_of, load_dataset, normalize, split_rows
from data_pipeline.windows import attacker_count

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (1, 20, 42)
WINDOWS = (100, 250, 500, 1500)
RATIOS = (.01, .05, .1, .25, 1.)
FAMILY_CANDIDATES = {
    "model_leeching": ("Model Leeching", "Context-based QA"),
    "Meaeq_SST-2": ("MeaeQ", "SST-2 sentiment"),
    "ME_BERT_sst2_wiki": ("ME_BERT", "SST-2 target / wiki query source"),
}


def file_sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def row_stats(rows):
    texts = {normalize(row["query"]) for row in rows}
    ids = {row["id"] for row in rows}
    contexts = [context_of(row["query"]) for row in rows]
    return {"raw_rows": len(rows), "unique_normalized_texts": len(texts),
            "duplicate_text_rows": len(rows) - len(texts), "unique_ids": len(ids),
            "parsed_context_rows": sum(c is not None for c in contexts),
            "unique_parsed_contexts": len({c for c in contexts if c is not None})}


def verify_partitions(partitions, policy):
    """Independent check of manifests against actual IDs, normalized text and contexts."""
    owners = {}
    for part, classes in partitions.items():
        for label, rows in classes.items():
            for row in rows:
                keys = [("id", row["id"]), ("text", normalize(row["query"]))]
                if label == "attack" and policy != "id-text-only" and context_of(row["query"]) is not None:
                    keys.append(("source", context_of(row["query"])))
                for key in keys:
                    if owners.setdefault(key, part) != part:
                        raise ValueError(f"Cross-partition {key[0]} collision")


def capacity_rows(dataset, seed, sizes):
    """Capacity means distinct rows within each window, not independent windows."""
    rows = []
    for size in WINDOWS:
        for ratio in RATIOS:
            na = attacker_count(size, ratio)
            needs = {"reference_benign": size, "calibration_benign": size,
                     "test_benign": size, "test_attack": na}
            pools = {"reference_benign": sizes["reference"]["benign"],
                     "calibration_benign": sizes["calibration"]["benign"],
                     "test_benign": sizes["test"]["benign"], "test_attack": sizes["test"]["attack"]}
            shortages = [f"{key}: {pools[key]} < {need}" for key, need in needs.items() if pools[key] < need]
            # Benign-only evaluation is required in every condition; the mixed-window
            # bound below is in addition to that requirement.
            bounds = [pools["test_attack"] // na]
            if size > na:
                bounds.append(pools["test_benign"] // (size - na))
            rows.append({"dataset": dataset, "seed": seed, "window_size": size,
                         "requested_ratio": ratio, "attacker_count": na, "actual_ratio": na / size,
                         "supported": not shortages, "shortages": "; ".join(shortages),
                         "benign_disjoint_test_windows_row_bound": pools["test_benign"] // size,
                         "condition_disjoint_test_windows_row_bound": min(bounds),
                         "disjoint_calibration_windows_row_bound": pools["calibration_benign"] // size})
    return rows


def training_rows(dataset, seed, sizes):
    # Provisional training sizes, not final objective/model choices.
    result = []
    for size in (100, 250):
        for ratio in (1., .01, .05, .1, .25):
            na = attacker_count(size, ratio)
            shortages = []
            for part in ("train", "validation"):
                # Reference benign and benign portion of incoming window must be disjoint.
                for label, need in (("benign", 2 * size - na), ("attack", na)):
                    if sizes[part][label] < need:
                        shortages.append(f"{part}_{label}: {sizes[part][label]} < {need}")
            result.append({"dataset": dataset, "seed": seed, "training_window_size": size,
                           "training_mode": "pure" if ratio == 1 else "mixed", "requested_ratio": ratio,
                           "attacker_count": na, "supported": not shortages, "shortages": "; ".join(shortages)})
    return result


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def provenance_records():
    path = ROOT / "pilot" / "ADDITIONAL_DATA_PROVENANCE.json"
    if not path.exists():
        return {}, None
    record = json.loads(path.read_text(encoding="utf-8-sig"))
    return {entry["path"].replace("\\", "/"): entry["sha256"] for entry in record["files"]}, record


def audit(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite audit: {output}")
    existing_hashes, prior_provenance = provenance_records()
    datasets, splits, feasibility, training, split_sets = {}, [], [], [], {}
    local = {p.name for p in (ROOT / "data").iterdir() if p.is_dir()}
    for name in sorted(local):
        paths = {"benign": ROOT / "data" / name / "normal/queries.jsonl",
                 "attack": ROOT / "data" / name / "attacker/queries.jsonl"}
        missing = [str(path) for path in paths.values() if not path.is_file()]
        if missing:
            datasets[name] = {"status": "missing", "missing": missing}
            continue
        print(f"Auditing {name}", flush=True)
        spec, benign, attack = load_dataset({"dataset": name, "data_root": "data"}, ROOT)
        rows = {"benign": benign, "attack": attack}
        stats = {label: row_stats(entries) for label, entries in rows.items()}
        collisions = {normalize(r["query"]) for r in rows["benign"]} & {normalize(r["query"]) for r in rows["attack"]}
        clean = {label: {normalize(r["query"]) for r in entries} - collisions for label, entries in rows.items()}
        family, domain = FAMILY_CANDIDATES.get(name, ("unclassified", "unclassified"))
        datasets[name] = {"status": "available", "spec": spec, "raw_stats": stats,
                          "clean_unique_rows": {label: len(texts) for label, texts in clean.items()},
                          "cross_label_unique_text_collisions": len(collisions),
                          "candidate_attack_family": family, "candidate_domain": domain,
                          "family_mapping_status": "candidate based on repository naming; original attack protocol not verified here",
                          "files": {label: {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                                              "sha256": file_sha256(path)} for label, path in paths.items()}}
        for entry in datasets[name]["files"].values():
            expected = existing_hashes.get(entry["path"].replace("\\", "/"))
            entry["prior_record_sha256_matches"] = entry["sha256"] == expected if expected else None
        for seed in SEEDS:
            partitions, details, _ = split_rows(rows["benign"], rows["attack"], seed, spec["grouping_policy"])
            verify_partitions(partitions, spec["grouping_policy"])
            total = {label: sum(len(partitions[p][label]) for p in PARTITIONS) for label in rows}
            if total != datasets[name]["clean_unique_rows"]:
                raise ValueError(f"Split retention mismatch for {name}: {total}")
            for part, classes in partitions.items():
                splits.append({"dataset": name, "seed": seed, "partition": part,
                               "benign": len(classes["benign"]), "attack": len(classes["attack"]),
                               "cross_partition_id_text_source_check": "passed"})
            feasibility.extend(capacity_rows(name, seed, details["sizes"]))
            training.extend(training_rows(name, seed, details["sizes"]))
            split_sets[name, seed] = {p: {label: {normalize(r["query"]) for r in entries}
                                         for label, entries in classes.items()} for p, classes in partitions.items()}
        datasets[name]["clean_text_sets"] = clean
    overlaps, transfer = [], []
    for left, right in itertools.combinations([n for n, d in datasets.items() if d["status"] == "available"], 2):
        for left_label, right_label in itertools.product(("benign", "attack"), repeat=2):
            a = datasets[left]["clean_text_sets"][left_label]
            b = datasets[right]["clean_text_sets"][right_label]
            overlap = len(a & b)
            overlaps.append({"left_dataset": left, "left_label": left_label, "right_dataset": right,
                             "right_label": right_label, "shared_normalized_texts": overlap,
                             "left_fraction": overlap / len(a) if a else 0, "right_fraction": overlap / len(b) if b else 0})
    for source, target in itertools.permutations([n for n, d in datasets.items() if d["status"] == "available"], 2):
        for seed in SEEDS:
            before_test = set().union(*(split_sets[source, seed][p][label]
                                       for p in PARTITIONS if p != "test" for label in ("benign", "attack")))
            for label in ("benign", "attack"):
                target_test = split_sets[target, seed]["test"][label]
                transfer.append({"source_dataset": source, "target_dataset": target, "seed": seed,
                                 "target_test_label": label, "target_test_rows": len(target_test),
                                 "shared_with_source_pretest_unique_texts": len(before_test & target_test)})
    for details in datasets.values():
        details.pop("clean_text_sets", None)
    report = {"scope": "Local files only; no downloads, embedding or model training",
              "seeds": SEEDS, "windows": WINDOWS, "ratios": RATIOS,
              "dataset_discovery": "folders under data/; no dataset registry or JSON required",
              "datasets": datasets, "prior_provenance_record": prior_provenance,
              "split_protocol": {"partitions": PARTITIONS, "source": "data_pipeline.datasets.split_rows",
                                 "split_code_sha256": file_sha256(ROOT / "data_pipeline" / "datasets.py")},
              "capacity_definition": "No replacement within each window; windows can overlap. Row-disjoint bounds do not prove source/user independence.",
              "cross_dataset_check": "Exact normalized text only; semantic near-duplicates and true source/user linkage not verified"}
    output.mkdir(parents=True, exist_ok=False)
    (output / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for name, entries in (("split_counts.csv", splits), ("window_capacity.csv", feasibility),
                          ("training_capacity.csv", training), ("dataset_overlap.csv", overlaps),
                          ("cross_dataset_pretest_overlap.csv", transfer)):
        if entries:
            write_csv(output / name, entries)
    lines = ["# Local dataset readiness audit", "", "## Clean counts and candidate families", "",
             "| Dataset | Raw benign / attack | Clean benign / attack | Candidate family |", "|---|---:|---:|---|"]
    for name, details in datasets.items():
        if details["status"] == "available":
            raw, clean = details["raw_stats"], details["clean_unique_rows"]
            lines.append(f"| {name} | {raw['benign']['raw_rows']} / {raw['attack']['raw_rows']} | {clean['benign']} / {clean['attack']} | {details['candidate_attack_family']} |")
    lines += ["", "Family/domain labels are candidates inferred from repository names, not verified attack-family isolation.",
              "", "## Grid supported across all three seeds", "",
              "| Dataset | Window | Supported requested ratios |", "|---|---:|---|"]
    for name, details in datasets.items():
        if details["status"] != "available":
            continue
        for size in WINDOWS:
            supported = [r for r in RATIOS if all(row["supported"] for row in feasibility
                                                if row["dataset"] == name and row["window_size"] == size and row["requested_ratio"] == r)]
            lines.append(f"| {name} | {size} | {', '.join(f'{r:g}' for r in supported) or 'none'} |")
    lines += ["", "## Nonzero exact normalized-text overlaps", ""]
    for row in overlaps:
        if row["shared_normalized_texts"]:
            lines.append(f"- {row['left_dataset']} ({row['left_label']}) / {row['right_dataset']} ({row['right_label']}): {row['shared_normalized_texts']} shared texts")
    lines += ["", "## Interpretation limits", "",
              "- Capacity is per window. Repeated sampling does not create independent new queries.",
              "- Inspect split_counts.csv and window_capacity.csv for seed-level counts and shortages.",
              "- training_capacity.csv uses provisional training sizes 100/250, not a locked training design.",
              "- cross_dataset_pretest_overlap.csv checks target test texts against every source pretest partition; positive counts require global decontamination before cross-dataset evaluation.",
              "- Exact normalized text/ID grouping does not verify semantic near-duplicates, campaigns or users.",
              "- No detector performance has been measured by this audit."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Audit written to {output}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "data_readiness")
    args = parser.parse_args()
    audit(args.output)


if __name__ == "__main__":
    main()
