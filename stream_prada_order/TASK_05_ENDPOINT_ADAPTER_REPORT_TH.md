# Task 05 — Endpoint-Aware Evaluation Adapter for Detection by Q250

11 พฤศจิกายน 2026 (Asia/Bangkok)

**ผล: endpoint accounting implementation และ synthetic tests ผ่าน; ไม่ใช่ scientific Hybrid integration หรือการรับรอง authentic-artifact readiness**
Task นี้ไม่รัน model/detector ไม่สร้าง research calibration, traffic, scores, receipts, chronology หรือ experimental artifacts และไม่เปลี่ยน historical outputs/thresholds

## 1. Repository และ existing mismatch

- Branch: `experiment/stream-prada-order`
- Expected และ actual base HEAD ตรงกัน: `5797d33b7155264d0b19258c0a803ac669d4856e`
- ก่อนแก้ไข `git status --porcelain=v1 --untracked-files=all` ว่าง ทั้ง working tree/index; ไม่มี HEAD difference ให้ reconcile
- อ่าน [AGENTS.md](AGENTS.md), [Task 01 protocol](../docs/hybrid/EXPERIMENT_PROTOCOL_V1_DRAFT.md), [Task 02 report](TASK_02_COMMON_STREAM_PRODUCER_REPORT_TH.md), [Task 03 report](TASK_03_CUSUM_EXPORT_REPORT_TH.md), [Task 04 report](TASK_04_DEEP_KERNEL_EXPORT_REPORT_TH.md), [hybrid_fusion.py](hybrid_fusion.py), [hybrid_integration.py](hybrid_integration.py) และ existing tests

`hybrid_fusion.evaluate()` เดิมใช้ `schedule.horizon` เป็น no-alert censor สำหรับ complete attack record ที่มี known onset ดังนั้น profile256 ซึ่งมี joint looks แค่150/200/250 ยังคืน `censor_query=256` ส่วนข้อมูล Q251–Q256 ไม่มี joint decision

ก่อน implementation รัน synthetic legacy tests ยืนยันจริงว่า:

- Horizon256 / last look250 / complete no alert → existing Result.censor_query=256
- Horizon300 → no-alert censor300 และ alert ที่Q300ยังคง first_alert_query300/delay299 เมื่อonset1

คง `hybrid_fusion.py`, Result, numerical decisions และ horizon300 behavior เดิมทั้งหมด ไม่แก้ config, exporters หรือ threshold แล้วเพิ่ม reporting adapter แยกเท่านั้น

## 2. Implemented API และ exact schedule

[hybrid_endpoint_adapter.py](hybrid_endpoint_adapter.py) เพิ่ม:

```python
evaluate_by_q250(model, rows, method, *, profile, attack_onset=None)
```

ต้องส่ง explicit `profile='research_256_grid_proposal_v1'` พร้อม existing compatible `Calibrated` และ `Aligned` records โดยตรวจ model/alignment schedules ตรง existing profile ทุก field:

| Schedule field | Required value |
| --- | ---: |
| horizon | 256 |
| window | 100 |
| stride | 50 |
| first_eligible | 102 |
| checkpoints | (150,200,250) |

ไม่ตรวจแค่ last look หรือ checkpoint tuple เพราะ horizon255/first_eligible101 อาจให้สาม looks เดียวกันแต่ไม่ใช่ protocol นี้ ไม่ยอมรับ horizon300 ใน adapter และไม่ truncate/reshape schedule ให้เข้ากัน

Adapter เรียก **`hybrid_fusion.evaluate()` เดิม** สำหรับ decisions, threshold comparisons, model/alignment compatibility, split/disjointness/onset validation, first observed/exact alert และ pre-attack/incomplete semantics ไม่มี ECDF/fusion/threshold/calibration calculations ชุดใหม่

คืน `EndpointReport` ซึ่งเป็น separate frozen dataclass ไม่ใช่ Result subclass และไม่เปลี่ยน existing wire schemas ไม่มี file I/O หรือ aggregate TPR/FPR computation

## 3. Exact reporting fields

