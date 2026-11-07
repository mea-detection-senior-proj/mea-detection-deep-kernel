# Stream PRADA Phase C — ผล bounded article-cohort pilot

วันที่ 7 พฤศจิกายน 2026 (Asia/Bangkok)

สถานะ: **รันครบ bounded pilot 100 permutations ต่อ cohort/ratio/order**
บน `experiment/stream-prada-order` ไม่ใช่ full 1,000-permutation study

ผลสำคัญคือไม่พบ benign-control FP หรือ pre-attack alert ในรอบนี้ แต่ตรวจจับ
attack ประมาณ 10% ได้น้อยมาก (0.25% ทุก ordering) ที่ 50% orderings ให้ผล
ต่างกันและ cohorts มีความแปรปรวนสูง ข้อมูลทุก article เคยใช้มาก่อนและ n=8
จึงยังยืนยัน population FPR≤5%, deployability หรือ superiority ไม่ได้

## Protocol ที่ freeze ก่อนเห็นผล

Freeze commit: `c62768dd26818e1ffb68c854dda4d51dfe87cc23`

ใช้ [PHASE_C_PROTOCOL_V1.md](PHASE_C_PROTOCOL_V1.md) และ
[phase_c_config_v1.json](phase_c_config_v1.json) ที่ commit ก่อน encoding/scoring:

- Phase B certificate เดิม: 12 calibration / 3 validation / 8 evaluation cohorts
  แบบ Wikipedia article-disjoint; SHA256 `25970769c8e5128aa974ae00eae723ec56ffe984169a7499f38ca0ee49649b53`
- Stream 256; ordered benign prefix 110 และ first attack query 111 เหมือนกัน
  ทุก ratio/order/permutation ภายใน cohort; source groups/queries ไม่แชร์ข้าม cohorts
- Actual attack counts 26/64/128 = 10.15625%/25%/50% จาก nested attack subsets
  ใช้ seed 20261107 และ 100 permutations เป็น bounded pilot ตั้งแต่ต้น
- Frozen BGE revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, batch 64,
  normalized embeddings, no prefix, max length 512, inference/eval mode
- Minimum L2/Growing Set/adaptive threshold/three-sigma/Shapiro/warm-up เดิม
  ผ่าน `experiment.trace` โดยไม่แก้ detector; first eligible test query 102
- ใช้ maximum score `1-min(W)` และ linear P95 จาก 12 calibration streams
  เท่านั้น ไม่ใช้ validation/evaluation fit threshold และไม่ retune หลังเห็นผล
- Shared benign prefix ไม่ถูกคัดใหม่เมื่อเห็น scores และไม่มีการใช้ BoolQ

Validation gate ที่ประกาศก่อนผล: benign controls ต้องมี **0/3 any alerts** และ
prefix alarms **0/3**; resource projection รวม safety factor 2 ต้องไม่เกิน
1,200 s หากไม่ผ่านต้องหยุดก่อน encode/score evaluation ไม่เปลี่ยน scope

ข้อจำกัดที่ประกาศไว้ก่อนผล: calibration/validation มีหนึ่ง article ต่อ cohort;
evaluation มีหนึ่ง cohort ที่บทความเดียวและเจ็ด cohorts ที่รวมสองบทความ
จึงมี source-composition shift ที่เป็นไปได้ แม้ไม่เกิด article leakage ข้าม split

## Gates และจำนวนที่รันจริง

| รายการ | ผล |
| --- | --- |
| Input/source/cohort/model hashes, CUDA operation | ผ่าน |
| Reference parity 12 cases (calibration ตัวแรก + benign controls) | W max absolute error 0.0 ทุก case; growth count/first alert ตรง |
| Calibration | 12 streams |
| Validation controls | 0/3 any alerts; 0/3 prefix alarms — gate ผ่าน |
| Validation pilot ก่อน evaluation | 135 mixed streams (3×3×3×5) |
| Runtime projection รวม safety factor 2 | 498.80 s < 1,200 s — gate ผ่าน |
| Validation mixed ครบ 100 permutations | 2,700 streams |
| Evaluation | 8 controls + 7,200 mixed streams |
| Mixed streams / paired comparisons รวม | 9,900 / 9,900 |
| Full stream traces รวม | 9,923 = 12 calibration + 11 controls + 9,900 mixed |

