# Task 04 — Provenance-Bound Deep Kernel MMD Score Export

11 พฤศจิกายน 2026 (Asia/Bangkok)

**ผล: isolated admission/export implementation และ synthetic contract tests ผ่าน; NO-GO สำหรับ real-data Deep Kernel export / scientific same-stream integration ใน inspected artifacts**
ไม่มี real score payload, checkpoint, reference bank หรือ provenance receipt ถูกสร้างเพื่อทำให้ตัวอย่างผ่าน และไม่ได้วัด scientific TPR/FPR/delay

## 1. Repository และ scope

- Working branch ก่อนและหลังงาน: `experiment/stream-prada-order`
- Base HEAD: `1140297f44ecf74661259d5984746f49bd0d49e4` (`feat: add provenance-bound CUSUM score exporter`)
- ก่อนแก้ไข working tree/index สะอาด ตรวจด้วย `git status --porcelain=v1 --untracked-files=all`
- อ่าน [AGENTS.md](AGENTS.md), [Task 01 protocol/audit](../docs/hybrid/EXPERIMENT_PROTOCOL_V1_DRAFT.md), [Task 02 report](TASK_02_COMMON_STREAM_PRODUCER_REPORT_TH.md), [Task 03 report](TASK_03_CUSUM_EXPORT_REPORT_TH.md), [integration adapter](hybrid_integration.py), [fusion consumer](hybrid_fusion.py), [common producer](common_stream_producer.py), [CUSUM exporter](cusum_curve_exporter.py), [MMD contract](HYBRID_MMD_CONTRACT_TH.md) และ [producer requirements](HYBRID_MMD_PRODUCER_REQUIREMENTS_TH.md)
- ตรวจ `origin/restructure/deepkernel` แบบ read-only ที่ `e5d890703f9abd2a5a8988969579cb3a3ff0ed48` ซึ่งตรง `origin/refactor/clean-architecture` ไม่ checkout/fetch หรือเปลี่ยน branch/ref อื่น
- อ่าน active source ใน branch นั้น: `mea_detection/detection/kernels/deep.py`, `detection/mmd.py`, `detection/training.py`, `detection/checkpoints.py`, `detection/kernels/fixed.py`, `experiments/locked.py`, `data/windows.py`, `evaluation/windows.py`, `identity.py` และ `configs/experiments/deep_pure.json`, `model_leeching_deep_pure_locked.json` พร้อม AGENTS/domain/glossary guidance ผ่าน Git objects ไม่ import runtime ของอีก branch

งานนี้ไม่แก้ numerical algorithms, previous exporters/validators, experimental protocol หรือ historical results ไม่ใช้ Torch/NumPy/model runtime ใน exporter ไม่โหลด checkpoint/vectors ไม่ train/infer/acquire/scientifically evaluate ไม่ merge/rebase/cherry-pick/push หรือสร้าง PR

## 2. Actual active Deep Kernel identity

Active `DeepKernelMMD` รับ frozen sentence embeddings และใช้ learned feature map `Linear(input_dim, hidden_dim) → ReLU → Linear(hidden_dim, feature_dim)` สูตร kernel จาก source ที่ตรวจคือ:

```text
q(x,y)     = exp(-||x-y||² / (2*sigma_base²))
kappa(x,y) = exp(-||g(x)-g(y)||² / (2*sigma_feature²))
kernel     = ((1-epsilon)*kappa + epsilon) * q
```

ทั้งสอง bandwidths เรียนผ่าน exponential parameters และ epsilon ผ่าน sigmoid การ score ใช้ **all-cross unbiased MMD²** โดยตัด within-set diagonals และใช้ทุก cross pair แล้วเฉลี่ยเหนือ explicit reference draws ของสถิติเดียวกัน ค่าติดลบที่ finite จึง valid ได้ ไม่ใช่ probability/p-value

