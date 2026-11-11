# Task 06 — Paired Same-Stream Admission and Alignment Gate

11 พฤศจิกายน 2026 (Asia/Bangkok)

**ผล: software admission/alignment gate และ synthetic compatibility tests ผ่าน; NO-GO สำหรับ authentic paired artifacts ใน inspected locations**
ไม่มีการสร้าง passing research example, traffic, scores, checkpoint hashes หรือ receipts เพื่อแก้ missing evidence ไม่รัน scoring/training/calibration/scientific evaluation และไม่อ้าง Hybrid performance

## 1. Repository และ preservation

- Mandatory branch: `experiment/stream-prada-order`
- Expected และ actual base HEAD ตรงกัน: `26e840c53790b8fd6273778516fd36781c65c076`
- ก่อนแก้ไข worktree/index สะอาด ไม่มี difference จาก expected HEAD ให้ reconcile
- อ่าน [AGENTS.md](AGENTS.md), [Task 01 protocol](../docs/hybrid/EXPERIMENT_PROTOCOL_V1_DRAFT.md), [Task 02](TASK_02_COMMON_STREAM_PRODUCER_REPORT_TH.md), [Task 03](TASK_03_CUSUM_EXPORT_REPORT_TH.md), [Task 04](TASK_04_DEEP_KERNEL_EXPORT_REPORT_TH.md), [Task 05](TASK_05_ENDPOINT_ADAPTER_REPORT_TH.md), relevant implementations และ tests
- คง [common producer](common_stream_producer.py), [CUSUM exporter](cusum_curve_exporter.py), [Deep Kernel exporter](deep_kernel_mmd_exporter.py), [integration validators](hybrid_integration.py), [fusion calculations](hybrid_fusion.py), [endpoint adapter](hybrid_endpoint_adapter.py), configs/protocols และ historical outputs เดิม ไม่มี branch merge/rebase/cherry-pick/PR/push

## 2. API: separate submissions และ independently agreed expectations

[paired_stream_admission.py](paired_stream_admission.py) เพิ่ม isolated entry point:

```python
admit_and_align(
    cusum, deep_kernel, *, profile, expected_representation,
    expected_cusum_revision, expected_cusum_definition,
    expected_mmd_revision, expected_mmd_definition)
```

ต้องระบุ `profile='research_256_grid_proposal_v1'` ไม่มี default/auto-detection และไม่ยอมรับ profile300

Producer inputs เป็น keyword-only frozen dataclasses สำหรับ **ส่งเข้า exporter** ไม่ใช่ unchecked exported payloads:

| Input | Fields |
| --- | --- |
| CUSUMInputs | manifest, certificate, embedding_index, source_evidence, evidence_records, raw_curve, curve_evidence, availability_evidence |
| DeepKernelInputs | manifest, certificate, embedding_index, source_evidence, evidence_records, raw_scores, reference, score_evidence, checkpoint_evidence, reference_evidence, availability_evidence |

Actual authorization/physical/chronology/fit/model/reference/availability requirements ยังคงตาม exporters เดิม Missing artifacts สามารถส่ง None ใน field ที่ขาดเพื่อรับ rejection ไม่มีการสร้างข้อมูลทดแทน การไม่ส่ง required API arguments เลยเป็น caller error ไม่ใช่ช่องทางให้ gate infer trusted values

Independently agreed representation, detector revisions และ definitions ต้องส่งแยกจาก producer submissions และ review/pin ก่อนนำ score outcomes มาเลือกค่า Gate ไม่อ่าน submitted evidence revision แล้วนำมาตั้งเป็น trusted expected revision ไม่ merge unchecked keyword dictionaries เพื่อ override expectations และไม่รับ producer payload dict เป็น bypass

การแยก API arguments เป็น software boundary ไม่ใช่หลักฐานว่าคนส่งได้ตกลง expectations อย่างอิสระจริง ต้องมี team review/register ภายนอกเช่นเดียวกับ semantic review ของ provenance records

## 3. Admission flow และ immutable result

Flow: explicit profile/input types → expected identity checks → identical shared inputs → CUSUM exporter → Deep Kernel exporter → existing `align_exports()` → immutable retained scores/fingerprints/coverage