Evaluation encoding เกิดหลัง validation/resource gates ผ่านเท่านั้น ไม่ใช้
evaluation outcomes เลือก settings ข้อมูลที่นำมา encode รวม 7,296 unique queries
แบ่ง calibration+validation 4,224 และ evaluation 3,072 queries

Threshold calibration-only = **0.04839049083312644**, W boundary =
**0.9516095091668736** ใช้ strict `W < boundary` Calibration มี 1/12 exceedance
= **8.33% in sample** ตามข้อจำกัด empirical P95 เมื่อ n เล็ก ไม่ใช่ 5% พอดี
ไม่ใช้ค่า P95 จาก evaluation มาปรับแก้

## Benign FPR และ pre-attack alerts

| Split | Benign control FP | Two-sided exact 95% interval | Prefix-alarm cohorts |
| --- | --- | --- | --- |
| Validation | 0/3 = 0% | [0%, 70.76%] | 0/3 |
| Evaluation | **0/8 = 0%** | **[0%, 36.94%]** | **0/8** |

Intervals ถือ independent identically distributed Bernoulli cohorts ตามนิยาม
เชิงปฏิบัติ แต่ reused sources และ population mismatch ไม่ได้ถูกแก้ด้วย interval
ถ้าใช้ one-sided exact 95% upper สำหรับ 0/8 จะเป็น **31.23%** ไม่ขัดกับค่า
two-sided 36.94% ซึ่งเป็นคนละ convention ทั้งสองไม่ยืนยัน FPR≤5%

Mixed streams ทั้ง validation/evaluation ไม่มี pre-attack alerts เช่นกัน
ดังนั้นรอบนี้ any-alert เท่ากับ first post-onset detection และทุก evaluation
cohort ยัง at risk ณ onset แต่ schema ยังคงแยก pre-alert/ineligible/null delay
เพื่อไม่ทำซ้ำข้อผิดพลาดของการตีความ Phase A

**ไม่เปรียบเทียบ 17% เดิมกับ 0/8 ใหม่ว่าเป็น detector improvement**:
cohort composition, query sets, calibration sample size, threshold และ prefix
construction ต่างกัน ไม่มี controlled ablation ที่แยกสาเหตุของความต่างนี้

## Evaluation detection และ delay

ทุกช่องมี **8 outer cohorts × 100 conditional schedules = 800 schedules**
ไม่ใช่ 800 independent population trials ค่าเฉลี่ย schedule rates เท่ากับ
ค่าเฉลี่ย cohort rates ในรอบนี้เพราะแต่ละ cohort มี 100 schedules เท่ากัน

| Attack จริง | Order | Post-onset detections / 800 | Rate | Median delay / detected | Right-censored | Mean max score |
| --- | --- | --- | ---: | --- | ---: | ---: |
| 10.15625% | Random | 2 | 0.25% | 61.5 / 2 | 798 | 0.023942 |
| 10.15625% | Clustered | 2 | 0.25% | 33 / 2 | 798 | 0.023637 |
| 10.15625% | Interleaved | 2 | 0.25% | 50 / 2 | 798 | 0.023895 |
| 25% | Random | 21 | 2.625% | 130 / 21 | 779 | 0.025224 |
| 25% | Clustered | 62 | 7.75% | 55 / 62 | 738 | 0.029082 |
| 25% | Interleaved | 21 | 2.625% | 118 / 21 | 779 | 0.025047 |
| 50% | Random | 198 | 24.75% | 108 / 198 | 602 | 0.041206 |
| 50% | Clustered | 288 | 36.00% | 96 / 288 | 512 | 0.045130 |
| 50% | Interleaved | 221 | 27.625% | 111 / 221 | 579 | 0.041333 |

