# Task 02 — Common Ordered Stream Manifest Producer

11 พฤศจิกายน 2026 (Asia/Bangkok)

**ผล: implement และ local validation ผ่าน; NO-GO สำหรับสร้าง genuine 256-query common stream จากหลักฐานจริงในขอบเขตที่ตรวจ**
ไม่มี real-data manifest ถูกผลิตในงานนี้ ไม่มีการสร้าง passing example ด้วยข้อมูลจริงหรือเติมข้อมูลที่ขาด ผล software tests ไม่ใช่ scientific FPR/TPR/delay หรือหลักฐาน Hybrid superiority

## 1. Repository และขอบเขต

- Working branch ก่อนและหลังงาน: `experiment/stream-prada-order`
- Base/current HEAD: `bfc1ce9d26babd564cb8d9cef5b531bb4f575ad0` (`Add initial draft of Hybrid Detection Experimental Protocol v1`)
- ก่อนแก้ไข `git status --porcelain=v1 --untracked-files=all` ว่าง; Task 01 ถูก commit ไว้แล้วโดยผู้ใช้ก่อน Task 02 ไม่ถือว่า SHA เก่าใน protocol เป็น current HEAD
- อ่าน [AGENTS.md](AGENTS.md), [protocol draft](../docs/hybrid/EXPERIMENT_PROTOCOL_V1_DRAFT.md), [integration adapter](hybrid_integration.py), [fusion consumer](hybrid_fusion.py), [contract](HYBRID_MMD_CONTRACT_TH.md) และ [producer requirements](HYBRID_MMD_PRODUCER_REQUIREMENTS_TH.md)
- ตรวจ `origin/refactor/clean-architecture` และ `origin/restructure/deepkernel` แบบ read-only ที่ HEAD เดียวกัน `e5d890703f9abd2a5a8988969579cb3a3ff0ed48`; ไม่ checkout/fetch/merge หรือเปลี่ยน refs
- อ่าน Deep Kernel branch AGENTS/domain/glossary/ADR และ source `mea_detection/embeddings/encoder.py`, `mea_detection/experiments/protocol_io.py` ผ่าน Git objects เท่านั้น ไม่ import active runtime ของอีก branch

ไฟล์เพิ่มทั้งหมดอยู่ `stream_prada_order/` ไม่มีการแก้ PRADA/CUSUM/Deep Kernel algorithms, existing adapters/validators/configs, historical results หรือ protocol ไม่มี acquisition, model execution/training, detector recomputation, scientific experiment, commit, push หรือ PR

## 2. สิ่งที่ implement

[common_stream_producer.py](common_stream_producer.py) เป็น Python standard-library API ขนาดเล็ก ไม่มี CLI ที่ค้นหา dataset อัตโนมัติ:

```python
produce_manifest(metadata, ordered_requests, certificate, embedding_index,
                 *, expected_representation, evidence, evidence_records, profile)

write_manifest(output_path, **inputs)
```

`produce_manifest()` ประกอบ header กับ ordered requests ที่ caller ส่งมา คืน detached dict ตาม **existing `hybrid-common-stream-v1` เท่านั้น** โดยเรียก `hybrid_integration.validate_manifest()`, `embedding_contract()`, `digest()` และ `hybrid_fusion.fingerprint()` เดิม ไม่คัดลอก schema validator ขึ้นใหม่ ไม่ default fields ที่ขาด ไม่ sort/renumber/deduplicate/pad/truncate requests และไม่แก้ inputs

`write_manifest()` validate ทั้งหมดและ serialize ก่อนเปิด output แบบ exclusive `xb`; parent directory ต้องมีอยู่แล้ว ไม่สร้าง directory และไม่ overwrite existing file ถ้า validation ไม่ผ่านจะไม่มี output หรือ directory ใหม่ และ existing output ไม่เปลี่ยน

Canonical JSON ใช้ sorted keys, compact separators, ASCII escaping และ no NaN ตาม fingerprint เดิม โดย **list order คงเดิม** เขียน UTF-8 bytes โดยไม่มี newline/envelope จึงได้ SHA256 ของไฟล์เท่ากับ `hybrid_fusion.fingerprint(manifest)` ตรวจพฤติกรรมนี้ด้วย test แล้ว

