# Task 03 — Provenance-Bound CUSUM Curve Export

11 พฤศจิกายน 2026 (Asia/Bangkok)

**ผล: isolated exporter และ synthetic contract tests ผ่าน; NO-GO สำหรับ real-data CUSUM export / same-stream integration ในหลักฐานที่ตรวจ**
ไม่มีการผลิตหรือประเมิน real score payload, ไม่มีการสร้าง curve จาก maxima/first-alert summaries และไม่มี scientific TPR/FPR/delay measurements

## 1. Repository และ scope

- Branch ก่อนและหลังงาน: `experiment/stream-prada-order`
- Base HEAD: `a3750a683a0d6146cc9eaafbaa8d856e289f8ea7` (`Add common stream manifest producer and associated tests`)
- ก่อนแก้ไข working tree และ index สะอาด ตรวจด้วย `git status --porcelain=v1 --untracked-files=all`
- อ่าน [AGENTS.md](AGENTS.md), [protocol draft](../docs/hybrid/EXPERIMENT_PROTOCOL_V1_DRAFT.md), [Task 02 report](TASK_02_COMMON_STREAM_PRODUCER_REPORT_TH.md), [producer requirements](HYBRID_MMD_PRODUCER_REQUIREMENTS_TH.md), [phase_d_pilot.py](phase_d_pilot.py), [experiment.py](experiment.py), [hybrid_fusion.py](hybrid_fusion.py), [hybrid_integration.py](hybrid_integration.py) และ [common_stream_producer.py](common_stream_producer.py)
- ตรวจ Deep Kernel branch แบบ read-only: `origin/refactor/clean-architecture` และ `origin/restructure/deepkernel` อยู่ `e5d890703f9abd2a5a8988969579cb3a3ff0ed48`; อ่าน AGENTS/domain/glossary กับ `mea_detection/detection/kernels/deep.py` และ `mea_detection/embeddings/encoder.py` ผ่าน Git objects ไม่ import หรือเปลี่ยนอีก branch
- คง main ที่ `5fb5e07d750a73a0a663a174433bab931ae7568a`; ไม่ merge/rebase/cherry-pick/fetch/push/สร้าง PR และไม่ฝึกหรือรัน model/detector

## 2. Current CUSUM semantics ที่คงเดิม

`experiment.trace()` ประมวลผล minimum L2 distance จาก query ปัจจุบันถึง PRADA Growing Set ก่อน admission; การรับสมาชิกเข้า Growing Set เป็นไปตาม adaptive threshold เดิม Distance History ยังคงเพิ่มทุก request และ state ยังคงอัปเดตตาม loop ไม่หยุดหลัง alert

`phase_d_pilot.fit_distance()` fit mean และ sample SD (`ddof=1`) รายตำแหน่ง Q2..Q256 จาก benign fit histories โดยใช้ sigma floor0.01 ส่วน `curves()` standardize distances แล้วใช้ `[100:]` ซึ่งตรง Q102..Q256:

```text
z_t = (d_t - mu_t_fit) / sigma_t_fit
C_plus_before_Q102 = C_minus_before_Q102 = 0
C_plus_t  = max(0, C_plus_(t-1)  + z_t - k)
C_minus_t = max(0, C_minus_(t-1) - z_t - k)
two_sided_t = max(C_plus_t, C_minus_t)
```

Exporter ไม่เรียกสูตรเหล่านี้ ไม่คำนวณ Growing Set/distances/CUSUM/fit ใหม่ และไม่พิสูจน์ recursive numeric parity ด้วยการ recompute แต่ผูก source/config/fit/upstream provenance ของ producer ที่ได้รับ review ไว้ก่อน

First eligible CUSUM score ยังคง Q102; Q1..Q101 เป็นช่วงที่ upstream state เห็น traffic แล้ว แต่ไม่ได้ถูกสมมติว่า benign ไม่มี benign-prefix normalization, onset-dependent reset หรือการเลื่อน onset มาที่ Q102 โดย exporter รองรับ upper/lower/two_sided และ k=.5/1.0 เป็น explicit documented alternatives ทั้งหมด ไม่เลือก best direction/k จากผล test

