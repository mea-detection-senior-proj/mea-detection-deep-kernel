# ร่างข้อเสนอโครงงาน: การตรวจจับ Model Extraction ด้วย Deep Kernel MMD ภายใต้งบประมาณ Query จำกัด

**สถานะ:** ร่างสำหรับหารือ ยังต้องระบุผู้จัดทำ อาจารย์ที่ปรึกษา ระยะเวลา และรูปแบบตามหลักสูตร

## ที่มาและความสำคัญ

การตรวจจับ model extraction จากข้อความที่ส่งเข้า LLM API สามารถมองเป็นปัญหาตรวจความแตกต่างระหว่างการกระจายของ benign traffic กับ traffic ที่กำลังตรวจสอบได้ วิธี Maximum Mean Discrepancy (MMD) วัดความแตกต่างดังกล่าวผ่าน kernel โดยไม่ต้องมีป้ายกำกับของแต่ละ query ในช่วงใช้งานจริง อย่างไรก็ตาม เมื่อจำนวน query ในหน้าต่างสังเกตน้อย หรือมี attack เพียงสัดส่วนเล็ก ความสามารถในการตรวจจับอาจลดลง

โครงงานนี้ศึกษาว่า kernel ที่เรียนรู้จากตัวอย่าง attack สามารถเพิ่ม detection power ภายใต้งบประมาณ query จำกัดได้หรือไม่ และผลที่ได้ยังคงอยู่เมื่อพบ attack family ที่ไม่ได้ใช้ฝึกหรือปรับโมเดลหรือไม่ การเปรียบเทียบต้องคำนึงถึง false positive rate (FPR) และความแตกต่างด้านรูปแบบหรือความยาวของข้อมูลด้วย

## คำถามวิจัย

Does a power-motivated Deep Kernel MMD improve detection power and query efficiency against known and unseen LLM model extraction attacks compared with fixed-kernel MMD, at a controlled false positive rate?

คำว่า power-motivated ใช้อธิบายเป้าหมายการออกแบบ ไม่ถือว่า objective ใน pilot ปัจจุบันเป็นตัวประมาณ test power ที่พิสูจน์แล้ว

## วัตถุประสงค์

1. พัฒนาและประเมิน Deep Kernel MMD เปรียบเทียบกับ RBF MMD และ Multi-RBF MMD ภายใต้ protocol เดียวกัน
2. วัดผลเมื่อเปลี่ยนขนาดหน้าต่างและสัดส่วน attack โดยรายงาน detection power เทียบกับ FPR และจำนวน query
3. ตรวจ generalization กับ attack family ที่ถูกกันออกจากทั้งการฝึกและการปรับ hyperparameters
4. ตรวจว่าผลอธิบายได้ด้วยลักษณะผิวเผิน เช่น ความยาวและรูปแบบ prompt หรือไม่ และเปรียบเทียบกับ supervised classifier ที่ได้รับข้อมูลฝึกในขอบเขตเดียวกัน

## วิธีดำเนินการ

1. **เตรียมข้อมูล:** ตรวจที่มาและความสัมพันธ์ของตัวอย่าง แบ่ง train, validation, benign calibration และ test ตาม source group เพื่อป้องกัน source เดียวกันข้ามชุด สำหรับ unseen attack ต้องกำหนด family ที่กันออกก่อนเลือกโมเดลและ hyperparameters
2. **สร้างระบบเปรียบเทียบ:** ใช้ encoder, source splits, test windows และ reference protocol ที่เปรียบเทียบกันได้สำหรับ RBF, Multi-RBF และ Deep Kernel บันทึก seed, settings, checkpoints และคะแนนรายหน้าต่าง Deep Kernel ใช้ attack labels ระหว่างฝึก จึงเพิ่ม supervised classifier เป็น baseline ในงานเต็ม
3. **ฝึกและเลือกโมเดล:** ใช้ข้อมูล train ปรับ parameters และใช้ validation เลือกโมเดล จากนั้น freeze model และใช้ benign calibration ตั้ง threshold โดยไม่ใช้ test ในการปรับโมเดลหรือ threshold ทดสอบ objective และพิจารณา estimator ของ test power ที่มีหลักฐานทางทฤษฎีรองรับ
4. **ประเมิน known attack:** ประเมิน window 100, 250, 500 และ 1,500 ที่ attack ratio หลัก 5% และ 10% โดย 250–500 เป็นช่วงหลักและ 100 เป็น stress test รายงาน TPR และ FPR ที่วัดได้จริง รวมถึงการทำงานเมื่อ FPR เป้าหมายต่างกัน
5. **ประเมิน unseen attack:** ฝึกจาก attack families ที่กำหนดไว้และทดสอบ family ที่กันออกทั้งหมด โดยใช้หลาย family และหมุนเวียน family ที่กันออกเมื่อข้อมูลเพียงพอ ต้องตรวจว่าแต่ละชุดเป็นคนละ family จริงและการเปลี่ยน family ไม่สับสนกับการเปลี่ยน benign domain
6. **ตรวจ nuisance และความไม่แน่นอน:** เพิ่ม length-only baseline, format/length-controlled comparisons และ ablation ที่ทำได้โดยไม่ทำลายความหมายของ attack ทำซ้ำด้วย source-level splits และประเมินความไม่แน่นอนโดยคำนึงถึง source groups และการใช้ข้อมูลซ้ำใน windows ระบุวิธีทดสอบทางสถิติล่วงหน้าก่อนสรุปผล

