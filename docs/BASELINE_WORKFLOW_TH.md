> Historical document: source locations and commands below predate the migration. Use [current English commands](RUN_EXPERIMENTS.md) and the [migration record](CLEAN_ARCHITECTURE_MIGRATION.md). ADR 0001 governs scientific scope; ADR 0003 supersedes older restructuring guidance.

# ทางรัน baseline สำหรับพัฒนา Deep Kernel MMD

## สถานะ

แยก Single-RBF และ Multi-RBF ออกจากตัวจัดการทดลองแล้ว และเพิ่ม Deep Kernel แบบ pure training ผ่าน locked comparison workflow ดู [DEEP_KERNEL_PROTOCOL_TH.md](DEEP_KERNEL_PROTOCOL_TH.md) สำหรับคำสั่งรันเต็ม ยังไม่ได้ย้าย baseline อื่นหรือเปลี่ยน Pilot/ผลเดิม

ทางรันใหม่เป็น protocol ใหม่ที่ตั้งใจแก้การแยก reference/calibration และใช้ repeated score เดียวกันทั้ง calibration/test จึงไม่อ้างว่าเป็นการ reproduce ตัวเลขเดิมแบบตรงตัว แม้สูตร MMD และชุด bandwidth ของ fixed kernels จะเทียบกับโค้ดเดิมแล้ว

## โครงสร้างที่ใช้งานได้

```text
detectors/mmd/detector.py       สูตร kernel/MMD และคะแนนเฉลี่ยหลาย references
data_pipeline/datasets.py      อ่าน JSONL, dedup และแบ่งกลุ่มไม่ให้ข้าม partitions
data_pipeline/embeddings.py    Frozen sentence encoder และ content-addressed cache
data_pipeline/windows.py       สร้าง windows และ reference draws ร่วมกัน
evaluation/windows.py         ตั้ง threshold และประเมินทุกวิธีด้วย draws เดียวกัน
experiments/run.py             เชื่อม workflow และบันทึกผล
configs/experiments/           เลือกวิธี seed และเงื่อนไขทดลอง
tests/test_mmd_pipeline.py     Numerical/protocol/integration tests
artifacts/                    ผลใหม่และ cache; ไม่เข้า Git
```

ยังไม่สร้างโฟลเดอร์ว่างสำหรับ Deep Kernel/demo หรือ shell scripts ที่เพียงเรียก Python อีกทอดหนึ่ง เมื่อมีงานจริงจึงเพิ่มในกลุ่มที่ออกแบบไว้

## คำสั่งใหม่

ปัจจุบัน `experiments.run` เตรียม lock และสรุปผลให้ในคำสั่งเดียว พร้อม flags สำหรับ window/seed/counts ดู [คู่มือ CLI ปัจจุบัน](RUN_EXPERIMENTS_TH.md) ผลดิบของ CLI อยู่ใต้ `output/results/` และรายงานใต้ `output/report/` ส่วนผังผลแบบเดิมในเอกสารนี้อธิบาย artifacts รุ่นก่อน

