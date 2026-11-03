"""Group-disjoint splits using inspected query identity and source information."""
import hashlib
import json
from pathlib import Path
import unicodedata

import numpy as np

PARTITIONS = ("train", "validation", "reference", "calibration", "test")
FRACTIONS = (.2, .1, .25, .2, .25)


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def context_of(text):
    marker = "Can you answer this question briefly:"
    if text.startswith("Given this context:") and marker in text:
        return normalize(text.split(marker, 1)[0])
    return None


def read_rows(path):
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                                                for k in ("id", "query")):
                raise ValueError(f"{path}:{line_no}: expected nonempty string id and query")
            rows.append({"id": row["id"].strip(), "query": row["query"].strip()})
    if not rows:
        raise ValueError(f"Empty dataset: {path}")
    return rows


def load_dataset(config, project_root):
    """Read a standard data/<name> folder; retain explicit specs for older callers."""
    def resolve(value):
        path = Path(value)
        return path if path.is_absolute() else Path(project_root) / path

    if config.get("dataset"):
        name = config["dataset"]
        if Path(name).name != name or name in (".", "..") or any(c in name for c in "/\\:"):
            raise ValueError("dataset must be one folder name under data_root")
        paths = [resolve(config["data_root"]) / name / label / "queries.jsonl" for label in ("normal", "attacker")]
        missing = [str(p) for p in paths if not p.is_file()]
        if missing:
            raise FileNotFoundError("Dataset requires normal/queries.jsonl and attacker/queries.jsonl. Missing: " + ", ".join(missing))
        benign, attack = map(read_rows, paths)
        parsed = sum(context_of(r["query"]) is not None for r in attack)
        policy = "id-text-attack-context" if parsed == len(attack) else "id-text-available-context" if parsed else "id-text-only"
        spec = {"name": name, "benign_path": f"{name}/normal/queries.jsonl", "attack_path": f"{name}/attacker/queries.jsonl",
                "grouping_policy": policy, "provenance_notes": "Discovered from data folder; available IDs, normalized text and recognized attack contexts are grouped. Source/user independence is not verified.",
                "recognized_attack_context_rows": parsed, "attack_rows": len(attack)}
        return spec, benign, attack
    # Compatibility only: new experiments do not need dataset JSON files.
    spec = json.loads(resolve(config["dataset_config"]).read_text(encoding="utf-8-sig"))
    required = {"name", "benign_path", "attack_path", "grouping_policy", "provenance_notes"}
    if set(spec) != required or any(not isinstance(v, str) or not v.strip() for v in spec.values()):
        raise ValueError(f"Dataset specification must contain exactly {sorted(required)}")
    paths = []
    for key in ("benign_path", "attack_path"):
        path = Path(spec[key])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Dataset paths must stay inside data_root")
        paths.append(resolve(config["data_root"]) / path)
    benign, attack = map(read_rows, paths)
    return spec, benign, attack


def split_rows(benign, attack, seed, grouping_policy):
    """Keep transitive ID/text/source groups intact; remove cross-label text ambiguity."""
    if grouping_policy not in ("id-text-only", "id-text-attack-context", "id-text-available-context"):
        raise ValueError("Unknown grouping policy")
    rows = [("benign", r) for r in benign] + [("attack", r) for r in attack]
    parent = list(range(len(rows)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, (label, row) in enumerate(rows):
        keys = [("id", row["id"]), ("text", normalize(row["query"]))]
        if label == "attack" and grouping_policy != "id-text-only":
            context = context_of(row["query"])
            if context is None and grouping_policy == "id-text-attack-context":
                raise ValueError("Attack source context missing under strict context policy")
            if context is not None:
                keys.append(("context", context))
        for key in keys:
            if key in seen:
                parent[root(i)] = root(seen[key])
            else:
                seen[key] = i
    collisions = {normalize(r["query"]) for r in benign} & {normalize(r["query"]) for r in attack}
    groups = {}
    for i, item in enumerate(rows):
        if normalize(item[1]["query"]) not in collisions:
            groups.setdefault(root(i), []).append(item)
    groups = list(groups.values())
    np.random.default_rng(seed).shuffle(groups)
    sizes = [int(len(groups) * f) for f in FRACTIONS[:-1]]
    sizes.append(len(groups) - sum(sizes))
    partitions = {part: {"benign": [], "attack": []} for part in PARTITIONS}
    cursor = 0
    for part, size in zip(PARTITIONS, sizes):
        used = set()
        for group in groups[cursor:cursor + size]:
            for label, row in group:
                key = (label, normalize(row["query"]))
                if key not in used:
                    partitions[part][label].append(row)
                    used.add(key)
        cursor += size
    manifest = {part: {label: [{"id_sha256": digest(r["id"]),
                               "text_sha256": digest(normalize(r["query"]))} for r in entries]
                       for label, entries in classes.items()} for part, classes in partitions.items()}
    audit = {"grouping_policy": grouping_policy, "groups": len(groups),
             "source_provenance_available": grouping_policy == "id-text-attack-context",
             "recognized_attack_context_rows": sum(context_of(r["query"]) is not None for r in attack),
             "cross_label_unique_texts_removed": len(collisions),
             "group_fractions": dict(zip(PARTITIONS, FRACTIONS)),
             "sizes": {p: {label: len(items) for label, items in classes.items()}
                       for p, classes in partitions.items()}}
    return partitions, audit, manifest
