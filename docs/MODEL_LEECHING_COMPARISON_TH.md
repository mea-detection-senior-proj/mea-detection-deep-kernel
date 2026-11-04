> Historical document: source locations and commands below predate the migration. Use [current English commands](RUN_EXPERIMENTS.md) and the [migration record](CLEAN_ARCHITECTURE_MIGRATION.md). ADR 0001 governs scientific scope; ADR 0003 supersedes older restructuring guidance.

# ผลเปรียบเทียบรอบแรก: model_leeching

## ข้อค้นพบหลัก

Deep Kernel ที่ฝึกด้วย pure attack ให้ TPR 100% ที่ requested attacker ratio ตั้งแต่ 5% ขึ้นไปใน windows 100/250 ของการทดลองนี้ ขณะที่ fixed kernels ยังตรวจ mixed traffic 5/10% ได้ไม่ครบ อย่างไรก็ตาม **ยังไม่ยืนยันการชนะภายใต้ matched FPR 5%** เพราะ measured benign FPR หลาย seed สูงกว่าเป้า และผลที่ 1% ยังอ่อน โดยเฉพาะ window 100

ผลนี้เป็น known-attack, within-dataset, resampled-window comparison ไม่ใช่ unseen-family evaluation หรือการรับประกันการใช้งานจริง

## สิ่งที่รันจริง

- Single-RBF และ Multi-RBF baselines: seeds 1/20/42 × windows 100/250 รวม 6 ชุดเงื่อนไขต่อ method
- Deep Kernel: pure training ขนาด 100, 30 epochs × 16 steps/epoch, validation 32 คู่คงที่ เลือก checkpoint จาก validation แล้วประเมินทั้ง window sizes
- แต่ละชุดเงื่อนไข: benign calibration 500 windows, benign test 200 windows และ attack/mixed test 200 windows ต่อ requested ratio 1/5/10/25/100%
- ทุกวิธีใช้ reference repeats 20 และ **windows/reference draws ที่บันทึกไว้ชุดเดียวกันจริง**
- Nominal calibration FPR 5%; thresholds แยกตาม method/seed/window โดยไม่ใช้ test เลือก threshold
- Encoder frozen; MLP 384→128→64; kernel และ variance objective ตามที่ระบุใน [protocol](DEEP_KERNEL_PROTOCOL_TH.md)
- Lock ID: `28329d08d302b40af78cc8377b657ebcacbfaceac1b6cdcc0e276abac1a26067`

Config สองไฟล์ถูกกำหนดก่อนเริ่ม baseline และเก็บ registration snapshot ก่อน Deep training ไม่มีการเปลี่ยน hyperparameters/checkpoint policy/threshold policy ตามผล test

## ผลเฉลี่ยระหว่าง 3 seeds

ทุกค่าเป็นเปอร์เซ็นต์ `±` คือ sample standard deviation ระหว่าง seeds ไม่ใช่ confidence interval

| Window | Method | Benign FPR | TPR 1% | TPR 5% | TPR 10% |
|---:|---|---:|---:|---:|---:|
| 100 | RBF | 6.00 ± 4.92 | 8.50 ± 2.78 | 13.00 ± 8.26 | 44.17 ± 19.81 |
| 100 | Multi-RBF | 6.33 ± 5.48 | 8.83 ± 3.82 | 14.83 ± 10.02 | 51.50 ± 22.42 |
| 100 | Deep Kernel | 5.50 ± 1.80 | 6.50 ± 2.78 | 100.00 ± 0.00 | 100.00 ± 0.00 |
| 250 | RBF | 11.67 ± 9.78 | 14.33 ± 11.81 | 36.17 ± 26.68 | 84.17 ± 25.26 |
| 250 | Multi-RBF | 12.83 ± 10.26 | 15.17 ± 12.74 | 41.50 ± 31.19 | 91.17 ± 15.30 |
| 250 | Deep Kernel | 11.50 ± 9.99 | 23.00 ± 16.53 | 100.00 ± 0.00 | 100.00 ± 0.00 |

