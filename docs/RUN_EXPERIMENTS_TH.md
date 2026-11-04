> Historical document: source locations and commands below predate the migration. Use [current English commands](RUN_EXPERIMENTS.md) and the [migration record](CLEAN_ARCHITECTURE_MIGRATION.md). ADR 0001 governs scientific scope; ADR 0003 supersedes older restructuring guidance.

# รันด้วย config และ flags ในคำสั่งเดียว

## เริ่มใช้งาน

เปิด PowerShell ที่รากโปรเจกต์ แล้วใช้ environment ที่ติดตั้ง dependencies ไว้:

```powershell
cd C:\Users\AAA\Documents\mmd-llm-mea-detection

.\.venv\Scripts\python.exe -m experiments.run `
  --config configs/experiments/deep_pure.json `
  --dataset model_leeching `
  --device cuda `
  --embedding-model artifacts/models/bge-small-en-v1.5 `
  --methods rbf multi_rbf deep_kernel `
  --window 250 `
  --seed 42 `
  --reference-repeats 20 `
  --calibration-windows 200 `
  --test-windows 500 `
  --output artifacts/my_comparison_500 `
  --dry-run
```

ดูแผนให้เรียบร้อยแล้วนำ `--dry-run` ออกเพื่อรันจริง Output ในตัวอย่างยังไม่ถูกสร้างโดย dry-run ใช้ชื่อใหม่ทุกครั้งที่รันจริง

คำสั่งเดียวจะตรวจข้อมูล เตรียม embeddings ล็อกชุดประเมินร่วม รัน methods ที่เลือก และสรุปผล ไม่ต้องเรียก prepare/run/summarize แยกกันสำหรับการใช้งานทั่วไป

Config `deep_pure.json` เลือกทั้งสามวิธีและใช้ค่าฝึกจากการทดลอง pure-training รอบแรก ตัวอย่าง window 250/seed 42 เปลี่ยนเฉพาะ evaluation window/seed ส่วน training window ยังคง 100

`artifacts/models/bge-small-en-v1.5` เป็นไฟล์ encoder ที่คัดลอกไว้สำหรับทางรันใหม่ เปลี่ยนเป็น encoder folder อื่นได้ ระบบใหม่ไม่ต้องอ่านไฟล์หรือ import โค้ดจาก `pilot/` ส่วน Pilot และผลเดิมยังเก็บไว้ครบ

หากติดตั้งในเครื่องใหม่ ให้เตรียม local encoder ไว้ในตำแหน่งนี้หรือระบุ `--embedding-model` เป็นโฟลเดอร์ที่มีอยู่จริง ไฟล์ใต้ `artifacts/` ไม่เข้า Git ข้อมูลแหล่งที่มาสำหรับ audit อยู่ที่ `data_pipeline/provenance/ADDITIONAL_DATA_PROVENANCE.json`

## กติกาการเลือกค่า

Dataset อ่านจาก `data/<ชื่อ>/normal/queries.jsonl` และ `data/<ชื่อ>/attacker/queries.jsonl` โดยตรง ไม่ต้องมี `configs/datasets/` หรือ registry หากต้องการข้อมูลอีกเวอร์ชัน ให้ copy เป็นโฟลเดอร์ใหม่ เช่น `data/model_leeching_v2/` แล้วใช้ `--dataset model_leeching_v2` หรือเลือก root อื่นด้วย `--data-root`

แต่ละแถวใช้ string fields `id` และ `query` เหมือนข้อมูลเดิม ชื่อ dataset มีช่องว่างได้เมื่อใส่เครื่องหมายคำพูด เช่น `--dataset "my dataset v2"` แต่ต้องเป็นชื่อโฟลเดอร์เดียว ไม่ใช่ path ที่มี slash หรือ parent-directory traversal

