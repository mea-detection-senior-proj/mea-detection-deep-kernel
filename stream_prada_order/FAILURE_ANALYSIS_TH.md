# Stream PRADA Failure Analysis — Phase A

วันที่ตามบริบทผู้ใช้: 6 พฤศจิกายน 2026

Branch: `experiment/stream-prada-order`

หลักฐานตั้งต้น: commit `c1915e5517404df4963a0a20abb4a72c7df6e98a`

**สรุป:** ยืนยันเส้นทางการเกิด false positives และ pre-attack alerts ได้แล้ว:
หลาย stream มี W ต่ำตั้งแต่ช่วงต้น และคะแนน maximum เก็บเหตุการณ์นั้นไว้แม้
W ภายหลังกลับมาปกติ ส่วน 50% ใช้ benign prefix ที่ alert ตั้งแต่การทดสอบแรก
แล้วทำซ้ำ prefix เดียวกันทุก permutation จึงไม่ใช่ attack detection 100%
แต่ **สาเหตุเชิงประชากร/เนื้อหาว่าทำไม held-out FPR สูงกว่า calibration ยัง
ระบุอย่างเป็นเหตุเป็นผลไม่ได้** ห้ามสรุปว่าเกิดจาก topic shift หรือ sample size
เพียงอย่างเดียวจากหลักฐานนี้

ไม่มีการแก้ detector, threshold, encoder setting, configuration หรือผลเก่า
ไม่แก้ Deep Kernel MMD, ไม่ merge/rebase/PR และไม่ push งาน Phase A
ชื่อ repository ในคำขอคือ `taetaevrh/Deep-Kernel` แต่ remote ของ checkout ที่
ตรวจเป็น `ASippakorn/Deep-Kernel`; ใช้ checkout ที่มี baseline commit ข้างต้น
โดยไม่เปลี่ยน remote หรือส่งข้อมูลออก

## 1. ขอบเขตหลักฐานและเหตุผลที่ต้อง replay

เริ่มจากตรวจ saved results และ implementation ที่ตรึงไว้ พบว่า
`benign_scores.csv.gz` มีเพียง stream ID, maximum score และ alert ไม่มี
first-alert query หรือ per-query W ส่วน calibration มีเพียง 200 maximum scores
จึงไม่สามารถตอบ timing ของ 34 false positives หรือ nested-length analysis
อย่างตรวจสอบได้จากไฟล์เดิมเพียงอย่างเดียว

รายงานทรัพยากรก่อนรันแล้ว: ไม่เกิน 120 วินาที, RAM ประมาณไม่เกิน 2 GiB,
GPU peak ประมาณ 1 GiB จากนั้น replay เฉพาะ calibration 200 และ held-out benign
200 streams ด้วย frozen `experiment.trace` เดิม ใช้ query order เดิมและ threshold
**0.06419320835771236** (W threshold **0.9358067916422876**) ไม่มีการ calibrate ใหม่

Encode ชุดเดิมครบ 3,000 queries เพื่อเทียบ embedding hash ทั้งก้อนและสร้าง
distance matrices รูปทรงเดิม แต่ไม่รัน mixed-stream PRADA 9,000 streams ซ้ำ
Embedding SHA256 ตรงของเดิม และ **คะแนนทั้ง 400 streams ตรงทุกค่า: max error 0.0**
alert decisions ตรงทั้งหมด โดยตรวจ original source/model/data/pool hashes ก่อนใช้
ผล replay เป็นหลักฐาน ไม่มีการสร้าง query สังเคราะห์หรือเรียก LLM/API

Replay ใช้ 25.5841 s; ทั้ง Phase A runner 32.0162 s Peak process working set
1,432.38 MiB, GPU allocated/reserved 680.14/882.00 MiB อยู่ในงบที่แจ้งไว้
Traces ที่กู้ได้บันทึก gzip ไว้แล้ว การวิเคราะห์และทำกราฟต่อจากนี้ไม่ต้องรัน
BGE/Stream PRADA ซ้ำ