ที่ ratios 25% และ 100% ทุกวิธีได้ TPR 100% ทุก seed/window ที่ทดสอบ จึงยังแยกข้อได้เปรียบในสองเงื่อนไขนี้ไม่ได้

Requested ratios ไม่เท่ากับ actual ratios เสมอ: window 250 มี attacker 3/13/25/63/250 queries จึงเป็น actual 1.2/5.2/10/25.2/100% ส่วน window 100 มี 1/5/10/25/100 queries ตามลำดับ

## FPR จริง: จุดที่ยังไม่ผ่านเป้าหมาย

| Seed | Window | RBF FPR | Multi-RBF FPR | Deep Kernel FPR |
|---:|---:|---:|---:|---:|
| 1 | 100 | 4.5% | 4.5% | 7.0% |
| 20 | 100 | 2.0% | 2.0% | 3.5% |
| 42 | 100 | 11.5% | 12.5% | 6.0% |
| 1 | 250 | 21.0% | 21.5% | 22.5% |
| 20 | 250 | 1.5% | 1.5% | 3.0% |
| 42 | 250 | 12.5% | 15.5% | 9.0% |

จึงเรียกได้ว่า “ใช้ calibration policy/nominal target เดียวกัน” แต่ไม่ใช่ “measured FPR เท่ากันที่ 5%” การเพิ่มจำนวน resampled windows ทำให้วัดพฤติกรรม conditional ต่อ pools ได้ละเอียดขึ้น แต่ไม่สร้าง benign queries หรือ source groups ใหม่ที่เป็นอิสระ

ยังไม่ได้วินิจฉัยว่า FPR ที่แตกต่างเกิดจาก split/domain composition, reference conditioning หรือความผันผวนอื่นมากน้อยเพียงใด ห้ามสรุปสาเหตุจากตารางนี้อย่างเดียว และไม่ปรับ threshold จาก test ย้อนหลังเพื่ออ้างว่าคุม FPR สำเร็จ

## AUROC ประกอบการอ่านผล

AUROC คำนวณจาก scores ของ benign test เทียบกับแต่ละ attack condition ไม่ได้ใช้เลือก threshold หรือฝึกโมเดล ค่าเฉลี่ยระหว่าง seeds:

| Window | Method | AUROC 1% | AUROC 5% | AUROC 10% |
|---:|---|---:|---:|---:|
| 100 | RBF | 0.5104 | 0.6150 | 0.8672 |
| 100 | Multi-RBF | 0.5092 | 0.6280 | 0.8963 |
| 100 | Deep Kernel | 0.5144 | 1.0000 | 1.0000 |
| 250 | RBF | 0.4905 | 0.7309 | 0.9803 |
| 250 | Multi-RBF | 0.4918 | 0.7573 | 0.9904 |
| 250 | Deep Kernel | 0.6393 | 1.0000 | 1.0000 |

ที่ window 100 / 1% คะแนนของทุกวิธีแยก benign/attack ได้น้อยมากในชุดนี้ ส่วน Deep Kernel ที่ window 250 / requested 1% มี AUROC สูงขึ้น แต่ยังไม่ใช่การตรวจจับที่แข็งแรง ข้อดีที่ ratio 5% ขึ้นไปไม่ได้ปรากฏเฉพาะการตัดสินด้วย threshold เดิม อย่างไรก็ตามยังไม่มีการทดสอบนัยสำคัญที่คำนึงถึงการ reuse queries

## การฝึกและ checkpoint

| Seed | Initial validation J | Best validation J | Selected epoch |
|---:|---:|---:|---:|
| 1 | 1.931 | 15.594 | 30 |
| 20 | 1.706 | 16.432 | 27 |
| 42 | 1.788 | 15.053 | 30 |

ทุก checkpoint เลือกจาก maximum validation objective รวม epoch zero ตาม policy ที่กำหนดไว้ และ freeze ก่อน calibration/test ค่า validation J ไม่ใช่ TPR หรือความน่าจะเป็น และไม่ได้รับประกัน finite-window power

