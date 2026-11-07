# Phase D — Sequential Detector Improvement Pilot: แผนก่อนประเมิน

วันที่ 7 พฤศจิกายน 2026; branch `experiment/stream-prada-order`

อ่าน PHASE_C_REPORT_TH.md, PHASE_C_PROTOCOL_V1.md,
PHASE_B_FEASIBILITY_TH.md และ FAILURE_ANALYSIS_TH.md ก่อนกำหนดแผนนี้
คำตัดสิน: **ทำได้เฉพาะ development pilot; ยังทดสอบ improvement ที่ FPR 5%
อย่างมีพลังทางสถิติไม่ได้** ไม่มีข้อมูล untouched สำหรับ final confirmation

## ข้อมูลและความเป็นไปได้

ใช้ distance/W traces ที่บันทึกจาก frozen BGE ของ Phase C เท่านั้น ไม่ encode
หรือสร้าง distance/Growing Set ใหม่ และไม่แก้ Original Stream PRADA
ใช้ cohorts 0–3 fit nuisance, 4–11 calibration, 12–14 validation/development
ไม่อ่าน traces/scores ของ Phase C evaluation cohorts 15–22 เพื่อทดสอบ variants
การอ่านรายงานเดิมตามโจทย์ไม่ได้ทำให้ outcomes ที่เห็นแล้วกลับเป็น unseen
พารามิเตอร์ด้านล่างมาจาก grid ขนาดเล็กที่ประกาศไว้ ไม่เลือกจาก evaluation TPR

Article-disjoint ตาม certificate เดิม แต่ทุก article เคยใช้ในงานก่อนหน้า
และ source disjointness ไม่รับรอง independent sessions/topics ประชากรจริง
มีเพียง 4 fit, 8 calibration, **3 validation outer cohorts**; permutations
ไม่เพิ่ม outer n ใช้ 10 permutations แรก (0–9) ของ Phase C validation schedule
รวม mixed 270 streams + benign controls 3 + calibration/fit 12 = 285 inputs
Shared prefix 110, onset 111, horizon 256, attack 26/64/128, three orderings
และ frozen seed/membership/order เดิมทุกประการ ไม่คัด prefix หลังเห็นคะแนน

## Candidates ที่กำหนดล่วงหน้า (10 ตัว ไม่มี winner selection)

ทุกตัวใช้ distances จาก minimum-to-Growing-Set เดิม ดังนั้นไม่ใช่การแก้
upstream representation/state; ทดสอบตั้งแต่ query 102 ถึง 256 เท่ากัน

1. **Original Stream PRADA**: W history/three-sigma/warm-up เดิม ใช้ saved
   cumulative W โดยไม่เปลี่ยน algorithm ตั้ง threshold ใหม่ตาม calibration
   ของ Phase D เพื่อเทียบ operating recipe เดียวกัน ไม่ใช้ threshold Phase C
2. **Rolling Shapiro–Wilk L=32,64,100**: ที่ query t ใช้ raw distances ล่าสุด
   L ค่า รวม current distance; three-sigma ภายใน window ด้วย function เดิม
   แล้วคำนวณ W ใช้ score `1-W` ไม่ใช้ per-query p-value; ไม่มี future values
   หาก sample ไม่พอ/constant/nonfinite ให้ hard fail ไม่สร้าง W ทดแทน
3. **Distance CUSUM k=0.5,1.0**, แต่ละ k มี upper/lower/two-sided:
   fit `mu_t=mean(d_t)` และ `sigma_t=max(sample_std(d_t,ddof=1),0.01)`
   จาก fit benign cohorts 0–3 ตาม query position t=2..256 เท่านั้น
   Position conditioning ลดการสมมติ mean คงที่ระหว่าง Growing Set โต
   แต่ n=4 ต่อ position noisy มาก และไม่มีการรับรอง stationarity/normality
   `z_t=(d_t-mu_t)/sigma_t`; เริ่ม state 0 ก่อน query 102 แล้วอัปเดต
   `S+_t=max(0,S+_(t-1)+z_t-k)` และ
   `S-_t=max(0,S-_(t-1)-z_t-k)`
   Upper score=S+, alternative ระยะสูงกว่ารูปแบบ benign;
   lower score=S-, alternative ระยะต่ำกว่า; two-sided=max(S+,S-)
   ไม่ reset ที่ attack onset ไม่ใช้ label/onset ใน statistic ไม่มี head start
   k สอดคล้อง design shifts 1 หรือ 2 standardized units ตาม heuristic k=delta/2
   แต่ไม่ใช้ textbook h/ARL เพื่ออ้าง stream FPR ของ distances ที่ dependent