## 3. Input และ output schema

### Existing wire contracts — ไม่เปลี่ยน schema

| Input | ข้อกำหนด |
| --- | --- |
| `metadata` | existing common-stream fields ทั้งหมด **ยกเว้น queries**: schema_version, session_id, outer_group, split, label, chronology_kind, dataset_revision, victim_revision, grouping_certificate_sha256, representation; ต้องส่ง explicit ไม่มี default/inference |
| `ordered_requests` | exact list ของ query records ตามลำดับจริงที่ได้รับอนุญาต; แต่ละ record มี query_index, request_id, text_sha256, embedding_row, embedding_row_sha256, source_group_sha256 ตาม contract เดิม |
| `certificate` | actual `hybrid-groups-v1` เดิม: schema_version, provenance_sha256, assignments; ไม่สร้าง certificate ให้จาก cohort names |
| `embedding_index` | actual `hybrid-embedding-index-v1` เดิม: schema_version, embedding_artifact_sha256, representation_sha256, rows; แถวผูก embedding_row กับ exact text hash และ physical row hash |
| `expected_representation` | independently reviewed expected representation ที่ทั้งสอง detector ตกลงไว้: encoder_id/revision, tokenizer_revision, preprocessing_sha256, normalized, dimension, dtype, embedding_artifact_sha256; producer ไม่สร้าง expected view จาก incoming view ให้เอง |
| `profile` | explicit existing profile; สำหรับ proposed256 ใช้ `research_256_grid_proposal_v1` ซึ่งบังคับครบ256 requests; generic API ยังยอมรับ existing `illustrative_300_v1` เมื่อ caller ระบุชัด ไม่เปลี่ยน defaults ของ Hybrid เดิม |

Output มี metadata ทั้งหมดข้างต้นและ `queries=ordered_requests` ตาม existing contract โดยไม่มี evidence fields เพิ่มใน wire manifest Request IDs ต้อง unique แต่ repeated identical query text และ embedding row ที่อ้างซ้ำได้ต้องคงอยู่ด้วย request IDs ที่ต่างกัน ไม่เท่ากับลบ repeated exposures

Singleton metadata ไม่มี raw text ให้ producer hash ใหม่ Caller ต้องส่ง `text_sha256` ของ exact submitted encoder view และ `embedding_row_sha256` จาก physical byte verification จริง Producer ตรวจ binding กับ index ไม่สร้าง physical hashes จากเลข row หรือ normalized grouping text

### Admission evidence — Python inputs แยกจาก wire manifest

ไม่มีการเพิ่ม competing schema version; dataclasses ต่อไปนี้เป็น typed API inputs สำหรับ admission เท่านั้น ไม่เปลี่ยน validators หรือ schemas ของ consumers เดิม

| Input | Fields และการตรวจ |
| --- | --- |
| `SourceEvidence` | authorized ต้องเป็น True จริง; authorization_record_sha256, authorized_manifest_sha256, grouping_certificate_sha256, chronology_kind, chronology_basis, chronology_record_sha256, ordered_query_sha256, physical_embeddings |
| `PhysicalEmbeddingEvidence` | receipt_sha256, verifier_revision (SHA256 ของ pinned verifier source), embedding_artifact_sha256, embedding_index_sha256, representation_sha256, row_count, layout; ต้องตรง artifact/index/expected representation; row_count เป็น positive int ครอบคลุมทุก indexed row และ layout=`contiguous-little-endian` |
| `evidence_records` | dict จาก SHA256 → **actual nonempty bytes** ของ authorization record, chronology record, source-group provenance audit และ physical verification receipt; แต่ละ record ≤1 MiB; producer ตรวจ byte SHA256 ตรง reference ก่อนคืน/เขียน manifest ไม่มีการสร้าง record ที่หายไป |

Authorization ผูก fingerprint ของ **whole manifest**, chronology ผูก exact ordered queries และ grouping evidence ผูก certificate ที่ส่งมา การเปลี่ยน session/representation/requests ต้องมี authorization binding ที่ตรงกันใหม่; การเปลี่ยนลำดับแล้ว renumber ไม่สามารถ reuse ordered-query evidence เดิมผ่านได้

