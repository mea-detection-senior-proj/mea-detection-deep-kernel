# Phase G — ผลตรวจ implementation และ offline tests

วันที่ 7 พฤศจิกายน 2026 | branch `experiment/stream-prada-order`

**PASS: 130 tests, failures/errors/skips = 0** จาก bounded offline verification
รอบสุดท้าย v3 ใช้เวลา test worker **34.202 วินาที** ภายใต้ gate 120 วินาที
เป็นผลทดสอบ software ด้วย numeric mocks/fixtures ไม่ใช่ผล detector experiment

หลักฐานหลัก: [verification.json](diagnostics/phase_g_verification_20261107_v3/verification.json),
[รายชื่อ tests และผล](diagnostics/phase_g_verification_20261107_v3/test_results.json),
[preflight/source hashes](diagnostics/phase_g_verification_20261107_v3/preflight.json)
และ [artifact hashes](diagnostics/phase_g_verification_20261107_v3/artifact_hashes.json)

## 1. ขอบเขตและ resource ที่วัดจริง

| รายการ | ผล |
| --- | --- |
| Environment | Conda `senior`, Python 3.11.17, SQLite 3.53.4 บน Windows |
| Tests ใหม่ Phase G | 66 |
| Regression tests เดิม | 64; numeric CPU matrices/fixtures ของ Phase A–E |
| เวลา worker รวม discovery/import/tests | 34.20183460001135 วินาที ไม่รวมเวลาเปิด Conda/parent process |
| Peak working set ของ worker | 643,592,192 bytes หรือประมาณ 613.78 MiB; ต่ำกว่า review cap 2 GiB |
| Model weights loaded/downloaded | 0 |
| Real victim/API requests | 0 |
| Extraction/student training/private participant collection | 0 |
| CUDA visibility | ปิดใน worker; ไม่ใช้ GPU สำหรับ tests |
| Network guard | ปิด socket connect/connect_ex/create_connection ใน worker; HF/Transformers offline env |
| Prior tracked files / main | SHA ก่อนและหลังตรงกันทั้งหมด |

Peak ข้างต้นรวม legacy tests ที่ import Torch สำหรับ numeric CPU regressions
ไม่ใช่ model VRAM benchmark และไม่ใช่ cumulative peak ของ process tree ทั้งหมด
Collector modules เองใช้ standard library เท่านั้น มี test ตรวจว่า import และ
mock collection ไม่ต้องใช้ model/network libraries

ค่า execution=0 ระบุขอบเขต workflow/code ที่รันและ guards นี้ ไม่ใช่การอ้างว่า
มี packet capture ของทุก process บนเครื่อง ไม่โหลด tokenizer/weights เพื่อทดสอบ
ความพร้อมของ Qwen ใน Phase G

## 2. สิ่งที่ tests ยืนยัน

| Test module | จำนวน | พฤติกรรมที่ตรวจ |
| --- | ---: | --- |
| `test_phase_g_collector.py` | 8 | chronology/IDs/hashes/usage, manifest labels, retries, unknown delivery, duplicate IDs, disabled real execution |
| `test_phase_g_integrity.py` | 38 | schema/provenance/privacy, budgets, writer concurrency, append-only guards, corruption, crash recovery, Unicode, CLI sanitization |
| `test_phase_g_audit.py` | 15 | native lengths/Q102/256, no concatenation, grouping/leakage/common support, unknown/interrupted exclusion, negative findings |
| `test_phase_g_views.py` | 5 | joined attempt records, retry links, success/failure/recovery timestamps, cross-epoch latency null, snapshot consistency |
| Existing modules | 64 | baseline/Phase A–E numeric behavior และ integrity checks เดิม |

กรณีสำคัญ:

- Concurrent callers ถูก serialize; request/dispatch sequences และ session
  boundaries ถูกเก็บตามลำดับที่ adapter ถูกเรียก ไม่ sort ใหม่ตาม wall clock
- UTC ถอยหลังถูก flag; token counts ที่ไม่มีเป็น null; boolean token counts/
  invalid responses ไม่กลายเป็น success
- Retry เฉพาะ confirmed not_sent; accepted/unknown ไม่ resend การ recover
  ก่อน dispatch ไม่ invent exposure และหลัง durable success ไม่ call ซ้ำ
- ทดสอบ subprocess `os._exit(73)` ระหว่าง uncommitted SQLite transactionจริง
  แล้ว reopen/rollback ได้ รวมถึง release OS writer lock หลัง process ตาย
  การทดสอบนี้ **ไม่ใช่ power-loss หรือ hardware-failure test**
