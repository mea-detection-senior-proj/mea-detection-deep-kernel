# Offline Hybrid Fusion — ผลทดสอบและขอบเขตหลักฐาน

8 พฤศจิกายน 2026 | `experiment/stream-prada-order`

**PASS: 22 unit tests, failures/errors/skips=0** ด้วย synthetic numeric score fixtures เท่านั้น
implement ครบ sequential-only, MMD-only, OR, AND และ normalized weighted score fusion
ไม่มี real same-stream detection experiment จึง **ยังไม่วัด scientific FPR/TPR/detection delay**
ไม่ใช้ fixture results อ้าง improvement, generalization หรือ novelty

## หลักฐาน execution

- [Tests และรายชื่อครบ](diagnostics/hybrid_fusion_20261108_v1/tests.json)
- [Resource/preservation verification](diagnostics/hybrid_fusion_20261108_v1/verification.json)
- [Preflight source/config/design hashes](diagnostics/hybrid_fusion_20261108_v1/preflight.json)
- [Development attempts](diagnostics/hybrid_fusion_20261108_v1/development_attempts.json)
- [Final source/evidence manifest](HYBRID_FUSION_MANIFEST.json)

| รายการ | ผลที่วัดจริง |
| --- | --- |
| Base HEAD |60490a7a8f8f2db42f1bcaaba3d3965f33c78c41|
| Test worker ตั้งแต่ suite load ถึงผล |0.015 s; unittest runner ภายในรายงาน0.011 s|
| Parent interval launch/containment/wait |0.188 s เทียบ gate120 s|
| Observed peak working set |24,465,408 bytes|
| Windows Job committed-memory cap |512 MiB; working set กับ committed memory เป็นคนละ metric|
| Model/array runtime imports ใน test worker |[]: ไม่ import torch/transformers/sentence_transformers/numpy|
| Network |socket connect/connect_ex/create_connection ถูกปิดใน worker|
| Model/tokenizer/encoder/detector execution |0 ใน workflow นี้|
| Real sessions/scores evaluated |0|
| New data acquisition/extraction/student/kernel training |0|
| Source/config/design hashes ก่อน–หลัง verification |ตรงทั้งหมด|
| main |5fb5e07d750a73a0a663a174433bab931ae7568a ไม่เปลี่ยน|

Windows Job attach ก่อน BOOT มี independent parent timeout/memory checks; ไม่เพิ่ม gate
ตัวเลขไม่ใช่ model latency/VRAM benchmark หรือ packet audit ของทุก process บนเครื่อง
ชุด tests เล็กและไม่มี GPU/model work จึงไม่จำเป็นต้องรัน full experiment เพื่อ verify software นี้

## พฤติกรรมที่ยืนยันได้

| กลุ่ม tests | จำนวน | สิ่งที่ตรวจ |
| --- | ---: | --- |
|Alignment|6|config ตรง defaults, joint Q150/200/250/300, inclusive boundaries, future/late availability, missing/stale/invalid, warm-up, mismatch revisions/session/context, duplicates/noncausal/nonfinite/orientation rejection|
|Calibration/fusion|10|benign-only fit/calibration, outer-group/split disjointness, all-look maxima, infinity/ties, normalization before addition, OR/AND truth tables, missing abstention, distinct joint OR threshold, simultaneous AND, n19 finite-rank resolution, immutable thresholds/spec binding|
|Timeline/accounting|6|first alert/delay/right censoring, pre-attack exclusion/onset1, unknown earlier look, incomplete coverage, one FP event per stream, repeated outer/session rejection, component-only availability, benign onset/mixed-method counter rejection|
|รวม|**22**|ไม่มี scientific performance inference|