## ผลการตรวจความเป็นไปได้เบื้องต้น

สามารถเตรียมข้อมูล รัน fixed-kernel baseline และฝึก Deep Kernel บน GPU ได้ โดยมีการตรวจ gradient และแยก source groups สำหรับชุด `model_leeching` Pilot ที่ใช้ 3 seeds และ window 250/500 ให้สัญญาณว่าควรศึกษาต่อ แต่ **ยังไม่พิสูจน์ว่า Deep Kernel ดีกว่าที่ FPR เท่ากัน**: บางรอบมี FPR สูงกว่าเป้าหมายมาก และหน้าต่างทดสอบใช้ข้อมูลซ้ำกัน

การตรวจเพิ่มเติมพบว่า length-only diagnostic ตรวจ mixed-attack windows ได้ครบใน pilot ทั้งหกกรณี โดย FPR อยู่ระหว่าง 0% ถึง 11% เมื่อสอบเทียบด้วยวิธีเดียวกันในระดับ window ข้อมูลนี้ชี้ว่าชุดทดลองมีความต่างด้านความยาวที่รุนแรง และยังไม่แสดงว่าประโยชน์ของ Deep Kernel มาจากความแตกต่างเชิงความหมายหรือ MMD objective โดยเฉพาะ จำเป็นต้องทดสอบข้อมูลและเงื่อนไขที่ควบคุมปัจจัยเหล่านี้

## ผลที่คาดว่าจะได้รับ

- ระบบทดลองที่ทำซ้ำได้และเปรียบเทียบวิธีตรวจจับภายใต้ protocol ที่ระบุชัด
- หลักฐานเชิงประจักษ์ว่าการเรียนรู้ kernel ช่วยหรือไม่ช่วยที่ระดับ FPR และ query budget ที่กำหนด รวมถึงข้อจำกัดกับ attack ที่ไม่เคยเห็น
- ความเข้าใจว่าผลอ่อนไหวต่อการแบ่ง source, calibration และความต่างด้านรูปแบบ/ความยาวเพียงใด

## ความเสี่ยงและแผนรองรับ

- **FPR ไม่คงที่:** ศึกษาความต่างของ calibration/test และประเมินซ้ำในหลาย source splits โดยไม่ใช้ test ตั้ง threshold
- **ข้อมูล attack กับ benign ต่างกันแบบชัดเจน:** ใช้ length/format baselines และสร้างหรือเลือกชุดข้อมูลที่ควบคุมปัจจัยเหล่านี้โดยตรวจความถูกต้องของ attack
- **Attack families หรือข้อมูลไม่เพียงพอ:** ตรวจแหล่งข้อมูลก่อนกำหนดขอบเขต unseen evaluation และรายงานข้อจำกัดแทนการอ้าง generalization เกินหลักฐาน
- **Deep Kernel ไม่ชนะ baseline:** รายงานเป็นผลเชิงลบพร้อม ablation และเงื่อนไขที่ทดสอบ ไม่ถือว่าความสำเร็จของโครงงานขึ้นกับการชนะ

## ขอบเขตและแผนงาน

ก่อนส่ง proposal: ตรวจข้อมูลและ protocol, ยืนยัน training/baseline ทำงาน และรายงาน pilot พร้อมข้อจำกัดตามจริง หลัง proposal: ปรับการสอบเทียบและ objective, ทดลองหลาย seeds/windows/ratios, unseen families, controlled baselines, uncertainty และ ablation ก่อนจัดทำรายงานฉบับเต็ม

## เอกสารตั้งต้น

- Liu, S., Guo, Q., & Dong, Y. (2026). *An Embarrassingly Simple Detector for Model Extraction Attacks in Large Language Model API Traffic*. [arXiv:2606.05725](https://arxiv.org/abs/2606.05725).
- [Processed query-traffic dataset](https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data) ประกอบ repository ของงานตั้งต้น
- ผลและข้อจำกัดของ pilot ในโครงงานนี้: [PILOT_RESULTS.md](PILOT_RESULTS.md)
