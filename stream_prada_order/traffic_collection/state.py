"""Replayable lifecycle, provenance, sequence and exposure invariants."""
from .schema import require, validate_event, validate_manifest


class LedgerState:
    def __init__(self):
        self.sequence = 0
        self.last_utc = None
        self.epoch = None
        self.epochs = set()
        self.last_monotonic = 0
        self.runs = {}
        self.sessions = {}
        self.requests = {}
        self.attempts = {}
        self.inflight = None

    def advance(self, event):
        validate_event(event)
        require(event["event_sequence"] == self.sequence + 1, "event_sequence_gap")
        stamp, epoch = event["utc"], event["clock_epoch"]
        require(event["utc_regressed"] == bool(self.last_utc and stamp < self.last_utc), "clock_flag_mismatch")
        if epoch == self.epoch:
            require(event["monotonic_ns"] >= self.last_monotonic, "monotonic_regression")
        else:
            require(epoch not in self.epochs, "reused_clock_epoch")
        kind, run_id, sid, rid, data = (event[k] for k in ("kind", "run_id", "session_id", "request_id", "data"))
        if kind == "run_opened":
            validate_manifest(data["manifest"])
            require(sid is None and rid is None and run_id == data["manifest"]["run_id"], "run_identity_mismatch")
            require(run_id not in self.runs and all(r["closed"] for r in self.runs.values()), "run_already_active")
            self.runs[run_id] = {"manifest": data["manifest"], "closed": False, "reason": None, "requests": 0, "attempts": 0}
        else:
            require(run_id in self.runs and not self.runs[run_id]["closed"], "run_not_open")
            run = self.runs[run_id]
            manifest = run["manifest"]
            if kind == "session_opened":
                require(sid is not None and rid is None and sid not in self.sessions, "session_identity_mismatch")
                self.sessions[sid] = {"run_id": run_id, "native_sha256": data["native_session_sha256"],
                                      "closed": False, "reason": None, "requests": 0, "attempts": 0}
            elif kind == "run_closed":
                require(sid is None and rid is None and self.inflight is None, "run_has_pending_request")
                require(all(s["closed"] for s in self.sessions.values() if s["run_id"] == run_id), "run_has_open_session")
                run.update(closed=True, reason=data["reason"])
            else:
                require(sid in self.sessions and self.sessions[sid]["run_id"] == run_id and not self.sessions[sid]["closed"], "session_not_open")
                session = self.sessions[sid]
                if kind == "request_started":
                    require(rid is not None and rid not in self.requests and self.inflight is None, "duplicate_or_inflight_request")
                    require(data["request_sequence"] == run["requests"] + 1 and data["session_request_sequence"] == session["requests"] + 1, "request_sequence_gap")
                    require(run["requests"] < manifest["budget"]["max_requests"], "request_budget_exhausted")
                    require(set(data["document_ids"]) <= {s["document_id"] for s in manifest["sources"]}, "source_not_authorized")
                    require(data["task_id"] in manifest["task_ids"], "task_not_authorized")
                    decision = data["decision"]
                    require(not decision["based_on_attempt_ids"] or decision["sha256"] is not None, "decision_provenance_missing")
                    for aid in decision["based_on_attempt_ids"]:
                        require(aid in self.attempts and self.attempts[aid]["run_id"] == run_id and self.attempts[aid]["outcome"] == "attempt_succeeded", "invalid_response_dependency")
                    require(data["query_bytes"] <= manifest["budget"]["max_query_bytes"], "input_budget_exhausted")
                    self.requests[rid] = {"run_id": run_id, "session_id": sid, "data": data,
                                          "attempt_ids": [], "finished": False, "status": None}
                    run["requests"] += 1
                    session["requests"] += 1
                    self.inflight = rid
                elif kind == "session_closed":
                    require(rid is None and not any(not r["finished"] and r["session_id"] == sid for r in self.requests.values()), "session_has_pending_request")
                    session.update(closed=True, reason=data["reason"])
                else:
                    require(rid in self.requests and self.inflight == rid, "request_not_pending")
                    request = self.requests[rid]
                    require(request["run_id"] == run_id and request["session_id"] == sid and not request["finished"], "request_boundary_mismatch")
                    previous = self.attempts[request["attempt_ids"][-1]] if request["attempt_ids"] else None
                    if kind == "attempt_started":
                        aid = data["attempt_id"]
                        require(aid not in self.attempts, "duplicate_attempt_id")
                        require(data["attempt_number"] == len(request["attempt_ids"]) + 1 and data["dispatch_sequence"] == run["attempts"] + 1, "attempt_sequence_gap")
                        require(data["retry_of"] == (request["attempt_ids"][-1] if previous else None), "retry_link_mismatch")
                        if previous:
                            require(previous["outcome"] == "attempt_failed" and previous["result"]["delivery"] == "not_sent" and previous["result"]["retryable"], "unsafe_retry")
                        budget = manifest["budget"]
                        require(len(request["attempt_ids"]) < budget["max_attempts_per_request"] and run["attempts"] < budget["max_attempts"] and session["attempts"] < budget["max_session_attempts"], "attempt_budget_exhausted")
                        self.attempts[aid] = {"run_id": run_id, "session_id": sid, "request_id": rid,
                                              "started": event, "outcome": None, "result": None}
                        request["attempt_ids"].append(aid)
                        run["attempts"] += 1
                        session["attempts"] += 1
                    elif kind in {"attempt_succeeded", "attempt_failed", "attempt_unknown"}:
                        require(previous is not None and previous["outcome"] is None and data["attempt_id"] == request["attempt_ids"][-1], "attempt_not_pending")
                        if kind == "attempt_succeeded":
                            require(data["response_bytes"] <= manifest["budget"]["max_response_bytes"], "output_budget_exhausted")
                            unavailable = data["input_tokens"] is None and data["output_tokens"] is None
                            require((data["token_origin"] == "unavailable") == unavailable, "token_origin_mismatch")
                            require(data["token_origin"] == "unavailable" or data["token_origin"] == ("mock_reported" if manifest["traffic_kind"] == "mock" else "adapter_reported"), "token_origin_mismatch")
                        previous["outcome"], previous["result"] = kind, data
                        previous["finished"] = event
                    elif kind == "request_finished":
                        require(previous is None or previous["outcome"] is not None, "attempt_outcome_missing")
                        status = "failed" if previous is None else (
                            "succeeded" if previous["outcome"] == "attempt_succeeded" else
                            "unknown" if previous["result"]["delivery"] == "unknown" else "failed")
                        require(data["status"] == status, "request_status_mismatch")
                        request.update(finished=True, status=status)
                        self.inflight = None
                    else:
                        require(False, "unsupported_event")
        self.sequence = event["event_sequence"]
        self.last_utc, self.epoch = stamp, epoch
        self.epochs.add(epoch)
        self.last_monotonic = event["monotonic_ns"]


def replay(events):
    state = LedgerState()
    for event in events:
        state.advance(event)
    return state