ตรวจ common manifest, embedding index และ source-group certificate ของทั้งสองฝั่งต้องเท่ากันก่อน export แต่ equality อย่างเดียวไม่พอ Exporters เดิมยังตรวจ certificate/hash/group/split/request-order/representation/physical-evidence binding ของแต่ละฝั่ง ถ้าทั้งสองส่ง certificate ที่ผิดเหมือนกันก็ยังถูก reject

เรียก real `export_cusum_curve()` และ `export_deep_kernel_mmd()` โดยส่ง independently expected parameters ไปยังฝั่งที่ถูกต้อง จากนั้นเรียก **`hybrid_integration.align_exports()` เดิม** ไม่สร้าง Aligned/Point เองเพื่อข้าม validators และไม่มี independent method revision ถูกยุบเป็น revision เดียว

ใช้ existing `export_scores()` เพิ่มเติมเพื่อเก็บ immutable full Score tuples หลัง alignment เพราะ `align_exports()` คืนเฉพาะ checkpoint points ไม่คืน full paths ขั้นนี้เป็น repeated contract validation/representation conversion ไม่ใช่ detector recomputation

| Reporting type / field | ความหมาย |
| --- | --- |
| AdmissionResult.contract_admitted | ทั้งสอง exporter และ same-stream alignment/identity checks ผ่าน ไม่ได้แปลว่า joint coverage ครบหรือ scientifically ready |
| AdmissionResult.pair | PairedAlignment เมื่อผ่านทั้งหมดเท่านั้น; rejection เป็น None ไม่มี partial payload/alignment ให้ใช้ต่อ |
| AdmissionResult.diagnostic | None เมื่อผ่าน; ถ้าปฏิเสธเป็น AdmissionDiagnostic(stage,code) ไม่มี raw evidence bytes/exception text |
| PairedAlignment.profile_id | explicit profile256 |
| identities | immutable InputFingerprints ตามหัวข้อ4 |
| cusum_revision / mmd_revision | original independently expected producer revisions แยกกัน |
| aligned | existing immutable Aligned; points ที่ Q150/Q200/Q250 พร้อม raw available values/reasons ตาม aligner เดิม |
| cusum_scores / mmd_scores | tuples ของ existing immutable Score records คง raw signed values, valid, computed_through และ actual available_at รวม late scores ที่ point ใช้ไม่ได้ |
| joint_availability | tuple ของ JointAvailability(query_index,cusum_available,mmd_available,joint_available) สาม looks |
| joint_complete | True เฉพาะทั้งสอง component valid/on-time ทุก look |

Aligned Spec ใช้ adapted revisions ของ existing integration adapter ตามเดิม ส่วน original expected producer revisions ยังเก็บแยกใน pair ไม่ตีความความต่างจาก adapter fingerprints ว่าเป็น source mismatch

**Contract admission กับ coverage คนละเรื่อง:** invalid/null หรือ late exact-checkpoint row อาจผ่าน existing export contract จึง contract_admitted=True แต่ point มี reason=invalid/not_available, value=None และ joint_complete=False ไม่ fallback ไป prior score และไม่เติม0

Complete required positions ที่ขาด, missing authentic curve/window bytes หรือ rejected provenance ทำให้ไม่มี successful pair แม้ exporter อีกฝั่งเคยผ่านแล้ว Internal intermediate payloads ไม่ถูกคืนใน rejection

ทั้งหมดเป็น separate immutable Python orchestration records ไม่มี schema_version/kind ใหม่สำหรับ scores ไม่เปลี่ยน existing `hybrid-common-stream-v1`, `hybrid-reference-v1`, `hybrid-producer-scores-v1` หรือ Result/wire schemas

## 4. Exact input identity fingerprints

InputFingerprints มี12 fields:

- cusum_input_sha256, mmd_input_sha256: identities ของ submissions ทั้งชุด รวม source metadata, evidence claims และ actual supplied record bytes
- expectations_sha256: independently supplied representation/revisions/definitions/profile ทั้งชุด
- common_manifest_sha256, ordered_query_sha256, embedding_index_sha256, grouping_certificate_sha256, reference_manifest_sha256: existing canonical fingerprints
- cusum_curve_sha256, mmd_score_sha256: SHA256 ของ exact raw file bytes ที่ส่งจริง ไม่ใช่เพียงค่าที่ evidence อ้าง
- cusum_payload_sha256, mmd_payload_sha256: existing canonical fingerprints ของ payloads ที่ผ่าน exporter

