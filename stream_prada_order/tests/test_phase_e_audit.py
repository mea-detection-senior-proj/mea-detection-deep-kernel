"""Reject a corrupted shortcut artifact before numeric reproduction."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import phase_e_audit as e


class IntegrityTests(unittest.TestCase):
    def test_feature_metadata_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory); raw=b'{"words":12}'
            (path/'features.json').write_bytes(raw)
            (path/'artifact_hashes.json').write_text(json.dumps({'features.json':hashlib.sha256(raw).hexdigest()}))
            e.verify_hashes(path)
            (path/'features.json').write_bytes(b'{"words":120}')
            with self.assertRaisesRegex(ValueError,'Artifact hash mismatch'): e.verify_hashes(path)


if __name__=='__main__': unittest.main()