## 2. ทำไม calibration 5% จึงไม่รับประกัน held-out FPR 5%

Calibration threshold เป็น linear P95 ของ **200 scores ชุดเดียวกัน** จึงได้
10/200 strict exceedances = 5% ตาม construction ไม่ใช่ out-of-sample validation
การแบ่ง source groups กันช่วยป้องกัน leakage แต่ไม่รับประกันว่าทั้งสอง pools
มี score distribution เดียวกัน และ percentile จากตัวอย่างจำนวนจำกัดมี uncertainty

| สถิติ maximum stream score | Calibration | Held-out benign |
| --- | ---: | ---: |
| จำนวน streams | 200 | 200 |
| Mean | 0.037210 | 0.048066 |
| Median | 0.034737 | 0.045831 |
| P95 เชิงพรรณนา | 0.064193 | 0.084479 |
| Maximum | 0.104235 | 0.135518 |
| Exceedances ที่ threshold เดิม | 10 (5%) | 34 (17%) |

**ยืนยันแล้ว:** held-out empirical score distribution สูงกว่าของ calibration
ตามตาราง/ECDF Threshold เดิมถูกใช้เหมือนกันและการนับ 34/200 ถูกต้อง P95 ของ
test ในตารางใช้บรรยาย distribution เท่านั้น ไม่ถูกเลือกเป็น threshold ใหม่
Wilson interval 12.43–22.82% จากผลเดิมเป็น conditional Monte Carlo uncertainty
ไม่ใช่ population interval ที่พิสูจน์ความเป็นอิสระของ source cohorts

**ยังไม่ยืนยัน:** ความต่างนี้เกิดจาก source/topic/semantic geometry ใด, finite
pool realization หรือปัจจัยใดมีสัดส่วนอธิบายเท่าไร มีเพียง calibration pool
หนึ่งชุดและ test pool หนึ่งชุด จึงยังแยก pool effect ออกจาก sampling variation
ระดับ cohort ไม่ได้ ไม่ใช้ KS p-value บน resampled streams เพื่ออ้าง independence

## 3. Source-group composition และ stream construction

ตรวจไฟล์ข้อมูลเดิมแบบอ่านอย่างเดียว ใช้ `pilot/protocol.py` เดิมแบ่งข้อมูล
และสร้าง pool membership ให้ตรง query hashes ที่บันทึกไว้ทุกตำแหน่ง จากนั้น
เชื่อม source groups แบบ transitive ตาม ID, normalized text และ attack context
ใช้ hashed group identifiers ภายใน analysis โดยไม่บันทึก query ดิบลง Git

| Pool ที่เลือกจริง | Queries | Source groups | Effective groups (1/HHI) | Mean words | Word P95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Calibration benign | 1,000 | 343 | 250.63 | 10.500 | 17 |
| Held-out benign | 1,000 | 350 | 261.37 | 10.379 | 17 |
| Held-out attack | 1,000 | 345 | 250.38 | 193.365 | 287.05 |

Calibration กับ held-out benign มี **0 shared source groups และ 0 shared normalized
queries** ภายใต้กฎ grouping นี้ ทั้งสองสุ่ม streams ยาว 256 แบบ uniform queries,
without replacement ภายใน stream, จาก pool ขนาด 1,000 เท่ากัน ไม่มีหลักฐาน
ว่า gap เกิดจากความยาว stream ต่างกัน หรือ replacement rule ต่างกัน

อย่างไรก็ตาม ใช้ pool เดิมซ้ำข้าม streams: calibration/test ใช้ครบ pool 1,000
queries และแชร์คำถามเฉลี่ย **65.548/65.565 queries ต่อคู่ streams** จึงไม่ใช่
200 source-disjoint cohorts การสุ่มตาม query ทำให้ source group ใหญ่มีโอกาส
ปรากฏตามจำนวน queries ไม่ใช่ uniform source-group sampling การแยก groups
ระหว่าง pools ไม่ได้ทำให้ streams ภายใน pool อิสระต่อกัน