Submission/expectation identity ใช้ deterministic in-memory metadata projection ก่อน `hybrid_fusion.fingerprint()`:

1. bytes → `{raw_bytes_sha256: actual SHA256, byte_count: length}` ไม่ส่ง byte contents ออก
2. Dataclass → `{dataclass: class name, fields: projected fields}`
3. Dict ใช้ string keys และ canonical sorted-key serialization เดิม; tuple/list เป็น JSON arrays ที่คงลำดับ
4. Scalar/None คงเดิม; ไม่ hash Python repr/object addresses และไม่ sort request/query/draw lists

ดังนั้น metadata identity เป็น canonical-content identity ไม่ใช่ file-whitespace identity ของ manifest JSON ที่ API ไม่ได้รับ ส่วน raw curve/score/evidence bodies ผูก exact bytes จริง รวม supplied extra record entries ที่ไม่ได้ใช้ในการ score admission ด้วย การมี fingerprint ของ extra entry ไม่ได้แปลว่า exporter รับรอง entry นั้นเป็น provenance ของ scores

Result ไม่มี private receipt body/raw score-file bytes หรือ reference-bank payload blobs Caller ต้องเก็บ authentic originals และ reviewed sidecars ใน authorized private storage คู่กับ fingerprints/library records ไม่ใช้ digest แทน semantic/physical/source audit

## 5. Diagnostic และ programming-error boundary

| Stage | Public diagnostic behavior |
| --- | --- |
| inputs | explicit_profile_required / producer_inputs_required |
| expectations | independent_revisions_required หรือ contract_rejected จาก existing expected-representation/definition validation |
| shared_identity | common_manifest_mismatch / embedding_index_mismatch / group_certificate_mismatch |
| cusum_export | cusum_curve_unavailable หรือ contract_rejected |
| mmd_export | mmd_windows_unavailable หรือ contract_rejected |
| alignment | contract_rejected ถ้า existing align/retained-score validation ปฏิเสธ |
| fingerprints | fixed identity/type rejection codes สำหรับ metadata ที่ fingerprint ไม่ได้ตาม admitted input types |

Diagnostic ไม่ใส่ original exception message/args, raw bytes, request IDs หรือ paths จาก supplied evidence มีเพียง stage/code ที่กำหนดใน software ไม่ log/write diagnostic ให้อัตโนมัติ

ไม่ catch Exception ทั้งหมด และ **ไม่ถือทุก ValueError ว่าเป็น data rejection** โดยอัตโนมัติ แยก explicit known validation raise sites (`hybrid_fusion.require`, `hybrid_integration.strict_json`) และ CurveUnavailable/MMDWindowsUnavailable จาก actual exporter raise sites ที่ pin ไว้เมื่อ import เพื่อไม่ต้องคัดลอก error catalogs/validators

Unexpected RuntimeError/KeyError/TypeError และ ValueError จาก origin อื่น re-raise เดิม ไม่มี fake successful pair หรือ sanitized data-rejection result มาซ่อน programming bug หาก dependencies เปลี่ยน exception paths ต้อง review compatibility แยก ไม่เพิ่ม broad catch เพื่อให้ผ่าน

## 6. Tests ที่ execute จริง

[test_paired_stream_admission.py](tests/test_paired_stream_admission.py) ใช้ synthetic numeric metadata fixtures จาก Task03/04 เท่านั้น ไม่มี research texts, vectors, weights หรือ authentic research receipts ที่สร้างขึ้นใหม่

TDD: เพิ่ม tests ก่อน implementation แล้ว focused run fail ด้วย expected ImportError (1 loader error) จากนั้นรอบแรก **15 tests ผ่าน** ใน1.783s เพิ่ม malformed source JSON diagnostic test แล้ว required combined run ผ่าน **139 tests = ใหม่16 + existing123**, failures/errors/skips=0; unittest runtime **11.004s** ไม่ใช่ model/detector latency benchmark

คำสั่งที่ execute:

