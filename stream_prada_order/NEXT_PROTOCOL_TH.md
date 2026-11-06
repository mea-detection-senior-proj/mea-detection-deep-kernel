# ข้อเสนอ protocol ถัดไปหลัง Failure Analysis Phase A

สถานะ: **ข้อเสนอเพื่อพิจารณา ยังไม่สร้าง config หรือรัน experiment ถัดไป**
คง Stream PRADA, frozen BGE, minimum L2, Growing Set, three-sigma, warm-up,
Shapiro ทุก query และ one-sided benign P95 ตามเดิม ไม่เสนอ detector ใหม่
หรือเลือก threshold จาก held-out results ที่วิเคราะห์ไปแล้ว

## หน่วยอิสระและการแยกข้อมูล

1. ถือข้อมูล calibration/test เดิมที่ใช้ใน Phase A เป็น development evidence
   ทั้งหมด ไม่ใช้ซ้ำเป็น final test ที่อ้างว่ายังไม่เคยเห็น
2. เชื่อม source groups แบบ transitive ตาม ID/text/context ก่อนแบ่งข้อมูล
   Freeze ข้อมูล revision, file hashes, deduplication rules และ group manifest
   โดยไม่บันทึก query ดิบลง Git ตรวจ label และ group leakage แบบ fail closed
3. แบ่ง source groups ออกเป็น **calibration / validation / final test** ที่ไม่ทับกัน
   และกัน source groups ของ final test ไว้ตั้งแต่ต้น เหตุผลการแบ่งและสัดส่วนต้อง
   กำหนดก่อนเห็น score; ไม่เลือก split ที่ให้ FPR ดีที่สุด
4. สร้าง independent outer query cohorts โดยไม่ใช้ query หรือ source group
   ข้าม cohorts ภายในหรือข้าม split หาก source group ใหญ่ให้ทั้งกลุ่มอยู่ใน
   cohort เดียวหรือเก็บส่วนเกินไว้ไม่ใช้ ห้ามตัดกลุ่มไปสอง cohort เพื่อเพิ่ม n
5. Cohort คือหน่วยข้อมูลอิสระ; permutations ของ cohort เดียวเป็น repeated
   measurements แบบ paired ไม่ใช่ query cohorts อิสระเพิ่มขึ้น

### Feasibility gate ที่ต้องผ่านก่อนกำหนด sample size

Benign เดิมมี 10,062 แถว ก่อนหัก dedup/group constraints ที่ความยาว 256
จึงสร้าง query-disjoint benign cohorts ได้ **ไม่เกิน floor(10,062/256) = 39**
รวมทุก split และจริงอาจน้อยกว่านี้เพราะห้ามแชร์ source group

ตัวอย่างเป้าหมาย 200 independent calibration + 200 independent final-test
benign streams ต้องมีอย่างน้อย **102,400 unique benign queries** โดยยังไม่รวม
validation และ mixed cohorts จึงทำไม่ได้จาก artifact เดิม จำนวน resamples
200/1,000 ครั้งไม่สามารถแก้ข้อจำกัดนี้ได้

ก่อนรอบถัดไปต้องตรวจจำนวน source-disjoint cohorts ที่สร้างได้จริง และเลือก
อย่างชัดเจนระหว่าง (ก) feasibility pilot ขนาดเล็กพร้อม uncertainty กว้างและไม่
อ้าง precise 5% population FPR หรือ (ข) จัดหาข้อมูลจริงจาก source groups ใหม่
และตรวจสิทธิ์/คุณภาพก่อนเริ่ม ห้ามแทนด้วยประโยคสังเคราะห์หรือเปลี่ยนหน่วยนับ
ให้ permutations กลายเป็น independent data การหาข้อมูลใหม่ไม่ถูกดำเนินการ
อัตโนมัติใน Phase A นี้

## Pairing, prefix และ attack onset

- กำหนดความยาว 256 และ prefix 110 เป็นแผนที่ต้องตรวจ feasibility ก่อน freeze
  แต่ละ outer cohort มี prefix เป็นของตนเอง ไม่ใช้ prefix เดียวซ้ำทุก cohort
- **ภายใน cohort เดียว ใช้ ordered benign prefix เดียวกันสำหรับทุก ordering
  และทุก attack ratio** โดย onset ที่ query 111 เท่ากัน
- ภายใน cohort/ratio ใช้สมาชิกชุดเดียวกันทุก ordering และ paired permutation
  seed รวมทั้งสุ่มลำดับภายใน label อย่างสอดคล้องกัน เก็บ order hashes