| ค่าเฉลี่ยต่อ stream | Calibration | Test FP (34) | Test TN (166) |
| --- | ---: | ---: | ---: |
| Distinct source groups | 181.765 | 183.029 | 183.566 |
| Effective groups | 145.997 | 147.496 | 148.936 |
| Largest group fraction | 0.01785 | 0.01654 | 0.01734 |
| Mean words | 10.497 | 10.373 | 10.390 |

ข้อมูลนี้ไม่แสดงคำอธิบายง่าย ๆ ว่า FP เกิดเพราะข้อความยาวกว่าหรือมี source
group เดียวครอง stream: ค่าสรุปใกล้กัน และ descriptive Spearman ของ test score
กับ mean words = 0.036, effective groups = −0.116 ไม่ใช่หลักฐานเชิงเหตุผล
หรือข้อสรุปว่า feature เหล่านี้ไม่มีผล Semantic/topic composition ยังไม่ได้ตรวจ
ด้วย independent controls จึงยังเป็นสมมติฐาน

## 4. False-positive benign streams ทั้ง 34 รายการ

**16/34** alert ที่การทดสอบแรก Query 102; **19/34** alert ภายใน Query 110;
median first alert = **106**, ช่วง **102–232** ทุก query ใน streams นี้เป็น benign
จึงเป็น false positive ไม่ว่า alert จะเกิดก่อนหรือหลัง query 111

| First-alert query range | FP streams |
| --- | ---: |
| 102–110 | 19 |
| 111–128 | 6 |
| 129–160 | 3 |
| 161–192 | 3 |
| 193–224 | 2 |
| 225–256 | 1 |

ตารางเจาะจง stream IDs (เริ่มที่ 0) กับ first query (เริ่มที่ 1):

| First query | Stream IDs |
| --- | --- |
| 102 | 5, 9, 26, 32, 36, 37, 55, 61, 64, 93, 96, 156, 163, 166, 167, 173 |
| 103 | 107 |
| 109 | 52, 138 |
| 113 | 16, 79 |
| 114 | 67, 97 |
| 116 | 189 |
| 122 | 4 |
| 129 | 24 |
| 147 | 129 |
| 156 | 47 |
| 173 | 126 |
| 176 | 115 |
| 188 | 18 |
| 197 | 38 |
| 211 | 140 |
| 232 | 143 |

รายละเอียด score, raw/retained sample counts และ first/min W อยู่ใน
[false_positive_streams.csv](diagnostics/phase_a/false_positive_streams.csv)
และ per-stream endpoint diagnostics ใน
[per_stream_details.csv](diagnostics/phase_a_details/per_stream_details.csv)

เมื่อจบที่ query 256 มีเพียง **5/34** ที่ W ยังต่ำกว่า threshold; อีก **29/34**
W กลับเหนือ threshold แล้ว แต่ stream score คือ `1 - minimum W over history`
จึงยัง alert ตาม algorithm เดิม Calibration ก็มี pattern นี้: เคย alert 10/200
แต่ endpoint W ไม่ต่ำกว่า threshold ทุก stream นี่อธิบายการคงอยู่ของ alert หลัง
transient crossing ไม่ใช่คำแนะนำให้เปลี่ยน detector ไปใช้ endpoint W

## 5. ทำไมทุก permutation ของ 50% alert ที่ Query 102

Warm-up เช็ก **raw distance history > 100** Query 101 มี 100 distances จึงยังไม่
ทดสอบ; Query 102 มี 101 distances จึงเป็นครั้งแรก ไม่ใช่ off-by-one bug
three-sigma เกิดหลัง warm-up check ดังนั้น retained Shapiro n อาจไม่เกิน 100

