# รายงานการทดลองความไวต่อลำดับของ Stream PRADA

วันที่ตามบริบทผู้ใช้: 6 พฤศจิกายน 2026

สถานะ: **หยุดที่ resource gate ก่อนวัดผลการตรวจจับ** จึงยังสรุปไม่ได้ว่า
การเรียงคำถามทำให้ผลการตรวจจับเปลี่ยนหรือไม่ โค้ด ตัวตั้งค่า การทดสอบ
หลักฐาน parity และผล preflight ถูกเก็บบน `experiment/stream-prada-order`
ใน worktree แยก โดยไม่แก้ไข `main` หรือ implementation ของเพื่อนร่วมทีม

## วัตถุประสงค์และวิธีควบคุม

ศึกษาว่าชุดคำถามเดียวกัน เมื่อจัดแบบ random, clustered attack และ interleaved
attack ทำให้ Growing Set, Distance History, Shapiro–Wilk W, คะแนนสูงสุด
และ alert แตกต่างกันหรือไม่ นี่เป็นการจัดลำดับข้อมูล offline ไม่ใช่ chronological
API trace จริง และไม่ใช่การเสนอ detector ใหม่

ใช้คำถามจริงใน `model_leeching`: benign 10,062 แถว และ attack 10,062 แถว
จาก artifact ของ repository ซึ่งมีสำเนาอยู่ใน checkout ข้างเคียง อ่านข้อมูลเท่านั้น
ไม่มีการสร้างประโยคทดแทนหรือเรียก LLM/API เพื่อสร้างข้อมูลใหม่ ใช้
`pilot/protocol.py` เดิมโดยไม่แก้ไข เพื่อจัดกลุ่มแบบ transitive ตาม ID,
normalized text และ source context ของ attack ก่อนแบ่งข้อมูล ผล audit ไม่พบ
ID, normalized text หรือ attack context ข้าม partition ภายใต้กฎนี้
มี calibration source groups 369 กลุ่ม และ test source groups 371 กลุ่ม
การตรวจนี้ไม่ใช่หลักฐานว่าไม่มี semantic overlap ทุกชนิด