```powershell
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_paired_stream_admission -v
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_paired_stream_admission stream_prada_order.tests.test_hybrid_endpoint_adapter stream_prada_order.tests.test_deep_kernel_mmd_exporter stream_prada_order.tests.test_cusum_curve_exporter stream_prada_order.tests.test_common_stream_producer stream_prada_order.tests.test_hybrid_integration stream_prada_order.tests.test_hybrid_fusion -q
```

| Coverage | Observed verification |
| --- | --- |
| Valid pair | Both real exporters และ align_exports ถูกเรียก; direct evaluation/calibration ถูก patch ให้ fail หาก gate เรียก และไม่มีการเรียกเกิดขึ้น |
| Exact alignment | Q150/Q200/Q250, windows[51,150]/[101,200]/[151,250], negative MMD values และ independent revisions คงเดิม |
| Shared identity | Different manifests/query order/indices/certificates ปฏิเสธก่อน export; equally wrong shared certificate ยังไม่ผ่าน actual validator |
| Independent expectations | Wrong expected representation, detector/model/config/fit/selection revision หรือ definition ไม่ถูกแทนด้วย producer claims |
| Missing artifacts | Missing CUSUM curve ไม่เรียก MMD; required MMD window หายหลัง CUSUM ผ่านก็ไม่เรียก alignment/คืนpartial pair |
| Missing/tampered provenance | Diagnostic stage ระบุ responsible exporter; ไม่มี successful pair |
| Invalid/late | Export contractผ่านได้ แต่ joint coverageไม่ครบ; retained scoreคงvalue/available_atจริง pointไม่backfill |
| Error privacy / programming bugs | Expected rejects/invalid JSON ไม่มี private bytesในdiagnostic; unexpected error typesรวมunknown ValueError propagate |
| Identity / immutability | Canonical deterministic hashes, exact raw-byte hashes, inputไม่เปลี่ยน, frozen nested records/tuple containers |
| Regressions | Endpoint20 + Deep Kernel24 + CUSUM22 + common18 + integration17 + fusion22 =123เดิมผ่านครบ |

## 7. Authentic-artifact readiness: NO-GO ใน inspected scope

ตรวจเฉพาะ bounded existing metadata locations จาก previous reports ไม่มี machine-wide/private data search หรือ new acquisition ไม่มี real pair ถูกนำมา admit

| Explicit location | พบจริงใน Task06 |
| --- | --- |
| Repository-root artifacts/migrated_deep_pure_comparison | ไม่มี directory |
| Repository-root artifacts/migrated_model_leeching_deep_pure_v1 | ไม่มี directory |
| Repository-root artifacts/model_leeching_deep_pure_v1 | ไม่มี directory |
| Repository-root artifacts/model_leeching_protocol_v1 | ไม่มี directory |
| Repository-root pilot/outputs | ไม่มี directory |
| results/phase_d_pilot_20261107_v2/distance_fit.json ภายใต้ stream_prada_order | มี mu/sigma255 positions, fit metadata keys เดิม; SHA256=`805c79422b7cb838462cb523f85762f990363d361c29819d195402e693cf97b6` |
| results/phase_d_pilot_20261107_v2/per_stream.csv.gz | อ่านเฉพาะ header พบ max_score/first_alert/summary fields ไม่ใช่ saved per-query CUSUM curve |
| Repository-root experiment_result/main/seed=42/MMD/model_leeching_bge_bs1500/metadata.json และ batch_scores.csv | Metadata/header เท่านั้น: batch1500, repeats20; ไม่มี common100-window/session/request/availability contract |

JSON metadata cap4 MiBต่อไฟล์ และ selected header cap8192 characters; ไม่อ่าน score rows เพื่อประเมิน performance ไม่โหลด vectors/checkpoints Existing MMD metadata SHA256=`b2dcfe691cd5d97858f0d9dafe6f6323f183c27de2b375ba528518f266171628`

### Missing artifacts และ responsible producer roles

