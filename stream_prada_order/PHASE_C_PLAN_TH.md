# แผนถัดไปหลัง Phase B — ยังไม่รัน experiment

ข้อเสนอนี้คง frozen Stream PRADA/BGE และ P95 rule เดิม ไม่ implement detector
ใหม่ ไม่มีการเปลี่ยน threshold จากผล held-out และไม่ถือว่าอนุมัติ full execution

## ทางเลือกหลักที่ทำได้ด้วยข้อมูลปัจจุบัน

ใช้ `model_leeching` ในระดับ **Wikipedia article-disjoint outer cohorts**
จาก allocation certificate `proposed_article_model_leeching_12_3_8.json.gz`:

- Calibration: 12 cohorts × 256 benign queries
- Validation/protocol check: 3 paired cohorts
- Evaluation partition: 8 paired cohorts
- หนึ่ง paired cohort มี benign reservoir 256 + attack reservoir 128 queries
  และใช้ source groups ไม่ซ้ำกับ cohort/split อื่น

ทั้งหมด 23 outer cohorts มี manifest ที่จัดได้จริงแล้ว แต่ข้อมูลทุก article
ถูกใช้ใน Phase A จึงเป็น **exploratory re-partitioning เท่านั้น** ห้ามเรียก
evaluation partition นี้ว่า untouched confirmatory final test
ไม่มีการเลือก article/seed ตาม PRADA scores

## ลำดับงานที่ต้อง freeze ก่อนประเมิน

1. ทบทวนวัตถุประสงค์ให้เป็นการตรวจ protocol/conditional order sensitivity
   พร้อมยอมรับว่า n=8 evaluation cohorts ไม่รับรอง FPR≤5%
2. ตรวจ source/data/model/license/provenance และ hashes ของ cohort manifests
   อีกครั้ง ไม่แตะไฟล์ผล/config เดิม Commit protocol version แยกบน branch ทดลอง
3. ใช้ stream length 256, warm-up raw distances >100, strict comparison,
   common ordered benign prefix 110 และ attack onset query 111
4. ภายใน cohort ใช้ **prefix เดียวกันทุก ratio/order** โดยไม่คัด prefix ที่
   ไม่ alert มาแทน ข้าม cohorts ใช้คนละ queries/source groups
5. Attack counts = 26/64/128 สำหรับเป้าหมาย 10%/25%/50% ใช้ nested subsets
   จาก attack reservoir 128 และ benign fills จาก reservoir เดียวกัน
   ทุก ordering ภายใน cohort/ratio มีสมาชิกเหมือนกัน เก็บ pairing seeds/hashes
6. ใช้ benign control stream 256 queries ของแต่ละ validation/evaluation cohort
   ด้วย จึงทราบว่าตัว block นั้น false alarm โดยไม่มี attack หรือไม่
   เป็น matched control ภายใน cohort ไม่ใช่ observation อิสระเพิ่มหนึ่งตัว
7. Encoder และ algorithm เดิม หา threshold จาก **calibration 12 stream maxima
   เท่านั้น** เก็บ per-query distance/Growing Set/raw+retained n/W/first alert
   ตั้งแต่รอบแรก เก็บ n เล็กและ calibration tail uncertainty ในรายงาน
8. Validation 3 cohorts ตรวจ implementation, provenance, prefix failures และ
   threshold transport ห้ามแก้โดยดู evaluation 8 cohorts หากต้องแก้ protocol
   ให้หยุดเป็น revision ใหม่ ไม่แอบคัด validation examples หรือ thresholds
9. เมื่อแผนถูก freeze แล้วจึงเปิด evaluation partition ครั้งเดียวภายใต้
   protocol revision นั้น แต่ยังคงป้าย reused/development data ตามประวัติจริง

อย่ารันกรณี BoolQ article-disjoint ในขั้นตอนนี้ เพราะ source mapping ยังไม่ครบ
หากอยากตรวจ passage-level sensitivity แยกต่างหาก มี certificate 20/4/10 ที่
จัดได้จริง แต่ต้อง label ว่าเป็น sensitivity/reference ไม่ใช่ article-held-out
confirmation ไม่ pool threshold ข้าม datasets และไม่เอามารวมเป็น n ใหญ่ขึ้น

## Endpoints และ uncertainty

- Benign any-alert FPR ต่อ independent outer cohort ภายใต้ grouping ที่ระบุ
- Prefix false-alarm rate ก่อน onset และ unconditional mixed any-alert rate
- Post-onset first detection เฉพาะ cohorts ที่ยัง at risk พร้อม denominator
  eligible/total แยกชัด; pre-alert เป็น failure ไม่ใช่ attack TP
