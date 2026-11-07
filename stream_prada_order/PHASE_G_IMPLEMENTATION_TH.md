# Phase G — Local LLM Traffic Collection Infrastructure

วันที่ 7 พฤศจิกายน 2026 | `experiment/stream-prada-order`
Base: `3683a0213de0a825620c0524fece7f488724e70e`

อ่าน Phase F data plan, protocol และ feasibility ฉบับเต็มก่อนเริ่ม
**สถานะ: collector/storage/schema/offline audit ทำงานและทดสอบด้วย mocks แล้ว**
Qwen adapter เตรียม identity/contract/deployment plan และปิด execution ไว้
อย่างชัดเจน ยังไม่มี inference runtime bridge และไม่ได้รับรอง live deployment
ไม่โหลด weights/tokenizer, ไม่เรียก victim API, ไม่รัน extraction/student training
และไม่เก็บ private participant traffic ในงานนี้

**GO สำหรับ offline infrastructure verification; NO-GO สำหรับ real-data pilot
จน prerequisites ใน [NEXT PILOT](PHASE_G_NEXT_PILOT_TH.md) ผ่าน**
ข้อมูล mock ไม่ใช่ scientific evidence และไม่ใช่ independent research cohorts

## 1. Implementation แยกจาก baseline

อยู่ใน [traffic_collection/](traffic_collection/README.md) ใช้ Python standard
library สำหรับ collector ไม่มี dependency ของ torch/transformers/HTTP client
ไม่แก้ Original Stream PRADA, CUSUM, detector thresholds, Deep Kernel MMD
หรือ evidence/config เดิม ทุกการเปลี่ยนแปลงของ Phase G เป็นไฟล์ใหม่

| Module | หน้าที่ |
| --- | --- |
| `schema.py`, `schemas/` | strict/versioned manifest/event validation, duplicate JSON keys/nonfinite rejection, namespaced HMAC helper |
| `state.py` | replay lifecycle, sequence, boundaries, budgets, source/task/dependency validation |
| `store.py` | single-writer lock, atomic SQLite commits, append-only rows, hash chain, immutable private content addresses |
| `collector.py` | durable request/attempt events, synchronous dispatch, safe retry/failure handling, explicit recovery |
| `adapters.py` | typed victim interface/response/failure และ disabled Qwen deployment descriptor |
| `audit.py` | session/exposure lengths, Q102/256 eligibility, source grouping, duplicate/leakage/common-support risks |
| `views.py` | joined metadata ต่อ attempt ที่คง timestamps/unknown semantics โดยไม่คืน raw text |
| `__main__.py` | offline status/describe/validate/audit/recover ไม่มี collect/enable/download command |

Collector ยอมรับเฉพาะ `traffic_kind=mock` และ mock adapter ใน Phase G
ตรวจ identity/revisions ทั้งตอนเริ่ม run และก่อน collect ไม่ใช้ environment flag
หรือ CLI switch เพื่อเปิด Qwen โดยอัตโนมัติ ไม่ถือ `is_mock` ว่าเป็น sandbox
สำหรับ arbitrary untrusted Python plugins; operator ต้อง review adapter code

## 2. Records และ provenance

Schema IDs: **traffic-manifest-v1**, **traffic-event-v1**;
SQLite `user_version=1`; joined view **traffic-attempt-view-v1**
ไม่ยอมรับ unknown schema version หรือ migrate/rewrite evidence อัตโนมัติ
JSON Schemas ใช้ draft2020-12 vocabulary ที่ runtime นี้รองรับตรงตามไฟล์ที่ ship
ไม่อ้างว่า validator เป็น general-purpose engine สำหรับ arbitrary external schemas

| Required information | ที่บันทึก/validation |
| --- | --- |
| Request/session/run IDs | event envelope และ joined view; request/attempt IDs ห้ามซ้ำใน collection ledger |
| Monotonic ordering | event_sequence, run request_sequence, session_request_sequence และ run dispatch_sequence; one in-flight request |
| UTC และ timing | attempt_started UTC, success/failure observation UTC, monotonic_ns และ clock_epoch; wall-clock rollback ถูก flag ไม่ rewrite |
| Victim/tokenizer revision | frozen manifest identity; adapter ต้องตรง exact model/tokenizer revisions |
| Query/content hashes | exact UTF-8 hashes, normalized query hash สำหรับ duplicate audit, response/decision blob hashes |
| Token usage | input/output counts และ origin จาก successful adapter response; unavailable เป็น null ไม่ประมาณด้วย words |
| Sources/tasks | allowlisted document IDs/content hashes/license/provenance references และ task IDs ใน manifest |
| Labels | benign/attack **จาก run manifest** ไม่ infer intent จาก length/format |
| Acquisition | method/code/config/lineage/query-pool hashes; response-dependent decisions อ้าง private decision artifact และ prior successful attempt IDs |
| Retries/failures | attempt number/retry link/dispatch sequence, delivery accepted/not_sent/unknown, sanitized code; ไม่เก็บ exception text ลง events |