ระบบจัดกลุ่มจาก ID/normalized text และ source context ที่ parse ได้จากข้อความโดยอัตโนมัติ หาก parse context ได้บางส่วนจะยังจัดกลุ่มส่วนที่รู้ และบันทึก coverage ไว้ ไม่อ้างว่า source provenance ครบ การกรองซ้ำและแบ่งชุดอยู่ใน memory ไม่เขียนทับข้อมูลต้นฉบับ

ลำดับ: **ค่าเริ่มต้น → JSON config → flags ที่พิมพ์จริง** ค่าที่ไม่ได้พิมพ์จะไม่ทับ JSON

Training flags จะรวมเฉพาะ field ที่เปลี่ยน เช่น `--epochs 10` ไม่ทำให้ hidden_dim/feature_dim/learning_rate ใน config หายไป โปรแกรมไม่เขียนกลับไปแก้ config ต้นฉบับ

| Flags | ความหมาย |
|---|---|
| `--config <JSON>` | ค่าเริ่มต้นของการทดลอง; ไม่บังคับหากระบุค่าจำเป็นด้วย flags ครบ |
| `--dataset <name>` | เลือกโฟลเดอร์ข้อมูลโดยตรงใต้ data-root ไม่ต้องสร้าง JSON |
| `--methods rbf multi_rbf deep_kernel` | รันเฉพาะวิธีที่ระบุ |
| `--window 250` | Evaluation window เดียว |
| `--window-sizes 100 250` | Evaluation หลายขนาด |
| `--seed 42` / `--seeds 1 20 42` | หนึ่งหรือหลาย seed |
| `--attacker-ratios 0.01 0.05 0.1 1` | Fractions ของ attacker ไม่ใช่เลขเปอร์เซ็นต์ 1/5/10/100 |
| `--reference-repeats 20` | จำนวน reference draws ที่เฉลี่ยต่อ window |
| `--calibration-windows 200` | จำนวน benign calibration windows ต่อ seed/window |
| `--test-windows 500` | จำนวน test windows ต่อ condition รวม benign แยกอีก condition |
| `--target-fpr 0.05` | Nominal calibration target; ไม่รับประกัน actual test FPR |
| `--train-window 100` | ขนาดคู่ฝึก Deep Kernel; แยกจาก evaluation window |
| `--epochs 30` / `--learning-rate 0.001` | ปรับค่าฝึกที่ใช้บ่อย |
| `--device cuda` / `--device cpu` | อุปกรณ์สำหรับ encoder และการคำนวณ |
| `--dtype float64` | Dtype สำหรับ kernel/MMD และการฝึก |
| `--embedding-model <path-or-model-id>` | Frozen encoder |
| `--embedding-revision <commit-SHA>` | ต้องตรึง commit 40 ตัวสำหรับ remote model |
| `--query-prefix <text>` | Prefix ของข้อความก่อนเข้า encoder |
| `--encode-batch-size 64` | Batch สำหรับ encoder; ไม่ใช่ traffic window |
| `--bandwidth-sample-size 2000` | จำนวน reference samples สำหรับ median bandwidth |
| `--data-root` / `--cache-dir` / `--output` | ตำแหน่งข้อมูล cache และผลรอบใหม่ |
| `--protocol-lock <folder>` | ใช้ embeddings/splits/draws ที่ล็อกไว้แล้ว |
| `--dry-run` | ตรวจค่ากับจำนวนข้อมูลและแสดงแผน โดยไม่สร้างไฟล์หรือเริ่มงานหนัก |

`--window` กับ `--window-sizes` ใช้พร้อมกันไม่ได้ เช่นเดียวกับ `--seed`/`--seeds`

Dry-run ตรวจข้อมูลจริงและความเพียงพอของแต่ละ split หากใช้ lock เดิมจะตรวจ settings กับ hashes ของ lock ด้วย แต่ไม่ตรวจว่า GPU ใช้งานได้จริงหรือว่า remote encoder ดาวน์โหลดได้ จนกว่าจะรันจริง

## เลือกเฉพาะ baseline

```powershell
.\.venv\Scripts\python.exe -m experiments.run `
  --config configs/experiments/deep_pure.json `
  --methods rbf multi_rbf `
  --window-sizes 100 250 `
  --seeds 1 20 42 `
  --output artifacts/my_baselines
