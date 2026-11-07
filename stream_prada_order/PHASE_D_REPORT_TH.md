# Phase D — Sequential Detector Improvement Pilot

วันที่ 7 พฤศจิกายน 2026 | `experiment/stream-prada-order`

**ทำ bounded development pilot ครบ แต่ยังยืนยัน detector improvement ที่
matched population FPR ไม่ได้** CUSUM ฝั่งระยะลดลงมี detection สูงกว่า baseline
บน development cohorts นี้ที่ observed benign controls เท่ากัน 0/3 แต่ n เล็กมาก
และจุด 5% ไม่มี finite threshold ตามวิธี calibration ที่กำหนดไว้
Rolling บาง history ให้ TPR เพิ่มพร้อม FPR เพิ่ม จึงไม่ใช่หลักฐาน improvement

## แผนและขอบเขตที่กำหนดก่อนผล

อ่านรายงาน Phase A/B/C และ protocol Phase C ตามโจทย์ก่อนออกแบบ
รายละเอียดอยู่ใน [PHASE_D_DESIGN_TH.md](PHASE_D_DESIGN_TH.md) และ
[phase_d_config_v1.json](phase_d_config_v1.json)
เขียน SHA256 ของ design/config/implementation/tests ลง `preflight.json`
ก่อนอ่าน experimental traces และยืนยัน hash เดิมหลังรัน ไม่มี parameter search
หรือ winner selection หลังเห็นผล Thresholds ถูกบันทึกก่อน scoring validation

ใช้ **4 fit / 8 calibration / 3 validation cohorts** ที่ article-disjoint ตาม
certificate เดิม แต่เป็นข้อมูล reused ทั้งหมด ไม่ใช่ real independent API sessions
ใช้ validation permutations 0–9, attack 26/64/128, orderings R/C/I เดิม
รวม **285 input traces** และ **8,190 candidate/operating-point rows**
แต่ยังมีเพียง **3 outer validation cohorts** ไม่ใช่ 8,190 independent trials
ไม่อ่าน Phase C evaluation traces/scores cohorts 15–22 เพื่อประเมิน variants
การอ่านรายงานที่เคยเผยแพร่ไม่ได้ทำให้ Phase D เป็น blinded confirmation

ไม่เปลี่ยน `experiment.py`, PRADA, Deep Kernel MMD, Growing Set, BGE หรือ
config/results เก่า ใช้ frozen BGE-derived distances ของ Phase C โดยไม่ encode
ใหม่และไม่สร้าง matrix ใหม่ Cumulative W ที่ recompute จาก distances ทั้ง
285 traces ตรง saved W ทุกค่า: **maximum absolute error 0.0**
นี่คือ distance-to-W parity ไม่ใช่การรัน independent encoder parity รอบใหม่
upstream encoder/Growing Set parity อาศัยหลักฐานและ hashes ของ Phase C

Candidates 10 ตัว: Original cumulative Stream PRADA; Rolling W histories
32/64/100; CUSUM k=0.5/1.0 แต่ละค่ามี upper/lower/two-sided
ทุกตัวเริ่มทดสอบที่ Q102, horizon 256, benign prefix 110, onset Q111
Rolling ทำ three-sigma ภายใน trailing raw-distance window
CUSUM ใช้ position-wise mean/sample SD จาก fit cohorts 0–3 เท่านั้น
SD floor 0.01; state เริ่ม 0 ที่ Q102 และไม่ reset ที่ onset
สูตรทั้งสองทิศทางและ alternatives ระบุชัดใน design ไม่ใช้ attack labels ใน score

## Calibration และ matched operating points

Threshold มาจาก **maximum statistic ตลอด stream** ของ calibration 8 cohorts
รวม repeated looks; two-sided CUSUM ใช้ maximum ของทั้งสองทิศทางร่วมกัน
ไม่ threshold per-query p-values และไม่ใช้ textbook ARL แทน stream false alarm
Baseline algorithm คงเดิม แต่ recalibrate threshold บน Phase D calibration
เดียวกับ variants จึงไม่ควรเทียบตัวเลขนี้กับ Phase C threshold โดยตรง

| Nominal alpha | Rank ceil(9×(1−alpha)) | Threshold | Calibration exceedances ทุกตัว |
| --- | ---: | --- | --- |
| 0.05 | 9 | **+infinity; finite=false** | 0/8 |
| 0.20 | 8 | maximum ของ calibration scores | 0/8 |
| 0.40 | 6 | sixth smallest calibration score | 2/8 |

