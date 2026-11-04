# ผลทดลองหลัก: Deep Kernel MMD บน model_leeching

| Method | Seed | Window | FPR | TPR 5% | TPR 10% |
|---|---:|---:|---:|---:|---:|
| RBF | 1 | 250 | 0% | 2% | 51% |
| Multi-RBF | 1 | 250 | 0% | 2% | 71% |
| Deep Kernel | 1 | 250 | 0% | 40% | 100% |
| RBF | 1 | 500 | 0% | 4% | 99% |
| Multi-RBF | 1 | 500 | 0% | 5% | 99% |
| Deep Kernel | 1 | 500 | 0% | 91% | 100% |
| RBF | 20 | 250 | 0% | 5% | 85% |
| Multi-RBF | 20 | 250 | 0% | 5% | 94% |
| Deep Kernel | 20 | 250 | 0% | 74% | 100% |
| RBF | 20 | 500 | 1% | 5% | 100% |
| Multi-RBF | 20 | 500 | 1% | 7% | 100% |
| Deep Kernel | 20 | 500 | 1% | 99% | 100% |
| RBF | 42 | 250 | 18% | 37% | 100% |
| Multi-RBF | 42 | 250 | 23% | 48% | 100% |
| Deep Kernel | 42 | 250 | 24% | 95% | 100% |
| RBF | 42 | 500 | 21% | 85% | 100% |
| Multi-RBF | 42 | 500 | 28% | 92% | 100% |
| Deep Kernel | 42 | 500 | 35% | 100% | 100% |

ดำเนินการครบ 6 กรณี (3 seeds × 2 ขนาดหน้าต่าง) และประเมินทั้งสามวิธี
รวม 18 ผลการประเมิน เมื่อวันที่ 1 พฤศจิกายน 2026

## เงื่อนไข

- ข้อมูล model_leeching ทั้งชุด; แบ่งตาม source groups เป็น train/validation/calibration/test
  ด้วยสัดส่วนกลุ่ม 40/20/20/20 และตรวจการซ้ำข้ามชุดตาม ID, normalized text และ attack context
- ตรึง BGE-small และใช้ embedding เดียวกัน; seeds 1, 20, 42
- หน้าต่างทดสอบ 250/500 queries; benign และ mixed attack 5%/10%
- ทุกวิธีใช้ test windows และ reference draws เดียวกันภายในแต่ละกรณี
- เฉลี่ย benign references 20 ชุด ทั้ง calibration และ test
- Calibration 200 benign windows; test 100 windows ต่อเงื่อนไข
- Threshold แยกวิธีด้วย percentile 95 ของ calibration; ไม่ใช้ test ปรับ threshold
- Deep Kernel ฝึก 20 epochs, 8 training windows ต่อ epoch, window 100, attack 10%
- เลือก checkpoint จาก 32 fixed validation windows รวม checkpoint ก่อนฝึกเป็นตัวเลือก
- ทุก seed เลือก epoch 20; เปลี่ยนขนาดหน้าต่างทดสอบแล้วการฝึกของ seed เดียวกันเหมือนเดิม

## ค่าเฉลี่ยข้าม 3 seeds

| Window | วิธี | FPR | TPR attack 5% | TPR attack 10% |
|---:|---|---:|---:|---:|
| 250 | RBF | 6.0% | 14.7% | 78.7% |
| 250 | Multi-RBF | 7.7% | 18.3% | 88.3% |
| 250 | Deep Kernel | 8.0% | 69.7% | 100.0% |
| 500 | RBF | 7.3% | 31.3% | 99.7% |
| 500 | Multi-RBF | 9.7% | 34.7% | 99.7% |
| 500 | Deep Kernel | 12.0% | 96.7% | 100.0% |

Deep Kernel มี TPR สูงกว่าสอง baseline ในเงื่อนไข attack 5% ที่ทดสอบ
และเมื่อเพิ่ม window จาก 250 เป็น 500 ค่าเฉลี่ย TPR เพิ่มขึ้น แต่ FPR เฉลี่ยก็เพิ่มขึ้นด้วย
ผลนี้ยังไม่ใช่การยืนยันว่า Deep Kernel ดีกว่าที่ FPR เท่ากัน

## ผลราย seed ของ Deep Kernel

