# Phase F — Implementation Feasibility และ bounded audit gates

วันที่ 7 พฤศจิกายน 2026 | `experiment/stream-prada-order`
อ่านคู่กับ [DATA PLAN](PHASE_F_DATA_PLAN_TH.md) และ
[PROTOCOL](PHASE_F_PROTOCOL_TH.md)

**GO: public metadata/schema audit บนเครื่องปัจจุบัน**
**NO-GO: data acquisition/actual extraction/training/full experiment ในงานนี้**
ยังไม่มี collector authorization, licensed MEA payload และจำนวน eligible outer
bundles ที่พิสูจน์แล้ว ไม่ถือ resource arithmetic เป็นการอนุมัติรันโมเดล

## 1. Inventory ที่ตรวจจริงแบบ read-only

หลักฐาน [hardware.json](diagnostics/phase_f_preparation/hardware.json) และ
[environment.json](diagnostics/phase_f_preparation/environment.json)
ค่าหน่วยความจำ/พื้นที่ว่างเป็น snapshot เปลี่ยนได้ ต้องวัดใหม่ก่อน execution

| รายการ | ผลตรวจ Phase F |
| --- | --- |
| OS | Microsoft Windows 11 Home, build26300, 64-bit |
| RAM ที่ OS เห็น | 63.77 GiB; available ประมาณ36.5 GiB ขณะตรวจ |
| GPU | RTX4060Ti, total8188MiB, driver-free6584MiB ขณะ inventory |
| NVIDIA driver | 617.42 |
| Workspace disk free | ประมาณ956.12GiB |
| Python/environment | `senior`, Python3.11.17 |
| PyTorch | 2.14.1+cu132; build CUDA13.2 |
| CUDA visibility | `torch.cuda.is_available()` true; **ไม่ได้รัน kernel/BF16/model load test** |
| NumPy / SciPy | 2.4.6 / 1.17.1 |
| Transformers / sentence-transformers | 5.20.2 / 5.7.0 |
| huggingface-hub | 1.33.0 |
| datasets / pyarrow / vllm / accelerate | ไม่พบ installed package metadata ใน senior |

Python platform string แสดง Windows-10 API version แต่ CIM caption ยืนยัน
Windows11 จึงไม่ใช้ platform string อย่างเดียวตัดสิน OS
ไม่มี package installation/update, model load หรือ GPU kernel execution ในงานนี้
การเห็นCUDAไม่ยืนยันว่า exact victim/attention backend จะรันผ่าน

## 2. MEA-Bench paper profile ไม่พร้อมรันตรง ๆ บนเครื่องนี้

