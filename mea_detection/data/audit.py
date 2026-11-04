"""In-memory duplicate, partition and capacity audit rules."""
from .datasets import normalize, context_of
from .capacity import evaluation_capacity, training_capacity

SEEDS = (1, 20, 42)
WINDOWS = (100, 250, 500, 1500)
RATIOS = (.01, .05, .1, .25, 1.)


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
    return [{"dataset": dataset, "seed": seed, **evaluation_capacity(sizes, size, ratio)}
            for size in WINDOWS for ratio in RATIOS]


def training_rows(dataset, seed, sizes):
    # Provisional training sizes, not final objective/model choices.
    return [{"dataset": dataset, "seed": seed, **training_capacity(sizes, size, ratio)}
            for size in (100, 250) for ratio in (1., .01, .05, .1, .25)]


