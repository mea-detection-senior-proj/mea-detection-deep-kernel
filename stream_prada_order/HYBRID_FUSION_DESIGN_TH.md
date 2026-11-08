# Offline Hybrid Fusion Prototype — Design

8 พฤศจิกายน 2026 | `experiment/stream-prada-order` | base `60490a7a8f8f2db42f1bcaaba3d3965f33c78c41`

**GO: isolated software prototype/tests; NO-GO: scientific performance claims หรือ same-stream experiment จน prerequisites ครบ**
ไม่ต้องใช้ Qwen หรือเปิด Phase K gate งานนี้ไม่รัน detector, encoder, inference, extraction, student/kernel training,
data acquisition หรืออ่าน private traffic และไม่แก้ PRADA/CUSUM/Deep Kernel/MMD/pilot/results เดิม

อ่าน Phase D/E reports, Phase F protocol, pilot README และ deep_kernel_pilot.py ก่อนออกแบบ
Phase E ยืนยัน length/format confounding และมีเพียง 3 outer development cohorts จึงไม่ใช้ผลเหล่านั้นเลือก fusion weights
ไฟล์ [config v1](hybrid_fusion_config_v1.json) ถูกสร้างก่อน implementation/test outcomes:
weights=.5/.5, alpha=.05, horizon300/window100/stride50/first eligible102 ไม่ทำ parameter search
ตัวอย่าง horizon300 นี้เป็น **software schedule ตามโจทย์** ไม่แก้ Phase F primary horizon256/online schedule

## Interface และการผูก provenance

Module [hybrid_fusion.py](hybrid_fusion.py) ใช้ Python standard library และ frozen dataclasses เท่านั้น
ไม่มีการ import หรือเรียก detector/model ของทีม และไม่มี infer/train/download entry point

| Type | ข้อมูล |
| --- | --- |
| Context | dataset revision, embedding revision, query-view/preprocessing revision, victim revision |
| Stream | session_id, SHA256 ของ ordered query manifest, outer connected group, split, manifest label, Context |
| DetectorRevision | detector source revision, detector model/weights revision, configuration revision, calibration/fit provenance |
| Score (`hybrid-score-v1`) | Stream+DetectorRevision, inclusive start/end, available_at, computed_through, value, valid, orientation |
| Spec | expected Context, expected sequential/MMD revisions แยกกัน, schedule และ weight |
| Aligned / Point | checkpoint query index, component values/validity และ missing/stale/invalid/not_available reason |
| Calibrated | frozen benign ECDF fit, independent calibration units, thresholds/ranks, provenance fingerprints |
| Result | decisions ต่อ checkpoint, first observed/exact alert query, completeness, onset/pre-attack/delay/censor metadata |

indices เริ่ม1 ทั้งหมด: sequential start=end=query index; MMD start/end เป็น actual contiguous window
computed_through ต้องเท่ากับ end และ available_at≥end หาก producer ใช้ข้อมูลอนาคตต้อง reject ไม่ backdate
valid=true ต้องเป็น finite Python int/float; invalid ต้อง value=null ไม่แทนด้วย0/NaN
orientation ต้อง higher_is_more_anomalous: PRADA export=-W, CUSUM export=positive statistic,
MMD export=raw signed MMD (unbiased estimate อาจติดลบได้) โดยบันทึก sign transform ใน config revision

ทั้งสอง detector ต้องอ้าง **Stream object เดียวกันทุก field** รวม session/order digest/context
expected source/model/config/calibration stamps ของแต่ละ detector ต้องตรง Spec; ไม่บังคับให้ detector สองชนิดมี weights เหมือนกัน
คนละ session/dataset/query view/embeddings/victim/kernel checkpoint หรือ calibration version ไม่ผ่านโดยเงียบ ๆ
IDs เป็น binding declarations ไม่ใช่หลักฐานว่า source/session เป็นอิสระหรือ exporter ซื่อสัตย์ ต้องมี content/provenance audit ภายนอก
ใช้ align() สร้าง Aligned จาก validated Score records ไม่ใช้การสร้าง Point/Aligned เองเพื่อข้าม input contract

## Causal alignment และ availability

MMD windows บน grid: [1,100], [51,150], [101,200], [151,250], [201,300]
Q100 ยังไม่ผ่าน Original PRADA warm-up จึงไม่ใช่ joint checkpoint

| Joint checkpoint | Sequential score | MMD inclusive window | Query budget สูงสุด |
| --- | --- | --- | --- |
|150|Q150|51–150|150|
|200|Q200|101–200|200|
|250|Q250|151–250|250|
|300|Q300|201–300|300|