```

จะไม่ฝึก Deep Kernel และไม่ตรวจว่า train/validation มี attacker พอสำหรับ Deep training หรือไม่ รายงานแสดงเฉพาะ methods/ratios ที่เลือก ไม่มีแถว Deep Kernel ที่ไม่ได้รัน

## ลองเส้นทางแบบสั้นก่อน

```powershell
.\.venv\Scripts\python.exe -m experiments.run `
  --config configs/experiments/deep_pure.json `
  --window 100 --seed 42 `
  --reference-repeats 2 `
  --calibration-windows 8 --test-windows 4 `
  --epochs 1 `
  --output artifacts/my_cli_smoke
```

มีไว้ตรวจว่ารันครบเท่านั้น ไม่ใช้สรุปประสิทธิภาพหรือการคุม FPR

## ใช้ protocol lock เดิม

เพิ่ม `--protocol-lock <previous-output>/protocol` และใช้ output ใหม่ ค่าที่กำหนด evaluation protocol ต้องตรงกับ lock เช่น dataset, encoder, dtype, seeds, window sizes, ratios, repeats และ counts

Lock เดิมที่บันทึก encoder ใต้ `pilot/cache/` ยังเป็นหลักฐานของรอบเก่า ไม่แก้ไขย้อนหลัง การเปลี่ยนตำแหน่ง encoder ทำให้ settings และ embedding cache key เปลี่ยน แม้เนื้อหาโมเดลเหมือนเดิม ให้สร้าง lock ใหม่ สำหรับ config `model_leeching_baseline_locked.json` และ `model_leeching_deep_pure_locked.json` ที่ยังระบุ lock รอบแรก ให้เตรียมและเลือก lock ใหม่อย่างชัดเจน:

```powershell
.\.venv\Scripts\python.exe -m experiments.prepare --config configs/experiments/model_leeching_baseline_locked.json --output artifacts/model_leeching_protocol_standalone
.\.venv\Scripts\python.exe -m experiments.run --config configs/experiments/model_leeching_baseline_locked.json --protocol-lock artifacts/model_leeching_protocol_standalone --output artifacts/model_leeching_baseline_standalone
.\.venv\Scripts\python.exe -m experiments.run --config configs/experiments/model_leeching_deep_pure_locked.json --protocol-lock artifacts/model_leeching_protocol_standalone --output artifacts/model_leeching_deep_pure_standalone
```

หากเปลี่ยนค่าที่ขัดกัน โปรแกรมจะบอกชื่อ field, requested value และ locked value แล้วหยุดก่อนสร้าง output ไม่แก้ lock เดิมให้เอง และไม่ข้ามเงียบ ๆ การเปลี่ยน config ที่มี protocol_lock เดิมอยู่แล้วให้เป็นการทดลองใหม่ควรใช้ config ใหม่ที่ไม่มี protocol_lock

สามารถเปลี่ยน methods, training settings หรือ device สำหรับการใช้ draws เดิมได้ แต่การปรับสูตร/ค่าฝึกตามผล test เดิมต้องถือเป็น exploratory work และไม่ใช่ independent confirmation

## ผลลัพธ์

```text
artifacts/my_comparison_500/
├─ config.json             ค่าจริงจาก defaults/config/flags
├─ resolved_config.json    ค่าภายในที่ระบุ lock/results paths หลังเตรียมเสร็จ
├─ plan.json               แผนและจำนวนข้อมูลที่ตรวจแล้ว
├─ run.json                สถานะ complete/failed และ phase
├─ protocol/               Embeddings, split manifests, shared draws และ lock ID
├─ results/
│  ├─ config.json
│  ├─ metadata.json
│  ├─ summary.csv
│  └─ seed_42/
│     ├─ deep_kernel.pt     มีเมื่อเลือก Deep Kernel
│     ├─ training.json
│     └─ window_250/        Scores และ calibration scores ของทุก method ที่เลือก
└─ report/
   ├─ REPORT.md
   ├─ overall.csv
   ├─ per_seed.csv
   ├─ minimum_windows.csv    ขนาด window ต่ำสุดที่ผ่านเกณฑ์ แยกต่อ seed
   ├─ availability.csv       เงื่อนไขที่ข้อมูลรองรับและสาเหตุที่ไม่รองรับ
   ├─ rates_*.png            กราฟ TPR คู่กับ measured FPR แยก dataset/สัดส่วน attack
   ├─ auroc_per_seed.csv
   └─ paired_differences.csv  มีเมื่อเลือก Deep Kernel คู่กับวิธีเปรียบเทียบอื่น