## 3. สิ่งที่ implement และ input contract

[cusum_curve_exporter.py](cusum_curve_exporter.py) เป็น admission-only standard-library API:

```python
export_cusum_curve(
    raw_curve, manifest, certificate, embedding_index, *,
    expected_representation, source_evidence, evidence_records, profile,
    expected_revision, expected_definition, curve_evidence, availability_evidence)
```

API คืน detached dict ของ existing `hybrid-producer-scores-v1`, `kind=cusum_curve` เท่านั้น ไม่มี file I/O, CLI/acquisition, score generation หรือ extra fields ใน score wire schema ใช้ `hybrid_integration.export_scores()` ตรวจ payload ก่อนคืน ไม่มีการเปลี่ยน frozen fusion/adapter calculations

| Input | ข้อกำหนดและ binding |
| --- | --- |
| manifest/certificate/embedding_index | existing `hybrid-common-stream-v1`, `hybrid-groups-v1`, `hybrid-embedding-index-v1` ที่ตรงกัน; เรียก Task 02 producer admission ซ้ำพร้อม expected representation, source evidence และ actual evidence record bytes ไม่รับ self-declared manifest ผ่านช่องทางลัด |
| profile | ต้องระบุ `research_256_grid_proposal_v1` ชัดเจน; exporter รุ่นนี้จำกัด256ตาม Phase D ไม่เปลี่ยน consumer/profile300 เดิมหรือ truncate input300ให้256 |
| raw_curve | exact already-computed UTF-8 JSON bytes ของ **list ที่ใช้ existing score-row fields**; ไม่มี competing curve/score schema; ≤8 MiB ไม่รับ summaries หรือ distances เพื่อสั่ง recompute |
| CurveEvidence | curve_sha256, manifest_sha256, embedding_index_sha256, revision, definition, provenance_record_sha256; hash curve เป็น SHA256 ของ exact raw bytes ไม่ใช่ canonical reserialization หรือ compressed-container hash |
| CusumDefinition | direction, k, fit_parameters_sha256, fit_provenance_sha256, upstream_provenance_sha256; ต้องตรง independently expected definition; upstream stamp นี้เป็น method-global source/embedding-policy provenance ส่วน per-stream history ต้องอยู่ใน curve provenance record |
| expected_revision | existing DetectorRevision: detector_revision จาก pinned actual source; model_revision=SHA256 ของ authentic saved fit parameter bytes; configuration_revision=`configuration_fingerprint(expected_definition)`; calibration_provenance=benign fit provenance SHA256 ไม่อ้างว่าเป็น Hybrid-calibrated threshold |
| AvailabilityEvidence | curve_sha256, manifest_sha256, basis, tuple ของ (query_index, available_at) ครบ Q102..Q256, record_sha256; ต้องตรง actual saved rows ทุกตำแหน่ง |
| evidence_records | actual bytes ของ Task 02 source records รวม curve provenance, availability, saved fit artifact, benign fit provenance และ upstream provenance; ใช้ bounded byte/hash check เดิมจาก Task 02, ≤1 MiB ต่อ record ไม่มีการสร้าง records ที่หายไป |

Configuration fingerprint ใช้ existing `hybrid_fusion.fingerprint()` ผูก definition และ declared Phase D semantics: initial state0, first eligible102, no reset, sigma floor.01, continuous PRADA minimum-L2 source และ current two-sided max ไม่ใส่ per-stream raw-curve hash ลง detector revisions เพื่อให้ frozen Spec เดียวใช้กับ independent streams ได้

Saved fit artifact ใช้ format เดิมของ `distance_fit.json`: fit_cohorts, sigma_floor, mu, sigma ต้องมีอย่างน้อย2 distinct nonnegative integer cohort IDs, mu/sigmaครบ255 positions, finite values และ sigma≥.01 โดย hashตรง model revision การตรวจ shape/bytes นี้ยังไม่พิสูจน์ว่า fit cohorts เป็น benign หรือ disjoint จาก test จริง ต้องมี reviewed fit provenance ที่รับรอง memberships/label/split/selection ไว้ภายนอก

