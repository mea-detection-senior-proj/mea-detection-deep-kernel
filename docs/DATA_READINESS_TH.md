> Historical document: source locations and commands below predate the migration. Use [current English commands](RUN_EXPERIMENTS.md) and the [migration record](CLEAN_ARCHITECTURE_MIGRATION.md). ADR 0001 governs scientific scope; ADR 0003 supersedes older restructuring guidance.

# ความพร้อมของข้อมูลก่อนรัน baseline จริง

## ขอบเขตและวิธีตรวจ

ตรวจไฟล์ในเครื่อง 3 datasets เท่านั้น ไม่มีการดาวน์โหลดข้อมูลใหม่ สร้าง embeddings ฝึกโมเดล หรือวัดประสิทธิภาพ detector

ใช้ protocol ใหม่จาก `data_pipeline/datasets.py` และ seeds 1/20/42: จัดกลุ่ม ID/normalized text ร่วมกัน, เพิ่ม source context สำหรับ model_leeching, ลบข้อความชนข้าม label, dedup และแบ่ง train/validation/reference/calibration/test ตามจำนวนกลุ่ม 20/10/25/20/25%

ตัวเลขนี้ไม่ใช้ split 4 ส่วนของ Pilot มาปะปน ตรวจซ้ำว่า ID/text และ source context ตาม policy ไม่ข้าม partitions และจำนวน retained rows ตรงกับจำนวน unique texts หลัง cleaning ทั้ง 9 dataset/seed combinations

## จำนวนข้อมูล

| Dataset | Benign ดิบ | Attack ดิบ | Benign หลัง cleaning | Attack หลัง cleaning |
|---|---:|---:|---:|---:|
| model_leeching | 10,062 | 10,062 | 9,900 | 9,923 |
| Meaeq_SST-2 | 10,000 | 1,536 | 10,000 | 1,536 |
| ME_BERT_sst2_wiki | 67,349 | 13,470 | 66,978 | 13,467 |

ไม่พบ normalized text ที่ชนข้าม benign/attack ภายในแต่ละ dataset การลดจำนวนในตารางนี้เกิดจากข้อความซ้ำภายใน label

model_leeching มี attack rows ที่ parse context ได้ครบ 10,062 แถว และ 1,866 unique normalized contexts จึงต้องแบ่งตามกลุ่ม source ต่อไป ไม่สุ่มแถวอิสระ ส่วนสอง SST-2 sets ไม่มี source provenance ที่ตรวจได้ในไฟล์ จึงยืนยันได้เพียง ID/text disjointness

ไฟล์ทั้ง 4 ของสอง SST-2 sets มี SHA256 ตรงกับบันทึก `data_pipeline/provenance/ADDITIONAL_DATA_PROVENANCE.json` ที่อ้าง dataset revision `7f96e886b424cc8cd384190f65c0cf0c6ea90d94` การตรวจนี้เทียบกับบันทึกในเครื่อง ไม่ได้ยืนยัน remote revision หรือ license ใหม่ ส่วน model_leeching บันทึก hash ปัจจุบันแล้ว แต่ไม่พบบันทึก hash อ้างอิงในไฟล์ provenance ดังกล่าว

## จำนวนต่อ partition: ช่วงต่ำสุด–สูงสุดจาก 3 seeds

| Dataset | Train B/A | Validation B/A | Reference benign | Calibration benign | Test B/A |
|---|---|---|---:|---:|---|
| model_leeching | 1,931–2,058 / 1,935–2,064 | 989–1,000 / 995–1,001 | 2,486–2,551 | 1,906–2,029 | 2,392–2,484 / 2,397–2,485 |
| Meaeq_SST-2 | 1,983–2,009 / 298–324 | 985–1,002 / 151–168 | 2,489–2,522 | 1,970–1,997 | 2,501–2,530 / 355–384 |
| ME_BERT_sst2_wiki | 13,331–13,349 / 2,740–2,758 | 6,690–6,718 / 1,326–1,354 | 16,659–16,797 | 13,365–13,480 | 16,764–16,818 / 3,294–3,348 |

B/A หมายถึง benign/attack แต่ละช่วงคำนวณแยกจากสาม seeds ไม่จำเป็นต้องเกิดใน seed เดียวกัน Attack rows ใน reference/calibration partitions ไม่ถูกใช้ตั้ง benign threshold

