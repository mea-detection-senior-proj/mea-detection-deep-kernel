# Phase H — Offline Readiness และ first benign-only pilot gate

วันที่ 7 พฤศจิกายน 2026 | `experiment/stream-prada-order`

**GO: implementation/offline mock verification เสร็จแล้ว**
**NO-GO: real inference / first real-data pilot ในขณะนี้**
Phase H ไม่ใช่ execution grant และไม่มีการดาวน์โหลด/โหลด weights, เรียก victim,
ใช้ API ภายนอก, ทำ extraction/training หรือเก็บ participant traffic

อ่านคู่กับ [PHASE_H_IMPLEMENTATION_TH.md](PHASE_H_IMPLEMENTATION_TH.md),
[PHASE_G_NEXT_PILOT_TH.md](PHASE_G_NEXT_PILOT_TH.md) และ
[PHASE_F_PROTOCOL_TH.md](PHASE_F_PROTOCOL_TH.md)

## 1. สิ่งที่ตรวจจริงแบบ offline

หลักฐาน [offline readiness receipt](diagnostics/phase_h_readiness_20261107_v1.json)
เกิดก่อน local commit ของ Phase H ใช้ default/configured HF cache สำหรับ
**exact Qwen revisionเท่านั้น** ไม่ค้นทุกdisk, private logs หรือ alternate caches
ที่ผู้ใช้ไม่ได้ระบุ Model runtime modules ที่ import ใน standalone check = []

| รายการ | ผล |
| --- | --- |
| Exact model snapshot | ไม่พบใน configured/default cache; bytesของweightsที่อ่าน/hash =0 |
| Model/tokenizer revision | pin `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`; availability/hash verification ของlocal weightsยังไม่ผ่าน |
| Python / OS | senior, Python3.11.17, Windows |
| torch / transformers | metadata2.14.1+cu132 /5.20.2 ตรง environment lock |
| tokenizers / hub / safetensors |0.23.3 /1.33.0 /0.8.0 |
| numpy / psutil / jinja2 |2.4.6 /7.2.2 /3.1.6 |
| Static API symbols | Qwen2ForCausalLM / apply_chat_template / generate พบใน installed source AST |
| Actual native import/kernel/BF16/model load/generation | **unverified** ไม่ execute เพื่อหาคำตอบใน Phase H |
| GPU snapshot | RTX4060Ti, driver617.42, free6,781MiB ณ check; ไม่ใช่ guaranteed future free VRAM |
| RAM / disk free snapshot |39,402,958,848 /1,026,628,292,608 bytes |
| Approval/evidence/private pilot store | ยังไม่ได้ supplied/validated สำหรับ real run |
| Code checkout ใน receipt | base3b2d291 พร้อม Phase H additionsที่ยังไม่ commit; ต้อง rerun จาก clean final commitก่อน pilot |
| Readiness decision | BLOCKED; real_execution_enabled=false |

ค่า GPU/RAM/disk ผ่าน numeric pre-load gate ณ snapshot นี้ แต่ไม่รับรองว่า
จะโหลด Qwen ได้จริง ไม่ถือ package version/AST symbol ว่าพิสูจน์ binary/runtime
compatibility และไม่ได้อ้างว่า cacheที่อื่นบนเครื่องไม่มีโมเดล

Public metadata ที่ bounded script ตรวจเพิ่มเป็น config/template/license เท่านั้น
3 logical GETsสำเร็จ รวม18,890bytes ไม่ใช่ network total ของ documentation tools
และไม่ fetch tokenizer vocabulary/model tensors รายละเอียด:
[config receipt](diagnostics/phase_h_metadata_20261107_v1/receipt.json),
[license receipt](diagnostics/phase_h_license_metadata_20261107_v1.json)
การเข้าถึง metadata เหล่านี้ไม่ใช่ victim API request

## 2. Blockers ที่ต้องปิดก่อน authorize pilot