Training ใน active source เป็น pure benign-versus-known-attack pairs ใช้ paired U-statistic numerator กับ regularized asymptotic variance `4*variance_population(row_mean(H))`; training numeratorตัด cross diagonal ตาม paired definition ซึ่ง **ต่างจาก all-cross scoring numerator** ไม่เปลี่ยนนิยามเหล่านี้ใน exporter เลือก checkpoint จาก maximum fixed-validation mean J รวม epoch zero แล้ว freeze eval/gradients ก่อน held-out scoring

ตัวอย่าง `deep_pure.json` ที่ตรวจ: float64, seeds1/20/42, window sizes100/250, reference repeats20, calibration500/test200 sampled windows, pure training100, hidden128/feature64, 30epochs×16steps, validation32pairs ค่านี้เป็น existing experiment configuration ไม่ใช่ผลใหม่หรือการกำหนด repeat countของทุก future run อัตโนมัติ

`checkpoints.py` บันทึก `format=mea-detection-deep-v1`, active `pipeline_source_sha256`, state_dict, input_dim, training config, initial bandwidth และ original lock_id; loaderเดิมตรวจ source/lock แล้วคืน eval model ที่ requires_grad=False งานนี้ตรวจเพียง source definition และรับ external checkpoint-verification evidence **ไม่เรียก loader/torch.load**

### ต่างจาก older pilot อย่างไร

| ประเด็น | Active implementation | `pilot/deep_kernel_pilot.py` เดิม |
| --- | --- | --- |
| Base kernel | Single base RBF กับ trainable bandwidth | Fixed multi-RBF base |
| Learned factor | Learned feature RBF มี trainable feature bandwidth และ epsilon | `0.1 + 0.9*learned_RBF` โดย mixing constants คงที่ |
| Training pairs | Pure known-attack pairs | 10% mixed-window pairs |
| Objective | Paired numerator / regularized variance of H row means | Mean sampled-window score / variability across sampled windows proxy |
| Scoring | Mean of explicit-reference all-cross unbiased estimates | มี all-cross estimator เช่นกัน แต่ kernel/training identity ต่างกัน |

จึงไม่ใช้ชื่อ “Deep Kernel” หรือ scores.csvเก่าแทน actual active checkpoint/source/config identity Existing contract ที่กล่าวถึง pilot ยังคงเป็น historical definition ไม่ถูกเขียนทับใน Task 04

## 3. Implemented functionality และ contracts

[deep_kernel_mmd_exporter.py](deep_kernel_mmd_exporter.py) เพิ่ม API:

```python
export_deep_kernel_mmd(
    raw_scores, manifest, certificate, embedding_index, reference, *,
    expected_representation, source_evidence, evidence_records, profile,
    expected_revision, expected_definition, score_evidence, checkpoint_evidence,
    reference_evidence, availability_evidence)
```

รับ already-computed unthresholded records เท่านั้น คืน detached payload ตาม existing `hybrid-producer-scores-v1`, `kind=mmd_windows` ไม่มี incompatible wire schema หรือ file I/O ใช้ Task 02 admission และ existing `hybrid_integration.validate_reference()` / `export_scores()` โดยไม่คัดลอก numerical MMD/window/reference-draw validator ขึ้นใหม่

