# Phase E — Sequential Detector Robustness & Shortcut Analysis

วันที่ 7 พฤศจิกายน 2026 | `experiment/stream-prada-order`

**ยังไม่มีหลักฐานพอว่า CUSUM gains เป็นการจับ sequential extraction behavior
ที่มีความหมายแยกจาก dataset shortcuts** ยืนยันว่าชุด development นี้มี
length/format shortcut รุนแรง: length-only endpoint ตรวจ mixed streams ได้
ทั้งหมด ณ diagnostic alpha=.20 และ non-sequential distance mean ได้ผลใกล้
CUSUM หลายเงื่อนไข การปรับความยาว/source prefix ไม่ได้แก้ common-support
failure จึงไม่ใช่หลักฐานว่าควบคุม shortcut สำเร็จแล้ว

ไม่ได้พิสูจน์ว่า CUSUM ใช้ความยาวเพียงอย่างเดียว เพราะ CUSUM รับ distances
ไม่รับ word count โดยตรง แต่หลักฐานไม่รองรับการอ้างความจำเป็น/เอกลักษณ์ของ
sequential attack mechanism หรือ confirmed improvement/generalization
ไม่เลือก detector หรือ threshold ที่ดีที่สุดจากผลรอบนี้

## ขอบเขตและ design ก่อนวิเคราะห์

อ่านรายงาน initial experiment/preflight, Phase A failure analysis, Phase B/C/D
ก่อนกำหนด [PHASE_E_PROTOCOL_TH.md](PHASE_E_PROTOCOL_TH.md) และ
[phase_e_config_v1.json](phase_e_config_v1.json)
Freeze source/config/protocol/tests/plot code ด้วย SHA256 ใน preflight ก่อนอ่าน
experimental inputs และตรวจ hash ไม่เปลี่ยนหลังจบ; fit/thresholds บันทึกก่อน
development scoring ไม่มีการเพิ่ม candidates หรือเลือก operating point ตามผล E

ใช้ **285 traces เดิม** ของ Phase D: 4 fit benign cohorts, 8 calibration benign
cohorts, 3 development paired cohorts (12–14), permutations 0–9, ratios
26/64/128 จาก 256 queries, prefix110/onset111/horizon256 ตามเดิม
ข้อมูล C/D ที่เคยเห็นเป็น development ทั้งหมด ไม่เรียก final confirmation
ไม่อ่าน Phase C evaluation outcomes 15–22 เพื่อประเมิน variants รอบนี้

อ่าน raw queries เดิมแบบ read-only เพื่อดึง whitespace word/character counts,
format flag และ official SQuAD article identity เท่านั้น ไม่บันทึก raw text
มี numeric metadata **4,224 unique queries** ใน 15 cohorts และ 285 growth paths
Source/query certificates และ file hashes ตรงเดิม

Original PRADA/Growing Set/BGE/Deep Kernel MMD ไม่เปลี่ยน ไม่มี BGE/nearest-
neighbor/victim API/training execution ใหม่ Distance paths มาจาก frozen BGE
ของ Phase C ไม่ได้ re-encode เพื่อตัด context หรือเปลี่ยนความยาว
Original และ lower CUSUM k=.5/1 ทั้ง metrics/scores ตรง Phase D **2,457 rows**
Growing admissions/count/threshold ที่ reconstruct จาก saved distances ตรง
Phase C ทุก selected trace; upstream encoder parity อาศัยหลักฐานเดิม ไม่อ้าง
ว่าได้รัน encoder parity ใหม่

## 1. Length และ format เป็น label shortcut ที่ยืนยันได้

ใช้ unique reservoirs ไม่เพิ่มน้ำหนัก query ที่ปรากฏซ้ำข้าม permutations
word count คือ whitespace words ไม่ใช่จำนวน BGE subword tokens

| Development source | Benign n / words min–median–max | Attack n / words min–median–max | Attack ใน fit-length support | Matched pairs ใน fixed length bins |
| --- | --- | --- | --- | --- |
| 12: Frédéric Chopin | 256 / 4–10–29 | 128 / 109–189–385 | 0/128 | **0** |
| 13: Kanye West | 256 / 4–11–21 | 128 / 98–219.5–387 | 0/128 | **0** |
| 14: New York City | 256 / 5–10–23 | 128 / 103–168.5–393 | 0/128 | **0** |

Fit benign support = **3–25 words**; development benign ทั้งหมด 4–29 และ attack
ทั้งหมด 98–393 words จึงไม่มี observed length overlap แม้ภายในบทความเดียวกัน
Fixed bins [0,8,16,32,64,128,256,infinity] ที่กำหนดก่อนผลให้ matched-pair
capacity เป็นศูนย์ทุก development cohort ไม่สร้าง length-matched streams ทดแทน