1. **Local snapshot:** ระบุ exact approved local snapshot มี8 required files
   ตาม snapshot_lock_v1.json และตรวจทุก size/Git blob/LFS SHA ผ่าน ไม่อนุญาต
   extra unreviewed code Model fileต้อง3,087,467,144bytes และ SHA256
   `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`
   ถ้ายังไม่มี ให้ขอ acquisition/download gate แยกก่อน ไม่ดาวน์โหลดเองในงานนี้
2. **Clean frozen implementation:** branchเดิม, mainเดิม, clean checkout ของ
   final Phase H commit; manifest collector_revision=HEAD, code/profile/snapshot/
   environment lock bindingsตรง ไม่มี pip/Conda update หรือแก้ configระหว่างrun
3. **Actual authorization:** operator อนุมัติ benign-only readiness scopeชัดเจน
   พร้อม grant SHA ที่ส่งแยก, evidenceของmodel license/source permission/privacy
   ที่อ่านตรวจเนื้อหาแล้ว ไม่ใช้ numeric fixture/hashที่ไม่มีgrantจริงแทนหลักฐาน
4. **Actual query/session provenance:** operator-owned legitimate benign requests
   จากงานจริง1 native session, ordered query plan1–4รายการ พร้อมexact query hashes,
   source document/task IDs, actor/native-session HMAC และ keyนอกGit ไม่ใช้ private
   participant logs หรือสร้าง fake independent sessions/synthetic research queries
5. **Private environment:** dedicated ignored storeใหม่, Windows ACL/retention/
   backup/key handlingได้รับreview, snapshot read-only/ไม่เปลี่ยนระหว่างhashกับload,
   grant registryป้องกันการแก้/คัดลอกเพื่อresetbudget และoperatorสามารถหยุดงานได้
6. **Runtime compatibilityยังต้องทดสอบใน authorizationใหม่:** อนุมัติ imports,
   tiny CUDA/BF16 probe และ cached load ภายใน120s gateเดียวกันก่อนรับreal requests
   ถ้าimport/kernel/probe failต้องหยุดก่อนweights/requestsตามstageที่ทำได้
   ไม่แก้environment/offload/quantizeแล้วรันต่ออัตโนมัติ

Offline command ที่ใช้ rerun หลัง prerequisites พร้อม:

```powershell
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_runtime readiness
```

ถ้าต้องตรวจ explicit snapshot/grant/plan ใช้ optional arguments ใน
[package README](traffic_runtime/README.md) โดยไม่เปิด inference Commandนี้ไม่มี
start/enable switch และยังรายงาน native runtime เป็น unverified แม้ static checksผ่าน
เก็บ private approval/readiness receipts ใต้ ignored local storage ไม่ redirect
ไป untracked public fileจนทำให้ clean-checkout gatefail

## 3. Exact proposed resource gate — แยกอนุมัติ ไม่ได้รัน

