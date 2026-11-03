# แผนจัดโครงสร้างและการทดลอง Deep Kernel MMD

สถานะ: เริ่ม implementation ทางรัน baseline ใหม่แล้ว โดยยังเก็บโค้ดเดิมและ Pilot ไว้

ความคืบหน้า: แยก detector/data pipeline/evaluation พร้อมคำสั่ง `python -m experiments.run` และ config สำหรับ fixed baselines แล้ว เพิ่ม Deep Kernel แบบ pure training และ protocol lock สำหรับการเปรียบเทียบร่วม ดู [BASELINE_WORKFLOW_TH.md](BASELINE_WORKFLOW_TH.md) และ [DEEP_KERNEL_PROTOCOL_TH.md](DEEP_KERNEL_PROTOCOL_TH.md) ส่วน mixed training, generalization และ baseline อื่นยังเป็นขั้นถัดไป

## ข้อตกลงจากการสนทนา

- คำถามหลัก: Deep Kernel MMD ช่วยตรวจ model extraction ที่ attacker ratio ต่ำและ window เล็กได้ดีกว่า fixed-kernel MMD หรือไม่ ภายใต้ FPR เป้าหมายเดียวกัน
- วิธีหลัก: Single-RBF MMD, Multi-RBF MMD และ Deep Kernel MMD
- Deep Kernel ฝึกด้วย benign และ known attacker; หลังฝึกตรึง kernel แล้วตั้ง threshold ด้วย benign-only calibration
- เริ่มด้วย pure-attack training แล้วเพิ่ม mixed-window training เป็นการเปรียบเทียบ โดยใช้ Deep Kernel implementation เดียวและเปลี่ยน config
- ประเมิน low-ratio mixed traffic ตั้งแต่รอบแรก แม้ฝึกด้วย pure attack
- เปรียบเทียบ pure/mixed training ด้วยการเริ่มฝึกใหม่และงบฝึกใกล้เคียงกัน; curriculum/fine-tuning ยังไม่ใช่แผนหลัก
- รองรับการประเมินภายใน dataset และข้าม dataset/attack family โดยแยกเงื่อนไขให้ชัด
- Pilot แยกจากระบบหลักได้; เปลี่ยนคำสั่งรันได้ แต่ต้องอธิบายทิศทางก่อนเปลี่ยน
- Deep Kernel ที่ฝึกด้วย benign-only ยังไม่อยู่ในขอบเขตหลัก

## โครงสร้างเป้าหมายที่เสนอ

```text
detectors/           วิธีตรวจจับและการฝึกที่เฉพาะกับแต่ละวิธี
data_pipeline/       อ่านข้อมูล ตรวจซ้ำ แบ่งชุด สร้าง embeddings/windows
experiments/         จัดลำดับฝึก เลือกโมเดล calibrate และประเมิน
evaluation/          Metrics ตาราง และกราฟ
configs/             Dataset specifications และ experiment settings
artifacts/           ผลที่เกิดจากการรัน: results/checkpoints/logs/cache
data/                ข้อมูลนำเข้า
demo/                Offline demonstration หลัง pipeline วิจัยพร้อม
pilot/               งานสำรวจและผลเดิม แยกจากระบบหลัก
tests/               ทดสอบโค้ดและ protocol
docs/                ข้อตกลง วิธีรัน และคำอธิบายผล
```

เริ่มย้ายเฉพาะ MMD และสร้าง Deep Kernel ในโครงใหม่ก่อน Detector อื่นยังอยู่ตำแหน่งเดิมจนผ่านการเปรียบเทียบและตรวจความถูกต้อง ไม่ย้ายทั้ง repo พร้อมกัน

Single RBF และ Multi-RBF ใช้ MMD implementation ร่วมกัน ต่างกันที่ kernel/config ไม่สร้าง pipeline ซ้ำ ส่วน Deep Kernel มีโมเดลและขั้นฝึกเพิ่ม

Detector รับข้อมูลที่เตรียมแล้วและคืนคะแนน/สถานะที่จำเป็น ไม่เลือก dataset ไม่แบ่ง train/test และไม่จัดโฟลเดอร์รายงานเอง Detector แบบ stateful ในอนาคตยังเก็บสถานะของตนเองได้

Experiment เป็นผู้คุม lifecycle และ calibration policy; ตัวคำนวณคะแนนที่ใช้ calibrate ต้องเป็นตัวเดียวกับที่ใช้ประเมิน รวมถึง reference repeats และขนาด reference

## การจับคู่ของเดิมกับกลุ่มใหม่

| ของเดิม | ตำแหน่ง/บทบาทเป้าหมาย |
|---|---|
| สูตร RBF, Multi-RBF และ MMD ใน `MMD_detection/mmd_detector_gpu.py` | `detectors/mmd/` |
| JSONL, embeddings และ window construction ที่ปนใน detector | `data_pipeline/` หลังตรวจความต่างระหว่าง implementation |
| Deep Kernel ใน `pilot/deep_mmd/` | ตรวจสูตร/gradient/objective ก่อนเลือกนำมาใช้ใน `detectors/deep_kernel_mmd/` |
| ตัวรัน main/sensitivity และ shell scripts | `experiments/` แยกตามคำถามทดลอง |
| การคำนวณ metrics และสรุปผล | `evaluation/` |
| ค่าที่ฝังใน shell scripts | `configs/` |
| ผลเดิมใน `experiment_result/` และ Pilot | เก็บตำแหน่งเดิม; ผลใหม่เข้า `artifacts/` |

