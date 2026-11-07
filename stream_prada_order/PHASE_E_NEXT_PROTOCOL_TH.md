# หลัง Phase E — protocol ที่แนะนำ (ยังไม่ execute)

## คำถามหลักและ go/no-go ก่อนผล

ทดสอบว่า sequential statistic เพิ่มข้อมูลที่ใช้ตรวจ actual extraction traffic
ได้มากกว่าความยาว รูปแบบ และ distribution ของระยะหรือไม่ ที่ stream FPR ซึ่ง
calibrate เท่ากันจริงใน sampling frame ที่กำหนด ไม่มี novelty/generalization
claim จาก Phase A–E และไม่แต่งตั้ง combined/CUSUM/length detector เป็น winner

**No-go** ถ้า label ตรงกับ format/length โดยสมบูรณ์, ไม่มี common support,
ไม่มี source/run provenance, insufficient independent cohorts หรือ victim/
data/model license/access/resource gates ยังไม่ผ่าน

## Sampling frame และ controls

1. เก็บ native chronological benign sessions และ actual extraction runs จาก
   victim/task/rendering ที่เทียบกันได้ เก็บ response dependence/retries/order
   จริง ไม่สร้าง chronology ด้วยการต่อ unrelated conversations
2. Predeclare length strata และ formats โดยอาศัย fit/intake metadata เท่านั้น
   ต้องมี benign long-context/RAG และ attack short/question-only พร้อม
   legitimate repetitive queries/low-distance sessions เป็น hard negatives
   สุ่มหรือ match/reweight ตาม rule ที่ freeze ก่อน scoring; รายงาน retained
   fraction/weights/positivity ทุก stratum ไม่ hide dropped difficult cases
3. มี same-format/same-source comparisons ภายใน domain และ held-out source/
   user/run/attack-family strata แยกกัน User/source/run components เป็น outer units
   repeated schedule/operator seeds เป็น within-unit ไม่เพิ่ม n
4. หากต้องศึกษาสาเหตุ context length ให้ใช้ genuinely acquired query variants
   ที่มีสิทธิ์และ protocol รองรับ รัน frozen embedding/upstream state ใหม่ตาม
   budget แยก ไม่ลบ context จาก saved distances แล้วเรียกว่า causal control

## แยกข้อมูลก่อน scoring

Fit nuisance (length/position/normalization) → calibration benign stream maxima
→ validation สำหรับการตัดสินใจที่ประกาศไว้ → untouched final test
หลัง selection ให้ freeze detector/hyperparameters/threshold rule/source revisions
ใหม่ และใช้ calibration ที่แยกจาก selection ตามแผน ไม่รักษา nominal guarantee
หลังเลือกหลาย candidates โดยไม่มี correction/independent recalibration

สำหรับ rank calibration 5% ต้อง n_cal≥19 เพื่อได้ finite threshold เท่านั้น
ไม่ได้ให้ tail precision ที่ดีหรือ guarantee conditional บน calibration นี้
ถ้าจะอ้าง one-sided exact 95% upper FPR≤5% จาก zero errors ต้อง n_test≥59
ภายใต้ iid Bernoulli cohorts แต่ P(0 errors | true FPR=.05)=.95^59≈4.85%
จึงไม่ใช่ sample-size plan ที่มีโอกาสสูงจะยืนยัน detector ที่ true FPR 5%
ต้องกำหนด precision/power/decision margin และ dependence model ก่อน recruitment
โดยไม่ใช้ permutations แทน independent sources

Current article capacity 23 ของข้อมูลเดิมไม่พอสำหรับ 4 fit+19 calibration+
3 validation อยู่แล้ว และไม่มี articles ที่ใหม่ต่อประวัติ Phase A–E
ขอให้ cohort feasibility audit ของข้อมูลใหม่เป็น prerequisite ก่อนกำหนดจำนวน
และใช้ null/blocked status หาก quota ไม่ครบ ไม่เปลี่ยน requirement เพื่อให้ผ่าน

## Detector/endpoint comparison ที่ต้อง freeze

เก็บ Original Stream PRADA unchanged, length-only negative control และ
non-sequential bag baseline คู่กับ sequential statistics ที่เลือกไว้ล่วงหน้า
ต้องใช้ upstream distance definition เดียวกัน และอธิบายว่า Growing Set เอง
ขึ้นกับ query order ถ้าต้องแยก contribution ของ representation ให้มี reference
bank ที่ freeze จาก fit data เป็น ablation แยก ไม่แก้ Original PRADA

Calibrate any-crossing probability ภายใน native horizon สำหรับแต่ละ statistic
รวม two-sided/rolling/repeated looks; matched nominal alpha ต้องตรวจ actual FPR
และ control uncertainty แยก ห้ามเลือก threshold จาก final outcomes
หากใช้หลาย horizons ให้ calibrate horizon-specific หรือ explicit horizon mixture
ไม่เอา threshold ของ horizon256 ไปอ้างควบคุม horizon อื่น

Sequential value ให้เทียบ detection ณ information budgets/checkpoints ที่กำหนด
ล่วงหน้าด้วย bag baselines ที่เห็น queries เท่ากัน พร้อม repeated-look calibration
และ time-to-event/censoring analysis ไม่เทียบ endpoint145กับmedian detected56
แล้วสรุป unconditional superiority ของ online detector

Random/cluster/interleave เป็น controlled ordering ablations เท่านั้น แยกจาก
native adaptive extraction chronology; fixed-distance shuffle เป็น statistic
sensitivity surrogate ไม่ใช่ rebuilt query/Growing Set counterfactual

## Required outcomes และการหยุด

รายงาน cohort-level TPR/FPR พร้อม intervals, pre-attack alarms, at-risk detection,
unconditional detection fraction, right censoring, delay distributions/detected n,
false alarms ต่อ native exposure และ legitimate long/repetitive hard-negative FPR
แยกบทความ/user/run/domain/family และ leave-source-out sensitivity โดยไม่เลือก
subset ที่ดูดีมาเป็น claim; final reporting รวม failed/negative outcomes

Meaningful sequential evidence ต้องแสดง incremental value เหนือ length/format/
distance-bag controls บน common-support cohorts ที่แยก sources/runs และควบคุม
FPR ได้ตาม protocol พร้อม native chronology/fidelity provenance ไม่ใช่แค่
score ขึ้นเมื่อเข้าช่วง prompts ที่ยาวกว่า หรือ AUC/TPR สูงจาก domain shortcuts

ก่อน download/collection/embedding/teacher/student execution ให้เสนอ exact
release/models/license/access, input manifests, byte/request/token caps,
GPU compatibility/VRAM/RAM/latency projection, runtime hard gate และ stop rules
ใหม่ แล้วจึงเริ่ม bounded acquisition pilot ตามสิทธิ์ที่ได้รับ ยังไม่เริ่มงานเหล่านี้
จากรายงาน Phase E และไม่ push/merge/rebase/PR/main changes