| Field | ความหมาย |
| --- | --- |
| profile_id | explicit profile ที่ผ่าน exact schedule check |
| recorded_horizon | 256; จำนวน queries ใน recorded stream ไม่ใช่ last evaluated look |
| evaluation_end | 250; endpoint ของ scheduled decisions ชุดนี้ |
| spec / stream / method | original immutable Spec/Stream และ method identity ไม่เปลี่ยน |
| calibration_provenance | original evaluator/model calibration provenance SHA256 เดิม ตรวจด้วย existing digest validator ไม่สร้าง receipt ใหม่ |
| threshold | original selected-method Threshold record; ไม่ปรับ value/rank/streams/alpha |
| points | tuple snapshot ของ existing immutable aligned Points รวม available raw component values และ availability reasons; ไม่ recover scores ที่ Aligned ไม่ได้ส่งมา |
| decisions / checkpoints | tuple จาก original Result ตรงเดิม ไม่มี Q256 decision เพิ่ม |
| complete | completeness ของ required decisions สำหรับ **method ที่เลือก** ตาม original evaluator |
| joint_complete | ทั้ง sequential และ MMD valid/on-time ครบทุก look; แยกจาก standalone-method completeness |
| any_alert_by_q250 | observed-event status แบบ True/False/None ตามกฎด้านล่าง |
| first_observed_alert | scheduled look แรกที่เห็น True จริง ตาม original Result |
| first_alert_query / first_alert_exact | exact first-alert timing/knownness จาก original Result ไม่แทนด้วย observed alert เมื่อก่อนหน้ามี unknown |
| attack_onset | original validated known onset หรือ None |
| pre_attack_alarm | original Result value รวม None เมื่อไม่ applicable/ยัง infer ไม่ได้ |
| scheduled_post_onset_opportunity | True ถ้ามี scheduled checkpoint≥known onset, False เมื่อไม่มี, None เมื่อ benign/onset unknown |
| post_onset_status | หนึ่งในเจ็ดสถานะในหัวข้อ4 สำหรับแยก denominator/eligibility ให้ชัด |
| detection_delay | original delay เฉพาะมี post-onset opportunity; มิฉะนั้น None ไม่สร้าง delay จาก incomplete path |
| censor_query | 250 เฉพาะมี opportunity และ original evaluator มี complete no-alert censor; กรณีอื่น None |

Record ไม่ถือ mutable threshold/provenance metadata ว่าเป็น compatible calibrated record และ snapshot point container เป็น tuple แม้ caller ส่ง list ที่ existing evaluator อ่านได้ สมาชิกเป็น existing frozen Points ไม่ normalize/เปลี่ยน values คง raw scores, thresholds, provenance และ inputs เดิม

### Any-alert-by-Q250

1. **True** หากมี True ที่ scheduled checkpoint ใด แม้ records ไม่ครบ
2. **False** เฉพาะ required decisions ของ method ครบและทั้งหมด False
3. **None** เมื่อ incomplete และไม่เห็น True

ตัวอย่าง synthetic accounting: decisions=(None,True,False) → any_alert_by_q250=True และ first_observed_alert=200 แต่ first_alert_query=None / first_alert_exact=False เพราะยังไม่รู้ว่า look150แจ้งก่อนหรือไม่ Detection delay/censor/pre-attack inference ยังคง unknown ตาม existing incomplete semantics

หาก first alert ที่150รู้ exact แล้วแต่ look250หาย จะยังคง exact first-alert150และ observed event=True ส่วน delay/censor ยังคง None ตาม conservative original evaluator เพราะ recordไม่ complete ไม่เปลี่ยนนิยามนี้ใน Task05

## 4. Onset, missingness และ post-onset rules

| post_onset_status | Condition / accounting |
| --- | --- |
| not_applicable_benign | benign record; opportunity/delay/post-onset censor=None |
| onset_unknown | attack label แต่ไม่มี known onset; opportunity/delay/censor=None |
| no_scheduled_post_onset_opportunity | onset251..256; opportunity=False, delay/censor=None แม้ complete และไม่มี alert ไม่ใช่ evaluated attack miss |
| incomplete | known onset≤250 แต่ selected-method decisions ไม่ครบ; opportunity=True แต่ไม่สร้าง exact delay/censor observation |
| pre_attack_alarm | complete มี first alertก่อนonset; คง pre_attack_alarm=True, delay/censor=None ไม่เรียก attack detection |
| censored | complete known onset≤250 ไม่มี alert; censor_query250, delay=None |
| detected | complete first alert≥onset; คง original delay=first_alert−onset ไม่ backdate ภายใน window |