หากต้นทางเก็บ gzip/container ให้ caller คง container hash แยกจาก exact decompressed JSON bytes/hash และส่ง explicit bytes ที่อนุญาตอ่าน API ไม่เปิด/เดา path หรือ decompress payload ให้เอง

## 4. Output contract และ availability

Payload ใช้ keys เดิมครบ: schema_version, kind, profile_id, manifest_sha256, representation_sha256, grouping_certificate_sha256, revision, availability_basis, reference_manifest_sha256=null, reference_repeats=0 และ rows ไม่มี ECDF, thresholds, p-values หรือ decisions ใหม่

แต่ละ row ต้องมี **start, end, available_at, computed_through, value, valid, query_slice_sha256, reference_draws** ตาม schema เดิม โดย sequential start=end=t และ reference_draws=null ตรวจ complete ordered endpoints Q102..Q256 จำนวน155 records เก็บ exact values/validity ไม่ทำ max pooling, sign change, smoothing, interpolation หรือ latch ก่อน checkpoint

`computed_through` ต้องส่งเป็น int ชัดเจนและเท่ากับ end ไม่ยอมรับ None แม้ legacy Score constructor เดิมมี default สำหรับกรณีนั้น `available_at` ต้อง≥end และตรง availability evidence; native chronology ใช้ declared_fixed_replay basis ไม่ได้ ส่วน observed query-position availability ไม่ใช่หลักฐาน wall-clock latency

| State | พฤติกรรม |
| --- | --- |
| Valid causal score | finite nonnegative current CUSUM, valid=true, computed_through=end และพร้อม ณ checkpoint จึงใช้ได้ |
| Invalid score | explicit valid=false/value=null คงไว้; consumer เห็น invalid ไม่เติม0หรือถือเป็น true negative |
| Missing/incomplete curve | raise `CurveUnavailable` (ValueError subclass) เช่น `complete_ordered_Q102_Q256_curve_unavailable`; ไม่มี payload/placeholder/missing score ที่ถูกสร้างใหม่ และไม่มี benign detection outcome |
| Late score | คง available_atจริง เช่นQ201สำหรับ scoreQ200; exportได้แต่ alignerคืน not_available ที่Q200 ไม่ backdate หรือ carry forward Q150 |
| Unverified provenance | reject ด้วย ValueError เมื่อ evidence/stamps/bytes/hash/representation/order ไม่ครบหรือตรงกันไม่ได้ ไม่มี outputหรือ scientific eligibility |
| Future dependency | computed_through≠end หรือ implicit None ถูก reject ไม่ยอมใช้ query อนาคตคำนวณคะแนนย้อนหลัง |

เก็บ raw curve bytes, CurveEvidence, AvailabilityEvidence, expected definition/revision และ reviewed records คู่กับ payload ใน authorized private storage เพราะ existing score wire schemaไม่มี raw-curve/evidence receipt fields ของตัวเอง Payload ที่แยกจาก sidecars **ไม่ใช่หลักฐาน provenance ที่ครบถ้วน** ห้ามส่ง payloadอย่างเดียวแล้วอ้างว่ามี authentic export review

Byte/hash/binding checks ไม่พิสูจน์ signatures, consent, actual chronology, independence, hidden future data หรือความจริงของ opaque provenance records Reviewer ต้อง independently ตรวจว่าผู้ผลิตใช้ causal inputs/benign fit/state initialization/continuous upstream ตาม definition ที่รับรองไว้จริง ไม่สร้าง attestations เพื่อทำให้ตัวอย่างผ่าน

## 5. Joint checkpoint verification และ scientific boundary

Tests ส่ง output ผ่าน `hybrid_integration.export_scores()` และ unchanged `hybrid_fusion.align()` แล้วได้ current values ที่ **Q150/Q200/Q250** ตรง source rows โดยจงใจมี synthetic value สูงที่Q149 เพื่อยืนยันว่าไม่ใช้ maximum/latch แทน Q150 และมี late/invalid checkpoint cases แยกกัน