Unit tests จงใจสร้าง paired numeric detector scores บน **declared same-stream fixtures** ไม่สร้าง scientific sessions
test ที่แสดง OR ต้อง calibrate ใหม่เป็น counterexample ทาง software ไม่ใช่ measured traffic FPR
test n19 แสดงเพียง rank resolution ไม่รับรอง tail precision/useful power
test first alert Q200/onset180 ตรวจ arithmetic เท่านั้น ไม่ใช่ measured extraction delay

เริ่ม TDD ด้วย import test ที่ fail ก่อนมี module จากนั้น implementation รอบแรกมี14ผ่านและ1error
เพราะ test สร้าง invalid future-dependency record นอก assertRaises; constructor ปฏิเสธเร็วตาม design อยู่แล้ว
แก้ test ให้จับ rejection ตอน construction ไม่ลด causality guard แล้วเพิ่ม joint-calibration/accounting/config tests
final guarded run22ผ่าน; attempts เก่าอธิบายไว้แยก ไม่อ้างว่าทุกขั้นผ่านตั้งแต่แรก

ไม่ได้ rerun legacy detector suites เพราะไม่ได้เรียก/แก้ code เหล่านั้น
ตรวจ prior tracked files ไม่มี changes และตรวจทุก frozen manifest Phase A–K ก่อน local commit
reference pilot source/readme และรายงาน D/E/F ถูก hash ก่อน–หลัง verification เท่ากัน

## วิธีทำซ้ำ

จาก repository root ใน Conda `senior`:

```powershell
conda run --no-capture-output -n senior python -m unittest stream_prada_order.tests.test_hybrid_fusion -v
conda run --no-capture-output -n senior python stream_prada_order/hybrid_fusion_verify.py --output stream_prada_order/diagnostics/hybrid_fusion_recheck_new
```

คำสั่งแรกเป็น unit tests เท่านั้น คำสั่งที่สองใช้ new-only output, Windows Job512MiB/120s และ import/network guards
หาก source เดิมถูกแก้หรือไม่อยู่ branch ที่กำหนด verifier จะหยุด ไม่มี inference/start/download option
เก็บ old verification receipts ไว้ ไม่ overwrite เพื่อ reset failed run
สำหรับข้อมูลจริงให้เก็บ exports/fit scores/session identifiers/reference sidecars/calibration receipts ใน ignored storage
ไม่ใช้ public diagnostics ตัวอย่างนี้เป็นที่เก็บ private traffic และไม่ commit raw text/weights/embeddings

## สถานะ integration และงานที่ยังขาด

อ่าน [design](HYBRID_FUSION_DESIGN_TH.md) กับ [MMD integration contract](HYBRID_MMD_CONTRACT_TH.md)
MMD pilot ปัจจุบัน export random-window scores ที่ไม่มี session/query boundaries และ availability
จึงยัง **ไม่ได้ integrate actual MMD outputs**; ไม่ join กับ Phase D/E โดยเดาว่า window_id/session ตรงกัน
scores ต้องมาจาก common ordered queries/embeddings/view/model/reference provenance และ completed windows จริง
ต้องมี separate same-stream exporter/protocol/resource gate ก่อนรัน detector เพื่อสร้างข้อมูลดังกล่าว

ก่อน fair experiment ต้องแก้ length/format shortcut ตาม Phase E, มี connected outer-group splits จริง,
independent benign calibration เพียงพอ, shared checkpoint horizon/membership, frozen source/normalization/weights,
untouched final data, matched nominal operating points พร้อม paired FPR uncertainty/coverage และ common controls
ห้ามใช้จำนวน permutations แทน independent cohorts หรือเลือก best method/threshold จาก final outcomes

**GO: software contract และ isolated offline tests**
**NO-GO: scientific hybrid improvement/generalization หรือ real fusion experiment จากข้อมูลเก่าที่จับคู่ไม่ได้**
ไม่รัน Qwen/attacks/student training/acquisition ไม่แก้ baseline/MMD/pilot/prior evidence
ไม่มี push/main/merge/rebase/PR และหยุดหลัง local commit