| Input | Requirement / binding |
| --- | --- |
| Common manifest/index/certificate | existing `hybrid-common-stream-v1`, `hybrid-embedding-index-v1`, `hybrid-groups-v1`; ผ่าน Task 02 authorization/chronology/physical-evidence checks กับ independently expected encoder/tokenizer/preprocessing representation |
| raw_scores | exact UTF-8 JSON bytes ของ list ที่ใช้ **existing score-row fields**; SHA256ตรง reviewed source-file binding; ≤8 MiB ไม่รับ historical batch summary/CSV เพื่อ infer scores |
| DeepKernelDefinition | source_revision, protocol_lock_sha256, input/hidden/feature dimensions, selected base/feature bandwidths และ epsilon, scoring dtype, reference_repeats, reference_manifest_sha256, training_provenance_sha256, selection_provenance_sha256, scoring_configuration_sha256 |
| CheckpointEvidence | actual checkpoint_identity/SHA256, independently matching definition, active format, eval_mode=True, requires_grad=False และ actual verification-record bytes/hash; ไม่สร้าง weight hashจากชื่อmodelหรือbranch |
| ReferenceEvidence | exact reference-manifest fingerprint, physical embedding artifact/contract identity, row_count/layout, frozen=True, physical-verification record และ provenance record |
| MMDScoreEvidence | raw score SHA256, common manifest/index fingerprints, independent detector revision/definition, reference-manifest fingerprint, exact draw-membership fingerprint และ source/draw provenance records |
| AvailabilityEvidence | raw score/common-manifest hashes, explicit basis, tupleของ(start,end,available_at) ตาม actual saved rows พร้อม actual receipt bytes/hash |
| evidence_records | supplied actual bytes ของ source authorization/chronology/physical/grouping, checkpoint verification, training/selection/scoring config, reference physical/provenance, score provenance/draw/availability records; ใช้ bounded byte/hash verification เดิม ≤1 MiBต่อrecord ไม่มีการสร้างrecordsที่ขาด |

`source_revision` ต้องเป็น active pipeline_source_sha256 ตาม actual reviewed checkpoint provenance ไม่ใช่การเดา pipeline hashจากGit HEAD; `protocol_lock_sha256` เป็น original producer lock_id ซึ่งเป็น digestตามวิธีproducerเดิม **ไม่ใช่ rehash raw lock.json ด้วย serializationใหม่** และไม่สร้าง/rewrite lock ให้กลายเป็น common256

Scoring configuration recordต้องรับรอง frozen dependencies/backend/precision/reference RNG policy ที่ใช้จริง Training/selection recordsต้องรับรอง memberships, permitted data, validation selection และ independence จาก test โดย external review ไม่มี model/epoch/method selectionใน exporter

Revision mapping ใน existing DetectorRevision:

- detector_revision = reviewed active pipeline source identity
- model_revision = actual Deep Kernel checkpoint SHA256
- configuration_revision = existing `hybrid_fusion.fingerprint()` ของ complete definition และ declared active method semantics/estimator/aggregation/window100/stride50
- calibration_provenance = model-selection/source provenance digest; **ยังไม่ใช่ Hybrid ECDF/calibration receipt** ส่วน training/scoring/reference identitiesถูกผูกใน configuration/provenance sidecars

Method-global revisionsไม่ใส่ per-stream score-file hash เพื่อให้ใช้ frozen Specเดียวกับ independent streamsได้ Source-file/draw/availability hashesอยู่ใน per-stream evidence sidecarsที่ต้องเก็บคู่ output

## 4. Window, score และ availability rules

ใช้ explicit `research_256_grid_proposal_v1` เท่านั้น: recorded horizon256, size100, stride50 และ required joint windows **[51,150], [101,200], [151,250]** เป็น1-based inclusive

Window[1,100] เป็น optional valid grid window ถ้าต้นทางมีอยู่จะคงไว้ แต่ไม่เป็น joint checkpointเพราะ CUSUM first eligible102 ไม่เพิ่ม terminal[157,256] หรือ interpolate/rename Q250เป็นQ256

ทุก valid rowต้องมี exact contiguous ordered-query slice fingerprint, actual reference draws100 distinct bank indicesต่อrepeat และ repeat countตรง definition Reference bankต้องอยู่fit, frozen, embedding contractตรงกับcommon query representation และไม่ทับ stream outer-group/exact query textตาม existing contract การมี repeated drawsข้ามrepeatsไม่แปลว่าได้ independent reference banksเพิ่ม

Raw signed scoreคงค่าและชนิด numericตามsource ไม่ clip/normalize/threshold/กลับsign รวม finite negative estimates Explicit invalid rowต้อง valid=false/value=null; invalid rowอาจไม่มี drawsตาม existing contract แต่ไม่เติมscore0