`chronology_kind=native` ต้องมี basis=`observed_request_order` กับ actual chronology audit record; `fixed_query_replay` ต้องมี basis=`declared_fixed_replay` กับ reviewed replay specification record ไม่ยอมรับ dataset row order เป็น native evidence ไม่เปลี่ยน kind อัตโนมัติ และไม่ผลิต availability timestamps หรือ detector scores

**Trust boundary:** producer ตรวจ consistency และ record byte identity ไม่ตรวจ digital signatures, human consent, semantic content ของ opaque audit records หรือ vector bytes เอง Caller/reviewer ต้องตรวจว่า records มีจริงและรับรอง bindings ที่ส่งมาจริง ห้ามสร้างคำรับรอง/record bytes เพื่อให้ validator ผ่าน การมี record hash ตรงไม่พิสูจน์ว่าข้อความใน record เป็นจริง หรือ source groups อิสระทางสถิติ Authentic physical byte verification ต้องเกิดภายนอกก่อนเรียก producer

สำหรับ JSON ที่ caller อ่านเองควรใช้ `hybrid_integration.strict_json()` เดิมก่อนสร้าง Python inputs เพื่อ reject duplicate JSON keys/nonfinite constants API นี้ไม่เปิด arbitrary input paths หรือโหลด raw traffic/embeddings และไม่ส่ง evidence records ออกใน manifest

## 4. Tests ที่ execute จริง

ใช้ Conda `senior`; synthetic numeric metadata/hashes/record bytes เท่านั้นตาม [test_common_stream_producer.py](tests/test_common_stream_producer.py) ไม่มี synthetic research sentences หรือ actual vector/query payloads ข้อมูลใน fixture ไม่อ้างว่าเป็น authentic consent/chronology/physical evidence

ลำดับ TDD ที่สังเกตจริง:

1. เพิ่ม tests ก่อน module แล้วรัน focused suite: fail ด้วย ImportError เพราะ common_stream_producer ยังไม่มี (1 loader error)
2. เพิ่ม implementation รอบแรก: ใหม่17 + regression39 = **56 tests ผ่าน**, failures/errors/skips=0; unittest runtime0.910s
3. เพิ่ม negative test สำหรับ missing/tampered/empty evidence bytes ก่อนเพิ่ม argument/validation: focused test fail ด้วย unexpected `evidence_records` argument (8 errors รวม subtests)
4. เพิ่ม bounded record-byte/hash checks แล้วรันใหม่: ใหม่18 + regression39 = **57 tests ผ่าน**, failures/errors/skips=0; unittest runtime **1.007s** ไม่ใช่ model/detector latency benchmark

คำสั่ง final ที่ execute:

```powershell
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_common_stream_producer stream_prada_order.tests.test_hybrid_integration stream_prada_order.tests.test_hybrid_fusion -v
```

| Required behavior | Test coverage |
| --- | --- |
| 1. Valid ordered manifest | unchanged existing v1 contract ผ่าน validator เดิม, detached output และ inputs ไม่เปลี่ยน |
| 2–3. Missing/duplicate request identity | reject missing/empty ID และ duplicate request ID |
| 4. Repeated identical text, distinct requests | คงครบ256 positions รวม repeated row/text และ IDs สองรายการ |
| 5. Wrong embedding-row hash | reject query/index row binding mismatch |
| 6. Missing provenance | reject missing revision/evidence, unauthorized source, missing/tampered receipt bytes |
| 7. Out-of-order indices | reject swap/reverse ไม่ sort/renumber ให้; renumbered reordered list ต้องตรง external audit |
| 8. Different encoder revisions | reject mismatch แม้ incoming index ถูก relabel ให้ตรง revision ใหม่; รวม tokenizer/preprocessing/dtype/dimension/normalization |
| 9. Native vs replay | รับแต่ละ kind เฉพาะ matching explicit basis/record; reject dataset-order inference และ kind mismatch |
| 10. Deterministic fingerprint | dict insertion order ไม่เปลี่ยน fingerprint/output; file digest ตรง canonical manifest fingerprint |
| 11. Invalid length/incomplete manifest | reject lengths0/100/255/257, missing fields และ absent explicit profile |
| 12. No output on invalid input | invalid identity/authorization/physical/order/record bytes ไม่สร้าง file/parent; existing fileไม่เปลี่ยน |
| Additional guards | split/group/certificate mismatch, authorization reuse, physical artifact/index/representation/count/layout mismatch, no overwrite |