Manifest authorization/source references ต้องมีรูปแบบ/hash ที่ถูกต้อง แต่ไม่ได้
verify external grant/consent/license หรือ actual attack semantics ให้โดยลำพัง
Label v1 เป็น **run intent label** ไม่ใช่ detector prediction, per-query harmfulness
หรือ proof ว่า model extraction สำเร็จ Mixed-condition/onset segments ยังต้อง
มี protocol/manifest extension ที่ review แยก ไม่ติด label prefix ตามการเดา

UTC ของ `attempt_unknown` เป็นเวลาที่พบ recovery ไม่ใช่ response timestamp
Joined view จึงให้ response_utc=null สำหรับ failure/unknown และแยก
failure_observed_utc/recovery_observed_utc; latency ข้าม clock epochs เป็น null
Collector timestamps เป็น local observation boundaries ไม่ใช่ victim-server
acceptance timestamps ที่ยังไม่เคยวัด และไม่ใช้ UTC sort ทับ dispatch order จริง

## 3. Append-only storage และ crash recovery

Event rows ใช้ SQLite transaction + synchronous FULL; triggers ปิด UPDATE/DELETE
และ hash chain ตรวจการเปลี่ยน row/sequence ไม่มีการ truncate/แก้ historical event
Database pages/rollback journals เปลี่ยนทางกายภาพได้ จึงเป็น **logical append-only**
ไม่ใช่ WORM/signed archive และไม่รับรองการต้าน malicious administrator

Write-ahead sequence:

1. เขียน private query blob แบบ exclusive content address แล้ว fsync
2. commit request_started และ attempt_started ก่อนเรียก adapter
3. เก็บ private response ก่อน commit attempt_succeeded หรือบันทึก sanitized failure
4. commit request_finished; session/run close เป็น events แยก

One writer ต่อ directory ใช้ OS file lock (Windows msvcrt/Unix flock) ร่วมกับ
thread mutex; concurrent callers ถูก serialize ตาม dispatch ที่เกิดจริง
Schema initialization อยู่ใน transaction เดียว; empty initialization ที่ถูกขัดจังหวะ
เริ่มใหม่ได้โดยไม่เขียนทับ unrelated databases

Recovery เป็น explicit offline operation ไม่ invoke adapter:

- request intention ก่อน dispatch: finalize failed ไม่ invent victim exposure
- attempt intention ที่ไม่มี outcome: append unknown ไม่ resend
- outcome success commit แล้วแต่ request ยังไม่ finalize: finalize success ไม่ callซ้ำ
- close interrupted sessions/runs และคง orphan blobs ไว้พร้อม audit count
  ห้ามนำมาเติม session lengths หรือเก็บเป็น experiment ที่ complete

Retry อัตโนมัติเฉพาะ adapter ยืนยัน `not_sent` และ retryable ภายใต้งบ
accepted/unknown ไม่ retry; generic exceptions จัด delivery unknown ไม่ assume
victim ไม่เห็น query Native lengthนับ accepted attempts แยกจาก logical requests
รวม retries ที่ victim รับจริงเป็น exposures แยก ไม่ dedup repetitionที่เกิดจริง

