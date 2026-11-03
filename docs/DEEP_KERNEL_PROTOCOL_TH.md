# Protocol การเปรียบเทียบ RBF / Multi-RBF / Deep Kernel รอบแรก

รันรอบแรกเสร็จแล้ว ดูผลและข้อจำกัดใน [MODEL_LEECHING_COMPARISON_TH.md](MODEL_LEECHING_COMPARISON_TH.md) โดยเฉพาะ actual FPR ที่ยังไม่ตรงเป้าหมายทุก seed

## ขอบเขตที่เลือกก่อนรัน

- Dataset: model_leeching; grouped splits ของทางรันใหม่ ไม่ใช่ตัวเลข reproduction ของ paper เดิม
- Seeds: 1/20/42; window sizes: 100/250; requested attacker ratios: 1/5/10/25/100% และ benign-only
- Benign reference/calibration/test แยกกัน และแยกจาก train/validation
- Calibration: 500 windows; test: 200 windows ต่อ condition; reference draws: 20 ต่อ window
- Frozen encoder: local BAAI/bge-small-en-v1.5, file-content hash บันทึกใน protocol lock
- คำนวณ kernel/MMD และฝึก MLP ด้วย float64; deterministic algorithms; ปิด TF32
- ข้อมูลดิบไม่ถูกลบหรือแก้ไข Cleaning/splitting เป็นการเตรียมใน memory และบันทึก manifest

## ล็อกการประเมินก่อนฝึก

`experiments.prepare` สร้าง embeddings, split manifests, training pools และ calibration/test draws ให้ครบก่อนเริ่ม baseline หรือฝึก Deep Kernel เก็บ hashes และ lock ID ใน `lock.json`

`experiments.run` ตรวจ hashes และค่าที่กำหนด protocol ทุกครั้งก่อนใช้ ห้ามเปลี่ยน window/ratio/seed/reference repeats โดยใช้ lock เดิม ผล baseline และ Deep Kernel แยกรันได้ แต่ summarizer ยอมรวมต่อเมื่อ lock ID และ draw hashes ตรงกันทั้งหมด

Lock เป็นการตรวจความสอดคล้องของ artifacts ไม่ใช่ระบบ access control ผู้ที่จงใจแก้ทั้งไฟล์และ hashes ยังเปลี่ยนได้ จึงต้องเก็บ artifact snapshot เมื่อเผยแพร่ผล

## Fixed baselines

ประมาณ sigma จาก benign reference pool เท่านั้น Single RBF ใช้ sigma เดียว ส่วน Multi-RBF ใช้ 0.5/1/2/4 เท่า เฉลี่ยน้ำหนักเท่ากัน

ทั้ง calibration และ test ใช้คะแนนเฉลี่ยจาก 20 reference draws ของสถิติเดียวกัน:

```text
score = mean_over_references(
  sum_off_diagonal(Kxx)/(m*(m-1))
  + sum_off_diagonal(Kyy)/(n*(n-1))
  - 2*mean(Kxy)
)
```

การคำนวณ references แบบ batch เป็นเพียงการลด overhead ตรวจเทียบกับการคำนวณแยกแต่ละ draw และสูตรเดิมด้วย float64 แล้ว

## Deep Kernel

