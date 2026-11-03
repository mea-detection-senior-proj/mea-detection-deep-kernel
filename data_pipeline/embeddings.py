"""Frozen encoder with content-addressed cache shared across split seeds."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np


def encoder_identity(model):
    path = Path(model)
    if not path.is_dir():
        return {"model": model}
    h = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file() and ".cache" not in p.parts):
        h.update(item.relative_to(path).as_posix().encode())
        with item.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
    return {"model": str(path.resolve()), "local_files_sha256": h.hexdigest()}


def embed_texts(texts, model, revision, prefix, batch_size, device, cache_dir):
    from sentence_transformers import SentenceTransformer
    identity = {**encoder_identity(model), "revision": revision, "prefix": prefix, "normalize": True}
    h = hashlib.sha256(json.dumps(identity, sort_keys=True).encode())
    for text in texts:
        h.update(json.dumps(text, ensure_ascii=False).encode("utf-8"))
        h.update(b"\n")
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{h.hexdigest()}.npy"
    if path.exists():
        encoded = np.load(path, allow_pickle=False)
    else:
        encoder = SentenceTransformer(model, device=device, revision=revision)
        encoded = np.asarray(encoder.encode([prefix + t for t in texts], batch_size=batch_size,
                             normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True), dtype=np.float32)
        with tempfile.NamedTemporaryFile(dir=cache_dir, suffix=".npy", delete=False) as stream:
            temporary = Path(stream.name)
            np.save(stream, encoded)
        os.replace(temporary, path)
    if encoded.ndim != 2 or len(encoded) != len(texts) or not np.isfinite(encoded).all():
        raise ValueError("Invalid embedding array")
    return encoded, {**identity, "cache_key": h.hexdigest()}