Format `Given this context:` พบ **384/384 attack queries** และ **0/768 benign**
ใน development reservoirs ส่วน benign เป็น question-only ไม่มี same-format
positive/negative examples ที่ใช้แยก extraction intent จาก rendering ได้
นี่เป็น **confirmed dataset confounding** ไม่ใช่ผลพิสูจน์ว่า long context เป็น
attack ใน traffic จริง หรือว่า format เป็น causal source ของ embedding distances

## 2. ความยาว minimum distance และ Growing Set

ตารางนี้เฉลี่ย descriptive stream summaries ของ 30 schedules/cohort ที่ attack
25% ไม่ใช่ independent query samples หรือ population inference

| Cohort | Mean distance B / A | Admission rate B / A | Final Growing Set mean | Mean within-stream rho(words,distance) | rho(distance,G before query) |
| --- | --- | --- | ---: | ---: | ---: |
| Chopin | 0.7254 / 0.5378 | 72.18% / 3.80% | 141.30 | −0.3585 | −0.4908 |
| Kanye West | 0.7149 / 0.5442 | 73.42% / 8.02% | 146.37 | −0.3464 | −0.5063 |
| New York City | 0.7991 / 0.6205 | 78.57% / 6.67% | 155.33 | −0.4503 | −0.4255 |

Attack-labelled queries มีระยะเฉลี่ยต่ำกว่าและเข้าชุด Growing Set น้อยกว่า
ในทุก source นี้ สอดคล้องกับ lower-distance accumulation แต่ **B รวม benign
prefix ขณะที่ A อยู่หลัง onset** จึงยัง confound position/history/label/format
ไม่ใช่ causal length effect และ Growing Set เป็น downstream state ของ distances
การที่ทั้งสองสัมพันธ์กันไม่ให้ independent mechanism confirmation

Mean rho(Growing Set size,CUSUM level) ที่ 25% = **0.8962, 0.9161, 0.0557**
ส่วน rho(current words,CUSUM level) = **−0.1356, −0.1434, +0.1746** ตามลำดับ
จึงไม่ใช่ความสัมพันธ์แบบ long query → high current cumulative score ทุก source
ทั้ง cumulative score/Growing Set มี time trend และ dependence ไม่ใช้ p-values
จาก correlated queries อ้าง independence

เมื่อ fix cohort+ratio ทุก ordering/permutation ใช้ query membership เดียวกัน
mean query length จึงคงที่และ correlation กับ maximum CUSUM **undefined/null**
ตามที่บันทึกไว้ ไม่แทน null เป็น 0 และไม่ pool ratios เพื่อสร้าง correlation
ที่แท้จริงสะท้อน attack fraction อย่างเดียว

## 3. Negative controls และ matched-calibration comparison

Predeclared 17 candidates รวม Original, lower CUSUM สอง k, length-only,
distance-mean endpoint, length-adjusted/prefix-centered/combined CUSUM สอง k
และ fixed-distance order surrogates 6 ตัว รายงานครบ ไม่เลือก winner

Length-only = endpoint mean(log1p(words)) ของ 256 queries ไม่ใช้ embeddings,
labels, distances หรือ article IDs; distance endpoint = negative mean ของ raw
minimum distances Q102–256 ไม่ใช้ recursive CUSUM แต่ distances เองยังขึ้นกับ
upstream Growing Set/query order จึงเป็น **non-sequential aggregation** เท่านั้น
ไม่ใช่ fully order-independent representation

ทุกตัวใช้ calibration cohorts4–11, stream maximum/endpoint score, strict
crossing และ rank ceil(9×(1−alpha)) เดียวกับ Phase D Thresholds freeze ก่อน
development; alpha=.05 ให้ infinity ทุกตัวเพราะ n=8 ไม่พอ ไม่ extrapolate tail
alpha=.20/.40 เป็น diagnostic ที่ตั้งใจสูง ไม่ใช่ FPR deployment targets

ตาราง ณ alpha=.20: detections ต่อ **30 conditional schedules** ในแต่ละ cell
R=random/C=clustered/I=interleaved; n ของ outer development ยังเป็น **3**

