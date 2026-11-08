# Phase K — เตรียม First Local Qwen Benign-only Pilot

วันที่ 8 พฤศจิกายน 2026 (Asia/Bangkok) | branch `experiment/stream-prada-order`

**GO เฉพาะ offline preparation; NO-GO สำหรับ real inference และ larger traffic collection**
หยุดตาม Step 2 ของคำสั่ง Phase K: ยังไม่มี legitimate benign requests จาก session จริง,
execution approval/grant และ source/privacy records ที่ operator จัดให้
Phase J acquisition approval ไม่อนุญาต inference และถูก runtime ปฏิเสธจริงเมื่อทดสอบ
ไม่มีการสร้าง PHASE_K_PILOT_REPORT_TH.md เพราะยังไม่ได้รับอนุมัติและไม่ได้ execute pilot

อ่าน Phase G implementation/test/next-pilot, Phase H implementation/readiness/design,
Phase I readiness/blockers, Phase J acquisition/integrity, package READMEs, authorization/storage/runtime source
และ Phase F protocol ก่อนเตรียม ไม่เปลี่ยน runtime, detectors, thresholds หรือ Deep Kernel MMD

## ผลที่ตรวจแล้วบน clean HEAD

ตรวจจริงบน `13271d150b58db3a5ec2c0320ef685c35af64b9d` ขณะไฟล์ preparation ยัง ignored ทั้งหมด
branch ถูกต้อง, clean=true, main คง `5fb5e07d750a73a0a663a174433bab931ae7568a`
G39/H46/I18/J21 manifest files ตรง hashes ทั้งหมด และ runtime code digest
`d163635f0a490a016b7a1fc4a0ce378d464577cd91ec99fe8f08804f9cd6dc87` ตรง frozen Phase H
หลังตรวจจึงเผยแพร่ report/code/tests/aggregate receipts; HEAD หลัง commit จะเปลี่ยน
ต้อง bind final manifest/grant กับ **clean HEAD ที่จะ execute จริง** และ recheck อีกครั้งก่อน pilot

Model/tokenizer `Qwen/Qwen2.5-1.5B-Instruct`, exact revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
อยู่ `traffic_local/qwen_snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
ตรวจครบ LICENSE, config.json, generation_config.json, merges.txt, model.safetensors,
tokenizer.json, tokenizer_config.json, vocab.json รวม **3,098,967,011 bytes** ผ่าน expected sizes/hashes
จาก frozen lock; small files ใช้ Git blob SHA1 และ weights ใช้ LFS content SHA256
`dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`
ไม่โหลด weights/tokenizer เพื่อ hash และไม่มี download/network/victim calls

| การตรวจ ณ 09:48 Asia/Bangkok | ผล |
| --- | --- |
| Offline worker wall / cap | 4.047 s /120 s |
| Observed peak working set / Windows Job committed cap |43,417,600 bytes /512 MiB |
| GPU / driver |RTX4060Ti /617.42 ตรง lock |
| Driver-free GPU / gate |7,012,876,288 bytes (6.53 GiB) /≥6 GiB |
| Available RAM / gate |40,863,551,488 bytes /≥8 GiB |
| Disk free / gate |1,023,530,717,184 bytes /≥1 GiB + write headroom |
| Environment |senior, Python3.11.17, Torch2.14.1+cu132, Transformers5.20.2; packages/static AST ตรง lock |
| Offline readiness |BLOCKED: valid_explicit_approval_and_evidence_required |
| Native imports/CUDA/BF16/model load/generation |ยังไม่ execute/ไม่ verified ใน Phase K |
| Actual requests, claims, model/tokenizer loads |0 ทั้งหมด |

รายชื่อ dependencies ทั้งหมดอยู่ [preflight.json](diagnostics/phase_k_preparation_20261108_v1/preflight.json)
และ [external supervisor](diagnostics/phase_k_preparation_20261108_v1/offline_supervisor.json)
ค่าทรัพยากรเป็น snapshot ต้องตรวจใหม่ ไม่รับรองว่าจะโหลด/ตอบครบภายใน120s
ไม่ได้ rerun CPU import probe ของ Phase I และไม่ได้ใช้ static symbols เป็น native compatibility proof
Job committed cap กับ observed working set เป็นคนละ metric; ไม่ใช่ GPU/latency benchmark

## Private store ที่เตรียมจริง

```text
stream_prada_order/traffic_local/phase_k_pilot_20261108_v1/
  store/                 # ว่าง ไม่มี SQLite/events/requests
  approvals/evidence/    # มีเฉพาะ frozen model LICENSE จริง
  operator_inbox/        # รอไฟล์ที่ operator ระบุสิทธิ์ให้อ่าน
  control/               # สำหรับ final private manifest/plan/grant หลัง records ครบ