| Benign prefix ของ condition | Source groups / 110 | W ที่ Q102 | Minimum prefix W | Retained n ที่ Q102 | Prefix first alert |
| --- | ---: | ---: | ---: | ---: | --- |
| 10% | 92 | 0.984098 | 0.951932 | 98 | ไม่มี |
| 25% | 102 | 0.954164 | 0.954164 | 99 | ไม่มี |
| 50% | 95 | **0.920863** | **0.920863** | 100 | **102** |

W threshold = **0.935807** ขณะที่ attack เริ่มที่ query **111** Prefix indices
ทั้งหมดชี้ไป benign pool และทั้งสาม orderings มี ordered prefix และ prefix
distance/W trajectories เหมือนกัน Growing Set lookup ใช้เฉพาะสมาชิกที่เคยเห็น
ก่อนหน้า จึงไม่มีหลักฐานว่า alert นี้เห็น attack queries ในอนาคต

สาเหตุเชิงกลไกที่ยืนยันได้คือ **prefix benign ชุดนี้มี W ต่ำกว่า threshold ตั้งแต่
ครั้งแรก** และ prefix เดียวถูกใช้ทั้ง 1,000 permutations × 3 orderings จึงได้
3,000 prefix alarms ที่ query เดียวกัน นี่คือการทำซ้ำหนึ่ง bad-prefix realization
ไม่ใช่ 3,000 independent confirmations ว่า attack 50% ตรวจได้แน่นอน

ที่ Q102 มี raw distances 101 ค่า กรองออก 1 เหลือ 100; filtered skew = −1.097,
excess kurtosis = 1.394 เทียบ skew ของ prefixes 10%/25% = −0.312/−0.775
เป็นคำอธิบายเชิงรูปร่างของระยะชุดนี้เท่านั้น ยังไม่พิสูจน์ว่ากลุ่มเนื้อหาใดหรือ
กลไก semantic ใดทำให้เกิดรูปทรงดังกล่าว และยังไม่พิสูจน์ว่า small n เป็นสาเหตุ
เพียงอย่างเดียว Alert ถูกต้องตาม PRADA rule แต่ **invalid ในฐานะ attack TP**
และไม่สามารถใช้คำนวณ attack-detection delay ได้

## 6. Prefix ต่างกันข้าม attack ratios ทำให้ confounding อย่างไร

Source code ใช้ seed `seed + 100 + ratio_index` สร้าง benign set/prefix ใหม่
สำหรับแต่ละ ratio และไม่เปลี่ยน prefix ข้าม permutations ภายใน ratio

| Ratios | Shared query members ใน prefixes | Query ตรงตำแหน่งเดียวกัน |
| --- | ---: | ---: |
| 10% vs 25% | 11/110 | 1/110 |
| 10% vs 50% | 18/110 | 0/110 |
| 25% vs 50% | 10/110 | 0/110 |

ดังนั้น onset เท่ากันไม่เพียงพอ: cross-ratio any-alert rate ผสม attack ratio กับ
prefix/source/query membership ที่ต่างกัน อัตรา 100% ที่ 50% เกิดจาก benign
prefix ไปแล้ว จึงไม่ใช่หลักฐาน dose-response ของ attack ratio

การเปรียบเทียบ orderings **ภายใน ratio** ยังเป็น paired comparison บนสมาชิก
และ prefix เดียวกัน แต่เป็น conditional finding ของ cohort เดียวต่อ ratio
ไม่ใช่การยืนยันความสามารถทั่วไปด้วย independent cohorts 1,000 ชุด

## 7. Stream length และ cumulative Shapiro sample size

ใช้เฉพาะ nested prefixes ของ replayed streams เดิมที่ **threshold เดิมของ
horizon 256** ไม่สร้าง threshold ใหม่และไม่เลือก length จากผล test