## 5. Read-only real-data feasibility

**NO-GO** สำหรับ authentic common stream256 ใน inspected evidence ทั้ง native และ authenticated fixed-query replay ไม่ได้อ้างว่า teammate ไม่มี artifacts ที่อื่น ถ้ามีต้องส่ง explicit authorized paths/records เพิ่ม ไม่มี machine-wide search และไม่อ่าน private traffic หรือ raw queries

ขอบเขตการตรวจปัจจุบัน: bounded JSON metadata สามไฟล์ด้านล่าง (≤4 MiB ต่อไฟล์), SHA256 ของ compressed historical certificate, CSV headers ของ CUSUM/MMD และ producer sources ไม่มี score-row analysis, trace replay, physical vector verification หรือ fresh data acquisition

| Metadata ที่ตรวจจริง | สิ่งที่พบ | Fields/artifacts ที่ยังขาด |
| --- | --- | --- |
| `results/phase_c_pilot_20261107_v1/metadata.json` | config horizon256, BGE revision5c38ec7…, source/cohort/model stamps | actual request/session IDs, exact256 request metadata rows, common physical row mapping, reviewed common victim/dataset identity และ chronology audit |
| `results/phase_c_pilot_20261107_v1/embedding_calibration_validation.json` | aggregate metadata ของ4224 queries, query_order/raw_text_order/embedding hashes | per-request exact-text hashes, global embedding_row mapping, per-row physical hashes/index, canonical layout/count receipt; aggregate hashesไม่สามารถเติม per-row evidenceให้ได้ |
| `diagnostics/phase_b_plan/proposed_article_model_leeching_12_3_8.json.gz` | compressed artifact278,732 bytes; SHA256ตรง config: `25970769c8e5128aa974ae00eae723ec56ffe984169a7499f38ca0ee49649b53`; งานนี้ hash bytes เท่านั้นไม่เปิด query payload | historical article allocationไม่ใช่ reviewed `hybrid-groups-v1` actor/user/source/run certificate; ไม่มี corresponding source-group audit record และ exact request membershipร่วมสองproducers |
| `results/phase_d_pilot_20261107_v2/per_stream.csv.gz` | headerมี cohort/key/max_score/first_alert/prefix/delay ฯลฯ | ไม่มี saved per-query CUSUM checkpoint curve ใน output schema นี้; เป็น downstream score-export gap ไม่ใช่ข้อกำหนดให้ manifest producer คำนวณ detector ใหม่ |
| Repository-root `experiment_result/main/seed=42/MMD/model_leeching_bge_bs1500/metadata.json` และ `batch_scores.csv` | batch_size1500, repeats20; header split/batch_id/label/size/attacker_ratio/count/score/p_value/suspicious | ไม่มี session/request order, exact encoder/tokenizer/preprocessing revisions, physical per-row index, common source groups/window membership/availability; ไม่ใช่ window100 common-stream output หรือ Deep Kernel checkpoint evidence |
| Repository-root `pilot/outputs` | ไม่มีใน current checkout | ไม่มี configured actual Deep Kernel handoff ให้ตรวจ; ไม่ค้น disk/remote เพิ่มเพื่อแทนข้อมูลที่หาย |
| Deep Kernel branch `mea_detection/embeddings/encoder.py` / `experiments/protocol_io.py` | cache key/content identity และ reproducible locked random-window draws | ไม่มี producer ที่ผูก exported common256 request sequenceกับ per-row physical receipt/chronology ใน source ที่ตรวจ; ไม่ถ่ายโอน ignored artifacts จากอีก branch |

Metadata fingerprints ของสาม JSON files ที่อ่านใน Task 02 เพื่อให้ review scope ได้ตรงกัน (plain file SHA256 ไม่ใช่ canonical manifest fingerprints):