| Role | Exact handoff ที่ยังต้องส่ง/ตรวจรับ |
| --- | --- |
| Shared data/provenance producer | Actual authorized common256 manifest, unique request IDs/actual order/exact-text hashes, shared physical embedding index/row evidence, source-group certificate และ authorization/chronology/physical/grouping record bytes |
| Sequential producer | Authentic saved CUSUM rowsครบQ102..Q256, exact raw bytes/SHA256, source/model/config/benign-fit/upstream bindings และ explicit actual availability evidence ไม่ใช่maxima/first-alert summaries |
| Deep Kernel model producer | Actual frozen active checkpoint identity/SHA256/verification record, architecture/kernel parameters/source/lock identity และ training/model-selection/scoring-configuration records |
| Deep Kernel window/reference producer | Frozen benign fit reference manifest + physical/grouping/source evidence, actual draw indices/repeats และ raw signed MMD windows[51,150]/[101,200]/[151,250] พร้อม file/draw/provenance/availability bytes/hashes |
| Joint reviewer / experiment coordinator | Independently agreed expected representation/revisions/definitions register ที่ผูก actual artifacts ก่อน admission ไม่ derive หรือเลือกจาก submitted outcomes |

Existing fit parameter fileอย่างเดียวไม่ทำให้ actual curve/source grouping/independenceพร้อม และ old batch scoresไม่สร้าง native chronology หรือ common-stream membership ห้าม recompute/generate missing dataภายใต้งานนี้ หากมี artifactsที่อื่นต้องให้ explicit authorized paths/bytes/hash สำหรับ review แยก ไม่อ้างว่าไม่มีอยู่ทุกที่

### Unresolved protocol decisions — แยกจาก missing artifacts

- Primary CUSUM direction/k หรือ prespecified alternatives/multiplicity plan; gateไม่เลือก best variant
- Actual active checkpoint/training fold/reference bank/RNG/precision choices ที่จะ freeze รวม source independence ของ train/selection/reference/ECDF-fit/calibration/test
- Native traffic estimand versus explicitly labeled fixed-query replay, sessionization และ native256 feasibility; ไม่ downgrade provenance เพื่อเติม quotas
- Actual independent cohort allocations/quotas, length/format common support และ matched hard-negative coverage
- Coverage eligibility/paired comparison rules, target-FPR calibration sample sufficiency, effect margins/power/uncertainty/multiplicity และ future execution/resource authorization

Software profileยังคง256/100/50/102 กับสาม looks; ไม่เปลี่ยน protocol draft หรือ Phase F definitions เพื่อให้ old artifactsดูเข้ากัน สิ่งที่ต้องตกลงไม่ถูกแก้ด้วยการสร้าง receipt หรือการผ่าน tests

## 8. Scientific limitations และ changed files

Synthetic compatibility ยืนยัน software plumbing/contract/coverage accounting เท่านั้น ไม่พิสูจน์ consent, hidden shared sources, physical equality, native chronology, selection independence หรือ truth ของ opaque records ต้อง independent semantic/byte review ภายนอกก่อน authentic admission

contract_admitted=True ไม่เท่ากับ joint_complete=True และทั้งสองไม่เท่ากับ scientifically ready ไม่มี scientific-ready flag หรือ TPR/FPR/delay/calibration computation ใน gate Task05 endpoint adapterคงเดิมและไม่ได้ถูกเรียกเพื่อทำ evaluation ในงานนี้ Q251–Q256ไม่เพิ่มเป็นjoint looks และผลถึงQ250ไม่ถูกเรียกdetection byQ256

Exact changed files:

1. `stream_prada_order/paired_stream_admission.py`
2. `stream_prada_order/tests/test_paired_stream_admission.py`
3. `stream_prada_order/TASK_06_PAIRED_ADMISSION_REPORT_TH.md`

ตรวจ complete diff และ protected implementation/report/config/protocol hashes แล้ว **14/14 ตรงก่อนงาน** พร้อม exact staged paths ก่อนหนึ่ง local commit และ `git diff --cached --check` / `git diff --cached --stat` ไม่มีการแก้ detectors/exporters/validators/fusion/endpoint adapter/historical results หรือ branch อื่น

Commit subject: `feat: add paired same-stream admission gate`; parent ต้องเป็น `26e840c53790b8fd6273778516fd36781c65c076` Actual SHA รายงานหลัง commit ในข้อความส่งมอบ ไม่เดา self-referential SHA ในไฟล์นี้ Resolve ด้วย:

```powershell
git log -1 --format=%H -- stream_prada_order/TASK_06_PAIRED_ADMISSION_REPORT_TH.md
```

หลัง commit ตรวจ branch/parent/SHA/committed file list/clean worktree แล้วหยุด ไม่ push ผู้ใช้เป็นผู้ push/sync fork และ independently review