stream_prada_order/traffic_local/execution_grants/  # registry ใหม่ ว่าง ไม่มี claim
```

สร้างเฉพาะ directories ใหม่ ไม่เปิด RuntimeStore หรือสร้าง fake session
ปิด inherited ACL ที่ private root/registry, ให้ FullControl เฉพาะ current Windows user SID กับ LOCAL SYSTEM
child folders สืบทอดจาก restricted root; เก็บ Get-Acl SDDL ใน ignored receipts
ตรวจ Git-ignore ของ SQLite/journal/lock/blob/runtime-receipt paths และไม่เป็น tracked files
เก็บ public เฉพาะ [sanitized storage summary](diagnostics/phase_k_preparation_20261108_v1/storage_summary.json)
ไม่มี private SID/query/response/secret ในรายงาน

**ยังไม่ใช่ approved private store**: operator ยังต้อง review retention/deletion authority,
backup/sync/exclusions, encryption requirements, HMAC key custody, registry protection และ read-only snapshot
ACL/ignore ไม่เท่ากับ encryption, consent หรือการป้องกัน malicious administrator
ยังไม่สร้าง HMAC key/actor/native-session identity โดยเดา และไม่เปลี่ยน permission ของ snapshot เดิม
LICENSE copy เป็นหลักฐานเนื้อหาจริง ไม่ใช่ข้อสรุปว่า operator ยอมรับหรืออนุญาต inference แล้ว

## Manifest/query plan ที่เตรียมไว้ และเหตุที่ยัง finalize ไม่ได้

[manifest.draft.json](diagnostics/phase_k_preparation_20261108_v1/manifest.draft.json) และ
[query_plan.draft.json](diagnostics/phase_k_preparation_20261108_v1/query_plan.draft.json)
เป็น **phase-k-nonexecutable-draft-v1** มี execution_authorized=false และ null สำหรับข้อมูลที่ยังไม่มี
wrapper และ inner document ถูก validator ปฏิเสธจริง ไม่ใช้ valid-looking dummy hashes/IDs แทน grant/source/session

ตรึงค่าที่ทราบแล้ว: traffic_kind=real, label=benign จาก intended authorized manifest เท่านั้น,
split=development, acquisition=null, exact victim/tokenizer identity, max_requests/attempts/session_attempts=4,
attempts/request=1, query≤64KiB, response≤16KiB, logical logs≤4MiB
schema v1 บังคับ retry_policy=not_sent_only แต่ budget attempts/request=1 และ H collector fail-stop
จึง **ไม่มี retries แม้ not_sent**; ไม่แก้ schema เดิมเพื่อสร้าง enum ใหม่

ยังขาด run/request/session IDs จริง, actor/native-session HMAC, source-group linkage,
source/document hashes/license/provenance references, task IDs, exact ordered query hashes,
protocol/authorization references และ collector_revision ของ final execution HEAD
queries=null หมายถึงยังไม่มีข้อมูล ไม่ใช่ session ว่างที่เก็บได้จริง
full-input/output token counts ยังเป็น null เพราะยังไม่ instantiate exact tokenizer

## Operator packet ที่ต้องจัดให้ก่อน execution gate

โปรดระบุ path ของไฟล์ที่อนุญาตให้อ่าน หรือวางใน ignored operator_inbox โดยไม่ส่ง participant logs/secrets
ไม่ค้น private approvals/queries บนเครื่องเอง และไม่สร้างคำขอวิจัยขึ้นแทนข้อมูลจริง

1. **Actual queries/session:** ข้อความ UTF-8 ที่ใช้จริง 1–4 รายการจาก legitimate operator-owned native session เดียว
   ระบุลำดับ, original/native session reference, request/document/task IDs, declared format
   (`question_only`, `context_request`, `code`, `mixed`, `other`) และ source rights จริง
   ห้ามต่อ unrelated queries เป็น session หรือเลือก query ถัดไปจากคำตอบ model
   hash exact UTF-8 bytes ไม่ trim/normalize/เปลี่ยน newline หลัง freeze; document content hash อ้าง source ที่ได้รับสิทธิ์
2. **Source authorization:** ผู้มีสิทธิ์ยืนยัน ownership/permission ของ query และ referenced documents,
   license/provenance, benign intent, ไม่มี participant data; source_group ต้องสะท้อน linkage จริง
   raw actor/native-session IDs อยู่ private ใช้ schema.pseudonym กับ namespaces actor/native_session
   และ secret≥32 bytes ที่เก็บนอก Git ภายใต้ reviewed ACL/key policy
3. **Privacy review:** ระบุ store/registry/snapshot paths, ACL, retention ระยะเวลาที่เลือกจริง,
   ผู้มีอำนาจลบ, backup/sync/encryption/key handling, read-only/integrity controls ระหว่าง hash กับ load
   และยืนยัน scope operator-owned only ไม่ใช่ participant traffic
4. **Execution approval:** operator อนุมัติ Phase K แยก ครอบ CPU runtime imports, tiny CUDA/BF16 probe,
   local cached load และ exact planned benign requests ภายใต้ทุก frozen limits ไม่มี external API/download
   authorization evidence ต้องเป็นข้อความอนุมัติจริง ไม่ใช่เอกสารนี้หรือ Phase J acquisition approval
5. **Evidence files:** operator_authorization, model_license, source_authorization, privacy_review
   เก็บ exact bytes เป็น `<sha256>.private` ใต้ approvals/evidence และ review **เนื้อหา/สิทธิ์** จริง
   operator_authorization SHA ต้องตรง manifest.authorization.evidence_sha256; model license SHA ที่เตรียมไว้คือ
   `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e`
6. **Finalize manifest/plan บน clean HEAD:** ตรวจ actual records ก่อนเติม null, จำกัด budgets ตามจำนวนที่อนุมัติจริง
   ใช้ validate_manifest_plan และ `traffic_runtime bindings` จาก exact documents
   bindings ครอบ code/profile/snapshot lock/environment lock/manifest/query-plan
   authority record อนุมัติ scope/query plan; final grant ผูก hashes ของ manifest ที่มี evidence reference แล้ว
   ไม่สร้างวงอ้าง hash ที่ต้องให้ approval file hash ตัวเอง
7. **Operator-issued/reviewed grant:** qwen-execution-grant-v1, unique grant_id,
   purpose=four_request_benign_readiness, traffic_kind=real, execution_authorized=true,
   issued/expires UTC มีอายุ≤24h, exact profile limits และ bindings/evidence ข้างต้น
   operator ส่ง **SHA256 ของ grant bytes แยก** พร้อมยืนยัน records ที่ review แล้ว
   ห้าม agent เปลี่ยน false→true, เดา timestamps หรือใช้ mock numeric evidence สร้างสิทธิ์
   hash/schema validity ไม่ใช่ลายเซ็นหรือหลักฐาน human consent โดยลำพัง

requirements ที่อ่านด้วย code ได้อยู่ [operator_requirements.json](diagnostics/phase_k_preparation_20261108_v1/operator_requirements.json)
และ [evidence inventory](diagnostics/phase_k_preparation_20261108_v1/evidence_inventory.json)

## Frozen execution gate — ยังไม่รัน

| เงื่อนไข | Cap / ขั้นตอนหลัง operator อนุมัติเท่านั้น |
| --- | --- |
| Data |1 genuine benign native session, exact approved order, ≤4 requests/dispatches, one attempt/request, retry0 |
| Native wall |≤120s จาก worker launch รวม worker rehash/import/probe/cached load/inference/logging/normal close |
| Offline preflight |read≤8GiB, ≤120s; clean HEAD/main/frozen source/snapshot/env/actual grant/private store ต้องผ่าน |
| Model |exact local snapshot, local_files_only, trust_remote_code=false; no external API/download |
| Rendering |frozen system/chat template, single-turn system+current user; ไม่เติม prior replies เป็น hidden context |
| Compute |CUDA0, BF16, eager, batch1, greedy/beams1; no quantization/offload/sampling |
| Input/output |full rendered input≤2048/request, generated suffix รวม EOS≤128/request; totals≤8192/512 |
| Bytes |query≤64KiB, decoded response≤16KiB; ไม่ truncate เพื่อผ่าน token gate |
| RAM |available≥8GiB ก่อน/ระหว่างrun, Windows Job aggregate committed cap8GiB |
| GPU |free≥6GiBก่อนload; tiny BF16 finite matmul probeก่อนweights; allocator/peak reserved≤5.5GiB; running free≥512MiB |
| Disk/logs |free≥1GiB + write headroom; logical≤4MiB, physical file sizes incl SQLite/journal≤20MiB; snapshot≤8GiB |
| Admission |RuntimeStore→LocalQwenAdapter→RuntimeCollector; actual grant+explicit flag; one-shot claim/worker preserved |

ก่อน start ต้อง rerun readiness พร้อม `--snapshot --storage-root --approval --approval-sha256 --manifest --query-plan --evidence-root`
expected result STATIC_READY_RUNTIME_UNVERIFIED ยังไม่พิสูจน์ native compatibility
ไม่เรียก backend/supervisor internals ข้าม admission และไม่เปิด execution จาก offline command ของ K
worker อยู่ใน Windows Job ก่อน BOOT, watchdog และ resource sampler แยกกัน
หาก import/probe fail หยุดก่อนweights/requestsตามstage ห้ามเปลี่ยน environment/ลดscope/เพิ่มtimeoutเอง

หลัง generate ต้องเก็บ immutable prepared/input-ID และ outcome/output-ID receipts ใน private store
exact input usage นับ full rendered tokens; output usage นับ generated suffix รวม EOS ไม่ re-tokenize decoded text
audit request/dispatch sequence, UTC/monotonic boundaries, approved source/session/model/template hashes,
G journal/hash chain/replay↔H runtime receipts, token sums, normal closure และ deadline
known failure/not_sent/accepted/unknown ต้องบันทึกตามจริง; unknown output usage=null ไม่เดาเป็น0
timeout/OOM/hash/source/clock/storage/token/resource/invalid-output/unknown ให้หยุดทั้งrun รักษา claims/partials
ไม่ resend หรือ promote unknown จากการเดา Recovery หลังdeadlineเพื่อเก็บหลักฐานไม่ถือว่าrunผ่าน120s

## Tests และ reproduction

[tests_v1.json](diagnostics/phase_k_preparation_20261108_v1/tests_v1.json): **15 ผ่าน** (K7 + frozen H policy8),
fail/error/skip0, 0.109s; numeric fixtures, socket network disabled, ไม่มี Torch/Transformers imports
ครอบ draft rejection, ไม่แต่ง queries/hashes/grants, frozen limits/identity, acquisition≠execution,
grant evidence/expiry/bindings, mock≠real และ one-shot no reset
เริ่มด้วย test ที่ fail เพราะ preparation module ยังไม่เกิด แล้ว implement จนผ่าน
ไม่ได้ rerun full174 H suite; frozen runtime source เดิมไม่เปลี่ยน
public-path test receipt เป็นการยืนยัน relocated test path แยก ไม่เพิ่ม independent test count

จาก repository root หลัง clean commit ใช้ output path ใหม่ที่ ignored (ไม่มี infer/enable CLI):

```powershell
conda run --no-capture-output -n senior python stream_prada_order/phase_k_prepare.py --snapshot stream_prada_order/traffic_local/qwen_snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306 --storage-root stream_prada_order/traffic_local/phase_k_pilot_20261108_v1/store --output stream_prada_order/traffic_local/phase_k_recheck_new --acquisition-record stream_prada_order/diagnostics/phase_j_acquisition_20261108_v1/operator_approval.json
conda run --no-capture-output -n senior python -m unittest stream_prada_order.tests.test_phase_k_preparation -v
```

offline command สร้างเฉพาะ technical receipts/nonexecutable drafts และ **ไม่สร้าง grant/claim หรือ inference worker**
source ที่เผยแพร่ตรง bytes ที่ตรวจบน clean base HEAD; actual bounded hash run ใช้ ignored external supervisor
ที่ attach 512MiB Windows Job และหยุดที่120s ไม่อ้างว่า manual CLI มี external quota โดยตัวมันเอง
readiness BLOCKED จาก approval ที่ขาดเป็นผลคาดหมายและไม่ถูกแก้ให้ผ่าน
ไม่ควรใช้ command หลัง store มีข้อมูล เพราะต้องเป็น empty store และไม่ scan/recover real logs อัตโนมัติ

## Decision

Preparation/integrity/static resources: **GO** ณเวลาตรวจ
First native pilot: **NO-GO รอ operator inputs และ explicit Phase K execution approval**
Larger traffic collection: **NO-GO**; แม้ pilot≤4requestsผ่านภายหลัง ก็พิสูจน์เพียง instrumentation readiness
ไม่ถึง PRADA Q102, ไม่พิสูจน์ horizon256, independent cohorts, detector FPR/TPR/delay/generalization
ต้องมี protocol/source/privacy/resource gate ใหม่ก่อนขยาย ไม่ run attacks/train student/collect participants
ไม่เปลี่ยน detectors/MMD หรือ prior results ไม่มี main/merge/rebase/PR/push และหยุดหลัง local commit