| Seed | Window | FPR | TPR attack 5% | TPR attack 10% |
|---:|---:|---:|---:|---:|
| 1 | 250 | 0% | 40% | 100% |
| 1 | 500 | 0% | 91% | 100% |
| 20 | 250 | 0% | 74% | 100% |
| 20 | 500 | 1% | 99% | 100% |
| 42 | 250 | 24% | 95% | 100% |
| 42 | 500 | 35% | 100% | 100% |

FPR แตกต่างระหว่าง seeds มาก โดย seed 42 มีค่าสูงในทั้งสามวิธี
ข้อมูลนี้แสดงความอ่อนไหวต่อการแบ่งชุดและการสุ่มของ protocol ปัจจุบัน
แต่ยังไม่ระบุสาเหตุ และไม่ได้ใช้ผล test ปรับโมเดลหรือ threshold ให้ดีขึ้น

## ขอบเขตการตีความ

- เป็น known-attack evaluation ของ dataset เดียว ไม่สรุปผลกับ unseen attack families
- เป้าหมาย calibration FPR 5% ไม่รับประกัน test FPR 5%
- หน้าต่างใช้ queries ซ้ำข้ามหน้าต่างได้ ผลเป็นสถิติเชิงพรรณนา ไม่ถือว่าทุกหน้าต่างอิสระ
- Deep Kernel ใช้ attack labels ระหว่างฝึก ส่วน fixed kernels ไม่ใช้
- Objective ปัจจุบันเป็น signal-to-noise proxy สำหรับทดลอง ไม่ใช่ตัวประมาณ test power ที่ยืนยันแล้ว
- Window 250 ที่ระบุ attack 5% มี attack จริง 12/250 หรือ 4.8%; เงื่อนไขอื่นตรงสัดส่วน
- ความต่างด้านความยาว/รูปแบบของข้อมูลเป็นข้อจำกัดประกอบ ไม่ได้เพิ่ม length-only เป็นวิธีหลัก
- ไม่ได้อ้างนัยสำคัญทางสถิติหรือวัด query efficiency แบบ time-to-detection

## ผลส่งมอบและการตรวจสอบ

ผลทั้งหมดอยู่ใน [โฟลเดอร์การทดลอง](outputs/main_model_leeching_repeats20/):

- [รายงานพร้อมช่วงต่ำสุด–สูงสุดและ checkpoint](outputs/main_model_leeching_repeats20/REPORT.md)
- [ผลราย seed ทั้งสามวิธี](outputs/main_model_leeching_repeats20/validated_runs.csv)
- [ค่าเฉลี่ยและช่วงระหว่าง seeds](outputs/main_model_leeching_repeats20/summary.csv)
- [กราฟ FPR/TPR](outputs/main_model_leeching_repeats20/rates.svg)
- [กราฟการฝึกและ validation](outputs/main_model_leeching_repeats20/training.svg)
- [Training history](outputs/main_model_leeching_repeats20/training_history.csv)

แต่ละ run เก็บคะแนน test/calibration, metadata, split hashes, checkpoint และ run log
สำเนาโค้ดพร้อม SHA256 อยู่ใน source_snapshot ภายในโฟลเดอร์การทดลอง
ไฟล์ผลใน outputs ถูก ignore ตามกติกา repository; รายงานฉบับนี้เก็บแยกไว้นอก outputs

ผ่าน unit tests ที่มี 7 รายการและ smoke run บน GPU ก่อนเริ่มรอบหลัก
ตัวรวมผลตรวจครบทั้ง 6 configurations, การไม่ซ้ำข้าม split ตาม audit,
จำนวนและความเป็น finite ของคะแนน, threshold calibration, detection decisions,
อัตราที่รายงาน และความตรงกันของ split ระหว่าง window sizes ของ seed เดียวกัน

## ทำซ้ำ

```powershell
.\.venv\Scripts\python.exe -u pilot/run_known_pilot.py --output pilot/outputs/main_model_leeching_repeats20_rerun
.\.venv\Scripts\python.exe pilot/summarize_main.py pilot/outputs/main_model_leeching_repeats20_rerun
```

ต้องเลือกโฟลเดอร์ใหม่เพื่อไม่เขียนทับผลเดิม ใช้เงื่อนไขเดิมทั้งหมดเมื่อเปรียบเทียบรอบทำซ้ำ