หาก onset251..256และมี alert ที่150/200/250 ให้คง any-alert/first-alert/pre-attack fields ตามเดิม แต่ post-onset statusยังเป็น no_scheduled_post_onset_opportunity ไม่ย้าย onsetมาที่250 ไม่เพิ่ม terminal window และไม่รายงาน delay/post-onset censor

Boundary checks ที่ทดสอบ:

- onset1 + alert150 → delay149, pre_attack_alarm=None ไม่มี guaranteed benign prefix
- onset250 + alert250 → delay0; onset250 + complete no alert → censor250
- onset251 หรือ256 → ไม่มี scheduled post-onset look; ไม่อยู่ใน evaluated post-onset misses

Missing/invalid/not_available/stale reasons คงจาก existing Aligned Points ไม่เติม0หรือ carry forward Incomplete no-alert eventเป็นNone แม้ไม่เห็น alertsเลย ห้ามใช้เป็น true negative หรือ exact censor observation

Standalone sequential_only อาจ complete แม้ MMD ขาดตาม behaviorเดิม: รายงาน complete=True, joint_complete=False และ eventที่สังเกตได้สำหรับ sequential_only ส่วน weighted/OR/AND ต้องการทั้งคู่จึง incomplete ข้อมูล primary paired comparisonยังต้องเลือก common-complete unitsตามprotocol ไม่ใช้ method-specific coverageต่างกันอ้าง improvement

เฉพาะ status **detected/censored** เป็น complete at-risk post-onset observations สำหรับ bookkeeping โดยยังต้องตรวจ joint_complete/outer-group/estimand ก่อนทำ research analysis ไม่มีตัวนับ evaluated misses หรือ scientific rates อัตโนมัติใน adapter

## 5. Tests ที่ execute และ observed results

ใช้ [test_hybrid_endpoint_adapter.py](tests/test_hybrid_endpoint_adapter.py) กับ synthetic numeric scores และ fixed synthetic calibrated metadata ไม่เรียก fit_normalizer/calibrate ใน testsใหม่ ไม่สร้าง research calibration/receipt artifacts Legacy regression testsที่มี numeric calibration fixturesยังเป็น software testsเดิม ไม่ใช่ scientific experiment

ลำดับที่สังเกตจริง:

1. รัน LegacyBehaviorTests **ก่อน adapter implementation**: 2ผ่านใน0.001s ยืนยัน Q256 censor และ unchanged horizon300
2. เพิ่ม failing endpoint testก่อนmodule: expected ImportError (1 error)
3. Implementationรอบแรก: 18ผ่านใน0.009s
4. เพิ่ม negative immutability testsก่อนแก้: พบ failuresจริงจาก mutable point-container alias และ mutable threshold/provenance metadata จากนั้นแก้เฉพาะadapterเพื่อคืน immutable reporting data
5. Required combined run ล่าสุดผ่าน **123 tests = Task05ใหม่20 + existing103**, failures/errors/skips=0; unittest runtime **8.564s** ไม่ใช่ detector/model latency benchmark (combined runก่อนเพิ่มprovenance guardผ่าน123เช่นกันที่5.492s)

คำสั่งที่ execute:

```powershell
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_hybrid_endpoint_adapter.LegacyBehaviorTests -v
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_hybrid_endpoint_adapter -v
conda run --no-capture-output -n senior python -B -m unittest stream_prada_order.tests.test_hybrid_endpoint_adapter stream_prada_order.tests.test_deep_kernel_mmd_exporter stream_prada_order.tests.test_cusum_curve_exporter stream_prada_order.tests.test_common_stream_producer stream_prada_order.tests.test_hybrid_integration stream_prada_order.tests.test_hybrid_fusion -q
```

