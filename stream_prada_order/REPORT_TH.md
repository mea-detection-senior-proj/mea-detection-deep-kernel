# รายงานผล Stream PRADA: ความไวต่อลำดับคำถาม

วันที่ตามบริบทผู้ใช้: 6 พฤศจิกายน 2026

สถานะ: **ครบ 1,000 permutations ต่อ ordering ต่อ attack ratio** รวม 9,000 mixed
streams พบว่าลำดับเปลี่ยน alert ราย stream บนชุดข้อมูลที่ตรึงไว้ แต่ held-out
benign FPR คือ **34/200 = 17%** และเงื่อนไข attack 50% ทุก stream alert ก่อน
attack เริ่ม จึงไม่สนับสนุนการใช้งานที่ FPR 5% หรือข้ออ้างว่าตรวจ attack ได้ 100%

## การแยก branch และการอนุมัติ

ทุกไฟล์อยู่บน `experiment/stream-prada-order` ใน worktree แยก เริ่มจาก main
`5fb5e07d750a73a0a663a174433bab931ae7568a` ไม่แก้ PRADA/pilot/Deep Kernel
implementation เดิม ไม่มี push, merge, rebase, cherry-pick หรือ PR

รอบแรก `results/seed20261106` หยุดที่ projection 21.12 นาที ภายใต้งบ 20 นาที
เก็บไฟล์เดิมและ null metrics ไว้ พร้อม [รายงาน preflight](REPORT_PREFLIGHT_TH.md)
ผู้ใช้ตอบ **Approve a 25-minute gate** จึงสร้าง `config_25min.json` เปลี่ยนเฉพาะ
resource limit 1,200 เป็น 1,500 วินาที โดยไม่เปลี่ยน experimental settings

ความพยายามแรกภายใต้งบใหม่ล้มเหลวก่อน calibration เพราะ relative config path
ใน provenance เก็บ `results/seed20261106_25min/failure.json` ไว้ แก้โค้ดพร้อม
regression test แล้วรันใหม่ใน `results/seed20261106_25min_retry1` โดยไม่ทับ
blocked/failed attempt ใด

## ข้อมูลและ protocol

ใช้คำถามจริง `model_leeching` จาก repository artifact: benign และ attack
อย่างละ 10,062 แถว อ่านสำเนาใน checkout ข้างเคียงโดยไม่แก้ไข ไม่มีประโยค
สังเคราะห์ ไม่มีการเรียก LLM/API และไม่มีการฝึกหรือปรับน้ำหนัก encoder

ใช้ `pilot/protocol.py` เดิม จัดกลุ่ม transitive ตาม shared ID, normalized text
และ attack source context ก่อนแบ่ง partition จากนั้นสุ่ม calibration benign,
held-out benign และ held-out attack อย่างละ 1,000 คำถามด้วย seed คงที่
Audit ไม่พบ ID/text/attack context ข้าม partition ภายใต้กฎนี้ แต่ไม่ได้พิสูจน์ว่า
ไม่มี semantic overlap ทุกชนิด Calibration/test มี 369/371 source groups
Train/validation ไม่ถูกใช้

