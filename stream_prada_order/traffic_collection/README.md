# Local traffic infrastructure v1 — offline phase

Run from the Deep-Kernel repository root, on `experiment/stream-prada-order`.
This package uses Python's standard library. It does not import a model runtime,
download weights, run an extractor, serve HTTP, or train a student.

```powershell
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection status
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection describe-qwen
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection validate-manifest --path stream_prada_order/traffic_collection/fixtures/mock_manifest_v1.json
```

The fixture is a **mock manifest**, not real authorization or research data.
`Collector` accepts mock adapters/manifests only in Phase G. `QwenLocalAdapter`
pins model/tokenizer revisions and a deployment plan but always raises
`ExecutionDisabled` on execution. There is no enable/download/collect CLI switch.
The local inference runtime bridge is intentionally not implemented in this phase.

Modules:

- `schema.py` and `schemas/`: strict manifest/event contracts; runtime validation
  implements the vocabulary used by these self-contained JSON Schemas, not an
  arbitrary general-purpose JSON Schema engine.
- `store.py`: one writer per private collection directory, immutable content
  addresses and logically append-only event rows with hash chaining.
- `state.py`: replay validation of run/session/request/attempt lifecycle,
  provenance references, sequence, retries, dependencies and budgets.
- `collector.py`: synchronous adapter invocation, durable dispatch intentions,
  sanitized failures, response usage and explicit offline recovery.
- `audit.py`: native lengths, Q102/horizon256 coverage, grouping, duplicate/
  leakage risks, declared/lexical formats and coarse common support.
- `views.py`: joined private metadata per dispatch intention; no raw contents,
  no invented response timestamp and no cross-process monotonic latency.

Explicit offline operations on a **separately authorized** collection directory:

```powershell
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection audit --root stream_prada_order/traffic_local/approved_collection
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection validate --root stream_prada_order/traffic_local/approved_collection
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection recover --root stream_prada_order/traffic_local/approved_collection
```

Do not run these against private participant logs without authorization. The
default `status` command does not scan storage. No real collection is performed
by the examples above, and a missing store fails instead of creating empty data.

Use one explicit collection ledger for the complete dataset grouping audit.
Multiple runs/sessions within it remain distinct. There is no directory crawler
or automatic cross-store merge; never sum independent-count claims from separate
audits. Audit after closing the writer. Joined views reject a changing snapshot.

Storage layout (all ignored locally):

```text
approved_collection/
  writer.lock
  events.sqlite3
  events.sqlite3-journal       # transient SQLite rollback journal
  blobs/<sha256>.private      # query/response/decision bytes
  blobs/part-<nonce>           # retained if interrupted before publish
```

`traffic_local/.gitignore` excludes all payloads. A storage directory inside any
Git repository must pass `git check-ignore` and must not contain tracked database/
blob write paths. Exact content-address and temporary paths are checked before
writing, so selective unignore exceptions and previously tracked blobs are refused.
Outside Git, use a dedicated private local directory with appropriate
OS permissions. Git ignore is not encryption, an ACL or protection against
`git add -f`. Hashes are not anonymization. Use the provided namespaced HMAC
helper with a secret kept outside Git for actor/native-session keys.

SQLite transactions and `synchronous=FULL` handle process interruption; event
UPDATE/DELETE triggers and a hash chain detect ordinary edits/corruption.
SQLite database pages are physically mutable. This is not WORM storage, a signed
audit trail, or protection against a malicious administrator recomputing hashes.
Local disk/hard-link support is required; network/UNC storage is unsupported.

Recovery appends terminal/unknown events and closes interrupted sessions/runs.
It never sends again. `attempt_started` is a dispatch **intention**, not proof of
victim acceptance. Delivery uncertainty stays unknown. Not-sent retry attempts
are excluded from accepted exposure length; accepted retries would be separate
exposures, but v1 automatically retries only confirmed `not_sent` failures.

Token counts come from adapter reports, never estimated from words. Failed or
unknown attempts have unavailable usage in the current contract. Declared labels
and provenance hashes are not cryptographic proof of intent/authorization.
The current format audit is descriptive and the full Phase F matching/caliper
procedure, BGE tokenization and an inference backend remain next-stage work.

Limits are checked against serialized event-body plus blob bytes. They are not
filesystem quotas covering SQLite page/journal overhead or execution deadlines.
The collector is synchronous; a future real runtime needs an external wall-time/
GPU supervisor before authorization. This version is suitable for bounded offline
verification, not a claim of large-scale or production readiness.

```powershell
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests -p "test_phase_g*.py" -v
conda run --no-capture-output -n senior python stream_prada_order/phase_g_verify.py --output stream_prada_order/diagnostics/new_phase_g_verification
```

The verifier has a 120-second subprocess gate, disables CUDA visibility and
outbound socket connections in its test worker, and runs the original numeric
regressions too. Mock data are never evidence for detector performance or the
availability of independent real sessions.
