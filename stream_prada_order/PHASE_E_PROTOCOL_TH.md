# Phase E — frozen shortcut/robustness diagnostic design

วันที่ 7 พฤศจิกายน 2026; branch `experiment/stream-prada-order`
อ่าน REPORT_TH.md/REPORT_PREFLIGHT_TH.md, FAILURE_ANALYSIS_TH.md,
PHASE_B_FEASIBILITY_TH.md, PHASE_C_REPORT_TH.md และ PHASE_D_REPORT_TH.md ก่อนแผน
นี้ ทุกผล C/D เป็น development evidence ไม่มี untouched test ในงานนี้

## Scope และ freeze

ใช้ 285 saved traces เดิมของ Phase D: fit cohorts 0–3, calibration 4–11,
development 12–14, permutations 0–9, attack 26/64/128, prefix 110, horizon 256
ไม่เปิด Phase C evaluation outcomes 15–22 ไม่เพิ่ม queries/schedules/embeddings
อ่าน processed query text และ official SQuAD lookup เดิมแบบ read-only เพื่อ
สร้าง numeric length/format metadata และ article identities เท่านั้น
ไม่แก้ raw queries ไม่ strip context แล้ว re-encode ไม่ resample ให้ length matched
หาก common support ไม่พอให้รายงาน blocker ไม่สร้าง controls ทดแทน

ก่อนอ่านข้อมูลจริง เขียน source/config/protocol/test hashes ลง preflight.json
และ resource estimate CPU-only คาด 5–40 s, hard gate **120 s**, RAM เพิ่มคาด
<=512 MiB, available RAM >=1 GiB ไม่ใช้ network/GPU ใน runner ไม่ overwrite runs
numeric benchmark 5 all-candidate paths, projection elapsed+2×P95×285 ต้องผ่าน
deadline ตรวจระหว่าง traces; resource gate failure ห้ามขยายอัตโนมัติ

## Metadata, upstream state และ associations

- words=`len(text.split())`, chars=`len(text)`, log length=`log1p(words)`
  ไม่เรียก whitespace words ว่า BGE token count ไม่วัด truncation causal effect
- format flag ใช้ exact processed context wrapper ตาม parser เดิม ไม่ใช้ flag
  ใน detector เป็นเพียง label/format confounding audit; ไม่มี raw text ใน Git
- เชื่อม query hashes กับ article title จาก official lookup ที่ hash ตรงเดิม
  แสดง source metadata ได้ แต่ไม่ใส่ raw questions/context
- ดึง Growing Set membership/thresholds ของ selected 285 traces จาก hashed
  Phase C calibration/validation logs เท่านั้น ไม่อ่าน evaluation log
  reconstruct admission/count/threshold จาก saved minimum distances ให้ตรง
  ไม่ compute BGE, cdist หรือ nearest-neighbor ใหม่ จึงไม่ใช่ causal intervention
- รายงาน per-stream descriptive Spearman length-distance/length-score/growth
  และ per-cohort/label mean distances/admission rates ไม่ใช้ query-level p-values
  หรือ pooled permutation sample size อ้าง population evidence
- Length distribution ใช้ unique query reservoir ไม่ใช้ query ซ้ำข้าม schedules
  Fixed word bins [0,8,16,32,64,128,256,infinity]; count overlap capacities
  ตาม cohort และ same-article sources โดยไม่ re-encode/reconstruct streams

## Candidates ที่กำหนดไว้ล่วงหน้า: 17 ตัว ไม่มี winner selection

1. Original Stream PRADA saved W เดิม (Q102–256)
2. Lower-distance CUSUM k=0.5 และ 1.0 จาก Phase D ทั้งคู่ ไม่เลือก k จากผล E
3. Length-only negative control: endpoint mean(log1p(words)) ทั้ง 256 queries
   ใช้ Q256 เท่านั้น; ไม่ใช้ embeddings, distances, labels หรือ article IDs
4. Non-sequential distance-statistic: endpoint **negative mean(raw minimum
   distances Q102–256)**; ไม่ใช่ CUSUM ไม่มี recursive change statistic
   เป็น bag statistic ของ distances ที่ upstream state ขึ้นกับลำดับอยู่แล้ว
   จึงไม่อ้าง query-order invariance แม้ aggregation invariant ต่อ reorder values
   Endpoint controls ไม่ใช่ early detectors; detection delay ถ้า detect=145
