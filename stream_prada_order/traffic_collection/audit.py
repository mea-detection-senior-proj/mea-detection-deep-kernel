"""Offline numeric audit. No detector, tokenizer, model, API or dataset loader."""
from collections import Counter, defaultdict
from pathlib import Path
import unicodedata

from .schema import digest, require
from .state import replay
from .store import read_events


def _bucket(words):
    return 0 if words <= 32 else 1 if words <= 128 else 2 if words <= 512 else 3


def audit(root):
    root = Path(root).resolve()
    require(not (root / "blobs").is_symlink(), "symlink_storage_rejected")
    events = read_events(root)
    state = replay(events)
    referenced = set()
    observed_formats = {}

    def blob(sha):
        path = root / "blobs" / (sha + ".private")
        require(path.is_file() and not path.is_symlink(), "blob_missing")
        raw = path.read_bytes()
        require(digest(raw) == sha, "blob_corrupt")
        referenced.add(path.name)
        return raw

    for request in state.requests.values():
        meta = request["data"]
        raw = blob(meta["query_sha256"])
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            require(False, "invalid_private_encoding")
        normalized = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        require(len(raw) == meta["query_bytes"] and len(text) == meta["characters"] and len(text.split()) == meta["words"], "query_metadata_mismatch")
        require(digest(normalized) == meta["normalized_query_sha256"], "normalized_hash_mismatch")
        observed_formats[meta["query_sha256"]] = {
            "multiline": "\n" in text,
            "code_fence": "```" in text,
            "context_marker": text.startswith(("Given this context:", "Passage:", "Context:"))}
        if meta["decision"]["sha256"] is not None:
            blob(meta["decision"]["sha256"])
    for attempt in state.attempts.values():
        if attempt["outcome"] == "attempt_succeeded":
            raw = blob(attempt["result"]["response_sha256"])
            require(len(raw) == attempt["result"]["response_bytes"], "response_metadata_mismatch")

    parent = {sid: sid for sid in state.sessions}

    def find(sid):
        while parent[sid] != sid:
            parent[sid] = parent[parent[sid]]
            sid = parent[sid]
        return sid

    seen_keys = {}
    def link(sid, key):
        if key in seen_keys:
            parent[find(sid)] = find(seen_keys[key])
        else:
            seen_keys[key] = sid

    query_sessions = defaultdict(set)
    query_labels = defaultdict(set)
    native_sessions = Counter()
    for sid, session in state.sessions.items():
        manifest = state.runs[session["run_id"]]["manifest"]
        for key in [("actor", manifest["actor_sha256"]), ("source", manifest["source_group_sha256"]),
                    ("native", manifest["actor_sha256"], session["native_sha256"])]:
            link(sid, key)
        native_sessions[(manifest["actor_sha256"], session["native_sha256"])] += 1
        if manifest["acquisition"]:
            for key in ["lineage_sha256", "query_pool_sha256"]:
                link(sid, (key, manifest["acquisition"][key]))
    for request in state.requests.values():
        sid, data = request["session_id"], request["data"]
        manifest = state.runs[request["run_id"]]["manifest"]
        sources = {s["document_id"]: s for s in manifest["sources"]}
        for source in data["document_ids"]:
            link(sid, ("document_content", sources[source]["content_sha256"]))
        q = data["normalized_query_sha256"]
        link(sid, ("query", q))
        query_sessions[q].add(sid)
        query_labels[q].add(manifest["label"])

    distributions = {label: {"accepted_exposures": 0, "word_bins": [0] * 4,
                            "format_counts": Counter(), "known_input_token_counts": 0,
                            "unknown_input_token_counts": 0, "unique_queries": {}}
                     for label in ["benign", "attack"]}
    sessions = []
    session_attempts = defaultdict(list)
    for attempt in state.attempts.values():
        session_attempts[attempt["session_id"]].append(attempt)
    for ordinal, (sid, session) in enumerate(state.sessions.items(), 1):
        run = state.runs[session["run_id"]]
        manifest = run["manifest"]
        accepted = unknown = not_sent = 0
        invalid_responses = 0
        previous_start = None
        idle_gap = False
        for attempt in session_attempts[sid]:
            start = attempt["started"]
            if previous_start and start["clock_epoch"] == previous_start["clock_epoch"]:
                idle_gap |= start["monotonic_ns"] - previous_start["monotonic_ns"] > 1800 * 10**9
            previous_start = start
            result = attempt["result"]
            delivery = result["delivery"] if result else "unknown"
            invalid_responses += bool(result and result.get("code") == "invalid_response")
            accepted += delivery == "accepted"
            unknown += delivery == "unknown"
            not_sent += delivery == "not_sent"
            if delivery != "accepted":
                continue
            q = state.requests[attempt["request_id"]]["data"]
            dist = distributions[manifest["label"]]
            dist["accepted_exposures"] += 1
            dist["word_bins"][_bucket(q["words"])] += 1
            dist["format_counts"][q["format_class"]] += 1
            dist["unique_queries"][q["query_sha256"]] = (_bucket(q["words"]), q["format_class"])
            known = result.get("input_tokens") is not None
            dist["known_input_token_counts"] += known
            dist["unknown_input_token_counts"] += not known
        complete = (session["closed"] and session["reason"] == "normal" and run["closed"] and run["reason"] == "normal"
                    and unknown == 0 and invalid_responses == 0 and not idle_gap)
        sessions.append({"ordinal": ordinal, "traffic_kind": manifest["traffic_kind"], "label": manifest["label"],
                         "logical_requests": session["requests"], "accepted_exposures": accepted,
                         "unknown_dispatches": unknown, "not_sent_attempts": not_sent,
                         "invalid_response_attempts": invalid_responses, "idle_gap_exceeded": bool(idle_gap),
                         "closed": session["closed"], "interrupted": session["reason"] == "process_interrupted",
                         "run_closed_normally": run["closed"] and run["reason"] == "normal",
                         "eligible_q102": complete and accepted >= 102,
                         "supports_horizon256": complete and accepted >= 256,
                         "_sid": sid})

    components = defaultdict(list)
    for row in sessions:
        components[find(row["_sid"])].append(row)
    cross_split = sum(len({state.runs[state.sessions[r["_sid"]]["run_id"]]["manifest"]["split"] for r in rows}) > 1
                      for rows in components.values())
    common = {}
    for label, dist in distributions.items():
        cells = Counter(dist["unique_queries"].values())
        common[label] = cells
        dist["unique_queries"] = len(dist["unique_queries"])
        dist["format_counts"] = dict(dist["format_counts"])
    signals = {label: Counter() for label in distributions}
    for attempt in state.attempts.values():
        if attempt["result"] and attempt["result"]["delivery"] == "accepted":
            request = state.requests[attempt["request_id"]]
            label = state.runs[request["run_id"]]["manifest"]["label"]
            for key, present in observed_formats[request["data"]["query_sha256"]].items():
                signals[label][key] += present
    overlap = sum(min(common["benign"][key], common["attack"][key]) for key in common["benign"])
    both = all(distributions[label]["accepted_exposures"] for label in distributions)
    kinds = {r["traffic_kind"] for r in sessions}
    for row in sessions:
        del row["_sid"]
    return {
        "schema_version": "traffic-audit-v1", "status": "valid",
        "evidence_kind": "mock_only_not_research" if kinds == {"mock"} else "mixed_or_real_requires_authorization_review" if kinds else "empty_not_research",
        "event_count": len(events), "session_count": len(sessions), "sessions": sessions,
        "session_lengths_are": "adapter-asserted accepted attempts; retries remain separate exposures; unknowns never imputed",
        "eligible_sessions_q102": sum(r["eligible_q102"] for r in sessions),
        "sessions_supporting_horizon256": sum(r["supports_horizon256"] for r in sessions),
        "operational_source_components": len(components),
        "components_with_eligible_q102_session": sum(any(r["eligible_q102"] for r in rows) for rows in components.values()),
        "components_with_horizon256_session": sum(any(r["supports_horizon256"] for r in rows) for rows in components.values()),
        "scientifically_verified_independent_sessions": None,
        "real_horizon256_feasibility": "unmeasured_no_real_data" if not any(r["traffic_kind"] == "real" for r in sessions) else "requires_provenance_and_matching_review",
        "word_bin_boundaries": [1, 33, 129, 513], "length_and_declared_format": distributions,
        "observed_lexical_format_signals": {label: dict(values) for label, values in signals.items()},
        "format_measurement": "declared class plus lexical markers; never an intent classifier",
        "common_support": {"unique_query_word_format_overlap_capacity": overlap if both else None,
                           "status": "insufficient_labels" if not both else "no_observed_support" if overlap == 0 else "word_format_overlap_only",
                           "whole_matched_sessions_constructed": 0, "bge_pretruncation_tokens": "unmeasured"},
        "leakage_risks": {"cross_split_components": cross_split,
                          "normalized_query_hashes_shared_across_sessions": sum(len(sids) > 1 for sids in query_sessions.values()),
                          "query_hashes_shared_across_labels": sum(len(labels) > 1 for labels in query_labels.values()),
                          "reused_native_session_keys": sum(n > 1 for n in native_sessions.values())},
        "wall_clock_regressions": sum(e["utc_regressed"] for e in events),
        "unreferenced_blob_files": sum(p.name not in referenced for p in (root / "blobs").iterdir() if p.is_file()),
        "provenance_validation": "reference integrity and chronology only; not a signature, license or real intent certification",
        "research_data_ready": False
    }