| File | SHA256 |
| --- | --- |
| Phase C metadata | `e5007bebfaf44fc9ff07e8eab191df5df1d7a482c6f0cc3cd6372d57eaee46b4` |
| Phase C embedding metadata | `723b51d5abeefb33d8dabf0db508a98dca67bf7e368c0dfeafda6c0c194fcb42` |
| Existing MMD metadata | `b2dcfe691cd5d97858f0d9dafe6f6323f183c27de2b375ba528518f266171628` |

**Exact missing admission artifacts ก่อน real production:**

1. Authorized source metadata header และครบ256 ordered request records ที่ preserve actual IDs/exposures พร้อม per-query exact-text/physical-row/source-group bindings
2. Authorization record bytes/hash และ externally reviewed whole-manifest fingerprint; task authorizationให้อ่าน metadataไม่ใช่ consent recordของ actual traffic
3. Native observed-order/session audit **หรือ** explicit fixed-query replay specification พร้อม record bytes/hash, exact ordered-query fingerprint และ truthful chronology_kind
4. Actual `hybrid-groups-v1` certificate และ source-group provenance audit record ที่ผูก outer_group/split อย่างถูกต้อง; ไม่สร้างจากบทความ/cohort labelsอัตโนมัติ
5. Independently agreed complete expected representation โดยเฉพาะ exact tokenizer/preprocessing policy และ physical artifact identityที่ตรงทั้งสอง detector
6. Actual `hybrid-embedding-index-v1` พร้อม per-row text/vector hashes และ actual physical byte-verification receipt bytes/hash, pinned verifier revision, canonical matrix identity/layout/row count

ไม่มีการกรอก auth/native IDs, physical hashes, certificates หรือ timestamps เพื่อทำให้ตัวอย่างจริงผ่าน validation Existing fieldsที่ขาดยังคง missing และไม่ผลิต real manifest

## 6. Scientific limitations และงานถัดไป

Manifest consistency ไม่พิสูจน์ native chronology, benign intent, independence, label correctness หรือ equal physical vectors หาก external auditไม่จริง ต่อให้ softwareรับข้อมูลก็ยังใช้อ้าง scientific readinessไม่ได้ ต้อง independently review semantic bindings ของ opaque evidence records ก่อนรับ real handoff

งานนี้ไม่สร้าง CUSUM curves, MMD windows, checkpoint/reference draw provenance, ECDF fit หรือ calibration receipts และไม่แก้ endpoint/censor gap ของ Hybrid evaluator ที่บันทึกใน Task 01 ต่อให้ manifestพร้อมแล้วก็ยังต้องผ่าน downstream producer acceptance และ experimental/resource gates แยก

Protocol ยังคง DRAFT: recorded horizon256, joint checkpoints150/200/250, endpoint **by Q250**, Q251–Q256ไม่ jointly evaluated ไม่เปลี่ยน Phase F definitions/calibration หรือ Hybrid300 profile เพื่อให้ historical artifactsดูเข้ากัน และ length/format confoundingยังไม่ถูกแก้ด้วย manifest producer

ลำดับงานภายหลัง: ทีมส่ง authentic authorized metadata/evidence ที่ขาด → independent identity/grouping/chronology/physical review → เรียก manifest producerภายใต้ reviewed profile → separately authorized score-export/evaluation tasks ไม่เริ่ม scientific executionอัตโนมัติจากผล tests นี้

## 7. Git diff และ preservation

เพิ่มสามไฟล์เท่านั้น: implementation, isolated tests และรายงานนี้ ทั้งหมดอยู่ `stream_prada_order/` เป็น untracked additions พร้อมให้ผู้ใช้ review ยังไม่ stage/commit; tracked diffเดิมว่าง ไม่มีการแก้ historical outputs/protocol/validators หรือ refs ของ main/Deep Kernel branches

ตรวจ `git diff --check` และ whitespace checks ของไฟล์ใหม่ก่อนส่ง พร้อมตรวจ status ให้ไม่มีไฟล์เปลี่ยนนอกขอบเขต ผู้ใช้เป็นผู้ push และ sync fork เอง
