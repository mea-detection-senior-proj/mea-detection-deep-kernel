# สถาปัตยกรรมและลำดับพัฒนาต่อ

```text
Dataset JSON + Experiment JSON + CLI overrides
                    |
         datasets: load / group / split / audit
                    |
         embeddings: frozen encoder / cache
                    |
         models + kernels + training
         (train; เลือก checkpoint จาก validation)
                    |
         evaluation: benign calibration threshold
                    |
         evaluation: benign / mixed test windows
                    |
         experiment: scores / metadata / weights
```

`experiment.run(args, spec)` เชื่อม workflow หลัก
เพิ่ม dataset รูปแบบเดิมผ่าน config; เปลี่ยน network ที่ `models.py`;
สูตร MMD ที่ `kernels.py`; objective ที่ `training.py`; calibration/test ที่ `evaluation.py`
dataset adapter คืน rows กลาง `{'id': str, 'query': str}`
จึงไม่ต้องรู้วิธีฝึก network และโค้ดฝึกไม่ต้องรู้ format ต้นทาง

metadata เก็บ dataset specification และ arguments จริงของแต่ละ run
`run_additional.py` เก็บ source snapshot รวม package และ configs หลังรันด้วย
โค้ด Deep MMD เลิกพึ่งการตั้ง global ใน paper detector แต่คงวิธีคำนวณและ embedding cache format

## พฤติกรรมที่คงเดิม

- เปรียบเทียบ RBF, Multi-RBF, Deep Kernel บน windows/reference draws เดียวกัน
- Deep kernel = Multi-RBF บน embeddings × (0.1 + 0.9 × RBF บน neural features)
- Network: input → 128 → ReLU → 32; frozen encoder
- แบ่งกลุ่ม train/validation/calibration/test 40/20/20/20
- แยก RNG สำหรับ bandwidth/training/validation/calibration/test
- เลือก checkpoint จาก fixed validation pairs รวม epoch 0 แล้ว freeze
- calibration แต่ละวิธีใช้ benign percentile 95
- ฝึก attack 10%; ทดสอบ benign, 5%, 10% ตาม rounding เดิม
- รูปแบบ scores/weights เดิม และไม่เขียนทับผลที่มีอยู่

## งานถัดไปสำหรับโมเดลเต็มรูปแบบ

รายการนี้เป็นแผน ยังไม่ได้เปลี่ยนพฤติกรรมวิจัยในการจัดโครงสร้างครั้งนี้

1. กำหนด known-attack, unseen-family และ cross-dataset protocols พร้อม
   train/tuning/test datasets และ source/session grouping ให้ชัดก่อนใช้ test
2. เลือก MMD variance/test-power objective ที่เหมาะสม ปัจจุบัน mean/std ของ
   mixed windows เป็น proxy และ windows อาจซ้ำกัน
3. แยก train/calibrate/score และเพิ่ม detector ที่โหลด encoder identity, architecture,
   bandwidth, reference pool และ threshold กลับไปตรวจ traffic ใหม่ได้
4. เพิ่ม experiment matrix สำหรับ datasets × seeds × windows และ summary
   ที่รองรับหลาย protocols; runners เดิมยังล็อกการทดลองเก่า
5. รองรับข้อมูลใหญ่ด้วย chunked embeddings, memory mapping, batch เข้า GPU
   และสร้าง evaluation windows ทีละส่วน ปัจจุบันยังเก็บ embeddings ทุก partition
   และ sampled windows ใน memory
6. ประเมินที่ FPR ควบคุม เพิ่ม uncertainty analysis, ablations, length/style confounds
   และตรวจ overlap ข้าม dataset

โครงสร้างรองรับการต่อ dataset เพิ่ม แต่ไม่ได้ทำให้ผลโมเดลดีขึ้นหรือยืนยัน source independence
ผลทดลองเก่ายังมีข้อจำกัดตามรายงานเดิม
