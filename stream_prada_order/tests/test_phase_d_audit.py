"""Audit rejects corrupt published evidence before reproducing statistics."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import phase_d_audit as audit


class AuditIntegrityTests(unittest.TestCase):
    def test_tampered_numeric_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory); blob=b'original numeric evidence'
            (p/'artifact_hashes.json').write_text(json.dumps({'data.gz':hashlib.sha256(blob).hexdigest()}))
            (p/'data.gz').write_bytes(blob)
            audit.verify_hashes(p)
            (p/'data.gz').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'Artifact hash mismatch'): audit.verify_hashes(p)


if __name__=='__main__': unittest.main()