- สำหรับหลาย ratio ให้ใช้ attack subsets แบบ nested และกำหนด benign fill
  ล่วงหน้า แต่ต้องระบุว่าอัตราเปลี่ยนพร้อมสมาชิก suffix จึงเป็น paired controlled
  comparison ภายใต้ cohort นั้น ไม่ใช่การแยก causal effect โดยไม่มีข้อสมมติ
- ใช้ prefix ทั้งหมดที่สร้างไว้ ไม่ทดลองแล้วคัด prefix ที่ไม่ alert มาแทน การคัด
  เช่นนั้นเปลี่ยน target population และทำให้ FPR/TPR ดูดีเกินจริง
- ให้ benign controls มี horizon และวิธีสุ่ม source/query เช่นเดียวกับ mixed
  cohorts รวมถึง prefix construction ที่สอดคล้องกัน

## Calibration, validation และ final test

1. ใช้เฉพาะ calibration cohorts หา P95 ของ **maximum stream score** ตลอด
   horizon ที่ระบุ ไม่ใช้ percentile ของ W query เดียวแทน stream maximum
   เก็บทั้ง scores, query order hashes และ per-query traces ตั้งแต่เริ่ม
2. หากประเมินหลาย stream lengths ให้ preregister horizons และใช้ calibration
   สำหรับ horizon แต่ละอันเท่านั้น เก็บ detector algorithm/rule เดิม ไม่ใช้
   current held-out test P95 ที่ 0.084479 เป็น threshold ใหม่
3. Freeze threshold และการจัด stream ก่อนใช้ validation Validation มีหน้าที่
   ตรวจ FPR transport, prefix false alarms, provenance, resource และคุณภาพ
   หาก fail ให้รายงาน protocol failure และหยุด ไม่แก้ด้วยการดู final test
4. หากเปลี่ยน protocol หลัง validation ต้องเป็น revision ใหม่ที่มีบันทึกชัดเจน
   ห้ามอ้าง validation เดิมว่าเป็น confirmation ของ protocol ที่แก้แล้ว
5. Final test ใช้ครั้งเดียวเมื่อ protocol/threshold ถูก freeze แล้ว รายงานทั้ง
   negative results และ prefix failures ไม่ retune และไม่เปิด final pool เพื่อ
   เลือก encoder/seed/prefix/length

## Endpoint และ uncertainty ที่ต้องรายงาน

- Benign stream-level any-alert FPR พร้อม denominator ระดับ independent cohort
- Prefix false-alarm rate ก่อน onset แยกจาก post-onset crossings เสมอ
- Any-alert rate ของ mixed stream พร้อมคำเตือนว่าอาจเป็น prefix false positive
- First attack-detection rate เฉพาะ cohorts ที่ยัง at risk ณ onset โดยแสดงจำนวน
  eligible/cohorts ทั้งหมด และรายงาน unconditional prefix failure ควบคู่กัน
- Detection delay เป็น null/ineligible ถ้าเคย alert ก่อน onset; nondetection
  หลัง onset เป็น right censoring ไม่แทนด้วย 0 และไม่ละทิ้งโดยไม่แสดงจำนวน
- Alert-change counts แบบ paired ภายใน cohort รวม Growing Set/Distance/W
  trajectory differences และ maximum score differences
- แยก uncertainty ระหว่าง **independent cohorts** ออกจาก Monte Carlo error
  ของ permutations ใช้ outer-cohort bootstrap หรือ paired cohort summaries
  ตามแผนที่กำหนดไว้ ไม่ใช้ 1,000 permutations เป็น n=1,000 population samples
- หลีกเลี่ยง causal attribution ว่า sample size เป็นเหตุเพียงอย่างเดียวเมื่อ
  horizon, retained distance count, growing-set state และจำนวน tests เปลี่ยน
  พร้อมกัน หากต้องแยกกลไกให้เสนอ diagnostic ใหม่พร้อม controls และงบก่อนรัน

## Logging และ hard gates

บันทึกต่อ stream: cohort/source manifest hashes, ordered query indices/hashes,
label/onset, d_min ทุก query, Growing Set growth, threshold history, raw/retained
Shapiro n, W/test query, first alert, endpoint W, maximum score และ censoring
เก็บ runtime/peak memory และ environment/model/data/config/code hashes

Unit tests ต้องครอบคลุม source-group isolation, membership/prefix/onset pairing,
raw-count warm-up, strict threshold, timing/censoring และการไม่อ้าง prefix alert
เป็น attack detection Parity กับ frozen reference เป็นเงื่อนไขบังคับ

ให้ resource gate, license/data provenance และ cohort feasibility ผ่านก่อน
เริ่ม encode และ freeze เวอร์ชัน protocol บน experiment branch แยกเดิม
ไม่มีการแก้ Deep Kernel MMD, merge หรือ push โดยอัตโนมัติ