`computed_through` ต้อง explicit int=end ไม่รับ implicit None/default ส่วน available_atต้อง≥endและตรง actual availability evidence หากlateจะคงlateไว้ Native chronologyรับ declared_fixed_replay availability basisไม่ได้ และ query-position availabilityไม่ใช่ wall-clock latency

**Missing required window policy:** raise `MMDWindowsUnavailable` ไม่มี partial payloadหรือplaceholder ไม่ถือmissingเป็นbenign true negative; optional Q100ไม่ชดเชยrequired lookที่หาย ส่วน invalid/late rowsที่มีจริงยังexportได้พร้อมสถานะเดิม Consumerเลือก exact-end scoreและabstainตามexisting rules ไม่carry forward stale windows

Complete output หมายถึงมีrequired row positionsครบ ไม่ได้หมายความว่า valid/on-timeครบหรือ scientific-ready และ complete window exportไม่ใช่ real integration

## 5. Same-stream compatibility findings — synthetic fixtures only

Tests ส่ง payloadผ่าน existing `export_scores()` และใช้ `align_exports()` กับ outputจาก **Task 03 CUSUM exporterจริงในsoftware** โดย source dataทั้งหมดเป็นsynthetic numeric fixtures ตรวจได้ว่า:

- ทั้งสองฝั่งผูกcommon manifest, embedding representation/index/rows และ source-group certificateเดียวกัน
- Independent CUSUM/Deep Kernel source/model/config revisionsคงแยกกัน และ mismatchถูกreject
- Joint pointsตรง Q150/Q200/Q250 และ MMD boundariesถูกต้อง ค่าติดลบยังตรงsource
- Invalid exact Q200ให้reason=invalid; scoreQ200ที่ available_at201ให้reason=not_available ทั้งที่มีprior scoreQ150 จึงไม่carry forward
- เมื่อrequired windowหาย exporterปฏิเสธ payload; การส่ง absenceให้consumerให้missing/None ไม่ใช่0 ไม่มีrejected exportถูกนำมาอ้างเป็นsuccessful integration
- Nativeและfixed-query-replay fixturesต้องมีmatching explicit evidence/basis ไม่แปลง replayเป็นnative

ไม่เรียก fusion calibration/threshold selection หรือคำนวณ scientific TPR/FPRจากfixturesเหล่านี้ Endpointตามdraftยังเป็น **any alert by Q250** และ Q251–Q256ไม่ jointly evaluated ไม่มีการแก้ Phase F definitions, Hybrid300 calculations หรือ censor gapเดิม

## 6. Tests และ observed results

ใช้ Conda `senior`, Python `-B`; ไม่มี queries, vectors, checkpoint weights หรือ modelsในfixtures [test_deep_kernel_mmd_exporter.py](tests/test_deep_kernel_mmd_exporter.py) Numeric hashes/receipt bytesในtestsไม่ใช่authentic research provenance

TDD ที่สังเกตจริง:

1. เพิ่มtestsก่อนmoduleแล้วfocused run failด้วย expected ImportError (1 loader error)
2. Implementation รอบแรกผ่าน **22 tests**, runtime2.606s
3. เพิ่มpositive native/multiple-repeat checks แล้วรวมregressionผ่าน103 testsใน5.465s
4. เพิ่มnegative testของ frozen scoring-configuration recordก่อนimplementation พบexpected unsupported-field error (1 error); จากนั้นเพิ่มfield/bindingจริงและรัน required suiteใหม่
5. ชุดล่าสุดผ่าน **103 tests = ใหม่24 + existing79**, failures/errors/skips=0, runtime **5.495s** เป็นsoftware test duration ไม่ใช่model/GPU/runtime benchmark

คำสั่ง focused / final regressionที่ execute:

```powershell
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_deep_kernel_mmd_exporter -v
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_deep_kernel_mmd_exporter stream_prada_order.tests.test_cusum_curve_exporter stream_prada_order.tests.test_common_stream_producer stream_prada_order.tests.test_hybrid_integration stream_prada_order.tests.test_hybrid_fusion -q
```