Curve exportครบถึงQ256ไม่ได้แปลว่า jointly evaluate ถึงQ256 Protocol draftยังคง endpoint **any alert by Q250**, Q251–Q256ไม่ jointly evaluated; ไม่แก้ evaluator censor gap ที่ Task 01 ระบุ ไม่ calibrate thresholds ใหม่ในงานนี้ และไม่เปลี่ยน Phase F online definitions หรือ illustrative Hybrid300

## 6. Tests ที่ execute จริง

ใช้ synthetic numeric metadata/score/fit/receipt fixtures เท่านั้น ไม่มี research sentence, model/vector/query execution หรือ scientific detector metrics Unit testหนึ่งตรวจ SHA256 ก่อน/หลัง export ของ source files และ historical output bytes เพื่อ preservation เท่านั้น ไม่ parse score rows เพื่อประเมิน detection

TDD: เพิ่ม tests ก่อน implementation แล้วรัน focused suite พบ expected ImportError (1 loader error) จากนั้น implementation รอบแรกผ่าน20 tests; หลังเพิ่ม explicit availability-binding และ missing-row-field cases ชุด final ผ่าน **79 tests = ใหม่22 + existing57**, failures/errors/skips=0; unittest runtime **3.103s** เป็น software test duration ไม่ใช่ detector/model latency benchmark

Pre-commit rerun ชุดเดิมด้วย `-q` ผ่าน79 testsอีกครั้งใน **3.036s** ไม่มี failures/errors/skips; ไม่มี required testค้าง failก่อน commit

คำสั่ง focused และ final regression ที่ execute:

```powershell
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_cusum_curve_exporter -v
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_cusum_curve_exporter stream_prada_order.tests.test_common_stream_producer stream_prada_order.tests.test_hybrid_integration stream_prada_order.tests.test_hybrid_fusion -v
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_cusum_curve_exporter stream_prada_order.tests.test_common_stream_producer stream_prada_order.tests.test_hybrid_integration stream_prada_order.tests.test_hybrid_fusion -q
```

| Required coverage | สิ่งที่ตรวจ |
| --- | --- |
| 1–2 Complete export / exact checkpoints | 155 ordered records, existing wire keys, unchanged values/revisions, current150/200/250 ไม่ใช้ max149 |
| 3–4 Manifest/order/embedding | wrong manifest/index hash, reversed request order, physical row hash และ encoder revision mismatch |
| 5 Missing/duplicate positions | missing Q102/checkpoint/Q256, duplicate/reordered rows, warm-up index และ absent row fields ไม่เติมให้ |
| 6 Invalid/nonfinite | explicit invalid nullผ่านแบบ unavailable; NaN/Inf/negative/bool/validity mismatchถูกreject |
| 7 Direction/k | ทั้ง6 explicit direction×k alternatives ผ่าน; mismatch/undocumented k/config hashถูกreject |
| 8 Detector/fit provenance | source/model/fit stamp mismatch, missing/tampered fit/upstream evidence, malformed position fit artifact |
| 9 Future/late | future/None dependencyและ backdated availabilityถูกreject; genuine late valueคง late, availability recordต้องตรง |
| 10 Repeated requests | identical query text/rowคง distinct unique request IDs; duplicate IDถูกreject |
| 11–12 Missing evidence/summary-only | absent/tampered bytes/record/kind/binding และ max_score/first_alert-onlyไม่ใช้แทน curve |
| 13 Preservation | detached output, caller inputsไม่เปลี่ยน; source/results hashesก่อนหลังเท่ากัน |
| 14 Regression | common producer18 + integration17 + fusion22 =57 testsเดิมผ่านครบ |

## 7. Real-data blockers ที่ยังเหลือ

**NO-GO real export จาก inspected artifacts** ไม่มี real CUSUM curve ส่งเข้า exporter ไม่มี score joins หรือ actual Hybrid evaluation

อ่านเฉพาะ existing metadata/header และ source codeเพิ่มเติมจาก Task 02:

- `results/phase_d_pilot_20261107_v2/distance_fit.json` มีจริง:12,539 bytes, keys fit_cohorts/sigma_floor/mu/sigma, cohorts0–3, floor.01, mu/sigmaอย่างละ255 ค่า SHA256=`805c79422b7cb838462cb523f85762f990363d361c29819d195402e693cf97b6` อ่านเพื่อ shape/metadata ไม่ fit/scoring ใหม่
- `results/phase_d_pilot_20261107_v2/per_stream.csv.gz` มี header cohort/key/attack_count/permutation/ordering/has_attack/candidate/alpha/max_score/any_alert/first_alert/prefix_alarm/eligible/detected/delay/right_censored; SHA256=`7cb0218a02f6902ef6e775346a78d00983400b53f5727a19108c73117a7cc8ea` ไม่มี saved per-query CUSUM curve ใน schema นี้
- Source `phase_d_pilot.py` สร้าง curves() ในหน่วยความจำและบันทึก aggregate rows ดังกล่าว ไม่ทำให้ temporary arrays กลายเป็น authentic saved curve ในงานนี้ Existing saved distance/W historiesไม่ใช่ saved CUSUM curve และไม่ recomputeมาแทน

Required handoff ที่ยังขาด:

1. Authentic already-computed CUSUM rowsครบQ102..Q256 แบบexisting row fields พร้อม exact source bytes/hash ไม่ใช่maxima/first alerts
2. Reviewed per-stream curve provenanceที่ผูก actual common manifest, query/embedding order, upstream history, direction/k/source/model/config และ raw-curve hash
3. Explicit actual per-query availability listกับ reviewed record/basis; ไม่มีการ infer available_at=t หรือ native chronologyจากreplay
4. Authentic authorized common256 manifest/index/group certificate และ physical identity/authorization/chronology recordsที่ยังเป็นblockersตามTask 02
5. Independently agreed benign position-fit/model/upstream provenanceที่รับรอง memberships/independence/causalityจริง แม้ existing distance_fit artifactมีอยู่ก็ยังไม่เท่ากับ new common-stream provenance

ไม่มี machine-wide/private traffic search และไม่ได้พิสูจน์ว่า teammateไม่มี outputsที่อื่น หากมีให้ส่ง explicit authorized paths/bytesพร้อมexpected hashes การสร้าง future authentic curveจะเป็น separately authorized producer task ไม่ใช่การเปิด recomputation ใน exporterนี้

Length/format confounding, independent benign calibration, actual paired MMD windows/reference/checkpoint evidence และ statistical comparison planยังไม่ถูกแก้ Scientific FPR/TPR/delay/generalization/superiorityยัง **unmeasured/null** ไม่ใช้79 passing testsเป็น scientific result

## 8. Changed files และ Git validation

Task 03 เพิ่มเฉพาะสามไฟล์:

1. `stream_prada_order/cusum_curve_exporter.py`
2. `stream_prada_order/tests/test_cusum_curve_exporter.py`
3. `stream_prada_order/TASK_03_CUSUM_EXPORT_REPORT_TH.md`

ไม่มีการแก้ original algorithms, historical outputs, Task 02 producer, existing fusion/integration หรือ protocol ตรวจ protected source/protocol hashesแล้ว **11/11ตรงก่อนงาน** และตรวจ tracked diff, branch กับ exact changed/staged file listก่อน commit ใช้ explicit pathsในการstage และตรวจ `git diff --cached --check` / `git diff --cached --stat` ตามคำสั่งผู้ใช้ ไม่มี push/PR หรือเปลี่ยนอีก branch

## 9. Final commit SHA

งานนี้จะมีหนึ่ง local commit subject `feat: add provenance-bound CUSUM score exporter` บน parent `a3750a683a0d6146cc9eaafbaa8d856e289f8ea7` เท่านั้น Actual final SHAรายงานหลัง commitในข้อความส่งมอบ และ resolve commitที่บรรจุรายงานนี้ได้ด้วย:

```powershell
git log -1 --format=%H -- stream_prada_order/TASK_03_CUSUM_EXPORT_REPORT_TH.md
```

ไม่ฝัง SHAคาดเดาของ commitที่บรรจุไฟล์นี้เอง และไม่สร้าง second commit/amendเพื่อแก้ self-reference หลัง commitตรวจbranch/SHA/file list/clean worktreeแล้วหยุด ผู้ใช้เป็นผู้pushและsync fork
