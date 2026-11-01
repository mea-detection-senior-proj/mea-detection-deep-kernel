import unittest

from pilot.protocol import audit_partitions, make_partitions


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


if __name__ == '__main__':
    unittest.main()
