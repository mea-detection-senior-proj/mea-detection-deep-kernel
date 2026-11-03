# Deep Kernel MMD — Model Extraction Detection

โค้ดหลักอยู่ใน `deep_mmd/` ส่วนไฟล์ชื่อ pilot เดิมเป็นทางเข้าสำหรับคำสั่งเก่า
เริ่มอ่าน workflow จาก `deep_mmd/experiment.py`

```text
pilot/
├── deep_mmd/                  # implementation หลัก
│   ├── cli.py, __main__.py    # อ่าน config/CLI และเริ่มทดลอง
│   ├── experiment.py         # workflow: load → split → encode → train → evaluate → save
│   ├── datasets/
│   │   ├── registry.py       # dataset specifications
│   │   └── protocol.py       # JSONL, dedup, grouped splits, leakage audit
│   ├── embeddings.py         # frozen encoder และ embedding cache
│   ├── models.py             # neural feature network
│   ├── kernels.py            # RBF, Multi-RBF, Deep Kernel, MMD²
│   ├── sampling.py           # reference และ mixed traffic windows
│   ├── training.py           # objective, optimizer, validation checkpoint
│   └── evaluation.py         # calibration threshold และ detection scores
├── configs/
│   ├── datasets/             # หนึ่ง JSON ต่อ dataset
│   └── experiments/          # ค่าการทดลองที่ใช้ซ้ำได้
├── tests/                    # protocol, gradient, training, dataset extension
├── docs/                     # คู่มือเพิ่ม dataset และแผนพัฒนาต่อ
├── cache/                    # encoder/embeddings; ไม่เข้า Git
├── outputs/                  # ผลทดลองและ checkpoints; ไม่เข้า Git
├── deep_kernel_pilot.py      # compatibility entry point
├── protocol.py              # compatibility imports
├── test_*.py                 # compatibility test paths
├── run_known_pilot.py        # runner เดิม: 3 seeds × 2 windows
├── run_additional.py         # audit/runner/report เดิมสำหรับ 2 SST-2 datasets
├── summarize_main.py         # สรุปเฉพาะ protocol 6 runs ที่ล็อกไว้
└── *.md, *.json, diagnose_length.py  # รายงาน, provenance, diagnostic เดิม
```

ข้อมูลดิบยังอยู่ใน `data/` ที่ราก repository ใช้ร่วมกับวิธีตรวจจับอื่นได้
ผลทดลองและรายงานเดิมอยู่ตำแหน่งเดิมเพื่อให้ลิงก์เดิมยังใช้ได้

## เริ่มใช้งาน

รันจากราก repository หลังติดตั้ง dependencies ใน `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m pilot.deep_mmd --help

.\.venv\Scripts\python.exe -m pilot.deep_mmd `
  --config pilot/configs/experiments/known_attack.json `
  --device cuda `
  --embedding-model pilot/cache/bge-small-en-v1.5 `
  --output pilot/outputs/model_leeching/run_001
```

ตัวอย่างใช้ encoder ในเครื่อง ถ้ายังไม่มีให้ใช้ `BAAI/bge-small-en-v1.5`
ซึ่งจะดาวน์โหลดเมื่อรันจริง ใช้ `--device cpu` ได้หากไม่มี GPU
ไม่อนุญาตให้ทับ output ที่มีผลอยู่แล้ว ให้ตั้งชื่อ run ใหม่เสมอ

CLI override ค่าจาก experiment JSON; path ใน experiment JSON อ้างจาก working directory
ส่วน path ของไฟล์ข้อมูลใน dataset JSON อ้างจาก `--data-root`
config ตัวอย่างใช้ 20 reference repeats; ถ้าไม่ใช้ config จะคง default เดิมที่ 1 repeat

## เพิ่ม dataset และทดสอบ

เพิ่ม JSON ใน `configs/datasets/<name>.json` แล้วใช้ `--dataset <name>`
หรือส่ง `--dataset-config <path>` โดยไม่แก้โค้ดฝึก
ดู [คู่มือเพิ่ม dataset](docs/ADDING_DATASETS_TH.md)

```powershell
.\.venv\Scripts\python.exe -m pilot.deep_mmd `
  --config pilot/configs/experiments/known_attack.json `
  --dataset Meaeq_SST-2 `
  --output pilot/outputs/Meaeq_SST-2/run_001