| Required coverage | สิ่งที่ตรวจ |
| --- | --- |
| 1–2 Complete export/alignment | existing wire keys, exact raw values, required3windows + optional100, current150/200/250 |
| 3–4 Manifest/order/embeddings | wrong manifest/index/slice hash, reversedrequestorder, encoder/tokenizer/preprocessing/row mismatch |
| 5–6 Checkpoint/kernel/config | wrong checkpoint/hash/format/frozen state, wrong architecture/bandwidths/epsilon/source/lock/config revision |
| 7 Training/model selection | missing training/selection/scoring-config record bytesถูกreject |
| 8 Reference evidence | missing/unfrozen/physical mismatch, wrongbankidentity/layout/count, query/source contamination |
| 9 Draws/repeats | missing/wrongcount/out-of-range/duplicate drawindices, changed authenticated draw membership; explicitmultiple repeatsผ่าน |
| 10 Windows | duplicate, wrongwidth/off-grid และ terminal256ถูกreject |
| 11–12 Score values | negativefiniteคงเดิม, NaN/Inf/bool/validity mismatchถูกreject, explicitinvalidnullคงinvalid |
| 13 Missing/late/future | missingrequiredwindowเป็นunavailable; actual lateคงlate, mismatched/backdated/None/future dependencyถูกreject |
| 14 Authentic evidence | absent/tampered raw bytes/sidecars และ summary-onlyไม่ถูกแปลงเป็นscores |
| 15 Preservation | detached outputsและinputsไม่เปลี่ยน; hash source/result bytesก่อนหลังexportเท่ากัน ไม่parse historical score rows |
| 16–17 Compatibility/regression | Task03 exporter22 + commonproducer18 + integration17 + fusion22 =79เดิมผ่านครบ |

## 7. Bounded real-data readiness audit

**NO-GO** ในcurrent checkout/explicit inspected locations ไม่ได้อ้างว่า teammateไม่มี artifactsที่อื่น ไม่มี machine-wide search, remote acquisition, private traffic access หรือ checkpoint/embedding payload read

ตรวจ existenceเฉพาะpathsจาก relevantconfigs และ historical reports:

| Path ที่ตรวจ | ผลปัจจุบัน |
| --- | --- |
| Repository-root `artifacts/migrated_deep_pure_comparison` | ไม่มี |
| Repository-root `artifacts/migrated_model_leeching_deep_pure_v1` | ไม่มี |
| Repository-root `artifacts/model_leeching_deep_pure_v1` | ไม่มี |
| Repository-root `artifacts/model_leeching_protocol_v1` | ไม่มี |
| Repository-root `pilot/outputs` | ไม่มี |

ตรวจ bounded metadata `experiment_result/main/seed=42/MMD/model_leeching_bge_bs1500/metadata.json` (≤4 MiB) พบmodel name BAAI/bge-small-en-v1.5, batch_size1500, reference_repeats20 และอ่านเฉพาะCSV headerของ `batch_scores.csv`: split,batch_id,label,size,attacker_ratio,attacker_count,score,p_value,suspicious ไม่มีscore-row analysis

Metadata file SHA256ยังเป็น `b2dcfe691cd5d97858f0d9dafe6f6323f183c27de2b375ba528518f266171628` ผลbatchนี้ไม่ใช่active Deep Kernel checkpoint/window100/native-common-stream evidence และbatch_idไม่ใช่chronology/window boundaries

Active `locked.py` มีpipelineเก็บ checkpoints/training metadata และlocked random-window/reference drawsจริงในsource แต่ไฟล์ที่ไม่ได้อยู่ในcheckoutนี้ **ไม่ถูกสร้างหรือrecertifyแทน** Existing resampled windowsแม้reproducibleก็ไม่ใช่common ordered native traffic

### Exact missing handoff artifacts