อ้างสูตร kernel จาก [Liu et al., ICML 2020, Eq. 1](https://proceedings.mlr.press/v119/liu20m/liu20m.pdf):

```text
g(z): 384 -> 128 -> ReLU -> 64
q(z,z') = exp(-||z-z'||² / (2*sigma_base²))
kappa(z,z') = exp(-||g(z)-g(z')||² / (2*sigma_feature²))
k(z,z') = ((1-epsilon)*kappa(z,z') + epsilon) * q(z,z')
```

MLP, bandwidths สองตัว และ epsilon เรียนรู้ได้ Bandwidths ใช้ exponential parameterization ส่วน epsilon ใช้ sigmoid เพื่อให้อยู่ระหว่าง 0 กับ 1 Initial base sigma ใช้ค่าจาก benign reference เดียวกับ RBF และ initial feature sigma ประมาณจาก mapped benign training rows เท่านั้น

นี่ต่างจาก Pilot ที่ใช้ multi-RBF เป็น base และ exploratory variability-across-windows proxy จึงไม่ควรนำผลมาสรุปรวมโดยใช้ชื่อ Deep Kernel เหมือนกันอย่างเดียว

## Objective และการฝึก

ใช้ paired U-statistic numerator และ regularized asymptotic variance estimator ตาม Eq. 2/4/5 ของ [งานต้นฉบับ](https://proceedings.mlr.press/v119/liu20m/liu20m.pdf):

```text
Hij = k(xi,xj) + k(yi,yj) - k(xi,yj) - k(yi,xj)
M = sum(i != j, Hij) / (n*(n-1))
V = 4*variance_population(row_mean(H))
J = M / sqrt(V + 1e-8)
loss = -J
```

V ใช้ H รวม diagonal ตาม variance V-statistic ของ Eq. 5 ไม่ใช่ sample variance ของหลาย traffic-window scores และไม่ใช่ variance ของ MMD ที่หาร n แล้ว Objective นี้เป็นเกณฑ์อิง asymptotic test power ไม่ใช่หลักฐานรับประกัน finite-window power

Training numerator ตัด cross diagonal ตาม paired U-statistic ของ paper แต่ score ตอนตรวจใช้ all-cross unbiased estimator เดียวกับ fixed baselines ทั้งคู่ประมาณ population MMD²; finite-sample values ไม่จำเป็นต้องเท่ากัน ไม่ได้อ้าง exact replication ของ training/testing algorithm แบบ permutation test ใน paper

Pure training เท่านั้น: benign 100 เทียบ known attacker ล้วน 100 ใช้ Adam learning rate 0.001, weight decay 0.0001, 30 epochs × 16 optimizer steps ต่อ epoch, gradient clipping 10

แต่ละ seed ใช้ validation pairs ที่ล็อกไว้ 32 คู่ โดยเลือก checkpoint ที่ mean validation J สูงที่สุด รวม untrained epoch zero เป็นตัวเลือก ไม่มี calibration/test arguments ใน training function หลังเลือกแล้วใช้ eval mode และปิด gradients ทุก parameter

Training RNG แยกจาก validation/calibration/test ชัดเจน ไม่มีการปรับ hyperparameters ตาม held-out results ในรอบนี้ Mixed training และ unseen-family ยังไม่ใช่ส่วนของการทดลองนี้

## การตั้ง threshold และการอ่านผล

ตั้ง empirical upper quantile แบบ `higher` ที่ nominal FPR 5% ด้วย benign calibration แล้วแจ้งเตือนเมื่อ score > threshold รายงาน held-out FPR ที่ได้จริงทุก method/seed/window ไม่ปรับ threshold จาก test ให้ดูเหมือน matched FPR

คะแนนที่รายงานเป็น resampled fixed-window results Queries อาจถูกใช้ซ้ำข้าม windows และ reference repeats ไม่ได้แปลว่ามี 20 ชุด reference ที่เป็นอิสระทั้งหมด จึงใช้ส่วนเบี่ยงเบนมาตรฐานระหว่าง seeds เป็นคำอธิบายความแปรปรวน ไม่ตีความเป็น confidence interval และไม่ใช้ naive binomial intervals จาก windows ที่ซ้อนทับ

หาก measured FPR ต่างกัน ไม่ควรสรุปว่า TPR ที่สูงกว่าคือความได้เปรียบที่ matched FPR จนกว่าจะตรวจ operating-point differences รวมถึงไม่มีข้อสรุปเรื่อง latency, streaming false-alert control หรือ unseen attacks จากผลรอบนี้

## คำสั่ง

สำหรับการรันทั่วไป แนะนำ [คำสั่งเดียวพร้อม flags](RUN_EXPERIMENTS_TH.md) คำสั่งแยกด้านล่างยังใช้ได้ แต่ CLI run ปัจจุบันเก็บผลดิบใต้ output/results และสร้างรายงาน output/report ให้อัตโนมัติ เมื่อต้องใช้ summarizer แยกกับผล CLI รุ่นใหม่ ให้ชี้ --runs ไปที่ results/ ของแต่ละ run

รันจากราก repository ใช้ output ใหม่เสมอ:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

.\.venv\Scripts\python.exe -m experiments.prepare --config configs/experiments/model_leeching_baseline_locked.json --output artifacts/model_leeching_protocol_v1

.\.venv\Scripts\python.exe -m experiments.run --config configs/experiments/model_leeching_baseline_locked.json

.\.venv\Scripts\python.exe -m experiments.run --config configs/experiments/model_leeching_deep_pure_locked.json

.\.venv\Scripts\python.exe -m experiments.summarize_comparison --runs artifacts/model_leeching_baseline_v1 artifacts/model_leeching_deep_pure_v1 --output artifacts/model_leeching_comparison_v1
```

เปลี่ยนทั้ง protocol_lock/output ใน config เมื่อต้องการรันรอบใหม่ ไม่ทับ artifact ที่เสร็จแล้ว