- Delay null/ineligible สำหรับ pre-alert; right-censored สำหรับ nondetection
- Paired alert-change counts, maximum score และ Growing Set/Distance/W changes
  ต่อ cohort/ratio แล้วค่อยสรุประหว่าง cohorts
- แยก between-cohort uncertainty ออกจาก within-cohort permutation Monte Carlo
  error; ไม่ใช้ permutations เป็น n ระดับ population และไม่ bootstrap แถวที่
  แชร์ source groups ราวกับอิสระ

แม้ไม่มี benign FP เลยใน n=8 cohorts ค่า one-sided 95% upper FPR ยังเป็น
**31.23%** ภายใต้ independent Bernoulli assumption ส่วน calibration n=12
มี P95 tail resolution หยาบ ไม่รับประกัน calibrated 5% จึงรายงานเป็น pilot
ที่อาจล้มเหลวได้ และไม่เรียก 0/8 ว่า FPR ต่ำกว่า 5%

## Resource gate ก่อนรอบใหม่

Phase B ไม่ encode หรือรัน detector ข้อประมาณต่อไปนี้เป็น planning estimate
จาก runtime เก่าประมาณ 0.0285 s/stream ไม่ใช่ resource preflight ใหม่:

- Evaluation 8 cohorts × 3 ratios × 3 orderings × 100 permutations = 7,200
  mixed streams: ราว 205 s เฉพาะ scoring ก่อน setup/encoding/validation
- ถ้าใช้ 1,000 permutations จะเป็น 72,000 streams: ราว 2,052 s หรือ **34 นาที**
  เฉพาะ scoring จึงอาจเกิน 20/25-minute budget เดิม ต้องขออนุมัติงบใหม่หาก
  projected runtime เกิน gate ห้ามลด scope หลัง freeze เพื่อให้ผ่านเงียบ ๆ
- หากเลือก 100 permutations ให้เลือกในฐานะ **bounded pilot ตั้งแต่ก่อนรัน**
  ไม่อ้างว่าเทียบเท่า independent cohorts หรือ full 1,000-permutation study
- ทำ CPU/GPU/RAM/license/hash preflight และ pilot 5 paired permutations บน
  validation cohorts ก่อน โดยยังไม่ใช้ evaluation outcomes เลือก runtime settings
- ใช้ per-cohort distance caches แบบ bounded; ตรวจ numerical parity กับ
  reference ก่อน หลีกเลี่ยงสร้าง matrix ทั้ง corpus โดยไม่ประเมิน RAM

ไม่เริ่ม encoding/full execution จนกว่างานทดลองรอบนั้นจะได้รับมอบหมายและ
protocol/resource gate ชัดเจน แผนนี้ไม่ใช่การอนุมัติ push หรือ integration

## ถ้าต้องการ final confirmation จริง

ต้องมี source/user/session-disjoint data ที่ยังไม่ถูกประเมินมาก่อน และมี
benign กับ actual extraction-query labels ที่ตรวจได้ ไม่ใช่เพียงเปลี่ยน seed:

1. เลือกแหล่ง benign เช่น curated legitimate sessions จาก public conversation
   corpus และแหล่ง attack-query collection ที่ provenance/license ผ่าน
   ตรวจเงื่อนไขและ group by user/time/content โดยไม่พยายามระบุตัวบุคคล
2. ตรวจ duplicates/article/source overlap กับข้อมูลเก่าและข้าม splits ก่อน
   ดู detector scores สงวน final sources ตั้งแต่ต้น
3. อย่างน้อย 59 genuinely independent final benign cohorts ที่ zero FP
   จึงจะได้ one-sided 95% upper ต่ำกว่า 5% ตามสมมติฐาน binomial ยังไม่ใช่
   การ estimate 5% อย่างแม่นยำ; เลือก sample size จาก precision/power ที่ต้องการ
4. จัด calibration/validation data เพิ่มแยกต่างหากและคำนึงถึง uncertainty ของ
   empirical P95 ด้วย ไม่ย้าย final data กลับมาปรับ threshold
5. ถ้า license, source mapping, independence หรือจำนวน cohorts ไม่ผ่าน ให้
   report blocker และหยุด ไม่ใช้ synthetic queries หรือเปลี่ยน labels ทดแทน

ทางเลือกเพิ่มข้อมูลและข้อจำกัด license อยู่ใน [PHASE_B_FEASIBILITY_TH.md](PHASE_B_FEASIBILITY_TH.md)
ไม่มีการดาวน์โหลด WildChat/LMSYS/MEA-Bench corpus หรือสร้าง attack queries
ใน Phase B นี้