Pilot README ระบุว่าใช้ mixed training 10% และ exploratory signal-to-noise proxy จึงยังไม่ถือว่า implementation นั้นตรงกับ pure-training หรือ objective ใหม่ที่ผ่านการตรวจแล้ว

## ทิศทางคำสั่งรัน

เสนอจุดเรียกเดียว เช่น `python -m experiments.run --config configs/experiments/mmd_comparison.json` โดยชื่อคำสั่งและ schema นี้ยังเป็นข้อเสนอ ไม่ใช่คำสั่งที่ใช้ได้แล้ว

Config เลือก dataset, methods, seed, window sizes, ratios และ training mode คำสั่ง Python ใช้ได้ทั้ง Windows และ Linux ส่วน `.sh` เก็บใกล้ experiment สำหรับเปิดหลายงาน/ตั้งค่าเครื่อง ไม่รวมเป็นโฟลเดอร์ bash ตามนามสกุล

## ลำดับลงมือและเกณฑ์ผ่าน

1. **ตรวจของเดิม:** แยกสูตร detector ออกจาก protocol ระบุจุดที่จะคงพฤติกรรมและจุดที่ต้องแก้ เช่น calibration statistic; ตรวจชุดข้อมูลและ provenance ที่มีอยู่
2. **สร้างทางรัน baseline:** Single-RBF/Multi-RBF ใช้ splits, windows และ reference draws เดียวกัน มี output config และ run identity ที่ตรวจย้อนหลังได้; ไม่ทับผลเดิม
3. **ตรวจ baseline:** ตรวจ MMD กับตัวอย่างที่คำนวณอ้างอิงได้ ตรวจ calibration ใช้ score เดียวกับ test และรัน smoke experiment ขนาดเล็กก่อนขยาย
4. **เพิ่ม Deep Kernel แบบ pure training:** ตรวจสูตร kernel, objective, variance estimator และ gradients; ใช้ validation เลือก checkpoint แล้ว freeze ก่อน calibration/test
5. **เพิ่ม mixed training:** เปลี่ยน config และ training windows โดยประเมินด้วย held-out windows ชุดเดียวกับ pure training ภายใต้ข้อจำกัดข้อมูลและงบฝึกที่รายงานไว้
6. **เพิ่ม generalization:** กำหนด attack-family/domain mapping ก่อนแบ่งชุด และกัน family ทดสอบออกจาก training/validation/model selection
7. **ขยาย baseline และ demo:** นำ detector อื่นเข้าทีละตัว แล้วสร้าง demo จาก pipeline ที่ตรวจแล้ว

## กติกาผลทดลองที่ต้องรักษา

- แยก training, validation, reference, benign calibration และ test ตาม protocol พร้อม audit การรั่วไหล/ข้อความซ้ำ
- เปรียบเทียบแต่ละวิธีบน test windows เดียวกัน; ห้ามใช้ test เลือก threshold หรือ checkpoint
- ตั้ง threshold แยกตามวิธีและ window size จาก calibration แล้วรายงาน FPR จริงบน test; percentile เดียวกันไม่รับประกัน measured FPR เท่ากัน
- บันทึกจำนวน attacker จริงและ actual ratio เมื่อ ratio × window size ไม่เป็นจำนวนเต็ม
- แยก requested repeats/window counts ออกจากจำนวนตัวอย่างอิสระ; windows ที่ใช้ queries ซ้ำมีความสัมพันธ์กัน
- บันทึก config, seed, split/data identity, code version เมื่อมี และ checkpoint ที่ใช้จริง ไม่เชื่อผลเก่าจากการมี `metadata.json` เพียงอย่างเดียว
- แยกการจำลอง fixed windows ออกจาก sequential monitoring; ยังไม่อ้างว่า window เล็กเท่ากับ latency ต่ำหรือคุม false alerts ระยะยาวได้

## รายละเอียดที่ต้องออกแบบระหว่าง implementation

- สูตร deep kernel และตัวประมาณ variance ที่จะใช้จริง
- Training window/reference sizes และงบฝึกที่ใช้เทียบ pure กับ mixed
- Grid ของ window sizes/attacker counts; ข้อเสนอเริ่มต้นจากร่างคือ windows 100/250/500/1500 และ ratios 1/5/10/25/100% โดยยังต้องตรวจความเพียงพอของข้อมูล
- Dataset/family/domain mapping และจำนวนข้อมูลหลัง dedup/splitting
- Generalization แบบมี benign ปลายทางตั้งระบบเป็นข้อเสนอเริ่มต้น; แบบไม่มีข้อมูลปลายทางต้องเป็น protocol แยก
- จำนวน seeds/calibration/test windows ที่รองรับความละเอียด FPR เป้าหมายและทรัพยากรจริง
- Supervised classifier baseline เป็นงานเพิ่มเติมเพื่อแยกประโยชน์ของ labeled training ออกจาก objective MMD

ยังไม่ล็อกตัวเลขหรือสูตรที่ไม่ได้ตรวจ และไม่อ้างว่าการย้ายไฟล์เป็นการยืนยันความถูกต้องของวิธีวิจัย
