"""Exercise a new dataset through the same entry point as real experiments."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from pilot.deep_mmd.cli import main
from pilot.deep_mmd.datasets.registry import get_dataset, load_dataset
from pilot.deep_mmd.datasets.protocol import make_partitions, read_rows


class DatasetExtensionTests(unittest.TestCase):
    def test_new_dataset_custom_columns_full_experiment_without_encoder_download(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            root = Path(temporary)
            for label in ('benign', 'attack'):
                rows = [{'row_id': f'{label}-{i}', 'text': f'{label} query {i}'} for i in range(400)]
                (root / f'{label}.jsonl').write_text(
                    '\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
            config = root / 'dataset.json'
            config.write_text(json.dumps({
                'name': 'future_dataset', 'benign_path': 'benign.jsonl',
                'attack_path': 'attack.jsonl', 'id_field': 'row_id', 'text_field': 'text',
                'grouping_policy': 'id-text-only', 'provenance_notes': 'Synthetic test rows.',
            }), encoding='utf-8')
            spec = load_dataset(config)
            normal = read_rows(root / 'benign.jsonl', spec=spec)
            attack = read_rows(root / 'attack.jsonl', spec=spec)
            splits, audit = make_partitions(normal, attack, 42, spec.name, spec=spec)
            self.assertEqual(sum(len(p['benign']) for p in splits.values()), 400)
            self.assertFalse(audit['source_provenance_available'])
            experiment = root / 'experiment.json'
            experiment.write_text(json.dumps({
                'data_root': str(root), 'output': str(root / 'unused'), 'epochs': 1,
                'window': 20, 'train_window': 20, 'steps': 2, 'validation_windows': 2,
                'calibration_windows': 3, 'test_windows': 2, 'reference_repeats': 2,
            }), encoding='utf-8')
            output = root / 'run'

            def encode(texts, *args):
                return np.random.default_rng(7).normal(size=(len(texts), 4)).astype('float32')

            argv = ['--config', str(experiment), '--dataset-config', str(config),
                    '--output', str(output)]
            with patch('pilot.deep_mmd.experiment.embed_texts', side_effect=encode), contextlib.redirect_stdout(io.StringIO()):
                main(argv)
                with self.assertRaises(FileExistsError):
                    main(argv)
            metadata = json.loads((output / 'metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['arguments']['dataset'], 'future_dataset')
            self.assertEqual(metadata['arguments']['epochs'], 1)
            self.assertEqual(metadata['arguments']['reference_repeats'], 2)
            self.assertEqual(metadata['dataset_spec'], spec.to_dict())
            self.assertEqual(set(metadata['rates']), {'rbf', 'multi_rbf', 'deep_kernel'})
            self.assertEqual(len((output / 'scores.csv').read_text().splitlines()), 19)
            self.assertEqual(len((output / 'calibration_scores.csv').read_text().splitlines()), 10)
            weights = torch.load(output / 'deep_kernel.pt', weights_only=True)
            self.assertEqual(tuple(weights['0.weight'].shape), (128, 4))

    def test_unknown_policy_and_missing_provenance_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            config = Path(temporary) / 'dataset.json'
            original = get_dataset('Meaeq_SST-2').to_dict()
            original['grouping_policy'] = 'random-rows'
            config.write_text(json.dumps(original), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'grouping_policy'):
                load_dataset(config)
            original['grouping_policy'] = 'id-text-only'
            del original['provenance_notes']
            config.write_text(json.dumps(original), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'provenance_notes'):
                load_dataset(config)