เลือก calibration benign, test benign และ test attack อย่างละ 1,000 คำถาม
ด้วย seed ที่กำหนดไว้ ใช้ frozen `BAAI/bge-small-en-v1.5` revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` ใน inference/evaluation mode,
normalized embedding, ไม่มี prefix และตัดความยาวที่ 512 tokens ตามโมเดล
ไม่มีการปรับน้ำหนัก บันทึก hash ของไฟล์โมเดล ข้อมูล pool และ embedding
ไว้ใน metadata โดยไม่ commit ข้อมูลดิบ น้ำหนัก หรือ embedding

แผนที่ freeze ไว้ใช้ stream ยาว 256 คำถาม benign prefix 110 คำถาม และ onset
ที่คำถาม 111 ร่วมกันทุก ordering ภายในแต่ละ attack ratio อัตราเป้าหมาย
10%, 25%, 50% ใช้ attack 26, 64, 128 คำถามตามลำดับ (อัตราจริง 10.15625%,
25%, 50%) ชุดสมาชิกคงเดิมสำหรับแต่ละ ratio ตลอด 1,000 paired permutations
จึงแยกผลของการเรียงลำดับออกจากการเปลี่ยนสมาชิกชุดได้ แต่ยังไม่ทดสอบ
ความแปรปรวนจากชุดคำถามใหม่ Random ถูกบังคับให้มี onset เดียวกันจึงเป็น
conditional random ordering; clustered วาง attack ต่อกันหลัง prefix;
interleaved กระจายตำแหน่ง attack อย่างสม่ำเสมอใน suffix

## กลไกและ parity

ไฟล์อ้างอิงใน checkout ตรงกับ
[LabRAI Stream PRADA](https://github.com/LabRAI/mmd-llm-mea-detection/blob/af9420da12a03bf321a2218870a68f7b38f5787c/PRADA/prada_stream_detector.py)
ที่ Git blob `5f951afa8cc750c5497e4efd793100db0648ad6a` การกล่าวถึง parity
ในรายงานนี้หมายถึง implementation PRADA-style สำหรับ query embeddings นี้
ไม่ใช่การยืนยันกับ PRADA สำหรับรูปภาพต้นฉบับที่ตรวจแยกต่างหาก

ใช้ minimum L2 ต่อ Growing Set, เริ่ม growth-distance ด้วย 0, เพิ่มสมาชิกเมื่อ
ระยะมากกว่า adaptive threshold และอัปเดต threshold เป็นค่าสูงสุดระหว่าง
ค่าเดิมกับ mean minus population SD ของ growth-distances เก็บระยะทุกคำถาม
ใน Distance History กรองแบบ inclusive three-sigma ตาม fallback ของ upstream
และทดสอบ Shapiro–Wilk ทุกคำถามเมื่อมีระยะ **มากกว่า 100 ค่า** (ครั้งแรกที่
คำถาม 102) ไม่มีการ subsample Shapiro สำหรับความยาวนี้

คะแนน stream คือ `1 - min(W)` เกณฑ์ตามแผนคือ one-sided P95 จาก benign
calibration 200 streams ใช้ร่วมทุก ordering และ ratio; alert เมื่อ `W < 1-P95`
แบบ strict และวัดครบ stream แม้เคย alert แล้วเพื่อเปรียบเทียบ maximum score
แผน FPR ใช้ held-out benign 200 streams ไม่มีการใช้ test pool ปรับ threshold

Unit tests 6 รายการผ่าน ครอบคลุมสมาชิก/prefix/onset, warm-up และ strict alert,
parity ทั้ง direct และ precomputed distance, monotone adaptive threshold,
resource projection และการปฏิเสธข้อมูลไม่ถูกต้อง ระหว่างทดสอบพบว่า upstream
direct norm และ float32 cdist ให้ค่าต่างกันเล็กน้อยเมื่อ embedding ซ้ำ จึงเทียบ
แต่ละโหมดกับการคำนวณระยะของโหมดเดียวกัน ไม่ได้ขยาย tolerance เพื่อซ่อนปัญหา

Hard gate บนคำถามจริง 3 streams เทียบกับ upstream precomputed mode ให้
maximum absolute W error **0.0 ทุก stream**, Growing Set size 159, 135, 157
และ first alert ตรงกันที่ query 102 ภายใต้ delta 0.99 ที่ใช้ทดสอบ parity เท่านั้น
ค่า delta นี้ไม่ใช่ threshold ที่ calibrate แล้ว และ alert จาก parity ไม่ใช่
Detection Rate หรือผลทดลองของสาม ordering

## ผล resource gate และสถานะการวัด

ใช้ Conda environment `senior` เดิม ไม่มีการติดตั้งหรือเปลี่ยน package
CUDA operation ผ่านบน NVIDIA GeForce RTX 4060 Ti ใช้ Torch
`2.14.1+cu132`, NumPy `2.4.6`, SciPy `1.17.1`, sentence-transformers `5.7.0`
รายละเอียด Python/platform อยู่ใน metadata

| รายการ | ค่าที่วัดได้ |
| --- | ---: |
| เวลา encode 3,000 คำถาม | 5.1009 วินาที |
| เวลาถึงจุดตรวจ gate | 26.1656 วินาที |
| เวลาสูงสุดของ calibration benchmark 5 streams | 0.06604 วินาที/stream |
| เวลารวมที่คาดพร้อม safety factor 2 เท่า | 1,267.1267 วินาที (21.12 นาที) |
| งบที่อนุญาตเริ่มต้น | 1,200 วินาที (20 นาที) |
| ขนาด distance matrices ที่คำนวณจากรูปทรง | 20,000,000 bytes |
| RAM ว่างก่อน encode | 31,174,168,576 bytes |
| GPU memory ว่างก่อนโหลดโมเดล | 7,418,675,200 bytes |

Projection สูงกว่างบจึงหยุดทันทีตามข้อกำหนด ไม่ลดจำนวน permutation,
ความยาว stream หรือเปลี่ยน algorithm เพื่อผ่าน gate ไม่มีการรัน calibration
ครบ 200 streams, ไม่มี held-out benign evaluation และไม่มี mixed-order pilot
หรือ 1,000-permutation evaluation คะแนน calibration 5 streams ที่ใช้ benchmark
ไม่ได้ persist จึงไม่สามารถนำมาคำนวณ threshold ย้อนหลังอย่างตรวจสอบได้

| ตัวชี้วัดหลัก | สถานะ |
| --- | --- |
| Growing Set / Distance History / W ต่างกันระหว่าง ordering | ยังไม่วัด |
| Maximum Detection Score / จำนวนและร้อยละ alert ที่เปลี่ยน | ยังไม่วัด |
| Detection Rate แยก ordering และ ratio | ยังไม่วัด |
| Held-out benign stream-level FPR | ยังไม่วัด |
| Detection Delay | ยังไม่วัด |
| Peak RAM / Peak GPU allocation ของ run | ไม่ได้บันทึกก่อนหยุด |

เก็บ null สำหรับรายการที่ยังไม่วัดใน `assessment.json` กราฟ
`resource_gate.png` แสดงเฉพาะเวลาและ projection ที่มีหลักฐาน ไม่สร้างกราฟ
ประสิทธิภาพการตรวจจับจากข้อมูลที่ไม่มี ผลลัพธ์นี้เป็นข้อจำกัดทรัพยากร
ไม่ใช่ negative finding ว่า order ไม่มีผล

## ขอบเขต uncertainty และงานที่รออนุมัติ

หากได้รับอนุมัติงบใหม่ จึงเริ่ม run ใหม่โดยเก็บ blocked run นี้ไว้ แล้วทำ pilot
ก่อนขยายเป็น 1,000 permutations ต่อ ordering ต่อ ratio (รวม 9,000 streams)
ใช้หนึ่ง threshold เดียวจาก calibration ที่สมบูรณ์ รายงาน Wilson intervals
เป็น conditional Monte Carlo uncertainty เท่านั้น เพราะแต่ละ stream ใช้ pool
ร่วมกัน และแต่ละ ratio ใช้สมาชิกชุดเดิม ไม่ใช่ population confidence interval
สำหรับ traffic จริงหรือหลักฐาน generalization ข้าม dataset

Detection Delay นับจาก query 111 (alert ณ onset มี delay 0) แยก prefix false
alarms ออกจาก detection หลัง onset และเก็บ nondetection เป็น right censoring
ไม่แทน nondetection ด้วยค่าเฉลี่ยของ detected streams การสรุป median delay
เฉพาะ detected streams ต้องระบุ denominator และข้อจำกัดนี้เสมอ

ได้ขออนุมัติ resource gate 25 นาทีไว้แล้ว ยังไม่ถือว่าการไม่ตอบคือการอนุมัติ
ไม่มีการ push, merge, rebase, cherry-pick หรือเปิด PR และห้ามรวม branch นี้
เข้า `main` จนกว่าผู้ใช้จะเปลี่ยนคำสั่งอย่างชัดเจนในคำขอใหม่