## Evaluation grid ที่สร้างได้ครบทุก seed

คำว่า “ได้” หมายถึงมีแถวไม่ซ้ำพอภายใน window และมี benign reference/calibration/test พอ ไม่ได้หมายถึงมี windows อิสระเพียงพอสำหรับการอนุมานทางสถิติ

| Dataset | Window 100 | Window 250 | Window 500 | Window 1,500 |
|---|---|---|---|---|
| model_leeching | 1/5/10/25/100% | 1/5/10/25/100% | 1/5/10/25/100% | 1/5/10/25/100% |
| Meaeq_SST-2 | 1/5/10/25/100% | 1/5/10/25/100% | 1/5/10/25% | 1/5/10% |
| ME_BERT_sst2_wiki | 1/5/10/25/100% | 1/5/10/25/100% | 1/5/10/25/100% | 1/5/10/25/100% |

Meaeq_SST-2 มี attacker test เพียง 355–384 queries จึงสร้าง pure-attack window 500/1,500 ไม่ได้ และที่ window 1,500 ratio 25% ต้องใช้ 375 attacks ซึ่ง seed 20 มีไม่พอ

ไม่ควรเพิ่ม attacker ซ้ำภายใน window เพื่อทำให้ช่องเหล่านี้รันได้ เพราะจะเปลี่ยนความหมายของการทดลอง ให้เว้นช่องที่ไม่พอหรือแยก config ของ mixed-only ออกจาก config ที่รวม pure attack

## Ratio ที่ร้องขอกับจำนวน attacker จริง

| Window | 1% | 5% | 10% | 25% | 100% |
|---:|---:|---:|---:|---:|---:|
| 100 | 1 | 5 | 10 | 25 | 100 |
| 250 | 3 | 13 | 25 | 63 | 250 |
| 500 | 5 | 25 | 50 | 125 | 500 |
| 1,500 | 15 | 75 | 150 | 375 | 1,500 |

ใช้ half-up rounding ของ protocol ใหม่ เช่น requested 1% ที่ window 250 เป็น actual 1.2% และ requested 5% เป็น actual 5.2% ต้องแสดง actual ratio/attacker count ในผล ไม่ใช้ชื่อ condition แทนจำนวนจริง

## ความพร้อมสำหรับการฝึก Deep Kernel ในขั้นถัดไป

ตรวจเบื้องต้นภายใต้ training window/reference ขนาดเท่ากัน และ reference benign ไม่ซ้ำกับ benign ส่วนของ incoming window ภายในคู่ฝึก:

- Pure training ขนาด 100: มีข้อมูล train และ validation พอทั้งสาม datasets ทุก seed
- Pure training ขนาด 250: model_leeching และ ME_BERT_sst2_wiki พอ แต่ Meaeq_SST-2 validation attacker มีเพียง 151–168 แถว จึงไม่พอ
- Mixed training ขนาด 100/250 ที่ ratios 1/5/10/25%: มีแถวพอในคู่ train/validation ทุก dataset/seed ที่ตรวจ

นี่เป็นเพียง capacity check ไม่ได้ยืนยัน loss, gradients, sampling schedule หรือประสิทธิภาพ และยังไม่ได้ล็อกขนาดฝึกให้ต้องเท่าขนาดประเมิน ข้อเสนอเริ่มต้นคือ pure training ขนาด 100 แล้วประเมินหลาย window sizes

## การซ้อนทับข้าม dataset

พบ benign normalized texts ที่ซ้ำระหว่าง Meaeq_SST-2 กับ ME_BERT_sst2_wiki **9,629 ข้อความ** คิดเป็น 96.29% ของ benign ใน Meaeq_SST-2

เมื่อใช้ splits ใหม่แยกกันตาม dataset พบ target-test benign ที่ซ้ำกับข้อมูลก่อน test ของ source dataset ดังนี้:

| ทิศทาง | Target-test benign ที่ชน source pretest: seeds 1/20/42 |
|---|---|
| ME_BERT_sst2_wiki → Meaeq_SST-2 | 1,838 / 1,848 / 1,823 |
| Meaeq_SST-2 → ME_BERT_sst2_wiki | 1,770 / 1,797 / 1,800 |