ใช้ sequential score **ตรง t** ไม่ใช้ maximum จาก t+1 เป็นต้นไป หรือ latch สัญญาณระหว่าง looks
นี่เป็น checkpoint-only baseline ablation ไม่ใช่การอ้างว่าเหมือน Original PRADA ที่ monitor ทุก query
ทุก method ใน primary prototype มีเพียง4 decision opportunities และ calibration ใช้4 looks เดียวกัน
MMD มี frozen reference bank จาก fit เท่านั้น ต้องไม่ใช้ future test queries/labels เป็น reference หรือเลือก reference ย้อนหลัง

- Missing: ไม่มี score ที่จบตรง t → abstain; ถ้ามีเพียง window เก่าที่พร้อมแล้วให้ reason=stale
- Stale: **ไม่ carry forward**, ไม่ reuse Q100 ที่ Q150, ไม่ interpolate หรือเติม0
- Invalid: exact window จบตรง t แต่ invalid → abstain ไม่ fallback หา window ก่อนหน้า
- Not available: score อ้าง end=t แต่ available_at>t → ใช้ที่ t ไม่ได้ และไม่ backdate หลังได้รับ
- Sequential baseline ต้องการเฉพาะ sequential valid; MMD baseline ต้องการเฉพาะ MMD valid
  OR/AND/weighted ต้องมี **ทั้งคู่ valid** แม้ OR จะอนุมาน true จากด้านเดียวได้ เราเลือก complete-pair policy ไว้ก่อน
  ต้องรายงาน joint coverage และเปรียบเทียบ primary effects บน common-complete streams ไม่ใช้ availability ต่างกันอ้าง improvement

available_at เป็น query-position availability ไม่ใช่ UTC/latency; ไม่มี wall-clock timestamps ให้รายงานจาก score fixture
ถ้าไม่มี completed checkpoint เช่น horizon100 จะไม่ผ่าน fit/calibration/evaluation coverage ไม่ถือเป็น true negative

## Five fixed fusion baselines

ให้ u=F_seq(score), v=F_MMD(score) เป็น right-continuous smoothed ECDF จาก **benign fit split เท่านั้น**:
`F(x)=(1 + number of fit checkpoint scores <= x)/(m+1)`
ใช้ pooled checkpoints จาก complete equal-length fit streams เป็น deterministic transform ไม่ใช้ m เป็นจำนวน independent streams
ค่าใน [1/(m+1),1] มี ties/saturation; ไม่ใช่ per-query p-value หรือ distribution-free alarm probability
ไม่ refit จาก calibration/validation/final outcomes

| Method | Statistic ณ checkpoint | Decision |
| --- | --- | --- |
|sequential_only|u|u>h_seq|
|mmd_only|v|v>h_mmd|
|or|max(u,v)|(u>h_or) OR (v>h_or)|
|and|min(u,v)|(u>h_and) AND (v>h_and)|
|weighted|.5u+.5v|weighted>h_weighted|

OR/AND ใช้ **joint-calibrated shared cutoff บน normalized scale** ไม่จำเป็นต้องเท่ากับ standalone component cutoffs
AND หมายถึงสองด้านข้าม ณ **checkpoint เดียวกัน** ไม่ใช่เคยข้ามคนละเวลาแล้วนำมา AND
calibrate max_t min(u_t,v_t), ไม่ใช่ min(max_t u_t,max_t v_t)
decision_fusion() เป็น Boolean primitive ที่แยกใช้ได้ แต่ OR/AND ของ independently calibrated decisions ไม่มี automatic combined-FPR guarantee
ไม่บวก raw CUSUM กับ raw MMD และไม่กล่าวว่า rank normalization ทำให้ two scores เป็น independent

## Joint stream-level calibration

1. Freeze detector/kernel training/nuisance fits, reference bank, context/revisions, score direction, schedule, weights และ alpha ก่อน evaluation
2. Fit ECDF บน benign fit streams ที่ครบทุก joint checkpoint; MMD training/epoch selection ต้องเสร็จและแยกจาก calibration/final
3. ใช้ benign calibration streams ที่ outer groups/session IDs/ordered-stream digests ไม่ทับ fit
   ต่อ method คำนวณ `M_i=max_t statistic_i(t)` เหนือ **ทุก4 looks**; overlap ระหว่าง windows ไม่ได้เพิ่ม n
4. n=จำนวน declared independent outer calibration streams, k=ceil((n+1)(1−alpha)); strict `score>kth ordered maximum`
   ถ้า k>n เก็บ threshold.value=null หมายถึง +infinity/no-alert ไม่มี tail extrapolation
5. Reject calibration stream ที่ขาด/invalid checkpoint ไม่ silently discard แล้วเปลี่ยน deployment eligibility
   ถ้ามี missingness ในจริงต้องประกาศ quality/coverage policy ใหม่ก่อน final และ calibrate ตาม estimand นั้น
