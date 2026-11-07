# Phase C v1: frozen bounded exploratory pilot

วันที่ 7 พฤศจิกายน 2026; งานนี้ได้รับมอบหมายจากผู้ใช้ว่า “ทำ phase c”
ใช้ branch `experiment/stream-prada-order` และ allocation article-disjoint
12 calibration / 3 validation / 8 evaluation ของ Phase B ตาม hash ใน config

## ขอบเขตที่ freeze ก่อน scoring

- ใช้ `phase_c_config_v1.json` และ `phase_c_runner.py` ที่ commit ก่อนรัน
  ไม่แก้ผล/configs/implementation เดิม ไม่ใช้ BoolQ หรือเพิ่ม dataset
- เลือก **100 permutations ต่อ cohort/ratio/order** เป็น bounded pilot ตั้งแต่ต้น
  ไม่ใช่ full 1,000-permutation study และไม่ใช่ independent cohorts เพิ่มขึ้น
- Frozen BGE snapshot, max length 512, batch 64, normalized embeddings,
  no query prefix; CPU float32 per-cohort cdist และ `experiment.trace` เดิม
- Seed 20261107; stream 256; prefix 110; first attack query 111;
  attack counts 26/64/128 จาก nested fixed subsets ของ reservoir 128
- Benign order ของแต่ละ cohort มาจาก SeedSequence([seed,cohort,0]);
  attack reservoir order จาก [seed,cohort,1]; paired schedule จาก
  [seed,cohort,ratio_index,permutation,2] ไม่เลือก seed ตามคะแนน
- **Ordered prefix เดียวกันทุก ratio/order/permutation ภายใน cohort**
  และไม่ใช้ query/article source group ข้าม cohorts/splits
- Calibration มีหนึ่ง benign stream ต่อ cohort (รวม 12) ใช้ linear P95 ของ
  maximum scores เฉพาะชุดนี้ ไม่ใช้ validation/evaluation fit threshold
- Scoring ครบ stream แม้ alert แล้ว; min W, distance history, Growing Set,
  adaptive threshold history, raw/retained sample count และ first alert ถูกเก็บ

## Hard gates และการหยุด

1. Branch/input/cohort/model/frozen-source hashes ต้องตรง ไม่มี source leakage
   CUDA operation ต้องผ่าน; driver-free GPU ≥1.5 GiB และ free RAM ≥2 GiB
2. Actual-query reference parity ต้องผ่าน W absolute tolerance 2e-5,
   Growing Set count และ first-alert decision ต้องตรง ห้ามเปลี่ยน algorithm
3. Encode/score เฉพาะ calibration และ validation ก่อน evaluation
4. Validation pilot ใช้ 5 paired permutations ต่อ cohort/ratio/order = 135
   mixed streams ร่วมกับ benign controls 3 streams
5. Resource projection = elapsed + 2 × P95 pilot stream seconds × remaining
   stream count ต้อง ≤1,200 s เช็ก deadline ระหว่าง native operations/streams
   หากเกินให้หยุด ไม่เพิ่มเป็น 25 นาทีหรือปรับ scope โดยอัตโนมัติ
6. **Validation gate:** benign controls ต้องมี any-alert **0/3** และ prefix
   alarms **0/3** หากผิดแม้หนึ่ง cohort ให้หยุดก่อน encode/score evaluation
   บันทึกว่า validation failed ไม่ retune/reseed/resample prefix และไม่แอบเปิด
   evaluation เพื่อเลือก setting Gate นี้เป็น quality screen ไม่ใช่หลักฐาน FPR≤5%
7. หากผ่านจึงใช้ validation permutations 5–99 และเปิด evaluation ครั้งเดียว
   ภายใต้ revision นี้: 8 controls และ 7,200 mixed streams รวมทั้งหมดเมื่อครบ
   validation/evaluation = 9,900 mixed + 11 benign controls + 12 calibration

## Interpretation ที่ประกาศก่อนผล

ข้อมูลทุก article เคยใช้ใน Phase A แล้ว จึงเป็น exploratory re-partitioning
ไม่ใช่ untouched final confirmation ที่ n=8 แม้ 0 FP ยังได้ one-sided 95% upper
FPR 31.23% ภายใต้ iid Bernoulli assumptions และ n=12 calibration มี tail
uncertainty สูง ไม่อ้าง population FPR control

Source composition ไม่เท่ากันทุก split: calibration/validation เป็นหนึ่ง article
ต่อ cohort; evaluation มีหนึ่ง cohort บทความเดียวและเจ็ด cohorts สองบทความ
นี่เป็นข้อจำกัดที่ทราบก่อน scoring ไม่ใช่เหตุให้เปลี่ยน allocation ย้อนหลัง และ
ยังไม่ใช่ causal explanation ของ FPR หากพบ transport failure

แยก any-alert, prefix false alarm, eligible-at-onset, post-onset first detection,
null/ineligible delay และ right censoring เสมอ ไม่เรียก prefix alert ว่า TP
รายงาน per-cohort rates และ conditional permutation MC intervals แยกจาก
between-cohort descriptive bootstrap; n เล็ก/แหล่งข้อมูลซ้ำไม่ให้ population
coverage guarantee ไม่มีการใช้ permutations เป็นจำนวน outer observations

## Resource และ artifacts

คาด encoding/scoring อยู่ใน 20 นาที แต่ต้องใช้ measured preflight ตัดสิน
Per-cohort matrix สูงสุด 384×384 float32 = 589,824 bytes ไม่สร้าง corpus-wide
distance matrix Cached vectors/weights ไม่ commit; evaluation encoding ทำหลัง
gate เท่านั้น เก็บ environment และ peak RAM/GPU จริง

Full per-query traces ของทุก stream เก็บ local gzip/ignored พร้อม SHA256
Commit calibration/control traces, permutation-zero examples, full score/pair
tables แบบ gzip แยก cohort, gates, summary, provenance และรายงานภาษาไทย
เก็บผล blocked/failed attempt ไม่ overwrite

Freeze commit นี้เป็นขั้นเตรียมตามแผน Phase C แล้วดำเนินงานที่ผู้ใช้มอบหมาย
ต่อจนถึงผลของ gates/รอบ pilot จบ จึงทำ local result commit และหยุด
ไม่ push, merge, rebase, cherry-pick หรือเปิด PR และไม่แก้ `main`
