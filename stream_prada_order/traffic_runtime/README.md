# Local Qwen runtime bridge v1 — Phase H

This package integrates with Phase G's unchanged SQLite ledger, event schema,
private blobs, joined views, and recovery. Importing it cannot load a model.
Real execution is disabled by default. Phase H authorizes **no real inference**.

From the repository root, on `experiment/stream-prada-order`:

```powershell
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_runtime describe
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_runtime readiness
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests -p "test_phase_h*.py" -v
conda run --no-capture-output -n senior python stream_prada_order/phase_h_verify.py --output stream_prada_order/diagnostics/new_phase_h_verification
```

`readiness` exits 2 when blocked. It checks only the configured exact Qwen cache
snapshot, metadata, byte hashes, package versions, static API symbols, OS resource
metadata, branch state, and explicitly supplied approval records. It does not
import Torch/Transformers, instantiate a tokenizer, load weights or call a victim.
It does not search other disks or private logs. `STATIC_READY_RUNTIME_UNVERIFIED`
would still not certify imports, CUDA/BF16 kernels, model loading or generation.

Optional readiness arguments are `--snapshot`, `--approval`, `--approval-sha256`,
`--manifest`, `--query-plan`, `--evidence-root`, and `--storage-root`. All supplied
records must be authorized for inspection. `bindings --manifest ... --query-plan
...` computes required hashes; it does not create authorization. `audit --root
...` checks one explicit private store and its runtime receipts. There is no
infer/start/enable/download CLI.

The future, separately authorized library path is `RuntimeStore` →
`LocalQwenAdapter` → `RuntimeCollector`. A real adapter additionally requires an
explicit execution flag, an unexpired operator grant, matching private evidence,
a clean pinned checkout and manifest, approved snapshot hashes, frozen environment,
resource gates, and a one-shot checkout-local grant claim. Neither a Boolean flag
alone nor a mock grant can authorize it. Do not use backend/supervisor internals
as a replacement for this admission path or run unreviewed plugins.

The grant format `qwen-execution-grant-v1` has exact keys:

- `schema_version`, `grant_id`, `purpose=four_request_benign_readiness`,
  `traffic_kind`, `execution_authorized`, `issued_utc`, `expires_utc`;
- `bindings` from the bindings command, and `limits` exactly from the profile;
- `evidence`: SHA256 references for `operator_authorization`, `model_license`,
  `source_authorization`, `privacy_review`, stored as `<sha256>.private` files
  under the explicit evidence root. The operator authorization reference must
  equal the run manifest's approval evidence hash.

Grants last at most 24 hours. Their exact bytes' SHA256 is supplied independently
by the operator. A hash/reference is not a signature or proof of human consent.
The operator must review the evidence contents and authorize the scope separately.
The real one-shot registry is `traffic_local/execution_grants/`; claims are never
deleted/reset automatically, even after a pre-load failure. Changing stores or
copying an approval file does not reset this checkout's grant budget. ACLs and
operational controls must prevent copying the entire checkout/registry to bypass
accounting; this is not a malicious-administrator security boundary.

`qwen-query-plan-v1` contains `run_id`, `session_id`, `native_session_sha256`, and
1–4 ordered `queries`. Each query declares request ID, exact query hash, source
document IDs, task ID, and declared format. Runtime selection cannot substitute,
reorder or append requests. See `tests/phase_h_helpers.py` for numeric **mock**
structures; these are not real authorizations or research traffic.

`QwenBackend` renders system+current user, tokenizes without extra special tokens,
padding or truncation, and counts full input IDs and generated suffix IDs including
EOS. No conversational history is silently added. Model/tokenizer file identities,
system message, chat template, greedy generation, dtype/device/attention and caps
are frozen in the three v1 lock/profile JSON files. The upstream default sampling
configuration is recorded as provenance; this pilot deliberately uses the declared
greedy profile, not a claim of matching upstream default generations.

`RuntimeStore` adds immutable `runtime_receipts/<attempt>.<stage>.private` files
for binding, prepared input, and outcome. Prepared receipts include private rendered
prompts and token IDs before generation admission. They and all raw content stay
ignored locally. Failed/unknown generated token usage remains null. A durable runtime
result without a committed collector success is conservatively recovered as unknown,
never resent or silently promoted to success.

The worker waits for Windows Job Object attachment before boot. An independent
watchdog terminates it at the whole-run deadline; a separate resource sampler
cannot delay that watchdog. Windows jobs enforce aggregate committed memory and
kill-on-close. GPU allocator limits do not cap all driver/display allocations.
Disk checks count file sizes including SQLite/journal/receipts with headroom;
they are not filesystem quotas, sector-allocation measurement or protection from
arbitrary concurrent writers. Polling may overshoot between samples. Keep a
dedicated private store and review these limits before the proposed pilot.

Public Qwen configuration/template provenance is at exact model revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`; see [QWEN_LICENSE.txt](QWEN_LICENSE.txt)
for the upstream Apache 2.0 license. No weights or tokenizer vocabulary are bundled.

Read [PHASE_H_IMPLEMENTATION_TH.md](../PHASE_H_IMPLEMENTATION_TH.md) and
[PHASE_H_READINESS_TH.md](../PHASE_H_READINESS_TH.md) for verified tests, current
blockers, and exact prerequisites. No detector performance follows from mocks.
