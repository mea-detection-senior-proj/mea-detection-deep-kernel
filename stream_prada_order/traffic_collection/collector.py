"""Synchronous single-inflight collector with write-ahead dispatch intentions."""
import copy
import unicodedata
import uuid

from .adapters import AdapterFailure, AdapterResponse
from .schema import ExecutionDisabled, IntegrityError, require, validate_manifest, digest


class Collector:
    def __init__(self, store, manifest, adapter):
        validate_manifest(manifest)
        if manifest["traffic_kind"] != "mock" or adapter.is_mock is not True:
            raise ExecutionDisabled("real_collection_disabled_in_phase_g")
        require(adapter.identity == manifest["victim"], "adapter_revision_mismatch")
        self.store, self.adapter = store, adapter
        self.manifest = copy.deepcopy(manifest)
        self.run_id = manifest["run_id"]
        self.store.max_logical_bytes = min(store.max_logical_bytes, manifest["budget"]["max_logical_storage_bytes"])
        self.store.append("run_opened", self.run_id, data={"manifest": self.manifest})

    def open_session(self, session_id, native_session_sha256):
        with self.store.mutex:
            require(all(s["closed"] for s in self.store.state.sessions.values() if s["run_id"] == self.run_id), "previous_session_not_closed")
            return self.store.append("session_opened", self.run_id, session_id,
                                     data={"native_session_sha256": native_session_sha256})

    def close_session(self, session_id):
        return self.store.append("session_closed", self.run_id, session_id, data={"reason": "normal"})

    def close_run(self):
        return self.store.append("run_closed", self.run_id, data={"reason": "normal"})

    def collect(self, session_id, request_id, query, document_ids, task_id, format_class,
                decision=None):
        with self.store.mutex:
            if self.adapter.is_mock is not True or self.manifest["traffic_kind"] != "mock":
                raise ExecutionDisabled("real_collection_disabled_in_phase_g")
            require(self.adapter.identity == self.manifest["victim"], "adapter_revision_mismatch")
            require(request_id not in self.store.state.requests, "duplicate_request_id")
            require(session_id in self.store.state.sessions and not self.store.state.sessions[session_id]["closed"], "session_not_open")
            require(self.store.state.sessions[session_id]["run_id"] == self.run_id, "session_boundary_mismatch")
            require(type(query) is str and bool(query.strip()), "query_missing")
            raw = query.encode("utf-8")
            budget = self.manifest["budget"]
            require(len(raw) <= budget["max_query_bytes"], "input_budget_exhausted")
            require(set(document_ids) <= {s["document_id"] for s in self.manifest["sources"]}, "source_not_authorized")
            require(task_id in self.manifest["task_ids"], "task_not_authorized")
            run = self.store.state.runs[self.run_id]
            session = self.store.state.sessions[session_id]
            require(run["requests"] < budget["max_requests"] and run["attempts"] < budget["max_attempts"] and session["attempts"] < budget["max_session_attempts"], "request_budget_exhausted")
            # Reserve sufficient logical bytes for outcomes and orderly closure before invoking anything.
            require(self.store.logical_bytes() + len(raw) + budget["max_response_bytes"] + 16384 <= self.store.max_logical_bytes, "storage_reserve_insufficient")
            decision = copy.deepcopy(decision or {"sha256": None, "based_on_attempt_ids": []})
            if decision["sha256"] is not None:
                self.store.read_blob(decision["sha256"])
            normalized = " ".join(unicodedata.normalize("NFKC", query).casefold().split())
            query_hash = self.store.write_blob(raw)
            self.store.append("request_started", self.run_id, session_id, request_id, {
                "request_sequence": run["requests"] + 1, "session_request_sequence": session["requests"] + 1,
                "query_sha256": query_hash, "normalized_query_sha256": digest(normalized),
                "query_bytes": len(raw), "words": len(query.split()), "characters": len(query),
                "document_ids": list(document_ids), "task_id": task_id, "format_class": format_class,
                "decision": decision})
            status, reason, response_hash = "failed", "adapter_failure", None
            previous = None
            for number in range(1, budget["max_attempts_per_request"] + 1):
                if run["attempts"] >= budget["max_attempts"] or session["attempts"] >= budget["max_session_attempts"]:
                    reason = "budget_exhausted"
                    break
                aid = uuid.uuid4().hex
                self.store.append("attempt_started", self.run_id, session_id, request_id, {
                    "attempt_id": aid, "attempt_number": number, "dispatch_sequence": run["attempts"] + 1,
                    "retry_of": previous})
                context = {"run_id": self.run_id, "session_id": session_id, "request_id": request_id,
                           "attempt_id": aid, "attempt_number": number, "document_ids": list(document_ids),
                           "task_id": task_id, "decision": decision}
                try:
                    result = self.adapter.respond(query, context)
                except AdapterFailure as exc:
                    code = exc.code if exc.code in {"timeout", "adapter_failure", "rate_limit"} else "adapter_failure"
                    delivery = exc.delivery if exc.delivery in {"not_sent", "accepted", "unknown"} else "unknown"
                    retryable = exc.retryable is True
                    self.store.append("attempt_failed", self.run_id, session_id, request_id, {
                        "attempt_id": aid, "code": code, "delivery": delivery, "retryable": retryable})
                    status = "unknown" if delivery == "unknown" else "failed"
                    if delivery == "not_sent" and retryable:
                        previous = aid
                        continue
                    break
                except Exception:
                    # Do not persist provider exception text, URLs, credentials or stack locals.
                    self.store.append("attempt_failed", self.run_id, session_id, request_id, {
                        "attempt_id": aid, "code": "adapter_failure", "delivery": "unknown", "retryable": False})
                    status = "unknown"
                    break
                try:
                    require(isinstance(result, AdapterResponse) and type(result.text) is str, "invalid_response")
                    response = result.text.encode("utf-8")
                    require(len(response) <= budget["max_response_bytes"], "output_budget_exhausted")
                    for count in [result.input_tokens, result.output_tokens]:
                        require(count is None or type(count) is int and count >= 0, "invalid_token_count")
                    unavailable = result.input_tokens is None and result.output_tokens is None
                    require(result.token_origin == ("unavailable" if unavailable else "mock_reported"), "token_origin_mismatch")
                except (IntegrityError, AttributeError, UnicodeError):
                    self.store.append("attempt_failed", self.run_id, session_id, request_id, {
                        "attempt_id": aid, "code": "invalid_response", "delivery": "accepted", "retryable": False})
                    status, reason = "failed", "invalid_response"
                    break
                response_hash = self.store.write_blob(response)
                self.store.append("attempt_succeeded", self.run_id, session_id, request_id, {
                    "attempt_id": aid, "response_sha256": response_hash, "response_bytes": len(response),
                    "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                    "token_origin": result.token_origin, "delivery": "accepted"})
                status, reason = "succeeded", "completed"
                break
            self.store.append("request_finished", self.run_id, session_id, request_id,
                              {"status": status, "recovered": False, "reason": reason})
            return {"request_id": request_id, "status": status, "response_sha256": response_hash}


def recover(store):
    """Append interruptions/terminal events; never replay or resend an adapter call."""
    counts = {"requests_finalized": 0, "unknown_attempts": 0, "sessions_closed": 0, "runs_closed": 0}
    with store.mutex:
        for run_id, run in list(store.state.runs.items()):
            if run["closed"]:
                continue
            for rid, request in list(store.state.requests.items()):
                if request["run_id"] != run_id or request["finished"]:
                    continue
                sid = request["session_id"]
                last = store.state.attempts[request["attempt_ids"][-1]] if request["attempt_ids"] else None
                if last and last["outcome"] is None:
                    store.append("attempt_unknown", run_id, sid, rid, {
                        "attempt_id": request["attempt_ids"][-1], "code": "process_interrupted",
                        "delivery": "unknown", "retryable": False})
                    counts["unknown_attempts"] += 1
                status = "failed" if last is None else (
                    "succeeded" if last["outcome"] == "attempt_succeeded" else
                    "unknown" if last["result"]["delivery"] == "unknown" else "failed")
                store.append("request_finished", run_id, sid, rid,
                             {"status": status, "recovered": True, "reason": "process_interrupted"})
                counts["requests_finalized"] += 1
            for sid, session in list(store.state.sessions.items()):
                if session["run_id"] == run_id and not session["closed"]:
                    store.append("session_closed", run_id, sid, data={"reason": "process_interrupted"})
                    counts["sessions_closed"] += 1
            store.append("run_closed", run_id, data={"reason": "process_interrupted"})
            counts["runs_closed"] += 1
    return counts