| Scope | Frozen cap / prerequisite |
| --- | --- |
| Purpose | Instrumentation readiness ของ local Qwen เท่านั้น ไม่ใช่ detector experiment |
| Data | benign-only, operator-owned requests, 1 actual native session |
| Logical/dispatch budget |1–4 planned requests, รวม<=4 dispatch intentions, one attempt/request, retry0 |
| Selection | exact planned hashes/order/source/task; no substitution, adaptive query selection หรือเติมrequestsหลังfailure |
| Victim/tokenizer | Qwen2.5-1.5B-Instruct revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` ทั้งคู่ |
| Rendering | frozen upstream chat template+system message, single-turn system/current-user, full input IDsเก็บprivate |
| Generation | BF16, CUDA0, eager, batch1, greedy, beams1, max_new128, no sampling/quantization/offload |
| Tokens/request | full input<=2048, generated outputรวมEOS<=128; ไม่ truncateเพื่อผ่านgate |
| Run tokens | input<=8192/output<=512; unknown outputเป็นnullและหยุด ไม่คิดเป็น0 |
| Bytes/request | query<=64KiB, decoded response<=16KiB |
| Offline byte/hash preflight | read<=8GiB, <=120s, ไม่มี model/tokenizer instantiation; ถ้า failไม่ load |
| Native run deadline |<=120s จาก worker launch ครอบ worker rehash, import, tiny probe, cached load, inference และ normal logging/close |
| RAM | available>=8GiB ก่อนและระหว่างrun; Windows job aggregate committed-memory cap8GiB |
| GPU before load | driver-free>=6GiB; reviewed RTX4060Ti/driver617.42; compatibility probeต้องผ่านก่อนweights |
| GPU during run | caching allocator/peak reserved<=5.5GiB; sampled global driver-free>=512MiB; ไม่เท่ากับ cap ทุก CUDA/driver allocation |
| Cache | exact local snapshot<=8GiB; cacheไม่ครบให้หยุด ไม่มีnetwork fetchใน120s run |
| Disk/logs | diskfree>=1GiB พร้อมwrite headroom, logicalevents+blobs+receipts<=4MiB, directoryfile sizesรวมSQLite/journal<=20MiB |
| Supervisor | Windows Job Object attachก่อนboot, kill-on-close, independent wall watchdog; real guard overrides forbidden |
| Grants | exact hash/evidence/bindings, benign-development only, validity<=24h, one-shot checkout-local claim/worker |
| Forbidden | external victim API, weight/corpus downloadในrun, attack/extractor/student/training/participant collection =0 |

GPU allocator capกับ periodic disk/GPU sampler ไม่ใช่ OS-wide perfect quota:
ใช้ dedicated machine/store, หยุดเมื่อชนguard และเก็บ receiptจริง อาจมี sampling
overshootหรือ driver allocationsนอกpool จึงยังไม่รับรอง production readiness

## 4. Pilot acceptance, stop และ evidence

Acceptเฉพาะเมื่อ approved planned requestsครบ, sequence/session/run/hash/model/
template/usage referencesตรง, responses/IDsอยู่private, runtime audit↔G auditผ่าน,
ไม่มี unknown/corruption/clock anomaly และ normal close/loggingเสร็จก่อนdeadline
ห้ามเรียก pilotผ่านเพียงเพราะมี decoded textกลับมา

Missing snapshot/hash/approval, package/driver/branch/code mismatch, token/byte/
RAM/GPU/disk cap, timeout, OOM, invalid responseหรือunknown delivery ต้องหยุด
เก็บ failed/interrupted evidenceและclaimไว้ ไม่ resend/overwrite/ลดsettingsให้ผ่าน
Failure/recovery loggingหลัง forced deadlineทำได้เพื่อรักษาหลักฐาน แต่runนั้น
ไม่ผ่าน120s success criterion และไม่อ้างว่าจบnormalภายในgate

หากruntime outcome durableแต่G commitไม่ครบ ใช้unknownตามG recoveryพร้อม
sidecarที่ยังอยู่ ไม่promoteเป็นsuccessแบบเงียบ ๆ Runใหม่ต้องมีoperatorอนุญาต/
grantใหม่พร้อม lineageที่บอกความเกี่ยวข้อง ไม่เพิ่มnจาก retries/resumes

4 requestsยังไม่ถึง Original PRADA Q102 จึงไม่คำนวณ FPR/TPR/detection delay
หรือยืนยัน horizon256/independent cohorts จากpilotนี้ Phase F fit/calibration/
validation/final-test quotas และ matching/uncertainty protocolยังไม่เกิดขึ้น
ถ้าจะขยาย acquisition/full experimentต้องมีdata/protocol/resource gateใหม่

## 5. Implementation verification ที่เสร็จแล้ว

[Final mock/regression receipt](diagnostics/phase_h_verification_20261107_v3/verification.json):
**174ผ่าน (ใหม่44+เดิม130)**, worker24.0354s, native backend load entries0,
model weights/downloads/victim requests/extraction/training/participants0
มีactual process interruption/Windows Job Object testsด้วยnumeric mock workers
ไม่มีหลักฐานให้ claim measured native Qwen performanceหรือdetector improvement

คำตัดสินสุดท้าย **NO-GO real pilot จนข้อ2–4พร้อมและได้รับauthorizationใหม่**
งานนี้จบที่ offline implementation/local commit ไม่มีpush/merge/rebase/main/PR
