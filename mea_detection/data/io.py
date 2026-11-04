"""Concrete query readers and dataset-folder discovery."""
import json
from pathlib import Path

from .datasets import context_of


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