.\.venv\Scripts\python.exe -m unittest discover -s pilot/tests -v
```

แต่ละ run ฝึกและประเมิน dataset เดียวแยกจากชุดอื่น
runner และ summary เดิมยังจำกัดการทดลองที่ล็อกไว้
test dataset ใหม่ใช้ embeddings จำลอง จึงไม่ดาวน์โหลด encoder

การจัดโครงสร้างครั้งนี้คงสูตร kernel, objective, RNG streams, splits และ calibration เดิม
objective ยังเป็น exploratory signal-to-noise proxy และ encoder ยัง frozen
จึงยังไม่ถือว่าจบ protocol งานวิจัยเต็มรูปแบบ
ดู [สถาปัตยกรรมและแผนพัฒนาต่อ](docs/ARCHITECTURE_TH.md)

---

# รายละเอียดการทดลอง pilot เดิม

## Additional datasets

`Meaeq_SST-2` and `ME_BERT_sst2_wiki` are inspected, downloaded datasets.
Pinned repository revision and file SHA256 hashes are recorded in
`ADDITIONAL_DATA_PROVENANCE.json`. `ADDITIONAL_DATA_AUDIT.json` records all
three split seeds and available class sizes. Run the audit alone with:

```powershell
.\.venv\Scripts\python.exe pilot/run_additional.py --audit-only
```

Run both datasets with the same six-case settings as model_leeching and
produce the combined method-first report:

```powershell
.\.venv\Scripts\python.exe -u pilot/run_additional.py
```

The two additional artifacts provide synthetic per-row IDs, index and query,
not source-passage provenance. Their splits link shared IDs and normalized
text, remove cross-label text collisions and deduplicate within each label.
This is an explicit ID/text-grouped protocol, not verified source-independent
evaluation. `model_leeching` retains its existing strict context parser and
source grouping. All datasets are trained and evaluated separately. The two
SST-2 benign pools overlap (see audit); this is not unseen-family testing.

The combined report is `MULTI_DATASET_RESULTS_TH.md`, with Method, Dataset,
Seed, Window, FPR, TPR 5%, TPR 10% at the top. Each dataset has its own
report, CSVs, charts, checkpoints and code snapshot under
`outputs/main_<dataset>_repeats20/`. Existing output folders are refused.
Individual runs use `run_known_pilot.py --dataset <name> --output <new-path>`;
individual summaries use `summarize_main.py <path> --dataset <name>`.

## Locked model_leeching experiment

Run the six-case comparison (seeds 1/20/42, windows 250/500) with 20
references in both calibration and test:

```powershell
.\.venv\Scripts\python.exe -u pilot/run_known_pilot.py
.\.venv\Scripts\python.exe pilot/summarize_main.py pilot/outputs/main_model_leeching_repeats20
```

The runner explicitly uses 20 epochs, 8 training windows per epoch, 32
validation windows, 200 calibration windows, and 100 test windows per
condition. The underlying pilot fixes training windows at 100 queries with
10% attacks; test conditions are benign, 5%, and 10% attacks. Each method
uses identical evaluation windows and reference draws. Thresholds use each
method's 95th calibration percentile. Checkpoints use validation only.

Output directories must be new; completed runs are never overwritten.
Use `--output` to choose a new experiment directory. `--reference-repeats`
is configurable for separate experiments, but the main summary validator
requires the locked value of 20. The summary checks all six settings, split
audits, calibration thresholds and reported rates before producing
`REPORT.md`, `summary.csv`, `validated_runs.csv`, `training_history.csv` and
`rates.svg` and `training.svg`. Ranges between seeds are descriptive, not confidence intervals.

This experiment studies known-attack behavior with the existing exploratory
objective. Length-only diagnostics remain background limitations; they are
not part of this experiment's method comparison.

This is exploratory code, not the complete research protocol. It compares a
median-bandwidth RBF, the repository's four-bandwidth RBF, and a learned
kernel. The learned kernel multiplies the fixed multi-RBF kernel by an RBF on
a small network's output. It trains on 10% mixed windows with a stabilized
signal-to-noise objective; this is a power-motivated proxy, not a validated
estimate of test power. Encoder embeddings are fixed.

Training uses independent RNG streams for bandwidth, training, validation,
calibration and test. A fixed set of validation windows is used to choose the
best epoch, including epoch zero (the untrained network); the checkpoint is
then frozen before calibration and testing. The default is 32 validation
windows. The objective uses variation among sampled mixed windows rather than
an established MMD power variance estimator, and these windows overlap. A
higher validation objective does not establish improved detection at a fixed
FPR. This is an exploratory proxy that needs further research validation.

For `model_leeching`, benign and attack rows reuse
question IDs, and attack prompts contain source passages shared by multiple
questions. Before splitting, rows are joined transitively by shared ID,
normalized query text, and normalized attack source passage. Connected groups
are randomly allocated 40/20/20/20 to train, validation, calibration and test.
Cross-label normalized text collisions are removed and same-label text is
deduplicated. Attacks in the calibration partition are reserved and unused.
The script fails if IDs or expected attack source passages cannot be parsed.
Each method uses identical test windows and reference draws and receives its
own threshold calibrated at the 95th percentile on the same held-out benign
calibration windows. `--reference-repeats` controls the number of benign
reference draws averaged for each window and applies to calibration and test.
With 20 repeats the test statistic uses the same number of reference draws as
the paper, but this protocol is not a reproduction of the paper: it uses a
separate source-grouped calibration pool and averages references during
calibration, whereas the paper calibrates using single benign-pair MMD scores
from its benign reference pool. Windows are sampled repeatedly, so rates are not based on
independent observations. The checks do not establish independence between
different source passages, detect paraphrases, or prove the meaning of IDs for
other datasets. This evaluates a known attack only. The prior
`known_attack_smoke` and `known_attack_gpu_smoke` results used text-only
splitting and should not be used as evidence of held-out performance.

From the repository root, with dependencies and the dataset installed:

```powershell
.\.venv\Scripts\python.exe pilot\deep_kernel_pilot.py `
  --dataset model_leeching --device cpu --window 250 `
  --embedding-model pilot/cache/bge-small-en-v1.5
```

Use `--device cuda` if the installed PyTorch supports the GPU. Outputs include
per-window scores, split hashes, settings, rates, training history and weights
in `pilot/outputs/known_attack`. Split hashes and the grouping audit are in
`metadata.json`. Set a different `--output` for each run. A capped run using
`--max-per-class` takes the first rows of each file and is only for smoke tests.
Before drawing research conclusions, add multiple seeds, source-aware splits,
uncertainty analysis, an unseen-family evaluation and systematic tuning.

For a direct exploratory comparison with 20 reference repeats:

```powershell
.\.venv\Scripts\python.exe pilot\deep_kernel_pilot.py `
  --device cuda --embedding-model pilot/cache/bge-small-en-v1.5 `
  --window 250 --seed 42 --reference-repeats 20 `
  --calibration-windows 200 --test-windows 50 `
  --output pilot/outputs/repeats20_bs250_seed42
```
