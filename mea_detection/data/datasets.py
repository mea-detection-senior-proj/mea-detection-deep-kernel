"""Group-disjoint splits using inspected query identity and source information."""
import hashlib
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
