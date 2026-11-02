"""Group inspected datasets by available identity, text and source provenance."""
import hashlib
import json
import unicodedata
from pathlib import Path

import numpy as np

PARTITIONS = ('train', 'validation', 'calibration', 'test')
SUPPORTED_DATASETS = ('model_leeching', 'Meaeq_SST-2', 'ME_BERT_sst2_wiki')


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def context_of(text):
    marker = 'Can you answer this question briefly:'
    if text.startswith('Given this context:') and marker in text:
        return normalize(text.split(marker, 1)[0])
    return None


def read_rows(path, limit=None):
    rows = []
    with Path(path).open(encoding='utf-8') as stream:
        for line_no, line in enumerate(stream, 1):
            row = json.loads(line)
            if not isinstance(row.get('id'), str) or not row['id'].strip():
                raise ValueError(f'{path}:{line_no}: missing string id; source grouping cannot be verified')
            if not isinstance(row.get('query'), str) or not row['query'].strip():
                raise ValueError(f'{path}:{line_no}: missing query')
            rows.append({'id': row['id'].strip(), 'query': row['query'].strip()})
            if limit is not None and len(rows) >= limit:
                break
    return rows


def make_partitions(normal, attack, seed, dataset='model_leeching'):
    """Link equal ids, normalized text and attack source contexts transitively."""
    if dataset not in SUPPORTED_DATASETS:
        raise ValueError(f'Uninspected dataset: {dataset}')
    require_context = dataset == 'model_leeching'
    rows = [('benign', r) for r in normal] + [('attack', r) for r in attack]
    parent = list(range(len(rows)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(a, b):
        a, b = root(a), root(b)
        if a != b:
            parent[b] = a
    seen = {}
    context_matches = 0
    for i, (label, row) in enumerate(rows):
        keys = [('id', row['id']), ('text', normalize(row['query']))]
        context = context_of(row['query']) if label == 'attack' else None
        if context:
            context_matches += 1
            keys.append(('context', context))
        for key in keys:
            if key in seen:
                union(i, seen[key])
            else:
                seen[key] = i
    if require_context and context_matches != len(attack):
        raise ValueError(f'Could identify source context in {context_matches}/{len(attack)} attack rows; inspect dataset before proceeding')
    # Ambiguous labels must not enter training or evaluation.
    benign_text = {normalize(r['query']) for r in normal}
    attack_text = {normalize(r['query']) for r in attack}
    collisions = benign_text & attack_text
    components = {}
    for i, (label, row) in enumerate(rows):
        if normalize(row['query']) not in collisions:
            components.setdefault(root(i), []).append((label, row))
    component_list = list(components.values())
    np.random.default_rng(seed).shuffle(component_list)
    counts = [int(len(component_list) * f) for f in (.4, .2, .2)]
    counts.append(len(component_list) - sum(counts))
    partitions = {part: {'benign': [], 'attack': []} for part in PARTITIONS}
    group_counts = {}
    cursor = 0
    for part, count in zip(PARTITIONS, counts):
        selected = component_list[cursor:cursor + count]
        cursor += count
        group_counts[part] = len(selected)
        dedup = {'benign': set(), 'attack': set()}
        for component in selected:
            for label, row in component:
                key = normalize(row['query'])
                if key not in dedup[label]:
                    partitions[part][label].append(row)
                    dedup[label].add(key)
    audit = audit_partitions(partitions)
    audit.update({'input_rows': {'benign': len(normal), 'attack': len(attack)},
                  'grouping_policy': 'id-text-attack-context' if require_context else 'id-text-only',
                  'source_provenance_available': require_context,
                  'dataset': dataset,
                  'attack_context_rows_parsed': context_matches,
                  'cross_label_normalized_collisions_removed': len(collisions),
                  'source_groups_per_partition': group_counts})
    return partitions, audit


def audit_partitions(partitions):
    fields = {'id': {}, 'normalized_text': {}, 'attack_context': {}}
    for part, classes in partitions.items():
        for label, rows in classes.items():
            for row in rows:
                keys = {'id': row['id'], 'normalized_text': normalize(row['query'])}
                if label == 'attack':
                    keys['attack_context'] = context_of(row['query'])
                for name, value in keys.items():
                    if value is None:
                        continue
                    prior = fields[name].setdefault(value, part)
                    if prior != part:
                        raise ValueError(f'{name} crosses partitions: {prior}, {part}')
    return {'cross_partition_id_collisions': 0, 'cross_partition_normalized_text_collisions': 0,
            'cross_partition_attack_context_collisions': 0}
