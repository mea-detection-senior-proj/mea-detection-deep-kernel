# Integration contract — MMD score export สำหรับ Offline Hybrid

8 พฤศจิกายน 2026 | ไม่แก้หรือเรียก `pilot/deep_kernel_pilot.py` / `MMD_detection`

Producer ของทีม MMD ส่ง scores ให้ consumer `stream_prada_order.hybrid_fusion.align()`
ผ่าน frozen dataclasses `Context`, `Stream`, `DetectorRevision`, `Score`, `Spec`
`dataclasses.asdict(Score)` serialize เป็น JSON-compatible nested record ได้ ไม่มี raw query/weights ใน score interface
หากใช้ JSON ให้ reconstruct Context/Stream/DetectorRevision/Score ผ่าน constructors ตาม fields ที่ระบุ
ไม่เอา dict/Point ที่สร้างเองข้าม align หรือแก้ Aligned ที่ผ่านแล้ว

## Session/representation manifest — ต้องมีหลักฐานรองรับ

| Field | Producer ต้องรับรอง |
| --- | --- |
|session_id|session/run identity เดียวกับ sequential exporter; boundary จริง ไม่ concat unrelated streams|
|ordered_query_sha256|SHA256 ของ canonical ordered query manifest ที่รวม request IDs + exact text hashes + positions; ใช้ serialization เดียวกันทั้งสองฝั่ง|
|outer_group|connected user/source/document/run lineage ที่ audit แล้ว; reorderings ใช้ group เดิม|
|split/label|จาก authorized frozen data manifest ไม่ infer benign/attack จาก score/length/format|
|dataset_revision|immutable source/acquisition/content-manifest revision ของ **common track** ไม่ใช่ชื่อ dataset อย่างเดียว|
|embedding_revision|hash/revision ของ encoder + tokenizer + normalization/dtype/dimension contract|
|query_view_revision|hash ของ query text view/preprocessing/truncation/max_length/prefix/system/context policy|
|victim_revision|exact victim/model condition เดียวกัน หรือ explicit controlled task identity ที่ review แล้ว|

Context equality เป็น guard ต่อ declared metadata เท่านั้น ไม่พิสูจน์ว่าใช้ embeddings เดียวกันจริง
ต้องส่ง sidecar ordered embedding-row/content digest และ source/split audit ให้ reviewer ตรวจด้วย
ถ้าใช้ BGE ตาม Phase F ให้ pin revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, normalized/max_length512/no query prefix
หาก existing MMD cache ไม่ตรง ต้องเสนอ same-stream re-export protocol ใหม่ ไม่ rename metadata ให้เหมือนกัน

## Detector/configuration/calibration stamp

- detector_revision: hash/commit ของ actual score implementation เช่น MMD estimator/kernel formula รวม dependencies
- model_revision: frozen Deep Kernel checkpoint digest; RBF-only ต้องประกาศ not-applicable พร้อม immutable kernel manifest แทนปล่อยว่าง
- configuration_revision: hash ของ bandwidths, mixing constants, estimator (biased/unbiased), window/grid,
  reference count/repeats/aggregation, RNG assignment, preprocessing/orientation, precision และ backend/version ที่มีผลต่อ score
- calibration_provenance: immutable source-fit/reference/calibration manifest ที่ประกาศก่อน eval;
  raw unthresholded exporter ต้องใช้ reference ถึง source provenance จริง ไม่ปลอมว่าเป็น hybrid-calibrated score
- exact train/validation/kernel selection/reference memberships ต้องไม่ปะปน final/calibration units ตาม protocol
  common victim/model ไม่ได้ทำให้ source groups ของข้อมูลอิสระโดยอัตโนมัติ

sequential และ MMD stamps ย่อมต่างกัน แต่แต่ละตัวต้องตรง expected stamp ของ Spec
การเปลี่ยน checkpoint/reference seed/normalization หรือตัว score หลัง calibration ต้องทำ artifact/calibration ใหม่

## Per-window Score (`hybrid-score-v1`)

window start/end เป็น **1-based inclusive contiguous positions** ของ stream นั้น
ตัวอย่าง grid100/stride50: [1,100], [51,150], [101,200], [151,250], [201,300]
available_at = query position ที่คะแนนพร้อมใช้จริง (หรือ declared offline idealized schedule ซึ่งต้องติดข้อจำกัดใน sidecar)
computed_through=end: ทั้ง current window และการเลือก reference/normalization ห้ามใช้ future evaluation queries/labels
reference bank frozen จาก fit ที่มี provenance; ระบุ reference IDs/hashes ต่อ window/repeat ใน private sidecar
หาก asynchronous score พร้อมหลัง checkpoint จะไม่ได้ใช้ย้อนหลัง; contract รุ่นนี้ไม่รองรับ late-score carry-forward

value เป็น finite Python float/int ที่ unthresholded และ higher_is_more_anomalous
unbiased MMD ที่ติดลบยัง valid ห้าม clip ตาม test outcome; invalid ให้ value=null, valid=false
ห้าม substitute NaN/0 หรือใช้ p-values/lower-tail statistics โดยไม่ประกาศ sign/transform ใหม่
Score.start/end สำหรับ sequential ให้ start=end=query_index และ Original PRADA W ต้อง export **-W**
config revision ต้องรวม sign mapping; CUSUM export positive selected statistic ที่ประกาศทิศไว้ก่อน

Consumer reject: stream/context/stamp mismatch, duplicate endpoint, wrong window grid/width,
future dependency, malformed validity/nonfinite scores; missing/stale/invalid/late ให้ availability reason และ abstention ตาม design
ทุก production field ต้องอ้าง actual reviewed manifest ไม่ใช้ numeric unit-test fixture เป็น provenance

## ข้อจำกัดของ pilot ปัจจุบัน

`repeated_score()` เฉลี่ย MMD เหนือ reference draws; `mmd()` เป็น diagonal-excluded estimator
Deep Kernel คือ multi-RBF × (0.1+0.9 learned RBF), checkpoint เลือกจาก validation objective ก่อน calibration
ต้อง export score **definition เดิมอย่าง faithful** พร้อม reference indices/repeats ไม่เอา thresholds ของ random windows มาใช้ online
`scores.csv` ปัจจุบัน window_id เป็น sampled-window index ไม่มี native session/boundaries/availability/query membership ต่อ row
`metadata.json` มี split hashes/config แต่ไม่พอสร้าง same-stream joins ย้อนหลัง
เก็บ old outputs เดิมไว้ทั้งหมด; การเพิ่ม exporter/รัน same-stream MMD เป็นงานแยกที่ต้องมี protocol/resource gate

## Acceptance checklist ก่อน real comparison

1. ทีม sequential/MMD ยืนยัน common ordered-stream/embedding-view hashes และ exact code/model/config stamps
2. มี source/user/run grouping + chronology + split integrity + shared query/reference leakage audit จริง
3. Freeze common horizon/checkpoints และข้อมูลเห็นได้ถึง t; delayed/invalid coverage มีกฎเดียวกัน
4. Freeze reference selection/kernel และ benign fit ECDF ก่อน benign-only joint stream-max calibration
5. Validate ครบทุก checkpoint, signed score orientation, strict threshold/ties และ no finite threshold cases
6. แยก validation/final outcomes; ห้ามเลือก weight/method จาก final และรายงาน paired FPR uncertainty/coverage

prototype นี้เป็น consumer ที่ isolated เท่านั้น ไม่อ้างว่าได้ integrate หรือทดสอบ actual MMD outputs แล้ว