| Candidate | Benign FP | Attack26 R/C/I | Attack64 R/C/I | Attack128 R/C/I |
| --- | --- | --- | --- | --- |
| Original | 0/3 | 0/1/0 | 1/1/0 | 11/21/13 |
| Length-only endpoint | 0/3 | **30/30/30** | **30/30/30** | **30/30/30** |
| Distance mean endpoint | 0/3 | 0/0/0 | **18/18/17** | **22/25/25** |
| Lower CUSUM k=.5 | 0/3 | 0/0/0 | **19/21/17** | **23/25/23** |
| Lower CUSUM k=1 | 0/3 | 0/3/1 | 14/23/16 | 23/25/22 |
| Length-adjusted k=.5 | 0/3 | 0/0/0 | 17/20/16 | 20/25/20 |
| Length-adjusted k=1 | 0/3 | 0/4/0 | 12/22/11 | 20/25/20 |
| Prefix-centered k=.5 | **1/3** | 10/23/13 | 28/30/28 | 30/30/30 |
| Prefix-centered k=1 | **1/3** | 5/16/7 | 18/30/16 | 30/30/30 |
| Combined k=.5 | 0/3 | 6/19/5 | 23/30/27 | 30/30/30 |
| Combined k=1 | 0/3 | 4/13/3 | 13/30/10 | 30/30/29 |

Attack26=10.15625%,64=25%,128=50% ตัวเลข TPR อ้าง dataset attack labels
ไม่ได้รับรอง successful extraction หรือ malicious intent ของทุก query ในโลกจริง
ผล length-only **270/270 mixed streams** พร้อม FP0/3 ยืนยันว่าภายใต้ protocol
นี้แยก labels ได้โดยไม่ใช้ sequential extraction behavior เลย ไม่ใช่ detector
ที่ควรนำไปใช้งานจริง หรือหลักฐาน true FPR=0

Distance endpoint ใกล้ CUSUM k=.5 ที่ 25% และ 50% บาง ordering ได้มากกว่า
โดยไม่ใช้ CUSUM recursion จึงยังไม่แสดงว่า recursion จำเป็นต่อ gains
แต่ endpoint เห็นครบ stream: ถ้า detect จะ delay **145** เสมอ เทียบ CUSUM
k=.5 ที่ 50% median detected delay **56/56/59** จาก detected n23/25/23
ยังไม่ใช่ unconditional early-detection superiority เพราะ information budget,
repeated looks และ detected subsets ต่างกัน ต้องเปรียบเทียบ checkpoints/censoring
ตาม protocol ใหม่ ไม่ยก endpoint accuracy หรือ median อย่างเดียวมาตัดสิน winner

## 4. Length-aware/source-aware controls ตอบได้เพียงใด

Length correction fit common log-length slope หลัง position demeaning จาก
benign fit cohorts0–3 เท่านั้น: beta=**−0.0163381** distance/log-word unit
clip prediction ที่ 3–25 words แล้ว fit residual SD ตาม position (floor0.01)
ไม่มี development label หรือ attack outcomes ใน fit/calibration

หลัง correction CUSUM ยังสูงกว่า Original ในหลาย cells เช่น k=.5/25% ให้
17/20/16 เทียบ1/1/0 และ FPR0/3 เท่ากันเชิงประจักษ์ แต่ **attack 384/384
อยู่นอก fit support** จึงเพียงแสดง sensitivity ต่อ capped correction นี้
ไม่ใช่ validated removal of length effect หรือหลักฐาน gains หลัง proper matching
Common-support/format-matched causal contrast **ยังทำไม่ได้จากข้อมูลเดิม**

Source-aware prefix centering ลบ mean standardized distance ของ Q2–101
ซึ่งทราบก่อน first test ไม่ fit article effects จาก development labels
Initial offsets cohorts12/13/14 = **−0.3214/−0.5029/+0.3588**
ช่วยเปลี่ยน source-level baseline แต่ไม่ควบคุม topic/semantic geometry ทั้งหมด
ทั้ง prefix-centered k ทำ FP ที่ **Chopin control Q177** =1/3 ใน alpha=.20
แม้ TPRสูงขึ้น จึง **ห้ามอ้าง improvement** จากจุดที่ FPRสูงขึ้นนี้

Combined correction มี FP0/3 และ TPRสูงในหลายเงื่อนไข แต่ยังมี support failure,
format-label identity และเพียง3 cohorts จึงไม่เลือกเป็น detector ใหม่
Same-article B/A comparisons ช่วยตัด cross-article identity ที่ง่ายที่สุด แต่
ไม่ตัด within-article query rendering/length confounds; ไม่ยืนยัน generalization

## 5. Particular articles และ order sensitivity