Pinned [requirements](https://github.com/sliu11-byte/MEA-Bench/blob/947c5d7988a5ffd4cc425dfbae3532fd2c160a5b/requirements.txt)
ระบุ torch2.11.0+cu128, transformers5.14.1, datasets5.0.1, accelerate1.14.0,
vllm0.26.0 ฯลฯ ต่างจาก senior ปัจจุบัน ห้ามติดตั้งทับ senior เพื่อให้เข้ากัน
ไม่ถือ broad version constraints ของ Deep-Kernel ว่าเป็น lock ของ benchmark

ตาม [official vLLM platform documentation](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/)
ไม่มี native Windows support ต้องมี compatible Linux/WSL environment หรือ
ทางเลือกอื่นที่ตรวจใหม่ รอบนี้ไม่ได้ตรวจรับ WSL/container/runtime และไม่ติดตั้ง
fork หรือเปลี่ยน model-serving stack โดยอัตโนมัติ Stable docs ไม่ใช่ผลทดสอบ
compatibility ของ pinned vllm0.26.0 กับ hardware/driverนี้

README paper profile ใช้ teacher70B/72B และ student7B/8B การคิด BF16 weights
อย่างเดียวของ70Bประมาณ140GB decimal เกิน VRAM8GBมาก ยังไม่รวม KV/activations
จึง **NO-GO สำหรับ unmodified local paper-profile reproduction** บน GPUนี้
CPU offload/quantization/external endpoint เป็นคนละ resource/model condition
ต้องมี protocol/สิทธิ์/งบใหม่ ไม่ลด modelหรือbudgetเงียบ ๆ แล้วเรียก paper-faithful

ห้าม execute attack CLI แม้ `--help`/`--dry-run` จน source/side-effect audit
ชัด เพราะ runners มีหน้าที่สร้าง prerequisites/transcripts/services/training
ไม่ใช้ CLI เป็นวิธีดู schema ใน Phase F

## 3. Small local victim: feasible candidate แต่ยัง unmeasured

Qwen2.5-1.5B-Instruct revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
ตรวจเฉพาะ public model metadata/license/config ไม่ดาวน์โหลด weights/tokenizer
มี **1,543,714,304 parameters** ตาม safetensors metadata; BF16 arithmetic
weights=**3,087,428,608 bytes≈2.875GiB** ส่วน actual weights file indexระบุ
3,087,467,144bytes (ไม่ใช่ peak VRAM ที่วัดแล้ว)

Config: layers28, KVheads2, hidden1536/attentionheads12 ให้ head dimension128
สมมติ batch1, input2048, new tokens128, BF16 KV:

`2(K,V)×28×2×128×2176×2 bytes = 62,390,272 bytes = 59.5 MiB`

ยังไม่รวม prefill/attention/logits/allocator/framework/workspace และ concurrent
display/GPU use จึงเป็น **arithmetic lower-component estimate** ไม่ใช่ load-
time guarantee หรือ measured latency/throughput
หลักฐาน [planning_calculations.json](diagnostics/phase_f_preparation/planning_calculations.json)

Candidate routeในอนาคตคือ native Transformers single-model inference บน
dedicated pinned environment เมื่อ compatibilityผ่าน ไม่ใช่เปลี่ยน MEA-Bench
paper stack แล้วอ้าง reproduction รุ่นเดิม ไม่มี student/training feasibility
ที่ยืนยันแล้วและไม่มี actual local extraction run ใน Phase F

## 4. Stage budgets และ hard stops

ตารางต่อไปนี้ **เป็น proposed gates** ต้องระบุขอบเขต/authorizationใหม่ก่อน
ข้ามไป stageที่มี payload/model/requests ไม่มีการให้ timeoutผ่านแล้วถือเป็นอนุมัติ

| Stage | Network/storage cap | เวลา/RAM/GPU | Victim/attack/training budget | สถานะ |
| --- | --- | --- | --- | --- |
| F0 public metadata/schema declaration | รอบละ<=20 logical metadata GETs, <=1MiB/response, <=5MiB received total, <=10MiB local evidence | <=120s/round; <=512MiB process RAM; GPU0 | victim0, attack0, train0 | GO; ทำเฉพาะการตรวจเอกสาร/metadataใน Phase F แล้ว |
| F1 bounded payload/schema sample | proposed<=200 records, <=5MiB wire bytesรวม redirects/retries, <=20MiB local; <=10 GETs | <=120s, RAM<=512MiB, GPU0 | victim0, attack0, train0 | NO-GO จน applicable data terms, source allowlist และ sampling/privacy protocolได้รับอนุญาต |
| F2 optional local runtime readiness probe | weights/cache cap8GiBหลังอนุมัติแยก; ไม่ fetch corpus; raw probe logs<=16MiB | cached-load/inference<=120s; RAM available>=8GiB; driver-free VRAM>=6GiB; own reserved peak<=5.5GiB | <=4 actual authorized benign requests, input<=2048/output<=128 tokensต่อrequest; attack0/train0 | ไม่ได้รัน; ต้อง pin environmentและผ่าน authorization/load gateใหม่ |
| F3 faithful extraction acquisition / study | ต้องมี family/run-specific byte/query/token/request caps และ worst-case retries | ต้อง benchmark/projectionตาม actual implementation ก่อน | **ยังไม่อนุญาต ไม่มีค่าที่วัดแล้ว** | NO-GO; ขอบเขตนอก Phase F |

F0 ใช้ stdlib HTTP/JSON + installed package metadata ได้ ไม่ต้อง datasets/pyarrow
การดู declared schema ไม่รับรอง actual row schema/chronology หากมีแต่ files
ที่ต้อง download payloadจึงตรวจได้ ให้คงunknownจนF1 ไม่เปิด row previewแทน
ไม่ใช้ generic `load_dataset`/snapshot_download/streaming loader ที่อาจดึง shards
หรือซ่อน cache/retry costs แล้วเรียกว่า bounded download

F1 fail-closed readerที่ต้อง implement/testในงานใหม่:

- pin exact revisionและfile allowlist; check Content-Length/Content-Range และ
  redirect targetก่อนรับ body นับ received bytesจริงรวม retries; บังคับ wall
  deadlineขณะรับไม่ใช่หลัง requestจบ ปิด connectionเมื่อ capถึง
- large Parquet shardของWildChatประมาณ180–336MBไม่ใช่bounded sample5MiB
  ห้าม download full shardเพื่อเอาแค่200 rows หากไม่มี row/range accessที่อยู่
  ในbudget ให้หยุดและขอแผนใหม่ ไม่ fallbackไปfull download
- HTTP Rangeเป็นเพียง mechanism ไม่รับรองsmall transfer ถ้า serverคืน200/full
  ให้abortก่อนbody; current F0ไม่ทำrangeหรือpayload requests
- จำลอง corrupt schema/missing IDs/out-of-order/cap exceeded ด้วย metadata/
  numeric fixturesก่อนใช้ข้อมูลจริง ไม่สร้างsynthetic research traffic

F2 ไม่มี downloadในcached-load120sถ้าไม่มีexactweightscacheต้องหยุดและใช้
separate authorized download planก่อน ไม่ขยายdeadline/dropdtype/offloadเพื่อผ่าน
OOM, incompatible kernels, VRAM/RAM gatefailเป็นstop ไม่ retryเปลี่ยนsettings
Probe4requestsไม่ใช่extractionrunและไม่ให้ countเป็นindependent researchcohorts

F3ต้องแยก collection-onlyกับfull method: ถ้าattackต้องstudent/warmup/training
ห้ามข้ามแล้วอ้างfaithful รุ่นบนsmallvictimไม่ใช่paperdefault ต้องระบุเป็น
authorized adaptationและfreezeadaptercommitก่อน acquisition ไม่มีการรันในPhase F

## 5. ขนาดข้อมูลและ sample-size feasibility

WildChat data filesตามindexประมาณ3.36GBdecimal; declared in-memory dataset
ประมาณ6.84GB แต่ RAM/diskที่พอ **ไม่ทำให้ full downloadอยู่ในขอบเขต**
MEA data filesตามindexประมาณ325.83MBdecimal; ไฟล์เล็กก็ยังติดlicense/provenance
Qwen indexed repositoryรวมประมาณ3.10GB ไม่ดึง weightsในรอบนี้

Protocol targets360 independent bundles/552streamsเป็น recruitment requirement
หลัง grouping/matching—not availability claim ปัจจุบัน **ไม่มี accepted new
bundlesที่ผ่าน audit** ค่าavailable scientific cohortsยังunknown ไม่ใส่0แทน
จำนวนที่ยังไม่วัด และไม่เพิ่มnด้วยseeds/budgets/sharedteacher transcripts

ข้อจำกัดหลักจึงเป็น data access/intent/chronology/common support และ effective
outer n ไม่ใช่ GPU speed การมีเครื่องพอ parse metadata ไม่ได้แปลว่าหา200
final benign bundles/150attack bundlesจากusers/sourcesอิสระได้
ไม่ประมาณเวลา/ราคา actual acquisitionจากPhase C/D/E CPU timing

## 6. งานที่ทำจริงและการตรวจเอกสาร

ทำ read-only OS/GPU/Conda package inventory, public HF metadata/schema index,
pinned README/license/configและGitHub code/schema readsเท่านั้น เก็บ exact
revisions/blob hashes/response hashes ไม่มี full datasets/private logs/model load
และไม่มี detector evaluation/training/extractionหรือpackage changes

Saved HF metadata batch3responses=18,592bytes; pinned public documents4responses
รวม43,118bytes ตัวเลขนี้คือ **body bytesของสอง batchesที่มี evidence files**
ไม่ใช่ network totalของทุก browser/connector/redirectใน session หรือ bandwidth
benchmark และไม่ใช้เป็นbudgetของdata acquisitionจริง
ตรวจ links/revision pins, schema/intent unknowns, quota arithmetic, memory formula,
Thai UTF-8, artifact hashesและGit preservation; ไม่มีanalysis-code changeที่
ต้องรันdetector testsซ้ำ ไม่รายงานtestsเก่าของPhase Eว่าเป็นnew executionของF

## 7. Final GO / NO-GO และ exact entry conditions

**GO F0:** เครื่อง/envรองรับ bounded public metadata/schema assessment และ
เอกสารPhase Fพร้อมreview โดยไม่ต้อง model/data execution

**NO-GO F1/F2/F3และ full experiment จนกว่าจะครบตามstage:**

1. exact sources/revisions/file allowlistพร้อมdata/model/code licenseและretention
   terms; MEA query-data rightsต้องresolveแยกจากMIT code
2. source/participant/victim accessauthorizationและprivacy/intent policy;
   ไม่มีการaccessprivate logsในTaskนี้
3. signed-off sample/collector protocolที่กำหนดchronology, missing/duplicate/retry
   semantics, actor/source/run components, exposure ledgerและcommon-support checks
4. accepted explicitbytes/storage/wall/request/token capsและfail-closed audit
   implementationก่อนpayload; futureGPU executionต้องkernel/load/peak-memory gate
5. measured eligible cohort countsผ่านquotasหรือรายงานlimited/nogoก่อน scoring;
   original PRADA warm-up/horizonไม่ถูกเปลี่ยนให้dataสั้นผ่าน
6. final-test lock/selection/power/multiplicity planก่อนclaim improvement;
   ไม่มีthreshold/hyperparameter optimizationบนconfoundedPhase C–Eอีก

จบที่localcommitบนexperimentbranchเท่านั้น เก็บหลักฐานเดิม ไม่push/merge/
rebase/PRและไม่แตะmain ไม่มีการเริ่มstageใหม่อัตโนมัติจากคำตัดสินGO metadata
