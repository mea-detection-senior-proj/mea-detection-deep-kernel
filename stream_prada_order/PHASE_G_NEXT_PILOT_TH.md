# หลัง Phase G — prerequisites สำหรับ first authorized real-data pilot

**สถานะปัจจุบัน: NO-GO สำหรับ real traffic; GO สำหรับ offline mock tests**
เอกสารนี้เป็น proposed gate ไม่ใช่ authorization เรียก victim หรือดาวน์โหลด model
อ่านคู่กับ PHASE_F_* และ PHASE_G_IMPLEMENTATION_TH.md

## 1. ต้องปิด implementation/provenance gaps ก่อนเปิด execution

1. Implement/review local inference runtime bridge และ explicit execution policy
   ในงานที่อนุญาตแยก เพราะ QwenLocalAdapter ปัจจุบันมีเฉพาะ pinned descriptor/
   contract และ respond() ถูกปิดโดยไม่มี enable switch ห้ามแก้ flagแล้วใช้จริง
   โดยไม่ review source/model/budget gates
2. Pin clean collector/runtime/adapter commit, Python/package lock, modelและ
   tokenizer revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, chat/system
   template hash และ generation settings ไม่เปลี่ยน senior เดิมโดยอัตโนมัติ
3. ต้องมี victim/source-document/license/participant authorizationจริงพร้อม
   approval record hash และ task/source allowlist ไม่ใช้ mock fixtureเป็นgrant
   ตรวจ evidence body/สิทธิ์ ไม่ถือ schema-valid SHA256 เป็น consent/signature
4. เลือก actual authorized benign requests เท่านั้น ไม่สร้าง fake participant
   sessionsหรือ synthetic research sentences และไม่อ่าน private logsที่ไม่มีสิทธิ์
   native actor/session IDsมาจากsourceจริง ใช้namespaced HMACกับsecretนอกGit
5. Review response-dependent metadata completeness/usage mapping ของ backend
   และ supervise hard deadline/cancellation ภายนอก synchronous call; ถ้าไม่รู้
   ว่า victimรับrequestหรือไม่ต้องunknownและหยุด ไม่retryเพื่อเติมผล
6. Resolve data-license/source/run lineageก่อน attack collection; MEA code MIT
   ไม่เป็นใบอนุญาต query data และ methodsที่แชร์transcriptไม่เป็นtrafficอิสระ
   ขั้นแรกนี้ไม่มี attack method/student trainingอยู่ในscope

## 2. Proposed first pilot: instrumentation readiness เท่านั้น

| รายการ | Cap/condition ที่ต้องยืนยันก่อนเริ่ม |
| --- | --- |
| Traffic | benign-only, 1 actual native session, ไม่เกิน4 logical requests |
| Attempts | ไม่เกิน4 dispatch intentions รวมทั้งrun, per-request attempts1; ไม่auto retry |
| Victim | local authorized Qwen2.5-1.5B-Instruct exact snapshot, batch1, greedy/no samplingที่freeze |
| Token budget | input<=2048/output<=128 ต่อrequest; ไม่เกิน8192 input/512 output tokensรวมrun |
| Model access | local_files_only, trust_remote_code=false; ไม่ดึง weightsเมื่อcacheไม่ครบ |
| Runtime | cached load+inference+logging<=120sภายใต้ external supervisor |
| GPU | driver-free>=6GiBก่อนload, reserved peak<=5.5GiB; kernel/BF16/backend probeต้องผ่าน |
| RAM/disk | available RAM>=8GiB; dedicated cache allowance<=8GiBหลังอนุมัติ downloadแยกถ้าจำเป็น |
| Private log storage | logical events+blobs<=4MiB; physical directory<=20MiBและmonitor overheadจริง |
| Input/output bytes | query<=64KiB, response<=16KiBต่อrequest; token capsยังต้องตรวจด้วยtokenizer |
| Privacy | dedicated local ACL/retention/backup, .gitignoreและgit-tracked-path checksผ่าน; ไม่มีsecretในmanifest |
| Forbidden | attack/extractor/student/APIภายนอก/download corpus/experimentเต็ม =0 |

4 requestsไม่ถึง PRADA Q102 จึงเป็น **readiness probe ไม่ใช่ detector experiment**
ไม่รายงาน FPR/TPR/detection delay ของ detectorหรือhorizon256จากpilotนี้
Known token countsต้องมาจากexact tokenizer/response usage ไม่ใช้word estimates
หาก usageไม่ทราบให้null/flagและหยุดขยายbudget ไม่ใส่0เพื่อให้ผ่านcap

หากweightsยังไม่มีหรือhash/compatibilityไม่ตรง ให้หยุดก่อนloadและเสนอ download/
environment preflightใหม่ ไม่เพิ่มtimeout/offload/quantize/reduce scopeเงียบ ๆ
Phase G ไม่ได้รัน kernel/model/latency/VRAM preflightดังกล่าว

## 3. Acceptance และ hard stops

Pilotผ่านเฉพาะเมื่อ request/dispatch IDs/sequence/UTC/monotonic recordsครบ,
source/task/label/protocol/approval/model referencesถูกต้อง, raw contentsอยู่
ignored storage, hashes/replay/usageตรงและauditไม่พบunknown/invalid metadata
ตรวจ Gitว่ามีเพียง code/schema/docs/aggregate receiptที่อนุญาต ไม่มีraw traffic

Timeout/OOM/disk/storage/token cap, source mismatch, partial response,
unknown acceptance หรือ clock/chronologyผิดต้องเก็บหลักฐานและหยุด
Recoveryเพิ่มeventsเท่านั้น ไม่resend ไม่แก้unknownเป็นsuccessหลังเดา
Interrupted requests/runsไม่ถูกแทนด้วยclean runโดยไม่เก็บattemptเดิม
Resumeต้องมีoperatorตัดสินใจและrun/session lineageที่บอกความเกี่ยวข้องตามจริง

## 4. ก่อนขยายเป็น dataset acquisition หรือ extraction

ต้องมี protocol/resource gateใหม่ที่ระบุจำนวนnative actors/sources/runsจริง,
format/length/common-support coverage, chronology/idle/session rules, Phase F
fit/calibration/validation/final-test allocation, exposure/duplicate ledger และ
independence guardที่ตรวจได้ก่อนscoring ไม่แทนcohortsด้วยretry/reorder seeds

Current auditorวัด coarse word/format supportเท่านั้น ต้องเพิ่มBGE pre-truncation
token descriptorsและwhole-session matching/caliper auditก่อนaccept scientific
dataset รวมถึงglobal groupingถ้าข้อมูลแยกหลายstores ห้ามsumcomponent countsเอง
ประเมินstreaming/memory/storage scaleตามจำนวนeventsจริงก่อนfullcollection

Actual extractionต้องมีexplicit authorizationและfaithful method-specific
implementation/source/model/licensing/budget ถ้าmethodต้องstudent/warmup
ห้ามตัดtrainingแล้วเรียกsuccessful/faithful extraction ตรวจintent provenance
แยกจากstudent fidelity ซึ่งยังไม่อยู่ในfirstbenignpilot

ไม่มีการเก็บข้อมูลจริงหรือเปิดstageถัดไปจากเอกสารนี้ ไม่push/merge/rebase/PR
และไม่เปลี่ยนmainหรือteammate Deep Kernel MMD implementations