Source pretest ในการตรวจนี้รวม train/validation/reference/calibration ทั้ง labels เพื่อหาส่วนที่อาจเปิดเผยก่อนทดสอบ ไม่ได้อ้างว่าข้อมูลทุกส่วนถูกใช้ฝึก kernel

ไม่พบ exact normalized-text overlap ใน label pairs อื่นระหว่างสาม datasets นี้ แต่ยังไม่ได้ตรวจ semantic near-duplicates, source passages ข้ามทุก dataset, campaigns หรือ users ดังนั้น “ไม่พบข้อความซ้ำ” ไม่เท่ากับยืนยัน independence

ก่อนทำ cross-dataset ต้องจัดกลุ่ม/ลบข้อความซ้ำร่วมกันในระดับหลาย datasets แล้ว audit ใหม่ ห้ามนำผล split แยกแต่ละ dataset มาต่อกันเป็น unseen-family experiment โดยตรง

## Attack-family mapping และขอบเขตที่ยังไม่ยืนยัน

| Dataset | Candidate family จากชื่อ/โครง repo | Candidate domain |
|---|---|---|
| model_leeching | Model Leeching | Context-based QA |
| Meaeq_SST-2 | MeaeQ | SST-2 sentiment |
| ME_BERT_sst2_wiki | ME_BERT | SST-2 target / wiki query source |

Mapping นี้เป็น candidate ยังไม่ได้ verify generation protocol ของ attack แต่ละชุดจากต้นทาง จึงยังไม่ล็อกเป็นสาม independent attack families และความต่าง QA/sentiment อาจเป็น domain shift ควบคู่กับ attack-family shift

ในเครื่องมีเพียงสาม datasets ข้างต้น แม้ README การทดลองเดิมกล่าวถึง 14 datasets ยังไม่ได้ตรวจหรือดาวน์โหลดชุดที่เหลือ ไม่ใช้จำนวน datasets แทนจำนวน attack families

## ข้อเสนอการทดลองรอบถัดไป

1. เริ่ม baseline ภายใน model_leeching: มี source grouping และรองรับ grid ที่เสนอทั้งหมด
2. ใช้ window 100/250 เป็นชุดเปรียบเทียบร่วมทั้งสาม datasets; เพิ่ม 500/1,500 แยกตาม capacity ในตาราง
3. ตรวจ FPR/uncertainty ก่อนเรียกผลว่า matched-FPR comparison: ที่ window 100 มี benign test แบบไม่ใช้แถวซ้ำได้เพียง 23–24 windows ใน model_leeching, 25 ใน Meaeq และ 167–168 ใน ME_BERT; ที่ window 1,500 model_leeching มีได้เพียง 1 window การสุ่มเพิ่มเป็น 100/1,000 windows ไม่สร้างข้อมูลใหม่ที่เป็นอิสระ
4. แยกการประเมินแบบ resampled windows และข้อจำกัดความสัมพันธ์อย่างชัดเจน ไม่รายงาน naive independent-binomial confidence intervals จาก windows ที่ reuse queries
5. เก็บ cross-family/cross-dataset เป็นขั้นหลังจาก global decontamination และยืนยัน family/domain mapping แล้ว

ข้อเสนอเหล่านี้ยังไม่ใช่การรัน baseline จริง และยังไม่ได้เปลี่ยน split หรือ config หลักโดยเงียบ ๆ

## ไฟล์หลักฐานและการรันซ้ำ

ผลรอบนี้อยู่ที่ `artifacts/data_readiness/`: `audit.json`, `split_counts.csv`, `window_capacity.csv`, `training_capacity.csv`, `dataset_overlap.csv` และ `cross_dataset_pretest_overlap.csv` มี hashes ของไฟล์ข้อมูลและโค้ด split ที่ใช้จริง

```powershell
.\.venv\Scripts\python.exe -m experiments.audit_data --output artifacts/data_readiness_run2
```

ใช้ output path ใหม่เสมอ Script ไม่แก้ไฟล์ข้อมูล ไม่ลบผลเดิม และไม่ import โค้ด Pilot ใช้เพียง provenance JSON เดิมเป็นข้อมูลอ้างอิงเมื่อไฟล์นั้นมีอยู่

Tests รวมของทางรันใหม่และ audit ผ่าน 10 รายการ รวมตัวอย่างที่ mixed window พอแต่ pure window ไม่พอ, validation training capacity และการตรวจข้อความรั่วไหลข้าม partitions