5. Length-aware lower CUSUM สอง k: fit common slope beta ของ distance ต่อ
   log length หลัง demeaning ทั้งสองตัวแปรตาม query position จาก benign fit
   cohorts 0–3 เท่านั้น (4×255 rows ไม่ใช่ 1,020 independent sources)
   `beta=sum((u-u_mean_t)*(d-d_mean_t))/sum((u-u_mean_t)^2)`
   predictor length ถูก clip ที่ global min/max ของ fit benign lengths
   residual distance=`d-beta*(clipped_u-u_mean_t)`
   residual sigma_t=sample SD across 4 fit cohorts, floor0.01; mean_t เดิม
   CUSUM บน residual z; coefficient/calibration ไม่แตะ development labels
   การ clip ป้องกัน unbounded extrapolation แต่ **ไม่แก้ lack of common support**
6. Prefix-centered source-aware lower CUSUM สอง k: ใช้ z จาก Phase D ลบ
   mean z ของ Q2–101 (100 distances, benign burn-in ที่ใช้ได้ก่อน first test)
   ตลอด stream ไม่ refit article fixed effects จาก development labels
   เป็น control ระดับ source/initial geometry ไม่ใช่การลบทุก topic effect
7. Combined length-aware + prefix-centered lower CUSUM สอง k
8. Fixed-distance bag-preserving order controls: lower CUSUM สอง k × suffix
   transformations reverse, shuffle seed17, shuffle seed29 =6 ตัว
   เก็บ z ของ Q2–110 แล้วเปลี่ยนลำดับ z ของ Q111–256 เท่านั้น
   apply same transformation/threshold calibration recipe ให้ benign ด้วย
   นี่เป็น offline score-path surrogate ใช้ future distances จึงไม่ deployable
   ไม่เรียก surrogate steps ว่า real detection delay และไม่อ้างว่าเป็น
   counterfactual query ordering เพราะ Growing Set/distances ไม่ถูก compute ใหม่

Original/lower CUSUM parity ต้องตรง Phase D ทุก row ภายใต้ thresholds เดิม
Length/source controls เปลี่ยน experimental statistics แยกชื่อและ calibrate ใหม่
ไม่เปลี่ยน upstream baseline และไม่อ้าง causal mechanism จาก residualization

## Calibration และ interpretation gates

ทุก candidate ใช้ 8 calibration stream maxima (endpoint หนึ่ง look สำหรับ
endpoint controls), rank ceil(9×(1-alpha)), strict crossing, augmented infinity
alpha=.05/.20/.40 เดิม ไม่มี retuning จาก validation/evaluation
Freeze fit/thresholds ก่อน development scoring ไม่มีเลือก detector ที่ดีที่สุด
5% ต้องเป็น infinity จาก n=8; 20/40% เป็น diagnostic ไม่ใช่ deployment target
รายงาน actual FPR/95% exact intervals/control vectors และ prefix alarms ทุกตัว
equal nominal alpha ไม่ใช่ matched population FPR; equal 0/3 เป็นแค่ empirical
screen การได้ TPR สูงขึ้นพร้อม FPR สูงขึ้นไม่ใช่ improvement

Metrics: detected/all และ detected/eligible, any alarm, prefix false alarm,
delay เฉพาะ original-time paths, right censoring, per-cohort rates, paired
order disagreements และ leave-one-development-cohort-out descriptive averages
ใช้ threshold เดิมทุก leave-out ไม่มี refit/selection; ไม่ถือ n=2 result เป็น test
รายงาน source titles/within-article B/A contrasts: same article ไม่ลบ format
หรือ length confound; ไม่ทำ article classifier โดยใช้ development outcome

หาก length-only control แยก labels ได้ดี หรือ distance bag controls detect ได้
โดยไม่ใช้ CUSUM จะลดหลักฐานความจำเป็นของ sequential attack mechanism
แต่ไม่พิสูจน์ว่า CUSUM ใช้ length อย่างเดียว (CUSUM ไม่รับ text length โดยตรง)
หาก gains คงอยู่หลัง capped length/prefix correction ก็ยังไม่พิสูจน์ meaningful
extraction behavior เพราะ residual source/format confounds/positivity อาจคงอยู่
หาก order surrogates เปลี่ยนผล แปลว่าสถิติไวต่อ order บน fixed distance bag
ไม่ใช่ proof ว่าไวต่อ adaptive extraction แทน geometry และ bag composition

## Deliverables และ stop

PHASE_E_REPORT_TH.md, reproducible scripts/tests, numeric features/growth paths,
fit/threshold/metric tables, plots, new-data provenance/access/license assessment
และ recommended next protocol แยกจากการเก็บข้อมูล/รัน experiment จริง
เก็บ negative findings และ blocked attempts ไม่มี raw text/weights/embeddings
ไม่ดาวน์โหลด corpus ใหม่ ไม่เรียก victim API/training ไม่เปิด final test
จบ local result commit แล้วหยุด ไม่ push/merge/rebase/PR/main changes