1. Actual selected active Deep Kernel checkpoint identity/SHA256 พร้อม external byte-verification record, format/source/lock identity, actual frozen architecture/kernel parameters/eval/gradient/precision metadata
2. Authentic training/model-selection recordsที่ผูก checkpointกับpermitted source memberships, fixed validation selectionและsource/data independence; frozen scoring dependency/backend/precision/RNG configuration record
3. Authorized actual common256 manifest/index/source-group certificate และ independently verified exact text↔physical embedding rowsที่ยังเป็นblockersจากTask02
4. Frozen benign fit reference bank `hybrid-reference-v1` จริง พร้อมphysical row/artifact/representation identity และprovenanceที่รับรองno query/group/test leakage
5. Already-computed raw signed MMD rows ของ [51,150]/[101,200]/[151,250], raw file bytes/SHA256 และ per-stream checkpoint/model/config provenance ไม่ใช่ old batch scores หรือ thresholded decisions
6. Actual reference draw indices/repeat membershipsและreviewed draw-provenance recordที่ตรงfile/window/bank; ไม่สุ่มใหม่ในexporter
7. Actual score-availability evidenceและcausal computed-through receiptsสำหรับทุก exported window ไม่สมมติ available_at=end หรือนำreplayไปเรียกnative

ไม่มีการสร้าง fake scores/checkpoint hashes/reference receipts/chronology เพื่อแก้ missing artifacts หากมี actual exports ที่อื่นต้องส่ง explicit authorized paths/bytes/hash ให้ review งานนี้ไม่เปิด training/scoring task ต่ออัตโนมัติ

## 8. Scientific limitations และ preservation

การตรวจนี้รับรอง software consistency, exact bytes/hash bindings และ existing schema compatibility ภายใต้ external inputs ที่ review แล้ว ไม่พิสูจน์ opaque record content/signatures, human consent, physical checkpoint/vector bytes, statistical independence หรือ hidden future-dependent computation ด้วยตัวเอง

Caller ต้องเก็บ raw score file, model/training/selection/scoring/ref/draw/availability sidecars คู่กับ payload ใน authorized private storage เพราะ wire schema เดิมไม่มี receipt fields ทั้งหมด Payload อย่างเดียวไม่ใช่ complete provenance ห้ามสร้างคำรับรองให้ตรง expected metadata โดยไม่มี actual source evidence

Length/format confounding, benign fit/calibration/test availability, new joint ECDF/threshold calibration, power/multiplicity/FPR comparison plan และ authentic paired traffic ยังไม่ผ่าน Scientific TPR/FPR/delay/generalization/superiority **unmeasured/null** ไม่ใช้ 103 passing tests อ้าง Hybrid superiority หรือ successful scientific integration

Changed files เฉพาะ Task 04:

1. `stream_prada_order/deep_kernel_mmd_exporter.py`
2. `stream_prada_order/tests/test_deep_kernel_mmd_exporter.py`
3. `stream_prada_order/TASK_04_DEEP_KERNEL_EXPORT_REPORT_TH.md`

ตรวจ protected source/report/protocol hashes แล้ว **13/13 ตรงก่อนงาน** และตรวจ exact changed/staged paths ก่อน commit พร้อม `git diff --cached --check` / `--stat` ไม่มีการแก้ algorithm, historical results หรือ branch อื่น และไม่ใส่ private artifacts เข้า commit

## 9. Commit identity

สร้างหนึ่ง local commit subject `feat: add provenance-bound deep kernel mmd score exporter` บน parent `1140297f44ecf74661259d5984746f49bd0d49e4` หลัง required tests/checks ผ่าน Actual SHA จะรายงานในข้อความส่งมอบหลัง commit และ resolve commit ที่บรรจุรายงานนี้ได้ด้วย:

```powershell
git log -1 --format=%H -- stream_prada_order/TASK_04_DEEP_KERNEL_EXPORT_REPORT_TH.md
```

ไม่ฝัง SHA คาดเดาของ commit ที่บรรจุไฟล์นี้เอง หรือสร้าง second commit เพื่อแก้หลัง commit ตรวจ branch/parent/commit file list/clean worktree แล้วหยุด **ไม่ push** ผู้ใช้เป็นผู้ push/sync fork และ independently review