| Required coverage | Verified behavior |
| --- | --- |
| No alert / endpoint | original256คงเดิม, adapter recorded256/evaluation250/censor250 |
| Exact alerts150/200/250 | current decisions, exact timing และ corresponding delays |
| Pre-attack / onset1/250/251/256 | prefix/null rules, delay0/149, no post-onset opportunityสำหรับlate onset |
| Missing/invalid/late/stale | reasonและunknown no-alert accountingคงเดิม ไม่เติมscore/decision |
| Observed alertหลัง earlier unavailable | missing/invalid/late150 + observed200ยังTrue แต่exact first timing unknown |
| Incomplete no alert | eventNone, no exact censor/delay observation |
| Wrong profile/schedule/compatibility | ทุกschedule field, points coverage, modelSpec, method และ onsetผิดถูกreject |
| Input/report preservation | raw points, decisions, threshold/provenance/receiptsไม่เปลี่ยน; frozen recordและtuple snapshot |
| Historical300 | existing no-alert300และterminal alert300คงเดิม; adapterไม่รับprofile300 |
| Existing regressions | Deep Kernel24 + CUSUM22 + common producer18 + integration17 + fusion22 =103ผ่านครบ |

## 6. Accounting readiness และ scientific blockers

**Accounting readiness: verified by synthetic software tests สำหรับ explicit profileนี้เท่านั้น** ไม่ได้แปลว่ามี authentic calibrated model, score exports หรือ independent traffic ที่พร้อมประเมินจริง

Task05ไม่ได้ตรวจรับ real artifacts เพิ่ม ข้อจำกัดที่รายงานใน Task02–04ยังต้องผ่าน handoff/reviewแยก:

- Authentic authorized common256 stream, exact request/text/physical embedding-row identities และ connected source/user/run grouping/chronology
- Saved per-query CUSUM curveกับ benign position-fit/source/config/availability evidence
- Actual frozen active Deep Kernel checkpoint, training/model-selection/scoring provenance, reference bank/draws และ exact window-score/availability evidence
- Independent benign fit/calibration/test unitsและ profile-specific frozen ECDF/stream-max thresholdsจริง ไม่ใช้metadata fixturesของtestsเป็นของจริง
- Length/format common support, paired coverage/outer-unit accounting, operating-point uncertainty และ statistical/power/multiplicity decisionsตามresearch protocol

ไม่อ้างว่า artifactsที่อื่นไม่มีอยู่ เพียงไม่มี authentic artifact acceptance หรือ scientific runในงานนี้ Scientific FPR/TPR/delay/superiority/generalizationยัง unmeasured ไม่ใช้123 passing testsเป็น scientific evidence

Protocolยัง DRAFT; Phase Fและhistorical Hybrid definitionsคงเดิม ไม่มี Q251–Q256 joint decisions, terminal windows หรือการเรียกผล Q250ว่า detection by Q256

## 7. Exact changed files และ Git workflow

เพิ่มเฉพาะ:

1. `stream_prada_order/hybrid_endpoint_adapter.py`
2. `stream_prada_order/tests/test_hybrid_endpoint_adapter.py`
3. `stream_prada_order/TASK_05_ENDPOINT_ADAPTER_REPORT_TH.md`

ตรวจ complete diff และ protected source/report/config/protocol hashes แล้ว **12/12 ตรงก่อนงาน** พร้อม exact changed/staged paths ก่อน commit ไม่แก้ detectors/exporters/hybrid_fusion.py/thresholds/historical results หรือ branch อื่น Stage สาม explicit paths ตามคำสั่งผู้ใช้ ตรวจ `git diff --cached --check` และ `git diff --cached --stat` ก่อนหนึ่ง local commit:

```powershell
git commit -m "fix: add endpoint-aware Q250 evaluation adapter"
```

Parent ต้องเป็น `5797d33b7155264d0b19258c0a803ac669d4856e` Actual commit SHA รายงานภายหลังในข้อความส่งมอบ ไม่เดา self-referential SHA ในรายงานนี้ Resolve commit ที่มีรายงานได้ด้วย:

```powershell
git log -1 --format=%H -- stream_prada_order/TASK_05_ENDPOINT_ADAPTER_REPORT_TH.md
```

หลัง commit ตรวจ branch/parent/SHA/file list/clean worktree แล้วหยุด ไม่ push/PR/merge/rebase/cherry-pick ผู้ใช้เป็นผู้ push และ sync fork