Delay นับ first alert query minus 111; nondetection เป็น right censoring ที่
stream end ตัวเลข median เฉพาะ detected schedules อาจเป็นคนละ subset ระหว่าง
orderings จึงไม่ใช่ unconditional time-to-detection superiority โดยเฉพาะที่
10% มีเพียงสอง detections ต่อ ordering

ที่ 50% clustered rate ระหว่าง cohorts อยู่ในช่วง **3–98%**, random **0–81%**
และ interleaved **0–87%**: ความต่างระหว่าง cohorts ใหญ่มาก ตัวอย่าง cohort 15
clustered 48% ต่ำกว่า random 54% แต่ cohort 21 clustered 65% เทียบ random 20%
จึงไม่ใช่ uniform ordering advantage

Descriptive outer bootstrap 95% (resample 8 cohort summaries, 2,000 draws)
ที่ 50% ให้ random 8.88–44.75%, clustered 16.00–57.38%, interleaved 10.88–48.26%
เป็นเพียง small-n reused-cohort summary ไม่ครอบคลุม calibration uncertainty
หรือให้ population confidence guarantee Conditional MC Wilson intervals ต่อ
cohort แยกอยู่ใน `summary.json` ไม่ใช้ denominator 800 แทน outer n=8

## Alert changes และ trajectory differences

แต่ละแถวมี 800 paired comparisons จาก 8 cohorts ไม่ใช่ 800 independent
cohorts Delta score คือ B ลบ A; distances/W เปรียบเทียบตาม query position
ที่สอดคล้องกัน และ Growing Set symmetric difference ใช้สมาชิก final sets

| Attack | A → B | Changed alerts | Mean Δ max score | Mean Growing symdiff | Distance MAE | W MAE |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 10.15625% | R → C | 4/800; 0.50% | −0.000304 | 12.570 | 0.076856 | 0.003011 |
| 10.15625% | R → I | 4/800; 0.50% | −0.000047 | 12.275 | 0.076016 | 0.002816 |
| 10.15625% | C → I | 2/800; 0.25% | +0.000258 | 2.440 | 0.074979 | 0.002179 |
| 25% | R → C | 55/800; 6.875% | +0.003858 | 13.973 | 0.083434 | 0.005140 |
| 25% | R → I | 32/800; 4.00% | −0.000178 | 13.758 | 0.081031 | 0.003105 |
| 25% | C → I | 41/800; 5.125% | −0.004036 | 2.320 | 0.082149 | 0.004485 |
| 50% | R → C | 212/800; 26.50% | +0.003924 | 14.163 | 0.077014 | 0.007038 |
| 50% | R → I | 179/800; 22.375% | +0.000127 | 14.005 | 0.076093 | 0.005735 |
| 50% | C → I | 89/800; 11.125% | −0.003798 | 0.825 | 0.073119 | 0.004091 |

R=random, C=clustered, I=interleaved เมื่อพิจารณาทั้งสาม orderings ใน paired
triplet เดียว มีอย่างน้อยหนึ่ง alert ต่างกัน **5/800 = 0.625%**, **64/800 = 8%**
และ **240/800 = 30%** ที่ attack 10.15625%, 25%, 50% ตามลำดับ
คู่ทั้งสามใน triplet ไม่เป็นอิสระต่อกัน ไม่บวก counts เป็นจำนวน observations ใหม่

ผลนี้รองรับ conditional order sensitivity โดยเฉพาะที่ 50% บน cohorts นี้
พร้อม negative finding ว่า low-ratio detection ต่ำมาก ไม่ใช่ novelty หรือ
deployable detector และไม่พิสูจน์ว่า article grouping เป็นสาเหตุของผลใด

## Runtime, provenance และ verification