ที่ alpha=.20/25%/random, raw lower CUSUM k=.5 detect **9/10,10/10,0/10**
ใน Chopin/Kanye/NYC; distance endpoint **8/10,10/10,0/10** และ length-adjusted
**9/10,8/10,0/10** ผลไม่ได้เกิดสม่ำเสมอทุก article
เมื่อทิ้ง development cohort ทีละชุดโดย **ไม่ refit threshold** raw CUSUM rate
เปลี่ยนเป็น **50%,45%,95%** ตามการทิ้ง Chopin/Kanye/NYC (full mean63.33%)
ที่ 50% random raw CUSUM เป็น10/10,10/10,3/10 และ length-adjusted10/10,10/10,0/10
จึงยังพึ่ง source composition มาก Leave-out เป็น descriptive n=2 ไม่ใช่ test ใหม่

Length endpoint invariant ต่อ query order ภายใน cohort+ratio โดย construction
ส่วน raw-distance bag มาจาก order-dependent upstream state จึงยังเปลี่ยนได้
ทดสอบ CUSUM กับ suffix z-values bag เดิมแบบ reverse/shuffle seeds17/29
โดยคง prefix Q2–110 และ calibrate transformed benign paths ด้วย recipe เดียวกัน
ไม่ re-query/rebuild Growing Set, ไม่ใช้ surrogate steps เป็น real delay

| Raw lower CUSUM → surrogate, alpha=.20 | Attack26 changed /90 | Attack64 changed /90 | Attack128 changed /90 |
| --- | --- | --- | --- |
| k=.5 reverse / shuffle17 / shuffle29 | 0 / 0 / 0 | 2 / 3 / 3 | 2 / 3 / 2 |
| k=1 reverse / shuffle17 / shuffle29 | 0 / 10 / 8 | 2 / 9 / 9 | 0 / 4 / 4 |

90 คือ3 orderings×3 cohorts×10 schedules ไม่ใช่90 independent sources
Matched nominal recipe และ observed controls ยัง0/3 ในทุก surrogate ที่จุดนี้
ผล k=.5 คงอยู่เกือบทั้งหมดหลังเปลี่ยน score-value order บน bag เดิม สอดคล้อง
กับ bulk distance shift มีบทบาทมาก แต่ไม่พิสูจน์ absence of sequential value
หรือ causal invariance ของ real queries เพราะ geometry/state ถูกตรึงไว้
k=1 บางกรณีไวต่อ order มากกว่า แสดง conditional statistic sensitivity เท่านั้น

## 6. FPR uncertainty, negative findings และ evidence boundary

Mixed paths ทั้งหมดไม่มี prefix alarms ในรอบนี้ แต่ endpoint controls ไม่ทดสอบ
จน Q256 จึงไม่มีโอกาส prefix alarm อยู่แล้ว ไม่ตีความเป็น early-alarm robustness
Benign FPR กับ mixed prefix alarms เป็นคนละ metric; prefix-centered controls
มี FPหลัง prefix จริง แม้ mixed prefix alarm=0

ที่ observed0/3: exact two-sided95% interval **[0%,70.76%]** และ one-sided95%
upper **63.16%**; ที่1/3 two-sided **[0.84%,90.57%]** ภายใต้ iid Bernoulli
cohort assumptions ซึ่ง source disjointness ไม่รับรอง semantic/session independence
Equal0/3 และ equal calibration alpha ไม่พิสูจน์ matched population FPR
ที่ alpha=.40 length endpoint มี FP2/3, distance endpoint1/3; raw CUSUM k=.5
2/3, k=1 1/3 เทียบ Original0/3 ต้องรายงาน trade-off ไม่อ้าง TPR gains เป็น improvement
ทุก candidate/level พร้อม risk/censor counts และ conditional MC intervalsอยู่ใน
summary.json.gz/[ตารางครบ](diagnostics/phase_e_verified/PHASE_E_TABLES.md)

| สิ่งที่ยืนยันได้ | สิ่งที่ยังยืนยันไม่ได้ |
| --- | --- |
| Development length/format label separation และไม่มี common support | CUSUM ใช้ length อย่างเดียว หรือ causal effect ของ length |
| Non-sequential distance aggregation ใกล้ CUSUM ในหลาย cells | Sequential extraction mechanism จำเป็น/มี incremental value |
| Capped length/prefix corrections เปลี่ยนผลและ FPR | Shortcut ถูกควบคุมแล้ว/combined detector เหนือกว่า |
| Article-specific rates และ conditional ordering sensitivity | Generalization ข้าม users/sessions/sources/attack families |
| All prior data reused, only3 development source cohorts | Population FPR control/novelty/successful model extraction |