ใช้ stream score = maximum statistic ตลอด eligible queries สำหรับทุกตัว
จึง calibrate เหตุการณ์ **any alarm ภายใน horizon** รวม repeated looks และ
ทั้งสองทิศทางของ two-sided ด้วยกัน ไม่ calibrate query p-values แยกกัน

## Operating points และข้อจำกัด calibration

ใช้ 8 calibration stream maxima ต่อ candidate กำหนด rank
`r=ceil((n+1)*(1-alpha))`; threshold เป็น r-th smallest ถ้า r<=n
ไม่เช่นนั้นเป็น +infinity (บันทึก JSON เป็น null พร้อม finite=false)
ใช้ strict score > threshold; ties conservative ไม่ interpolate/extrapolate tail

- **alpha=0.05**: r=9>8 จึงทุกตัวไม่มี finite threshold และไม่มี detection
  ต้องรายงานเป็น infeasible useful operating point ไม่เรียก TPR=0 ว่าได้แก้ FPR
- **alpha=0.20 และ 0.40**: secondary diagnostic operating points ที่ตั้งใจสูง
  เพื่อดู behavior ด้วยข้อมูลจำกัด ไม่ใช่ deployment targets และไม่ใช่เปลี่ยน
  เป้าหมาย 5% ให้ผ่าน rank=8/6 ตามลำดับ
- Smallest nontrivial nominal level กับ n=8 คือ 1/9≈11.11%; finite 5% ต้องมี
  calibration อย่างน้อย 19 cohorts เพิ่มจาก fit set ภายใต้ exchangeability
  ส่วน zero-FP validation ที่ one-sided 95% upper <=5% ต้องอย่างน้อย 59 cohorts

สูตร rank มี marginal interpretation เฉพาะคะแนน calibration/new cohort ที่
exchangeable ภายใต้ fitted statistic คงที่; reused sources และจำนวน cohorts
เล็กไม่ยืนยันสมมติฐาน ไม่ใช่ conditional-on-this-calibration guarantee
ไม่มี guarantee สำหรับการเลือกหนึ่งตัวจากหลาย candidates หลังเห็นผล

Fit nuisance เสร็จก่อน calibration; freeze thresholds ทุกตัวก่อนเปิด validation
ไม่ fit/เลือก hyperparameters จาก validation หรือ Phase C evaluation
รายงานครบ 10×3 ไม่เลือก winner หรือ retune ถ้า validation false alarms สูง

Matched comparison ใช้ alpha, calibration split, horizon และ strict rule เดียวกัน
พร้อมรายงาน actual calibration exceedances และ validation control alarm vector
เทียบกับ baseline แต่ละ alpha **ไม่ถือ nominal alpha เท่ากันว่า actual FPR เท่ากัน**
รายงาน paired TPR differences เฉพาะเชิงพรรณนา แยกกรณีที่ control alarm vector
ตรงและ prefix ทั้งคู่ไม่ alert ออกจาก FPR/prefix-confounded comparisons
แม้ vector ตรงก็เป็นแค่ empirical screen n=3 ไม่ยืนยัน population match
ห้ามอ้าง improvement จาก TPR สูงขึ้นที่ FPR สูงขึ้น หรือเลือกจุดบน validation
ให้ FPR ตรงกันแล้วอ้าง confirmation

## Metrics และ uncertainty

แยก any alarm, benign-control FPR, pre-attack alarms, eligible-at-onset,
post-onset first detection, delay=first query−111, null/ineligible delays,
right censoring ที่ 256 รายงาน detection/total และ detection/eligible ทั้งคู่
เพื่อไม่ซ่อน prefix false alarms; benign controls ไม่มี attack TPR/delay
รายงาน per-cohort และเฉลี่ย 3 cohorts, paired alert disagreement ระหว่าง
orderings บน schedules เดียวกัน, median delay เฉพาะ detected พร้อมจำนวน
ไม่ตีความ median เป็น unconditional speed improvement

