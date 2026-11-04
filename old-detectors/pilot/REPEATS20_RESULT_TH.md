# ผลทดลอง MMD และ Deep Kernel ที่ใช้ reference 20 ชุด

ทดลองกับ model_leeching, window 250, seed 42, attack ratio ที่กำหนด 5% และ 10%.
การปัดจำนวน attack ทำให้ 5% ใช้ 12 ใน 250 queries (4.8% จริง) และ 10% ใช้ 25.

## 1. โค้ดต้นฉบับจาก repository

ใช้ Multi-RBF, reference repeats 20, benign null samples 1,000, threshold
percentile 95, benign split 80/20, 50 test windows ต่อเงื่อนไข.
ผล: benign FPR 0%, mixed 5% TPR 2%, mixed 10% TPR 98%.
ผลอยู่ใน `outputs/paper_protocol_bs250_seed42/metadata.json`.

นี่ใช้ protocol เดิมแต่เปลี่ยน window จาก 1,500 ในผลหลักของบทความเป็น 250
และทดลองเฉพาะ dataset/seed เดียว จึงไม่ใช่การ reproduce ผลหลักทั้งหมด.
แหล่งข้อมูล test และ split ต่างจากการเปรียบเทียบข้อ 2 จึงไม่ควรเทียบตัวเลขข้ามตาราง.

## 2. การเปรียบเทียบบน source-grouped protocol เดียวกัน

ทุกวิธีใช้ test windows และ reference draws ร่วมกัน; 20 repeats ต่อ window;
calibration 200 windows, test 50 windows ต่อเงื่อนไข; 20 training epochs,
32 validation windows. Threshold แยกแต่ละวิธีโดยใช้ค่าเฉลี่ย 20 references
เหมือนขั้นทดสอบ และใช้ benign calibration ที่แยก source group จาก test.

| Method | FPR | TPR 5% | TPR 10% |
|---|---:|---:|---:|
| RBF | 20% | 46% | 100% |
| Multi-RBF | 24% | 64% | 100% |
| Deep Kernel | 26% | 98% | 100% |

ผลอยู่ใน `outputs/repeats20_bs250_seed42/metadata.json` และ `scores.csv`.
FPR สูงกว่าเป้าหมาย 5% และไม่เท่ากัน จึงยังไม่ใช่หลักฐานว่า Deep Kernel
ชนะที่ FPR เท่ากัน. เหล่านี้เป็นตัวเลขจากหนึ่ง seed และ test windows ที่ใช้
query ร่วมกัน. `model_leeching` มีความต่างด้านความยาว/รูปแบบอย่างชัดเจน.

การเปรียบเทียบนี้ใช้จำนวน repeats ตอน test เท่าบทความ แต่ calibration ต่างจาก
บทความ: ใช้ held-out calibration และค่าเฉลี่ย 20 references ในขณะที่บทความ
ใช้ benign pair เดี่ยวจาก reference pool สำหรับ null แต่ test เฉลี่ย 20 references.
Deep Kernel ได้ใช้ attack labels ขณะฝึก ต่างจาก MMD ต้นฉบับ.
