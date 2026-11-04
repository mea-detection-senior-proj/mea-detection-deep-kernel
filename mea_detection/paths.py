"""Project-relative resources are anchored at the package, not the caller depth."""
from pathlib import Path
import mea_detection

ROOT = Path(mea_detection.__file__).resolve().parent.parent


def project_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path