6. Freeze Calibrated object และ receipt() ก่อน validation/final; eval ปฏิเสธ fit/calibration group/session/stream reuse
   ห้ามเลือก best method/weight/threshold จาก final outcomes; alphaเดียวกันไม่พิสูจน์ actual population FPR เท่ากัน

ที่ alpha=.05 ต้อง n≥19 จึงมี finite rank **เท่านั้น** ไม่รับรองว่า threshold ใช้ตรวจได้หรือ tail precision เพียงพอ
ECDF saturation อาจทำให้แม้ finite threshold ก็ไม่มีคะแนนใหม่ข้าม โดยเฉพาะ fit น้อย/มี ties ต้องรายงาน negative finding
หาก n100 ตาม Phase F: k96; ภายใต้ exchangeability ของ outer streams bound=5/101 ไม่ใช่ conditional guarantee บน calibration ชุดนี้
group IDs ที่ไม่ซ้ำไม่พิสูจน์ exchangeability; source/topic/user dependence และ source shift ยังต้อง audit
การลอง5methodsแล้วเลือก winner ยังต้อง multiplicity/selection protocol แยก ไม่ใช้ guarantee ของแต่ละ method แทน

## First alert, delay และ false alarms

first_observed_alert คือ earliest true ที่สังเกตได้; first_alert_query จะเป็น null ถ้ามี unknown checkpoint ก่อนหน้านั้น
first_alert_exact ระบุว่า earliest crossing รู้แน่หรือไม่; complete ระบุ coverage **ทั้ง horizon**
เมื่อ incomplete จะไม่สร้าง delay/censor/pre-attack inference จากข้อมูลขาด แม้มี observed alert อยู่
complete attack streams: alertก่อน known onset เป็น pre-attack/ineligible, delay=null; หลัง onset delay=alert−onset
ไม่มี alert ให้ right-censor ที่ horizon ไม่ใส่ delay=0; onset1 ไม่มี genuine prefix จึง pre_attack_alarm=null
checkpoint discretization เพิ่ม delay ได้ถึงช่วง stride; ห้าม backdate alert ไปจุดใดภายใน MMD window
ไม่ได้ interpolate onset/warm-up และไม่อ้างเป็น UTC delay

false_alarm_counts() รับเฉพาะ benign controls ของ method/calibrationเดียวกัน
นับ any alert ตลอด horizon **ครั้งเดียวต่อ stream**; reject repeated outer groups/session IDs/stream digests
รายงาน total, complete, incomplete, observed alarms รวม incomplete และ conditional_complete_stream_fpr แยก
หากไม่มี complete stream FPR=null; ห้ามเรียก conditional complete-case rate เป็น unconditional population FPR
reorderings ต้องทำ paired within-group analysis แยก ไม่ส่ง permutations เข้า binomial n

## Integration และ prerequisites ของ fair experiment

รายละเอียดส่งต่อทีมอยู่ [HYBRID_MMD_CONTRACT_TH.md](HYBRID_MMD_CONTRACT_TH.md)
pilot scores.csv ปัจจุบันมี method/split/window_id/score/threshold/detected แต่ไม่มี native session/order/window/query bounds/availability
และสุ่ม reference/windows จาก pools จึง **ไม่ใช่ same-stream input** สำหรับ prototype นี้
Phase D/E traces horizon256 และ pilot random windows ไม่ถูก join/แต่ง chronology/extend เป็น300
ไม่รัน re-embedding หรือ MMD เพื่อเติมข้อมูลในงานนี้

ก่อนทดลองต้องมี: actual common streams และ chronology/content hashes; source/user/run outer-group certificate;
matched legitimate long-context/short/repetitive benign และ multiple verified extraction families ที่แก้ Phase E confounding;
fit/benign-calibration/validation/untouched-final splits แยกตาม Phase F พร้อม sufficient native lengths/quotas;
same frozen BGE/query view/normalization/token limits และ victim condition; faithful MMD reference/kernel export;
identical schedule/horizon/membership, independent calibration ที่เพียงพอ, coverage/control vectors และ paired FPR uncertainty;
length-only/non-sequential controls, predeclared superiority/noninferiority/multiplicity plan หรือจำกัดเพียง effect estimates;
request/reference/embedding/compute budgets แยกและ operator authorization/resource gate ใหม่ถ้าต้อง execute detector/data work
equal prefix query budget ไม่เท่ากับ equal active memory/reference/compute budget ต้องเปิดเผยความต่าง

ไม่มี real fused sessions ให้ประเมินในงานนี้: scientific FPR/TPR/delay/generalization/novelty **ยัง unmeasured**
ผลทดสอบ numeric fixtures ไม่ใช่หลักฐาน detection performance หรือ improvement
