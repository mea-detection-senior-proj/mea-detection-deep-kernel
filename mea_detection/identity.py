"""Identity of active sources; archived implementations are excluded."""
import hashlib
import subprocess

from .paths import ROOT


def code_identity():
    h = hashlib.sha256()
    for path in sorted((ROOT / "mea_detection").rglob("*.py")):
        h.update(path.relative_to(ROOT).as_posix().encode())
        h.update(path.read_bytes())
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {"git_head": commit, "pipeline_source_sha256": h.hexdigest()}