```

ถ้าใช้ external protocol lock จะไม่มี protocol/ สำเนาใหม่ใน output แต่บันทึกตำแหน่ง lock ใน resolved_config/run metadata การย้ายหรือเก็บผลจึงต้องเก็บ lock ที่อ้างถึงด้วย

เมื่อมี seed เดียว รายงานไม่แสดง between-seed standard deviation เป็น ±0 เพราะยังประมาณความแปรปรวนข้าม seed ไม่ได้

รายงานตรวจความครบเทียบกับ protocol lock และตรวจอัตราใน summary กับคะแนนรายหน้าต่างก่อนสรุป
จึงต้องเก็บไฟล์ config, scores, calibration scores และ lock ที่อ้างถึงไว้ด้วย
ผลหลาย dataset แสดงแยกกัน โดยแต่ละ dataset ต้องมี lock เดียวกันระหว่างวิธีที่เปรียบเทียบ
ชื่อวิธีในรายงานมาจากวิธีที่เลือกจริง ไม่จำกัดไว้เฉพาะสามชื่อเดิม

`minimum_windows.csv` ใช้เกณฑ์ measured TPR ≥ 90% พร้อม measured FPR ≤ 5%
แยกตาม dataset, seed, method และ attacker fraction จากขนาดที่ทดลองจริงเท่านั้น:

- `reached`: มีขนาดที่ผ่านเกณฑ์ แสดงขนาดต่ำสุดพร้อม TPR/FPR ของขนาดนั้น
- `not_reached`: มีขนาดที่รองรับ แต่ยังไม่มีขนาดผ่านเกณฑ์
- `unavailable`: ไม่มีขนาดที่ข้อมูลรองรับสำหรับเงื่อนไขนั้น

ค่าที่หายหรือ run ไม่สมบูรณ์จะถูกปฏิเสธ ไม่ถูกนับเป็น `unavailable` หรือ TPR ศูนย์
ส่วนตัวรันยังหยุดเมื่อพบข้อมูลไม่พอตามพฤติกรรมเดิม การข้ามช่องที่ไม่รองรับยังเป็นงานแยก
กราฟใช้ Matplotlib จาก `requirements.txt` และแสดงค่าเฉลี่ยเชิงพรรณนาข้าม seed;
การผ่านเกณฑ์ราย seed ไม่ใช่หลักฐานรับประกัน FPR ระดับประชากร

## คำสั่งเดิมและสูตรวิจัย

CLI `experiments.run --config ... --output ...` เดิมยังใช้ได้ และคำสั่ง prepare/summarize แยกยังมีอยู่ แต่ CLI run ตอนนี้รวม workflow และวางผลดิบใต้ `output/results/` พร้อมรายงานใต้ `output/report/` ให้อัตโนมัติ ผลการทดลองเก่าที่รันเสร็จแล้วไม่ถูกย้ายหรือแก้ไข

สูตร kernel, loss, sampling และ calibration policy ไม่ได้เปลี่ยนจาก [DEEP_KERNEL_PROTOCOL_TH.md](DEEP_KERNEL_PROTOCOL_TH.md) การปรับครั้งนี้เป็นการสั่งงานและจัด artifacts ไม่ใช่การแก้ข้อจำกัด actual FPR ที่พบในผลรอบแรก

ตรวจโค้ดด้วย `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