Benign FPR ใช้ exact two-sided 95% interval และ one-sided upper แยก convention
ที่ 0/3 one-sided upper≈63.16%, two-sided upper≈70.76%; conditional MC Wilson
สำหรับ 10 schedules ต่อ cohort ต้องระบุว่าไม่ใช่ independent cohort interval
ไม่ใช้ n=30 เป็น population n; ไม่ทดสอบ significance/claim novelty/generalization

## Resource preflight และ freeze

CPU-only ใน Conda `senior`, ไม่ต้อง GPU/network/model weights/embeddings
คาดประมาณ 10–60 s สำหรับ input audit + 285 traces × 3 rolling histories
และ 6 CUSUM; RAM เพิ่มไม่เกิน 512 MiB, minimum available RAM 1 GiB
hard wall budget **120 s** อยู่ภายใน gate เดิม 1,200 s; ไม่ขยาย scope อัตโนมัติ
ก่อน validation score ใช้ numeric fixture 5 traces วัด P95 ต่อ all-candidate trace
projection=elapsed+2×P95×285 ต้อง <=120 s; check deadline ระหว่าง traces
หาก gate/input/parity ผิด ให้เก็บ blocked attempt และไม่ retune/fallback

ก่อนคำนวณ candidate scores ให้เขียน preflight.json พร้อม SHA256 ของ protocol,
config, implementation และ tests เป็น filesystem freeze; ไม่ใช้ preliminary
commit เพื่อหลีกเลี่ยงหยุดกลางงานตาม AGENTS.md หลัง local commit
Baseline source/upstream metadata/certificate และ selected full-log hashes
ต้องตรงกับ Git/Phase C manifest ไม่อ่าน evaluation log
Recompute cumulative W จาก saved distances และ compare saved W tolerance 2e-5
พร้อม score/strict alert parity ก่อนใช้ variants; เป็น distance-to-W parity
ไม่ใช่ independent re-encoding parity (อาศัย BGE/upstream parity ของ Phase C)

Pre-score correction: attempt v1 หยุดก่อน data scoring เพราะเทียบ Git LF กับ
checkout CRLF แบบ byte-identical ตรวจยืนยันว่า PRADA hash ตรง historical
experiment metadata และต่างเฉพาะ newline จึงแก้ verifier ให้ตรวจ exact
historical raw hash **พร้อม** Git content ที่ normalize เฉพาะ CRLF เป็น LF
ไม่แก้ upstream files/config/candidates เก็บ failed v1 และ frozen source ไว้
รอบถัดไปใช้ directory v2 และ budget 120 s เดิม ไม่มีการขยาย resource gate

เก็บ selected numeric inputs แบบ gzip (<1 MB), thresholds, fit parameters,
per-stream/per-cohort metrics, paired comparisons, plots, audit/hash metadata
ไม่เก็บ raw text/weights/embeddings ไม่ overwrite previous runs
Tests ต้องครอบคลุม rolling causal windows, CUSUM direction/reset, calibration
resolution/ties, pre-alert eligibility/censoring และ prohibited evaluation cohorts
จบด้วย local result commit แล้วหยุด ไม่ push/merge/rebase/PR/main changes

## แหล่งวิธีที่ตรวจ ณ วันที่จัดทำ

- [NIST CUSUM](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm):
  mean-shift accumulation และ k=delta/2; ไม่มีการนำ ARL มาแทน finite-horizon FPR
- [SciPy Shapiro documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.shapiro.html):
  W statistic กับ p-value คนละค่า; ต้องมีอย่างน้อย 3 observations
- [Angelopoulos & Bates](https://arxiv.org/abs/2107.07511): finite-sample rank
  calibration ต้องมี exchangeability; การปรับใช้กับ stream maxima เป็น design
  ของ pilot นี้ ไม่ใช่ theorem ที่รับรองข้อมูล reused ว่าเป็น iid