| รายการ | ผล |
| --- | ---: |
| เวลารวม runner | **273.456 s = 4.56 min** |
| Runtime gate | 1,200 s |
| Projected total หลัง pilot รวม safety factor 2 | 498.802 s |
| Process peak working set | 1,450.57 MiB |
| GPU peak allocated / reserved | 680.14 / 882.00 MiB |
| Encoding calibration+validation / evaluation | 2.104 / 2.739 s |
| Maximum single-cohort distance matrix | 589,824 bytes |

Peak process working set และเวลาของ embedding แต่ละ stage อยู่ใน metadata
และ embedding JSONs ใช้ environment `senior` เดิม ไม่มีการติดตั้งหรือเปลี่ยน
packages/weights Raw data, model และ historical-source hashes ตรวจครบ
ไม่มีการแก้ prior tracked files ตาม runner และ independent Git check

Unit tests รวม **36 ผ่าน** (เดิม 27 + Phase C ใหม่ 9) ครอบคลุม matching prefix,
nested membership, seed reproducibility, strict threshold, prefix ineligibility,
right censoring, delay 0 ณ onset, benign control ที่ไม่ถูกนับเป็น attack detection
และ validation hard gate

Independent saved-result audit ตรวจ **9,900 schedule hashes, 9,900 pairs,
9,923 full traces**, รวม score/min-W, first alerts, growth membership differences,
Distance/W MAE, delays/censoring, gate order และ frozen commit/source/config
โดย **ไม่รัน encoder/detector ซ้ำ**

## Artifacts และการทำซ้ำ

ผลอยู่ใน `results/phase_c_pilot_20261107_v1/`: calibration/control traces,
per-cohort score/pair tables แบบ gzip, permutation-zero examples ที่เลือกล่วงหน้า,
gates, environment, timing/memory, parity และ summary ไม่มี raw queries/weights
หรือ embeddings ใน Git Full traces ทั้งหมดเก็บ local/ignored พร้อม hashes
ไม่ commit large logs และไม่ overwrite run directory

กราฟและ audit อยู่ใน `diagnostics/phase_c_verified/`:

- [Calibration/controls/validation W และ evaluation rates](diagnostics/phase_c_verified/phase_c_diagnostics.png)
- [Per-cohort alarm/detection breakdown](diagnostics/phase_c_verified/cohort_alarm_breakdown.png)
- `verification.json`: integrity audit; `findings.json`: tables ที่ใช้สรุปรายงาน

ตรวจจากไฟล์ที่เผยแพร่โดยไม่ใช้ local full logs:

```powershell
conda run --no-capture-output -n senior python stream_prada_order/phase_c_audit.py stream_prada_order/results/phase_c_pilot_20261107_v1 --summary-only --output stream_prada_order/diagnostics/new_phase_c_audit
```

ถ้าต้องการ audit full local traces ให้ตัด `--summary-only` ออก
Runner ทำซ้ำได้ด้วย output ใหม่ภายใต้ source/config ที่ commit และ prerequisites
ที่ตรึงไว้ แต่ไม่จำเป็นต้องรันซ้ำเพื่ออ่านผลนี้ ไม่มีการขยายเป็น 1,000 permutations
หรือเริ่ม experiment รอบใหม่โดยอัตโนมัติ

## ข้อสรุปและขอบเขตการหยุด

Phase C ทำ bounded pilot ครบตาม frozen protocol และผ่าน validation/resource
gates; รอบนี้แก้ **การจัด protocol/pairing และการนับ metrics** โดยไม่เปลี่ยน
detector ไม่ใช่หลักฐานว่าปัญหา FPR transport ถูกแก้ทั่วไปแล้ว

ข้อจำกัดยังคงมี: reused articles, n=12 calibration/n=8 evaluation, source-count
composition shift, ไม่มี real chronological sessions และ low-ratio detection ต่ำ
มาก ต้องตรวจผลก่อนพิจารณางานใหม่ ไม่ retune จาก evaluation, ไม่เพิ่มข้อมูล
ไม่ implement detector ใหม่ ไม่ push/merge/rebase/PR และคง main เดิม