| Horizon | Eligible tests | Raw distances | Mean retained n cal/test | Cal any-alert | Held-out any-alert |
| --- | ---: | ---: | --- | ---: | ---: |
| 101 | 0 | 100 | ไม่ทดสอบ | 0/200 | 0/200 |
| 102 | 1 | 101 | 99.760 / 99.555 | 7 (3.5%) | 16 (8%) |
| 110 | 9 | 109 | 107.590 / 107.385 | 7 (3.5%) | 19 (9.5%) |
| 128 | 27 | 127 | 125.390 / 125.135 | 8 (4%) | 25 (12.5%) |
| 160 | 59 | 159 | 156.865 / 156.625 | 9 (4.5%) | 28 (14%) |
| 192 | 91 | 191 | 188.435 / 188.150 | 10 (5%) | 31 (15.5%) |
| 224 | 123 | 223 | 219.815 / 219.610 | 10 (5%) | 33 (16.5%) |
| 256 | 155 | 255 | 251.320 / 251.160 | 10 (5%) | 34 (17%) |

Horizon 101 ได้ 0 เพราะยังไม่ทดสอบ ไม่ใช่ detector ที่ดีกว่า เมื่อ horizon ยาวขึ้น
any-crossing event เป็น cumulative จึงเพิ่มหรือเท่าเดิมตามนิยาม แต่ marginal
crossings ณ endpoint 256 มีเพียง 0%/2.5% เทียบ cumulative 5%/17%

**ยืนยัน:** มี early false positives และการสะสม alert จริง; calibration/test gap
เริ่มตั้งแต่ first eligible test (3.5% vs 8%) แล้วขยายเมื่อสะสมประวัติ
**ยังไม่ยืนยัน:** causal effect แยกของ n, จำนวน repeated tests, source geometry
หรือ growing-set dynamics เพราะเปลี่ยนพร้อมกัน และ W tests ใช้ histories ที่
ทับซ้อนกัน ไม่ใช่ independent tests

ระยะเฉลี่ย 101 ค่าแรก → ค่าที่เหลือของ stream ลดจาก 0.92096 → 0.84206 ใน
calibration และ 0.92115 → 0.83890 ใน test สอดคล้องกับ growing-state dynamics
เชิงพรรณนา แต่ไม่ใช่การทดลองควบคุม nonstationarity ทั้งสอง pools ใช้ maximum
ตลอด 155 tests เหมือนกันอยู่แล้ว จึง **ห้ามอธิบาย gap 5% → 17% ด้วยคำว่า
multiple testing เพียงอย่างเดียว** ไม่มี length-matched recalibration หรือ
causal sample-size ablation ใน Phase A นี้

## 8. สถานะข้อค้นพบและสิ่งที่ยังไม่ทราบ

| ประเด็น | สถานะ |
| --- | --- |
| 5% calibration เป็น in-sample P95 exceedance | ยืนยันจาก scores/rule |
| Held-out empirical scores สูงกว่า calibration; FPR 17% | ยืนยัน; ไม่ retune |
| Stream length/replacement rule ต่างกันระหว่าง cal/test | ไม่พบ; ทั้งคู่ตรงกัน |
| Cross-pool ID/text/source-group leakage ตามกฎเดิม | ไม่พบ |
| 200 streams เป็น independent source-disjoint cohorts | ไม่จริง; แชร์ queries ราว 65.5 ต่อคู่ |
| 34 FP first-alert timing และ endpoint recovery | ยืนยันด้วย exact replay |
| Query 102 ของ 50% เกิดจาก benign prefix ก่อน onset | ยืนยัน; ไม่ใช่ attack TP |
| Raw-count warm-up ต่างจาก retained Shapiro n | ยืนยันตาม code/filter |
| Prefix ต่างกันข้าม ratios | ยืนยัน; confound cross-ratio interpretation |
| Specific source/topic/embedding geometry เป็นเหตุของ gap | ยังไม่ยืนยัน |
| Small n หรือ repeated testing อธิบาย gap ทั้งหมด | ยังไม่ยืนยัน; ไม่มี causal controls |
| Threshold/P95 implementation หรือ first-step off-by-one bug | ไม่พบจาก audit/parity |

## 9. Protocol ถัดไปและขอบเขตข้อมูล

