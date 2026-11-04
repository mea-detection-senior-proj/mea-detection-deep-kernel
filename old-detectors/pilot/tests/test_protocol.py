import unittest

from pilot.deep_mmd.datasets.protocol import audit_partitions, make_partitions


def sample(i, context):
    return ({'id': str(i), 'query': f'question {i}'},
            {'id': str(i), 'query': f'Given this context: "{context}"\nCan you answer this question briefly: question {i}'})


class ProtocolTests(unittest.TestCase):
    def test_paired_ids_and_shared_context_stay_together(self):
        pairs = [sample(i, f'passage {i // 3}') for i in range(60)]
        splits, audit = make_partitions([x[0] for x in pairs], [x[1] for x in pairs], 42)
        self.assertEqual(audit['cross_partition_id_collisions'], 0)
        self.assertEqual(audit['cross_partition_attack_context_collisions'], 0)
        for partition in splits.values():
            self.assertEqual({r['id'] for r in partition['benign']}, {r['id'] for r in partition['attack']})
        self.assertEqual(splits, make_partitions([x[0] for x in pairs], [x[1] for x in pairs], 42)[0])

    def test_audit_rejects_shared_source(self):
        benign, attack = sample(7, 'same')
        with self.assertRaisesRegex(ValueError, 'id crosses partitions'):
            audit_partitions({'train': {'benign': [benign]}, 'test': {'attack': [attack]}})

    def test_unknown_attack_format_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'source context'):
            make_partitions([{'id': '1', 'query': 'normal'}], [{'id': '1', 'query': 'unknown'}], 42)

    def test_inspected_text_datasets_group_duplicates_and_remove_ambiguous_labels(self):
        normal = [{'id': f'n-{i}', 'query': f'normal {i}'} for i in range(100)]
        attack = [{'id': f'a-{i}', 'query': f'attack {i}'} for i in range(100)]
        normal += [{'id': 'n-copy', 'query': ' NORMAL  1 '},
                   {'id': 'n-ambiguous', 'query': 'ambiguous'}]
        attack += [{'id': 'a-ambiguous', 'query': ' AMBIGUOUS '}]
        for dataset in ('Meaeq_SST-2', 'ME_BERT_sst2_wiki'):
            splits, audit = make_partitions(normal, attack, 42, dataset)
            self.assertEqual(audit['grouping_policy'], 'id-text-only')
            self.assertFalse(audit['source_provenance_available'])
            self.assertEqual(audit['cross_label_normalized_collisions_removed'], 1)
            self.assertEqual(sum(len(p['benign']) for p in splits.values()), 100)
            self.assertEqual(sum(len(p['attack']) for p in splits.values()), 100)
            audit_partitions(splits)

    def test_uninspected_dataset_cannot_bypass_source_checks(self):
        with self.assertRaisesRegex(ValueError, 'Uninspected dataset'):
            make_partitions([], [], 42, 'other')


if __name__ == '__main__':
    unittest.main()
