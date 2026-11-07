"""Read-only joined records for private downstream consumers; never raw contents."""
import copy

from .audit import audit
from .state import replay
from .store import read_events
from .schema import require


def attempt_records(root):
    """One record per dispatch intention, retaining uncertain/non-sent attempts.

    Only delivery='accepted' is an adapter-asserted exposure. This view does not
    manufacture a global order across separate stores or a response time for a
    failure/recovery event. All returned metadata should remain in private storage.
    """
    events = read_events(root)
    audit(root)
    require(read_events(root) == events, "concurrent_write_retry_audit")
    state = replay(events)
    for aid, attempt in state.attempts.items():
        request = state.requests[attempt["request_id"]]
        manifest = state.runs[attempt["run_id"]]["manifest"]
        source = {s["document_id"]: s for s in manifest["sources"]}
        started, result = attempt["started"], attempt["result"]
        finished = attempt.get("finished")
        success = attempt["outcome"] == "attempt_succeeded"
        elapsed = (finished["monotonic_ns"] - started["monotonic_ns"]
                   if finished and finished["clock_epoch"] == started["clock_epoch"] else None)
        yield {
            "schema_version": "traffic-attempt-view-v1", "run_id": attempt["run_id"],
            "session_id": attempt["session_id"], "request_id": attempt["request_id"], "attempt_id": aid,
            "request_sequence": request["data"]["request_sequence"],
            "session_request_sequence": request["data"]["session_request_sequence"],
            "dispatch_sequence": started["data"]["dispatch_sequence"],
            "attempt_number": started["data"]["attempt_number"], "retry_of": started["data"]["retry_of"],
            "request_utc": started["utc"], "response_utc": finished["utc"] if success else None,
            "clock_epoch": started["clock_epoch"],
            "utc_regressed_at_outcome": finished["utc_regressed"] if finished else None,
            "failure_observed_utc": finished["utc"] if attempt["outcome"] == "attempt_failed" else None,
            "recovery_observed_utc": finished["utc"] if attempt["outcome"] == "attempt_unknown" else None,
            "collector_elapsed_ns": elapsed, "elapsed_is_response_latency": success,
            "victim": copy.deepcopy(manifest["victim"]), "traffic_kind": manifest["traffic_kind"],
            "label": manifest["label"], "label_basis": "authorized_manifest_reference_not_length_or_format",
            "authorization": copy.deepcopy(manifest["authorization"]),
            "collector_revision": manifest["collector_revision"], "protocol_sha256": manifest["protocol_sha256"],
            "query_sha256": request["data"]["query_sha256"],
            "normalized_query_sha256": request["data"]["normalized_query_sha256"],
            "response_sha256": result["response_sha256"] if success else None,
            "input_tokens": result["input_tokens"] if success else None,
            "output_tokens": result["output_tokens"] if success else None,
            "token_origin": result["token_origin"] if success else "unavailable",
            "source_documents": [copy.deepcopy(source[s]) for s in request["data"]["document_ids"]],
            "task_id": request["data"]["task_id"], "actor_sha256": manifest["actor_sha256"],
            "source_group_sha256": manifest["source_group_sha256"],
            "acquisition": copy.deepcopy(manifest["acquisition"]),
            "decision": copy.deepcopy(request["data"]["decision"]),
            "delivery": result["delivery"] if result else "unknown",
            "outcome": attempt["outcome"] or "pending", "request_status": request["status"],
            "error_code": result.get("code") if result else None,
        }