- UPDATE/DELETE ถูกปฏิเสธ, altered hash chain/private blob ถูกตรวจพบ,
  unknown schema/duplicate JSON keys/missing attack provenance ไม่ผ่าน
- ไฟล์ private ต้อง ignored และไม่ tracked: ตรวจ selective unignore ของ
  content-address filenameจริง และ previously tracked blob แม้เพิ่ม ignoreภายหลัง
- ตัวนับแยก Q101/Q102/Q256 ต่อ native session; sessions100+200 ไม่ถูกต่อให้256
  run ที่ recover ปิดแบบ interrupted ไม่ทำให้ session102 ก่อนหน้า eligible
- Actor/source/content/lineage/query reuse เชื่อม components ข้าม runs/splits
  ส่วน generic format ไม่ทำให้ทุก source เป็นกลุ่มเดียวโดยไม่มี linkage
- Benign/attack ที่ไม่มี length×format overlap รายงาน no_observed_support;
  histogram overlap ไม่ถูกเรียก whole-session matching หรือ independent cohorts

Tests ใช้ `TemporaryDirectory` และ numeric mock contents เท่านั้น ไม่ commit
SQLite stores/raw traffic และไม่ใช้ test mock authorization เป็นสิทธิ์จริง
การที่ schema/reference ถูกต้องไม่พิสูจน์ consent/license/attack semantics

## 3. Reproduce

จาก repository root และ branch ที่กำหนด ใช้ environment เดิม:

```powershell
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests -p "test_phase_g*.py" -v
conda run --no-capture-output -n senior python stream_prada_order/phase_g_verify.py --output stream_prada_order/diagnostics/new_phase_g_verification
```

คำสั่งแรกตรวจเฉพาะ 66 tests ใหม่ คำสั่งที่สองตรวจครบ130และบันทึก hashes/
resource receipt ต้องใช้ output directoryใหม่ที่ยังไม่มี ห้ามเขียนทับ v1/v2/v3
Verifier fail ถ้าเกิน120วินาที, testsไม่ผ่าน, sources/old tracked files/mainเปลี่ยน
หรือ measured worker peakเกิน2GiB โดยไม่ปรับ gate อัตโนมัติ

เก็บ receipts ก่อนหน้าไว้: v1 ผ่าน122 tests, v2 ผ่าน127 tests เป็น snapshots
ของ implementation ณ ตอนนั้น ไม่ใช่หลักฐาน final source ทั้งหมด รอบ v3
เพิ่ม regression tests หลังพบ interrupted-run eligibility และ exact blob ignore
guards ขาดหาย กรณีใหม่ทั้ง3 fail ก่อนแก้ แล้วผ่านหลังแก้

ใช้กฎ LF ใน `stream_prada_order/.gitattributes` เดิมเพื่อให้ hashes คงเดิมเมื่อ
checkout บน Windows ไม่มีการเปลี่ยน line-ending rules ของ evidence/code เดิม
[PHASE_G_MANIFEST.json](PHASE_G_MANIFEST.json) ครอบคลุม source/docs/receipts
ทั้งหมดของ Phase G โดยไม่รวมตัว manifest เอง

## 4. สิ่งที่ยังไม่วัดและ blockers

**Available real data รองรับ horizon256 หรือไม่: ยังตอบไม่ได้ (unmeasured)**
ไม่มี authorized native collection ใหม่ ไม่ scan private logs และไม่ใช้ query
pools เดิมที่ไม่มี native chronology มาประดิษฐ์ session จึงรายงานจำนวน
scientifically verified independent sessions เป็น **null ไม่ใช่ 0 ที่วัดแล้ว**
Mock session256 ยืนยันเพียง eligibility code path ไม่เพิ่ม research sample size

ยังไม่วัด real latency/VRAM/token accuracy/acceptance behavior, real source
provenance, actual session-length coverage/common support, whole-session matching,
FPR/TPR/delay/order sensitivity หรือ statistical generalization
ไม่เปลี่ยน threshold/detector parameters และไม่เรียกผล mock ว่าปรับปรุง detector

Qwen descriptor ถูก pin/disabled จริง แต่ **runtime bridge ยังไม่ implement**
ก่อน first authorized pilot ต้องมี implementation/review/explicit authorization,
source/model/license evidence, external timeout/GPU/physical-storage supervisor,
privacy ACL/key/retention controls และ resource preflightตาม
[PHASE_G_NEXT_PILOT_TH.md](PHASE_G_NEXT_PILOT_TH.md)

**GO offline infrastructure; NO-GO real collection/extraction/full experiment**
จน prerequisites ผ่าน ไม่มี push หรือ integration PR และ main ไม่เปลี่ยน