รันจากราก repository บน PowerShell ด้วย environment ที่มี dependencies ใน `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m experiments.run --help

.\.venv\Scripts\python.exe -m experiments.run `
  --config configs/experiments/mmd_smoke.json `
  --device cuda `
  --embedding-model artifacts/models/bge-small-en-v1.5 `
  --output artifacts/my_first_smoke

.\.venv\Scripts\python.exe -m experiments.run `
  --config configs/experiments/mmd_comparison.json `
  --device cuda `
  --embedding-model artifacts/models/bge-small-en-v1.5 `
  --output artifacts/my_mmd_comparison

.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux ใช้ `python` จาก environment แทน `.\.venv\Scripts\python.exe` และเขียนคำสั่งบรรทัดเดียวได้ ไม่มี Bash เป็นข้อบังคับ

ตัวอย่างใช้ encoder ที่คัดลอกไว้ใต้ `artifacts/models/bge-small-en-v1.5` ไม่มีการอ่านไฟล์หรือ import โค้ดจาก Pilot ข้อมูล provenance สำหรับ audit อยู่ใต้ `data_pipeline/provenance/` ส่วน `pilot/` ยังเก็บไว้ครบ สามารถเปลี่ยนเป็นโฟลเดอร์ encoder อื่นได้ ใช้ `--device cpu` ได้เช่นกัน โมเดลใต้ `artifacts/` ไม่เข้า Git จึงต้องเตรียมเองเมื่อติดตั้งในเครื่องใหม่

หากใช้โมเดลจาก Hugging Face ให้ใส่ `embedding_model` และ `embedding_revision` เป็น commit SHA 40 ตัวใน config ต้องระบุ revision ที่ตรึงไว้จริง มิฉะนั้นโปรแกรมจะปฏิเสธ เพื่อไม่ให้ cache/ผลทดลองใช้โมเดลต่างเวอร์ชันโดยไม่รู้ตัว Config ตัวอย่างจึงต้องใช้ local-model override ตามคำสั่งด้านบน หรือเพิ่ม pinned revision ก่อนรัน

`--config` อ้างจาก working directory; paths ภายใน config อ้างจากราก repository หรือเป็น absolute paths ส่วน paths ของ benign/attack ใน dataset specification อ้างจาก `data_root` คำสั่งที่แนะนำให้เริ่มจากราก repo เพื่อให้หา package ได้

ปัจจุบันไม่ต้องมี dataset specification JSON: ใช้ `--dataset <ชื่อโฟลเดอร์>` อ่าน `data/<ชื่อ>/normal/queries.jsonl` และ `attacker/queries.jsonl` โดยตรง คำอธิบาย specification รุ่นก่อนเก็บไว้เพื่ออ้างอิง artifacts เก่าเท่านั้น

แต่ละ output ต้องเป็น path ใหม่เสมอ ไม่มีการ resume/skip อัตโนมัติ หากล้มเหลวจะเก็บสถานะ `failed` ไว้ ไม่เอา metadata ที่มีอยู่มาสรุปเป็นงานสำเร็จ

## Protocol

1. อ่านข้อมูลและจัดกลุ่มร่วมจาก ID และ normalized text; `model_leeching` เพิ่มกลุ่ม source context ที่ parse ได้
2. ลบ normalized text ที่ชนข้าม benign/attack และ dedup ภายใน label
3. แบ่งเป็น train/validation/reference/calibration/test ด้วยสัดส่วนจำนวนกลุ่ม 20/10/25/20/25%; จำนวนแถวจริงไม่จำเป็นต้องตรงสัดส่วน
4. สำรอง train/validation สำหรับงานเรียนรู้ในขั้นถัดไป Fixed baselines ยังไม่ใช้สองชุดนี้เลือกพารามิเตอร์
5. ประมาณ median bandwidth จาก benign reference เท่านั้น Single RBF ใช้ค่านี้ Multi-RBF ใช้ 0.5/1/2/4 เท่าและเฉลี่ยเท่ากัน
6. สร้าง benign calibration windows แยกจาก reference และ test
7. ทุกวิธีใช้ windows และ reference draws ชุดเดียวกัน รวมถึง reference repeats ตาม config
8. ใช้ upper empirical quantile แบบ `higher` และแจ้งเตือนเมื่อ score มากกว่า threshold; ไม่ใช้ test ปรับ threshold และไม่อ้าง finite-sample FPR guarantee
9. สรุป detection rate ของ benign เป็น measured FPR และของ attacker/mixed เป็น TPR ต้องอ่านทั้งสองค่าคู่กัน

Window size คือจำนวน queries ของ incoming window; reference draw มีขนาดเท่ากันใน protocol รุ่นนี้ ค่า reference repeats คือจำนวน reference draws ที่นำคะแนนมาเฉลี่ย

ในแต่ละ window สุ่มโดยไม่คืนตัวอย่าง แต่ windows ต่างกันและ reference draws ต่างกันอาจใช้ query ซ้ำ จึงไม่ถือว่า windows ทั้งหมดเป็นอิสระ

Mixed windows กำหนดจำนวน attacker คงที่ ใช้การปัด half-up และจำกัดให้อยู่ระหว่าง 1 กับ window_size - 1 สำหรับ ratio ที่ไม่ใช่ 0/1 ผลบันทึกทั้ง requested ratio, actual ratio และจำนวน attacker จริง เช่น 1% ของ 250 จะได้ 3/250 = 1.2%

Strict grouped splits อาจทำให้ข้อมูลบางชุดไม่พอ โดยเฉพาะ window ใหญ่และ pure attack โปรแกรมจะตรวจความเพียงพอก่อนโหลด encoderและไม่สุ่มซ้ำภายใน window เพื่อกลบปัญหานี้ ให้แยก config ลด grid หรือเลือก dataset ที่เพียงพอ

## ผลลัพธ์

```text
artifacts/<run>/
├─ config.json                  Config หลังรวม CLI overrides
├─ metadata.json                Status, data/code identity, software และ encoder identity
├─ embedding_manifest.json      Hash ของข้อความตามลำดับ embedding indices
├─ summary.csv                  FPR/TPR แยกวิธี seed window size และ split
└─ seed_<seed>/
   ├─ split_audit.json
   ├─ split_manifest.json       Hashed IDs/texts ของทุก partition
   └─ window_<size>/
      ├─ scores.csv
      ├─ calibration_scores.csv
      ├─ draw_manifest.json    Embedding indices ของ windows และ references ที่ใช้จริง
      └─ metadata.json         Bandwidths และ thresholds
```

Small smoke config ใช้เพียง 8 calibration windows และ 4 test windows ต่อ condition มีไว้ตรวจว่าระบบทำงานครบ ไม่ใช้ตัดสินประสิทธิภาพหรืออ้างว่าคุม FPR 5% ได้

## ขั้นต่อไป

ตรวจความพร้อมของข้อมูลรอบแรกแล้ว ดู [DATA_READINESS_TH.md](DATA_READINESS_TH.md) โดยเฉพาะข้อจำกัด pure windows ของ Meaeq_SST-2 และ benign overlap ข้ามสอง SST-2 datasets รัน audit ใหม่โดยไม่โหลด encoder ได้ด้วย `python -m experiments.audit_data --output artifacts/data_readiness_run2`

- ตรวจความเพียงพอของข้อมูลและเลือก grid สำหรับ baseline จริง
- ระบุสูตร Deep Kernel/variance objective และตรวจ gradients ก่อนนำ implementation จาก Pilot มาใช้
- เพิ่ม pure-training แล้ว mixed-training ด้วย config แยก โดยตรึง held-out evaluation draws สำหรับการเปรียบเทียบ
- กำหนด family/domain mapping ก่อนทำ unseen-family และ cross-dataset experiments
- เพิ่ม aggregate variability/plots และ baseline อื่นหลังเส้นทาง MMD ตรวจแล้ว

ข้อมูลที่รองรับตอนนี้: model_leeching, Meaeq_SST-2 และ ME_BERT_sst2_wiki โดยสองชุด SST-2 มี benign ซ้อนทับกัน และ source independence ของชุด ID/text-only ยังไม่ยืนยัน การประเมินข้ามสองชุดนี้โดยตรงยังไม่ใช่หลักฐาน unseen-family generalization