ทดสอบ actual subprocess exit ระหว่าง uncommitted transaction แล้ว SQLite
rollback/reopen ผ่าน ไม่ใช่ power-loss/hardware-failure certification
อ้างอิงขอบเขต transaction จาก [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html)
และ [Python sqlite3](https://docs.python.org/3.11/library/sqlite3.html)

## 4. Privacy และ storage limits

ข้อมูลทั้งหมดของ collection—event metadata/hashes, query/response/decision
bytes, manifests และ lock/journal files—อยู่ใน ignored local directory
[traffic_local/.gitignore](traffic_local/.gitignore) ไม่ commit test databases
หรือ private text; committed mock fixture เป็น IDs/hashes ของตัวอย่าง numeric
ไม่ใช่ authorization/traffic ของบุคคลจริง

Storage path ภายใน Git repo ต้องผ่าน git check-ignore และไม่เป็น tracked DB/
blob path ตรวจชื่อ blob/temporary file จริงก่อนเขียนด้วย ไม่เชื่อเพียง probe path
จึงปฏิเสธ selective unignore และไฟล์ที่เคย tracked แม้เพิ่ม ignore rule ภายหลัง
ไม่สร้าง private database ใน public output directoryแบบเงียบ ๆ
ใช้ HMAC actor/native-session keys พร้อม secret นอก Git ไม่เก็บ credentials
ใน schema/config; source/model identities ไม่ใช่เหตุผลให้เปิด private logs

Git ignore ไม่ใช่ encryption/ACL หรือข้อห้าม `git add -f`; content hashes อาจมี
dictionary risk จึงเก็บ local เช่นกัน ก่อน real traffic ต้องตรวจ local ACL,
retention/key management/backup ตามสิทธิ์ที่ได้รับ ไม่อ้าง anonymization สำเร็จ
Store ต้องเป็น local disk ที่รองรับ hard-link publication ไม่รองรับ UNC/network store

มี logical-byte budget ของ serialized events + blobs (default64MiB และลดตาม
manifest), query/output byte caps, request/attempt/session attempt caps และ
reserveสำหรับ outcome/closureก่อน invoke เป็น guard ของ bounded collection
**ไม่ใช่ filesystem quota** ที่รวม SQLite page/journal overhead และยังไม่มี
preemptive timeout supervisor สำหรับ real backend ซึ่งยังปิดอยู่

## 5. Offline dataset feasibility tools

Audit ตรวจ hashes/content lengths, raw/normalized hashes และ replay schema/
lifecycle ก่อนวิเคราะห์ ไม่ print query/response contents หรือ actor/source IDs
ใน aggregate report Joined private view มี metadata references สำหรับ consumer
โดยไม่คืน text และ reject changing snapshot; ควร audit หลังปิด writer
รองรับหลาย runs/sessions ในหนึ่ง explicit collection ledger ไม่ auto crawl
private directories หรือ merge/บวก independent counts จากหลาย stores

วัดได้:

- logical request length, accepted exposure length, not_sent/unknown attempts,
  interrupted/closed state และ idle gap>30นาที (flag ไม่แบ่ง sessionปลอม)
- eligible Q102/horizon256 ต่อ **sessionจริงที่กำหนด** ไม่ sumข้าม sessions
  unknown/invalid-response/idle-gap/interrupted session หรือ run ที่ปิดด้วย recovery
  ไม่ผ่าน eligibility screen แม้บาง session จะปิดปกติก่อน run ถูกขัดจังหวะ
- word/character counts ที่ตรวจตรง content, declared formatและ actual lexical
  markers (multiline/code/context marker); marker ไม่ใช้กำหนด benign/attack label
- source componentsจาก actor/source group/used source-document hashes,
  native-session linkage, acquisition lineage/query pool และ normalized query reuse
  generic task/role header/formatไม่เชื่อมทุกคนเป็นcomponentเดียว
- cross-split components, shared queries/labels/native keys และ coarse word×format
  common support ใช้ทั้ง exposure-weighted distributionsและunique-query support

จำนวน eligible operational components **ไม่พิสูจน์ statistical independence**:
`scientifically_verified_independent_sessions=null`, research_data_ready=false
ยังไม่วัด BGE pre-truncation tokens/Phase F full whole-session matching/calipers
และไม่ได้สร้าง matched sessions จาก histogram overlap

**Available real data ยังพิสูจน์ horizon256 ไม่ได้**: Phase G ไม่มี authorized
real collection; statusไม่ scan private stores และรายงาน unmeasured ไม่ใช้ mock
session256หรือ query poolsที่ไม่มี chronology มาเป็นหลักฐานความพร้อม
Mock testsแสดงเพียงว่าตัวนับ Q101/Q102/Q256 และกฎไม่ concatทำงานถูกต้อง

## 6. การใช้และผลส่งมอบ

จาก repository root:

```powershell
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection status
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection describe-qwen
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_collection validate-manifest --path stream_prada_order/traffic_collection/fixtures/mock_manifest_v1.json
conda run --no-capture-output -n senior python stream_prada_order/phase_g_verify.py --output stream_prada_order/diagnostics/new_phase_g_verification
```

`audit/validate/recover --root <explicit ignored collection>` ใช้กับข้อมูลที่มีสิทธิ์
เท่านั้น ไม่ auto loadข้อมูลจริงจากตัวอย่างคำสั่ง รายละเอียดใน package README
ผล tests/limits อยู่ใน [PHASE_G_TEST_RESULTS_TH.md](PHASE_G_TEST_RESULTS_TH.md)
และข้อกำหนด acquisition ถัดไปใน [PHASE_G_NEXT_PILOT_TH.md](PHASE_G_NEXT_PILOT_TH.md)

คง Phase F quotas/calibration/detector protocol เดิม ไม่ใช้ Phase G mocks เพื่อ
ปรับ parameters หรืออ้าง FPR/TPR/generalization/novelty จบ local commitบนbranch
ที่กำหนด ไม่มี push/main/MMD changes และไม่มี model/API/extraction execution