## 7. Reproducibility และ resources

CPU-only run ใช้ **7.024 s** ภายใน hard budget120s; peak process working set
**239.17 MiB** ไม่ใช้ GPU/BGE/victim/network/download corpus ใหม่
Numeric-path projection1.421s รวม safety2 เป็น estimate เฉพาะ statistic work
ไม่รวม data lookup/parsing/plots; actual deadline รวมงานทั้งหมดและผ่าน

Tests **64 ผ่าน**: เดิม52 + control tests11 + artifact-corruption test1
ครอบคลุม endpoint bag invariance, prefix causality, growth reconstruction,
position-demeaned fit/capping/support failure, cohort-weighted leave-out,
constant-correlation null, surrogate reproducibility/delay semantics และ hashes

Saved numeric-input audit ใช้ **2.397 s** ทำซ้ำ285 traces, query metadata4,224,
growth paths285, calibration scores136, metric rows**13,923** และ
associations/common-support/leave-out/order summaries ผ่าน โดยไม่ใช้ raw queries
ในการ audit และไม่ rerun upstream detector กราฟสองภาพตรวจ visual layout แล้ว
และ regenerate จาก published numeric artifacts ได้ตรง original bytes ทั้งสองภาพ
Preservation checks ทั้ง runner และ Git ผ่าน: ไม่แก้ prior tracked files/main

ไฟล์หลัก:

- [Analysis script](phase_e_analysis.py), [saved-result audit](phase_e_audit.py),
  [plot code](phase_e_plots.py), tests/config/protocol และ hash manifests
- [Shortcut controls / cohort rates](results/phase_e_analysis_20261107_v1/shortcut_controls.png)
- [Length–distance–Growing Set–CUSUM fixed examples](results/phase_e_analysis_20261107_v1/length_distance_growth_paths.png)
- `results/phase_e_analysis_20261107_v1/`: numeric query metadata/growth paths,
  fit, frozen thresholds, per-stream CSV.gz, associations, summary.json.gz,
  provenance/preflight/parity/metadata/artifact hashes ไม่มี raw text/weights/vectors

```powershell
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests
conda run --no-capture-output -n senior python stream_prada_order/phase_e_audit.py stream_prada_order/results/phase_e_analysis_20261107_v1 --output stream_prada_order/diagnostics/new_phase_e_audit
conda run --no-capture-output -n senior python stream_prada_order/phase_e_replot.py stream_prada_order/results/phase_e_analysis_20261107_v1 --output stream_prada_order/diagnostics/new_phase_e_plots
```

หากจะ regenerate metadata จาก raw inputs เดิมต้องมี exact local Phase C
calibration/validation logs และ cached official SQuAD lookup; ใช้ output ใหม่
และ budget120s เดิม ไม่มี implicit download/model fallback:

```powershell
conda run --no-capture-output -n senior python stream_prada_order/phase_e_analysis.py --output stream_prada_order/results/new_phase_e_analysis
```

## 8. ข้อมูลใหม่และ protocol ถัดไป

[New-data feasibility](PHASE_E_NEW_DATA_FEASIBILITY_TH.md) ตรวจ primary cards/
licenses ปัจจุบันของ WildChat, LMSYS และ MEA-Bench พร้อม source register ใน
PHASE_E_SOURCES.json ไม่ดาวน์โหลด corpus ไม่ accept gated agreement
ยังไม่รับรองจำนวน natural independent benign/attack cohorts หรือ license/
chronological run provenance ของ query pools ว่าพร้อมใช้จริง

ข้อเสนอใน [NEXT PROTOCOL](PHASE_E_NEXT_PROTOCOL_TH.md): เก็บ genuinely acquired
long-context benign และ short-query actual extraction traffic บน victim/task/
rendering ที่เทียบกันได้ มี common support และ source/user/run components
แยก fit/calibration/validation/untouched final test ก่อน scoring พร้อม
length-only และ distance-bag controls และ information-budget-matched sequential
comparisons ไม่ใช้ permutations แทน outer cohorts

**คำตัดสิน:** ผล Phase E ลดความน่าเชื่อถือของคำอธิบายว่า gains เดิมพิสูจน์
meaningful sequential extraction detection แล้ว ควรแก้ data/shortcut/provenance
bottleneck ก่อนทดลอง detector ถัดไปหรือเพิ่ม full-run scope ไม่เลือก winner,
ไม่ retune จาก evaluation, ไม่เริ่ม acquisition/full experiment โดยอัตโนมัติ
ไม่ push/merge/rebase/PR และไม่แก้ main
