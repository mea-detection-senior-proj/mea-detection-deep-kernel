"""Declarative JSONL adapters; unknown datasets require an explicit specification."""
from dataclasses import asdict, dataclass
import json
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parents[2] / 'configs' / 'datasets'
SUPPORTED_DATASETS = ('model_leeching', 'Meaeq_SST-2', 'ME_BERT_sst2_wiki')
POLICIES = ('id-text-only', 'id-text-attack-context')


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    benign_path: str
    attack_path: str
    grouping_policy: str
    provenance_notes: str
    id_field: str = 'id'
    text_field: str = 'query'

    def __post_init__(self):
        for key, value in asdict(self).items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'Dataset {key} must be a nonempty string')
        if self.grouping_policy not in POLICIES:
            raise ValueError(f'grouping_policy must be one of {POLICIES}')
        for value in (self.benign_path, self.attack_path):
            if Path(value).is_absolute() or '..' in Path(value).parts:
                raise ValueError('Dataset paths must be relative to --data-root without ..')

    def paths(self, data_root):
        paths = tuple(Path(data_root) / value for value in (self.benign_path, self.attack_path))
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(f'Missing dataset file: {path}')
        return paths

    def to_dict(self):
        return asdict(self)


def load_dataset(path):
    try:
        return DatasetSpec(**json.loads(Path(path).read_text(encoding='utf-8')))
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f'Invalid dataset specification {path}: {exc}') from exc


def get_dataset(name):
    # Treat names as identifiers, never as filesystem paths.
    if not name or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for char in name):
        raise ValueError(f'Invalid dataset name: {name}')
    path = CONFIG_DIR / f'{name}.json'
    if not path.is_file():
        raise ValueError(f'Uninspected dataset: {name}; add {path.name} or use --dataset-config')
    return load_dataset(path)
