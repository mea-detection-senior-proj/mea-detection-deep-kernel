"""Result serialization and source identity shared by experiment entry points."""
import csv
import hashlib
import json
import subprocess

from experiments.configuration import ROOT


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def code_identity():
    h = hashlib.sha256()
    for folder in ("detectors", "data_pipeline", "evaluation", "experiments"):
        for path in sorted((ROOT / folder).rglob("*.py")):
            h.update(path.relative_to(ROOT).as_posix().encode())
            h.update(path.read_bytes())
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {"git_head": commit, "pipeline_source_sha256": h.hexdigest()}