ดู [NEXT_PROTOCOL_TH.md](NEXT_PROTOCOL_TH.md): แยก calibration/validation/final
test ตาม source groups และ independent outer cohorts; ใช้ shared ordered prefix
ข้าม orderings **และ ratios ภายใน cohort** แต่ใช้ prefix อิสระข้าม cohorts;
freeze P95 จาก calibration ที่ matching horizon/stream construction; แยก prefix
false alarms, at-risk attack detection และ right-censored delay ตั้งแต่ schema

ข้อมูลเก่าใน Phase A กลายเป็น development evidence แล้ว ห้ามเรียกซ้ำว่าเป็น
untouched final test และห้ามคัด prefix ที่ไม่ alert มาแทนโดยอาศัยผลที่เห็น
Benign 10,062 rows ให้ได้ไม่เกิน **39 query-disjoint streams ยาว 256** รวมทุก
split ก่อนหัก group constraints จึงทำ 200 independent calibration + 200
independent final benign streams ไม่ได้: ต้องมีอย่างน้อย 102,400 unique queries
โดยยังไม่รวม validation ข้อเสนอต้องผ่าน cohort feasibility gate ก่อนเลือก n
ไม่มีการจัดหาข้อมูลใหม่หรือเริ่ม experiment ถัดไปในงานนี้

## การทำซ้ำและ artifacts

ใช้ Conda `senior` เดิมบน experiment branch เท่านั้น คำสั่งแรกวิเคราะห์ scores,
sources และ saved examples โดยไม่รัน BGE/PRADA:

```powershell
conda run --no-capture-output -n senior python stream_prada_order/failure_analysis.py --output stream_prada_order/diagnostics/new_saved_audit
```

หากจำเป็นต้องกู้ benign timing ใหม่ทั้งหมด ให้แจ้งงบ 120 s / RAM 2 GiB / GPU
ประมาณ 1 GiB ก่อน แล้วใช้ `--replay` กับ output directory ใหม่ ห้าม overwrite
งานนี้ได้ทำไปแล้วครั้งเดียวและบันทึก traces ครบ สามารถใช้คำสั่งต่อไปนี้แทน:

```powershell
conda run --no-capture-output -n senior python stream_prada_order/replot_failure_analysis.py --output stream_prada_order/diagnostics/new_plots
conda run --no-capture-output -n senior python stream_prada_order/failure_analysis_details.py --output stream_prada_order/diagnostics/new_details
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests -v
```

Tests ใหม่ 10 รายการครอบคลุม strict alert, warm-up/horizon slicing, transitive
grouping, group-vs-query counts, replay mismatch hard gate, missing timing,
in-sample exceedance และ transient alert/recovery ทั้งหมดใช้ numeric/metadata
fixtures เท่านั้น ทดสอบรวมชุดเดิม 8 รายการ และตรวจ artifact/source hashes
กราฟหลักทั้งสามทำซ้ำ byte-for-byte จาก saved diagnostics ได้โดยไม่โหลดโมเดล

Artifacts อยู่ใน `diagnostics/phase_a/` และ `diagnostics/phase_a_details/`:
analysis JSON, source-composition features, 400 compressed replay traces,
first-alert timing, 34 FP table, horizon/marginal rates, resource/provenance และ
SHA256 manifests ไม่มี raw query, model weights หรือ embeddings ถูก commit

- [Score distributions และ composition](diagnostics/phase_a/score_distributions_composition.png)
- [Timing, stream horizon และ retained n](diagnostics/phase_a/benign_timing_length.png)
- [Prefix confounding](diagnostics/phase_a/prefix_confounding.png)
- [False-positive recovery](diagnostics/phase_a_details/false_positive_recovery.png)

ผล/configuration เดิมทั้งหมดคงเดิมและตรวจ hash ก่อน/หลัง Phase A ไม่มีการนำ
ผล Phase A ไปเปลี่ยน threshold หรือประกาศ detector ใหม่
