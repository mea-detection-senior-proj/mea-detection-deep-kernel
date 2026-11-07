"""Non-sensitive numeric test fixtures, never experimental traffic evidence."""
import copy
import hashlib
from datetime import datetime, timezone, timedelta


def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def manifest(run="run1", label="benign", actor="1", source="2"):
    return {
        "schema_version": "traffic-manifest-v1", "run_id": run,
        "traffic_kind": "mock", "label": label,
        "collector_revision": "1" * 40, "protocol_sha256": digest("3"),
        "actor_sha256": digest(actor), "source_group_sha256": digest(source),
        "victim": {"model_id": "mock-victim", "model_revision": "2" * 40,
                   "tokenizer_id": "mock-tokenizer", "tokenizer_revision": "3" * 40},
        "authorization": {"record_id": "test-only", "evidence_sha256": digest("4")},
        "sources": [{"document_id": "doc1", "content_sha256": digest(source),
                     "license_id": "numeric-fixture-only", "provenance_sha256": digest("5")}],
        "task_ids": ["task1"], "split": "development",
        "acquisition": None if label == "benign" else {
            "method_id": "mock-acquisition", "code_revision": "4" * 40,
            "configuration_sha256": digest("6"), "lineage_sha256": digest(source),
            "query_pool_sha256": digest(source), "response_dependent": True},
        "budget": {"max_requests": 300, "max_attempts": 310,
                   "max_attempts_per_request": 2, "max_session_attempts": 300,
                   "max_query_bytes": 4096, "max_response_bytes": 4096,
                   "max_logical_storage_bytes": 8 * 1024 * 1024},
        "retry_policy": "not_sent_only"
    }


class Clock:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=self.n)
        return stamp.isoformat(timespec="microseconds").replace("+00:00", "Z"), self.n * 1000


class MockAdapter:
    is_mock = True

    def __init__(self, identity=None, outcomes=None):
        self.identity = copy.deepcopy(identity or manifest()["victim"])
        self.outcomes = list(outcomes or [])
        self.calls = []

    def respond(self, query, context):
        from traffic_collection.adapters import AdapterResponse
        self.calls.append((query, context))
        value = self.outcomes.pop(0) if self.outcomes else AdapterResponse("4 5", 3, 2, "mock_reported")
        if isinstance(value, BaseException):
            raise value
        return value