Frozen encoder คือ `BAAI/bge-small-en-v1.5` revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`: eval/inference mode, gradients
ปิด, normalized embeddings, ไม่มี query prefix, max length 512 ใช้ cached model
เท่านั้น Query pools, model files, embedding hash และ split audit ของรอบสมบูรณ์
ตรงกับรอบ blocked เดิมทั้งหมด ไม่ commit ข้อมูลดิบ น้ำหนัก หรือ embeddings

Stream ยาว 256 คำถาม มี benign prefix 110 และ first attack ที่ query 111
เหมือนกันทุก ordering ภายในแต่ละ ratio ใช้ seed 20261106, calibration 200
streams, held-out benign 200 streams และ 1,000 paired permutations ต่อ ordering
ต่อ ratio รวม 9,000 mixed streams และ 9,000 pairwise comparisons

Attack เป้าหมาย 10%, 25%, 50% ใช้ 26/64/128 คำถาม อัตราจริงคือ 10.15625%,
25%, 50% สมาชิกคงที่หนึ่งชุดต่อ ratio ตลอด 1,000 permutations Random สุ่ม suffix
ภายใต้ prefix/onset ที่บังคับ; clustered วาง attack ต่อกันหลัง prefix; interleaved
กระจาย attack อย่างสม่ำเสมอใน suffix แต่ละ paired seed แชร์ลำดับภายใน label
ร่วมกัน การเปรียบเทียบข้าม ratio มีสมาชิก/prefix ต่างกัน จึงไม่ใช่ causal
dose-response ของ attack ratio และทุก ordering เป็น offline simulation
ไม่ใช่ chronological API trace จริง

## Algorithm และ parity

Local reference ตรงกับ [LabRAI Stream PRADA](https://github.com/LabRAI/mmd-llm-mea-detection/blob/af9420da12a03bf321a2218870a68f7b38f5787c/PRADA/prada_stream_detector.py)
ที่ Git blob `5f951afa8cc750c5497e4efd793100db0648ad6a` Parity ในที่นี้หมายถึง
PRADA-style adaptation บน embeddings นี้ ไม่ใช่ original image PRADA ที่ตรวจ
แยกต่างหาก

คง minimum L2 distance, Growing Set เริ่มด้วย growth-distance 0, adaptive
threshold = max(previous, mean minus population SD), Distance History ทุก query,
inclusive three-sigma พร้อม upstream fallback และ Shapiro–Wilk ทุก query หลัง
มีระยะ **มากกว่า 100 ค่า** (ครั้งแรกที่ query 102) ไม่มี Shapiro subsampling
ที่ความยาวนี้ วัดต่อหลัง alert เพื่อให้ maximum score/trajectory เปรียบเทียบได้

Score = `1 - min(W)` ใช้ common linear benign P95 **0.06419320835771236** หรือ
W threshold **0.9358067916422876** และ strict `W < threshold` ทุก ordering/ratio
ใช้ threshold เดียวกัน Distance lookup ใช้ shared CPU float32 torch.cdist matrix

Unit/parity suite ผ่าน 8 tests ครอบคลุม warm-up/strict alert, membership/prefix/
onset, monotone threshold, invalid input, projection, reference parity ทั้ง direct
และ precomputed, relative-path provenance และ LF JSON bytes Real-query parity
3 streams ให้ W error 0.0 ทุก stream รวม Growing Set count และ first alert ตรงกัน
Delta 0.99 ใน parity ใช้ทดสอบโค้ดเท่านั้น ไม่ใช่ผล detection-rate experiment

## Alert, delay, maximum score และ Growing Set

ทุก rate ใช้ 1,000 schedules ต่อช่อง ช่วง 95% เป็น Wilson **conditional Monte
Carlo** interval ของ fixed query set/prefix ไม่ใช่ population confidence interval
Delay = first alert query minus 111 (onset alert = 0) คำนวณ median เฉพาะ detected
streams ที่ไม่มี prefix alarm และเก็บ nondetection เป็น right censoring

| Attack จริง | Order | Any alert / 1,000 (95%) | Prefix alarms | Median delay / detected | No alert | Mean max score | Mean Growing Set size |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| 10.15625% | Random | 366; 36.6% (33.67–39.63%) | 0 | 4 / 366 | 634 | 0.061262 | 178.209 |
| 10.15625% | Clustered | 344; 34.4% (31.52–37.40%) | 0 | 2 / 344 | 656 | 0.061667 | 178.772 |
| 10.15625% | Interleaved | 350; 35.0% (32.11–38.01%) | 0 | 5 / 350 | 650 | 0.060784 | 178.207 |
| 25% | Random | 310; 31.0% (28.21–33.93%) | 0 | 22 / 310 | 690 | 0.059746 | 162.361 |
| 25% | Clustered | 430; 43.0% (39.96–46.09%) | 0 | 12 / 430 | 570 | 0.063202 | 162.849 |
| 25% | Interleaved | 310; 31.0% (28.21–33.93%) | 0 | 25 / 310 | 690 | 0.059484 | 162.303 |
| 50% | Random | 1,000; 100% (99.62–100%) | 1,000 | null / 0 eligible | 0 | 0.079168 | 115.523 |
| 50% | Clustered | 1,000; 100% (99.62–100%) | 1,000 | null / 0 eligible | 0 | 0.079180 | 115.510 |
| 50% | Interleaved | 1,000; 100% (99.62–100%) | 1,000 | null / 0 eligible | 0 | 0.079182 | 115.504 |

ที่ 50% ทุก first alert เกิด **query 102** ก่อน first attack query 111 Prefix
คงเดิมทำให้ false alarm นี้ซ้ำทุก permutation จึงไม่มี eligible first-detection
delay และห้ามเรียก any-alert 100% ว่า attack detection 100% หรือแทน null ด้วย
delay 0/ติดลบ ไม่มีการตัด prefix หรือปรับ threshold ย้อนหลังให้ผลดีขึ้น

ที่ 10% aggregate rates ใกล้กัน แต่ individual alerts เปลี่ยนมาก ที่ 25%
clustered minus random = +12 percentage points; paired conditional normal
95% interval ของผลต่าง = +8.12 ถึง +15.88 points ที่ 10% ผลต่าง = −2.2 points
(−6.05 ถึง +1.65) จึงไม่มีข้อได้เปรียบทิศทางเดียวทุก ratio Delay median ที่ต่ำกว่า
ไม่แปลว่าดีกว่าทั้งระบบ เพราะมี nondetection มากและเป็นคนละ detected subset

## จำนวน alert ที่เปลี่ยนและความต่างของ trajectory

แต่ละแถวมี 1,000 paired seeds ที่สมาชิก/prefix/onset ตรงกัน Delta score คือ
ค่าเฉลี่ย maximum score ของ B ลบ A Distance MAE เทียบประวัติ 255 ตำแหน่ง,
W MAE เทียบ 155 eligible steps และ Growing symmetric difference นับสมาชิก
ใน final sets ที่ไม่ร่วมกัน ค่าเฉลี่ย min W เท่ากับ 1 minus mean max score

| Attack จริง | A → B | Changed alerts | Mean Δ max score | Distance MAE | W MAE | Growing symmetric diff | Mean Δ growing size |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 10.15625% | Random → Clustered | 386/1,000; 38.6% | +0.000404 | 0.071794 | 0.007703 | 15.925 | +0.563 |
| 10.15625% | Random → Interleaved | 402/1,000; 40.2% | −0.000479 | 0.070051 | 0.008008 | 16.184 | −0.002 |
| 10.15625% | Clustered → Interleaved | 310/1,000; 31.0% | −0.000883 | 0.069835 | 0.005719 | 3.049 | −0.565 |
| 25% | Random → Clustered | 406/1,000; 40.6% | +0.003456 | 0.084461 | 0.008585 | 12.160 | +0.488 |
| 25% | Random → Interleaved | 382/1,000; 38.2% | −0.000262 | 0.082756 | 0.008388 | 12.072 | −0.058 |
| 25% | Clustered → Interleaved | 204/1,000; 20.4% | −0.003718 | 0.083572 | 0.006654 | 1.366 | −0.546 |
| 50% | Random → Clustered | 0/1,000; 0% | +0.000012 | 0.063423 | 0.005110 | 12.115 | −0.013 |
| 50% | Random → Interleaved | 0/1,000; 0% | +0.000015 | 0.062948 | 0.004717 | 12.097 | −0.019 |
| 50% | Clustered → Interleaved | 0/1,000; 0% | +0.000003 | 0.060211 | 0.002259 | 1.014 | −0.006 |

เมื่อดูสาม ordering ร่วมกัน มีอย่างน้อยหนึ่ง ordering ให้ alert ต่างจากอีกอัน
**549/1,000 = 54.9%** ที่ 10.15625% (Wilson 51.80–57.96%), **496/1,000 = 49.6%**
ที่ 25% (46.51–52.69%) และ 0/1,000 ที่ 50% (upper conditional bound 0.383%)
รวม 1,045/3,000 triplets; คู่ทั้งสามในแต่ละ triplet พึ่งพากัน ห้ามนับว่าเป็น
independent streams การที่ alert ที่ 50% ไม่เปลี่ยนไม่ใช่ order invariance:
Growing Set/Distance/W หลัง prefix ยังต่างกัน แต่ false alarm เกิดไปก่อนแล้ว

รายละเอียด uncertainty, score-delta quantiles และทุก permutation อยู่ใน JSON
และ CSV.gz Quantiles เป็น distribution ของ permutations ไม่ใช่ confidence
interval ของ population mean ไม่ใช้ zero-variance normal interval เป็นหลักฐาน
ความแน่นอนเมื่อไม่พบ discordant alerts

## Held-out benign FPR

Calibration strict exceedances = 10/200 = 5% ตาม construction ส่วน held-out
benign ได้ **34/200 = 17%**, conditional Wilson 95% **12.43–22.82%** จึงไม่ผ่าน
observed target 5% บน held-out pool นี้ P95 จาก calibration ไม่รับประกัน
held-out FPR 5% ยังสรุปสาเหตุของความคลาดเคลื่อนจากผลนี้เพียงอย่างเดียวไม่ได้
ไม่มีการใช้ test pool ปรับ threshold และไม่อ้างว่า ordering ใดใช้จริงได้ดีกว่า

## เวลา หน่วยความจำ และ reproducibility

| รายการ | ค่าที่วัดได้ |
| --- | ---: |
| เวลารวม runner รวม setup/calibration/evaluation/กราฟเดิม | 305.1435 s (5.086 min) |
| เวลา encode 3,000 คำถาม | 4.5847 s |
| Mixed-stream runtime mean / P95 / max | 0.02851 / 0.05694 / 0.09744 s |
| Process peak working set | 1,532,456,960 bytes (1,461.46 MiB) |
| PyTorch GPU peak allocated / reserved | 680.14 / 882.00 MiB |
| Shared distance matrices ตามรูปทรง | 20,000,000 bytes |
| Approved gate | 1,500 s |

Initial projection = 1,250.87 s; pilot projections 10%/25%/50% = 1,261.90 /
1,332.26 / 818.41 s ทุก gate ผ่านโดยคง 2x safety factor เวลารวมด้านบนไม่รวม
การเขียนรายงานและ postprocessing หลัง runner จบ RAM เป็น process peak,
GPU allocation เป็นของ PyTorch process นี้ ไม่ใช่ยอดทั้งเครื่อง/ทุก process

ใช้ Conda `senior` เดิมบน RTX 4060 Ti: Torch 2.14.1+cu132, NumPy 2.4.6,
SciPy 1.17.1, sentence-transformers 5.7.0 ไม่ติดตั้ง/เปลี่ยน environment
การทำซ้ำข้าม hardware/library อาจมี floating point differences จึงบันทึก
source/config/data/model/artifact hashes และ environment ไว้

แก้ปัญหา Windows CRLF/Git LF ใน commit แรก โดยคืน original hashed bytes ของ
evidence ลง Git ด้วย scoped `-text` ไม่แก้ measured values หรือ manifests เดิม
JSON ใหม่เขียน LF ชัดเจน CSV เต็มเก็บเป็น lossless gzip ไม่มี deliverable เกิน
1 MB ตรวจทั้ง staged blob bytes และ working-file bytes ก่อน commit

Audit ตรวจ 9,000 reconstructed schedule hashes, 9,000 paired differences,
200 calibration และ 200 benign streams; ตรวจ threshold/alert/count/delay/
censoring/summary/intervals/example trajectories/source/artifact hashes และ gzip
roundtrip พร้อมแยก source/output hashes ของ postprocessing

## ขอบเขตข้อสรุปและหลักฐาน

ผลรองรับ **order sensitivity ของ Stream PRADA adaptation บน fixed offline
query cohorts นี้** ไม่รองรับ population FPR control, generalization ข้าม dataset,
model หรือ length, deployable improvement, causal mechanism ที่พิสูจน์แล้ว
หรือ novelty ของ detector ไม่มีการ retune ตามผลและไม่มี experiment เพิ่มนอก
scope ที่อนุมัติ 1,000 permutations ไม่ใช่ 1,000 independent query cohorts;
benign streams ใช้ pool เดิมซ้ำ ช่วง uncertainty ทุกอันจึง conditional ต่อ
pool/prefix/model/protocol นี้

หลักฐานใน `results/seed20261106_25min_retry1/` ได้แก่ `summary.json`,
`supplemental_summary.json`, full CSV.gz, metadata/calibration/parity/gates,
artifact/archive/postprocessing manifests และ `validation.json`

- [กราฟแยก prefix false alarms](results/seed20261106_25min_retry1/alarm_outcomes.png)
- [กราฟ example trajectories](results/seed20261106_25min_retry1/example_trajectories.png)
- [กราฟ paired differences](results/seed20261106_25min_retry1/paired_differences.png)

`rates_scores_fpr.png` เป็นกราฟเดิมของ runner ที่ใช้คำว่า detection rate แทน
any-alert field จึงรวม prefix false alarms ที่ 50% ให้ใช้ `alarm_outcomes.png`
และตาราง prefix ในรายงานนี้ตีความ Graph examples ใช้ permutation 0 ที่เลือก
ไว้ล่วงหน้า ไม่เลือกจากผลที่ให้ความต่างมากที่สุด