ใช้ strict score > threshold และไม่มี tail extrapolation ที่ alpha=0.05 ทุกตัว
จึง TPR/FPR=0 จากการไม่ alert ซึ่งเป็น **ข้อจำกัดความเป็นไปได้ของ useful
operating point** ไม่ใช่ detector ที่ตรวจได้และควบคุม FPR 5% สำเร็จ
ระดับ 20%/40% เป็น diagnostic ที่ประกาศไว้ก่อน ไม่ใช่ deployment target
ด้วย rank discreteness ถ้า exchangeability เป็นจริง bound ของ ranks 8/6 จะเป็น
1/9≈11.11% และ 3/9≈33.33% ซึ่ง conservative ต่อ nominal 20%/40%
สมมติฐานนี้ไม่ได้รับการยืนยันจาก reused article cohorts

สูตร finite-sample rank ใช้ marginal exchangeability ของ stream scores ตาม
[Angelopoulos & Bates](https://arxiv.org/abs/2107.07511) ไม่มี conditional-on-this-
calibration guarantee และไม่รองรับการเลือก winner จากหลายตัวแล้วคง guarantee

ทุก candidate เทียบที่ alpha/calibration/horizon เดียวกัน แต่ nominal alpha
ตรงกัน **ไม่พิสูจน์ population FPR ตรงกัน** จึงบันทึก validation control alarm
vector และ prefix alarms เทียบ baseline ไว้ทุก cell ไม่เลือก thresholds ให้
validation FPR ตรงย้อนหลัง แล้วเรียกว่า confirmation

## ผลหลัก ณ diagnostic alpha=0.20

แต่ละ TPR cell มี **3 cohorts × 10 schedules = 30**; R=random,
C=clustered, I=interleaved ตัวเลขคือ post-onset first detections/30
pre-attack alarm ทั้ง 10 candidates × 3 levels เป็น **0 ทุก mixed schedule**
ดังนั้นรอบนี้ all-schedule กับ eligible-at-onset denominator เท่ากัน

| Candidate | Benign FP | Attack 26: R/C/I | Attack 64: R/C/I | Attack 128: R/C/I |
| --- | --- | --- | --- | --- |
| Original | 0/3 | 0/1/0 | 1/1/0 | 11/21/13 |
| Rolling 32 | 0/3 | 0/4/0 | 1/7/1 | 12/17/12 |
| Rolling 64 | **1/3** | 0/5/1 | 2/16/2 | 21/21/23 |
| Rolling 100 | **1/3** | 0/2/1 | 2/9/3 | 22/24/24 |
| CUSUM upper k=0.5 | **1/3** | 3/6/1 | 0/10/0 | 0/0/0 |
| CUSUM lower k=0.5 | 0/3 | 0/0/0 | 19/21/17 | 23/25/23 |
| CUSUM two-sided k=0.5 | 0/3 | 0/0/0 | 19/21/17 | 23/25/23 |
| CUSUM upper k=1.0 | 0/3 | 1/4/1 | 0/7/0 | 0/0/0 |
| CUSUM lower k=1.0 | 0/3 | 0/3/1 | 14/23/16 | 23/25/22 |
| CUSUM two-sided k=1.0 | 0/3 | 0/3/1 | 14/23/16 | 23/25/22 |

Attack 26 = 10.15625%, 64 = 25%, 128 = 50% ของ stream 256
เช่น lower k=0.5 ที่ 25% ได้ **63.33%/70%/56.67%** เทียบ Original
**3.33%/3.33%/0%**; ที่ 50% ได้ **76.67%/83.33%/76.67%** เทียบ
**36.67%/70%/43.33%** โดย control vectors ทั้งคู่เป็น [false,false,false]
ยืนยันได้เพียง **within-development conditional gains** ไม่ใช่ confirmed
improvement ที่ matched true FPR เพราะยังมี uncertainty ของ calibration/FPR สูง
ที่ attack 26 lower k=0.5 ไม่ detect เลย จึงไม่ใช่ข้อได้เปรียบทุก attack ratio

Lower และ two-sided มี outcomes เหมือนกันในรอบนี้ และ thresholds เท่ากัน
ตาม `thresholds.json` จึงไม่ใช่ independent confirmations สองวิธี
Upper มี behavior ต่างและที่ 50% แทบไม่ตรวจพบ ไม่คัด direction ที่ให้ผลดีไป
รายงานอย่างเดียว ทิศทางของ distance เป็น design alternative ที่กำหนดก่อนผล
ตามแนวคิด [NIST CUSUM](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm)
ไม่ใช่หลักฐานเชิงเหตุว่า extraction ทุกชนิดทำให้ระยะลดลง

## FPR, uncertainty และผลที่ห้ามเรียก improvement

ณ alpha=0.20 Original/Rolling32/CUSUM lower และ two-sided รวมถึง upper k=1.0
มี FP 0/3; Rolling64/100 และ upper k=0.5 มี FP 1/3
ณ alpha=0.40 FP ของ Original ยัง 0/3 แต่ Rolling32/upper ทั้งสอง k/lower และ
two-sided k=1.0 เป็น 1/3; Rolling64/100/lower และ two-sided k=0.5 เป็น 2/3
TPR ที่สูงมากของ lower k=0.5 ที่ alpha=0.40 จึงแลกกับ observed FPR **66.67%**
เทียบ Original 0% ต้อง **ไม่** อ้าง improvement จากจุดนี้

| Benign FP / n | Exact two-sided 95% interval | One-sided 95% upper |
| --- | --- | --- |
| 0/3 | [0%, 70.76%] | 63.16% |
| 1/3 | [0.84%, 90.57%] | 86.46% |
| 2/3 | [9.43%, 99.16%] | 98.30% |

Intervals ถือ iid Bernoulli cohorts; source/topic dependence และ domain mismatch
ไม่ถูกแก้ด้วยสูตรนี้ Equal 0/3 ไม่เท่ากับรู้ true FPR หรือพิสูจน์ equivalence
Per-cohort conditional Monte Carlo Wilson intervals อยู่ใน `summary.json`
ไม่ใช้ 30 schedules เป็น n ของ population binomial interval
ไม่มี significance/novelty/generalization claim และไม่มีการเลือก winner

ความต่างระหว่าง cohorts ใหญ่: ที่ alpha=.20/25%/random, lower k=.5 detect
**9/10, 10/10, 0/10** ใน cohorts 12/13/14 ตามลำดับ แม้ค่าเฉลี่ย 63.33%
ที่ 50%/random เป็น **10/10, 10/10, 3/10**; ไม่ใช่ผลสม่ำเสมอทุก source
4 fit cohorts ต่อ position ยังน้อย และ SD/noise/format/source geometry อาจมีผล
สาเหตุเหล่านี้เป็น **สมมติฐาน** ยังไม่มี causal ablation รองรับ

## Delay และ order sensitivity

Delay = first alert query −111; หาก prefix alarm ให้ ineligible/null delay;
ไม่ detect ให้ right-censored ณ query 256; benign controls ไม่มี attack delay
รอบนี้ prefix alarms=0 จึงมี eligible 30 schedules ต่อ cell

| alpha=.20, attack 50% | Median delay R/C/I (detected only) | จำนวน detected R/C/I | Changed detection RC/RI/CI ต่อ 30 pairs |
| --- | --- | --- | --- |
| Original | 108 / 98 / 104 | 11 / 21 / 13 | 12 / 8 / 8 |
| Rolling32 | 62 / 93 / 70 | 12 / 17 / 12 | 11 / 10 / 11 |
| CUSUM lower k=.5 | 56 / 56 / 59 | 23 / 25 / 23 | 2 / 2 / 2 |
| CUSUM lower k=1 | 49 / 43 / 46 | 23 / 25 / 22 | 2 / 3 / 3 |

ตัวอย่าง Original random มี 19/30 censored; lower k=.5 random มี 7/30
censored; medians มาจากคนละ detected subsets จึงยังไม่ใช่ unconditional
time-to-detection superiority การลด order disagreement เป็น conditional result
ของ schedules/cohorts นี้ ไม่ใช่ order invariance ที่พิสูจน์ทั่วไป
ทุก candidate/ratio/level/order มี metrics และ censor counts ใน `summary.json`
ตารางครบที่ [PHASE_D_TABLES.md](diagnostics/phase_d_verified/PHASE_D_TABLES.md)

## Execution, failed attempt และ audit

Design/config มีอยู่ก่อน scoring และ resource requirements รายงานก่อนรัน
preflight numeric fixture projection รวม safety factor 2 = **25.389 s**
เทียบ budget **120 s**; available RAM ≈37.36 GiB ผ่าน gate; ไม่ใช้ GPU/network
Successful v2 ใช้ **19.149 s**, peak process working set **145.02 MiB**
ใช้ BGE encoder **0 ครั้ง**, rerun upstream detector **0 ครั้ง**
มี recompute cumulative W เพื่อ parity และประเมิน sequential statistics ใหม่

Attempt v1 หยุดใน **2.127 s** ก่อน fit/calibration/validation scoring เพราะ
verifier เทียบ Git LF กับ checkout CRLF เป็น raw bytes ตรวจแล้วเนื้อหาตรงและ
raw hash ตรง historical experiment จึงแก้ verifier เท่านั้น พร้อม regression
test บังคับ exact historical hash และ normalized Git content ต้องผ่านทั้งคู่
ไม่แก้ PRADA ไม่เปลี่ยน candidates/threshold recipe/config เก็บ failed metadata,
preflight และ frozen source ของ v1 แยกจาก v2 ไม่ overwrite failed evidence

Tests รวม **52 ผ่าน** (เดิม 36 + sequential/provenance 15 + audit corruption 1)
ครอบคลุม causal rolling window, CUSUM direction/reset, fit/floor, infinity/ties,
prefix ineligibility/onset delay/censoring, prohibited evaluation cohorts,
benign semantics และ corrupted evidence rejection

Published-input audit ใช้ **11.575 s** ทำซ้ำ calibration scores 80 ค่า และ
candidate/operating-point rows **8,190 แถว** จาก numeric traces 285 ชุด
ตรวจ fit parameters, thresholds/rank, first crossings, maxima, risk accounting,
summary/pair metrics และ hashes ผ่าน โดยไม่ encode/rerun original detector
กราฟสองภาพตรวจ layout ด้วยสายตาแล้ว Original sources/config/results และ main
คงเดิม ไม่ push/merge/rebase/PR

## ไฟล์และวิธีทำซ้ำ

- [Design และ feasibility](PHASE_D_DESIGN_TH.md)
- [Implementation แยกจาก baseline](phase_d_pilot.py)
- [Saved-result audit](phase_d_audit.py)
- [FPR/TPR comparison plot](results/phase_d_pilot_20261107_v2/phase_d_comparison.png)
- [Per-cohort variability plot](diagnostics/phase_d_verified/phase_d_cohort_variability.png)
- `results/phase_d_pilot_20261107_v2/`: selected numeric traces (~634 KB gzip),
  distance fit, thresholds, compressed per-stream table, summary, preflight,
  parity, input/source hashes, timing/memory และ artifact manifest

ไม่มี raw queries, weights, embeddings หรือ caches ใน commit
Audit ใช้เฉพาะ published artifacts และ frozen source ไม่ต้องมี full local logs:

```powershell
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests -v
conda run --no-capture-output -n senior python stream_prada_order/phase_d_audit.py stream_prada_order/results/phase_d_pilot_20261107_v2 --output stream_prada_order/diagnostics/new_phase_d_audit
```

หากจำเป็นต้องรัน pilot ใหม่ ใช้ output directory ใหม่และ full local calibration/
validation logs ของ Phase C ที่ hash ตรง metadata โดยระบุ budget ก่อนเริ่ม:

```powershell
conda run --no-capture-output -n senior python stream_prada_order/phase_d_pilot.py --output stream_prada_order/results/new_phase_d_attempt
```

## คำตัดสินและข้อเสนองานถัดไป

**ยืนยัน:** variants ทำงานตาม frozen design, upstream W parity ตรง,
มี within-development gains ของ lower-distance CUSUM ณ diagnostic operating
level พร้อม observed control vector ตรง baseline; Rolling หลายจุดมี FPR trade-off;
5% useful operating point ยังทำไม่ได้ด้วย calibration n=8 ตาม rank recipe นี้

**ยังไม่ยืนยัน:** improvement ที่ matched population FPR, generalization,
causal mechanism, unconditional delay benefit, robustness ต่อ sources/traffic
ใหม่ หรือ novelty ไม่แต่งตั้ง candidate ที่ดีที่สุดจากข้อมูล reused นี้

ถ้าจะทำขั้นถัดไป ต้องกำหนด candidate family และ source/session sampling
จาก evidence นี้อย่างเปิดเผยแล้ว freeze ใหม่ก่อนข้อมูล fresh; แยก nuisance fit,
calibration, validation selection และ untouched final test พร้อม control
statistic/horizon/prefix/membership เท่ากัน และถือ source cohorts เป็น outer units
finite threshold ที่ 5% ต้องมี calibration อย่างน้อย **19** cohorts เพิ่มจาก
fit set (เพียง resolution ขั้นต่ำ ไม่ใช่ tail precision ที่เพียงพอ)
หากคง 4 fit +19 calibration +3 validation จะต้อง 26 cohorts ซึ่งเกิน article
capacity 23 เดิมอยู่แล้ว และ final zero-FP claim ที่ one-sided upper≤5% ต้องมี
อย่างน้อย **59** independent benign test cohorts ภายใต้ iid assumptions
จึงต้องแก้ data/provenance bottleneck ก่อน confirmatory study ไม่เพิ่ม permutations
เพื่อแทน cohorts และไม่เริ่ม dataset acquisition/experiment ใหม่อัตโนมัติ