เวลาประมาณบนเครื่องนี้: baseline สองวิธีรวม 212 วินาที; Deep training และ evaluation รวม 252 วินาที โดย pure training แต่ละ seed ใช้ประมาณ 13–15 วินาที ตัวเลขนี้ไม่ใช่ standardized runtime benchmark และไม่รวมขั้น prepare encoder/lock

## การตรวจสอบที่ทำแล้ว

- Tests ผ่าน 15 รายการ รวม scalar reference ของ kernel/MMD/variance, finite-difference gradient check, validation-only selection และ protocol-lock integrity
- ผลทั้งสอง runs มี lock ID และ draw hashes ตรงกันครบทุก seed/window
- โหลด checkpoints กลับมาบน CPU แล้วคำนวณ test scores ซ้ำ 18 จุดจากทุก seed/window ครอบคลุม benign, low ratio และ pure attack คลาดเคลื่อนจาก GPU มากที่สุดประมาณ `4.44e-16`
- ตรวจ threshold และ decision จาก CSV ของ Deep Kernel ครบทุก test row และตรวจว่า selected epoch ตรง validation argmax
- ไฟล์ข้อมูลดิบทั้ง 6 ไฟล์ยังมี hash ตรงกับก่อนเริ่มงาน
- Core detector/training/protocol/config 16 ไฟล์ตรงกับ source snapshot ที่บันทึกก่อน Deep training

หลักฐานอยู่ใน `artifacts/model_leeching_comparison_v1/verification.json`

## สิ่งที่ยังสรุปไม่ได้และงานถัดไป

1. **Matched-FPR superiority:** ยังไม่ผ่าน เพราะ actual FPR ไม่ได้คุมที่ 5% ทุก seed/window ต้องศึกษาการ calibrate และการเปลี่ยนแปลงของ benign pools โดยไม่ใช้ test ชุดนี้เป็น tuning set
2. **Low ratio 1%:** ยังไม่ดีสม่ำเสมอ ควรศึกษาทั้ง training distribution และพฤติกรรม estimator เมื่อมี attacker จำนวนน้อยมาก โดยกำหนด ablations ก่อนประเมินรอบใหม่
3. **Mixed training:** ยังไม่รัน รอบนี้เป็น pure-training baseline สำหรับเทียบกับ mixed training ภายหลัง
4. **Generalization:** ยังไม่ใช้ unseen family หรือข้าม dataset และยังไม่ได้แยกผลของความยาว/รูปแบบ prompt ออกจากสัญญาณการโจมตี
5. **Uncertainty/latency:** มีเพียง 3 seeds และ overlapping windows ไม่อ้าง independent-window confidence intervals หรือ streaming latency/false-alarm guarantees

หากนำผล test รอบนี้ไปกำหนดสูตรหรือ hyperparameters รอบถัดไป ต้องถือว่ารอบนี้เป็น exploratory evidence และใช้ outer holdout หรือข้อมูลที่กันไว้ต่างหากสำหรับข้อสรุปยืนยัน ไม่สุ่ม windows ใหม่จาก test queries เดิมแล้วเรียกว่าเป็นข้อมูลยืนยันใหม่

## Artifacts และวิธีรันซ้ำ

- `artifacts/model_leeching_protocol_v1/`: embeddings, pools, split manifests และ compressed draws ที่ล็อกแล้ว
- `artifacts/model_leeching_baseline_v1/`: baseline scores/calibration/summary
- `artifacts/model_leeching_deep_pure_v1/`: checkpoints, training histories และ scores
- `artifacts/model_leeching_comparison_v1/`: per-seed/aggregate results, paired differences, AUROC และ verification
- `artifacts/model_leeching_training_registration_v1.json`: configs และ hash snapshot ก่อน Deep training
- `artifacts/model_leeching_source_v1.zip`: source/config snapshot ของรอบนี้

คำสั่งและสูตรอยู่ใน [DEEP_KERNEL_PROTOCOL_TH.md](DEEP_KERNEL_PROTOCOL_TH.md) ใช้ชื่อ output/lock ใหม่สำหรับรอบใหม่เสมอ
