# Phase I — Qwen Snapshot & Runtime Preflight

วันที่ 7 พฤศจิกายน 2026 | `experiment/stream-prada-order`

**ผล: NO-GO สำหรับ real inference pilot และยังไม่อนุมัติ download**
ตรวจ clean Phase H commit และ frozen artifacts ผ่านแล้ว; CPU imports และ
dependency check ผ่าน แต่ไม่พบ exact snapshot ใน cache ที่ได้รับอนุญาตให้ตรวจ
ยังไม่มี supplied/validated execution grant, query plan และ private pilot store
GPU kernel/BF16, model loading และ generation ยังไม่ถูกทดสอบ

อ่าน Phase H implementation/readiness/design ฉบับเต็มกับ package README ก่อนทำ
งาน ไม่มีการแก้ Phase A–H evidence, runtime, detectors หรือ Deep Kernel MMD

## 1. Git/source revisions ที่ยืนยันก่อนสร้าง Phase I deliverables

ตรวจสองรอบขณะ checkoutสะอาด โดยเก็บ outputsใน ignored technical-preflight
directory ก่อนคัดเฉพาะ metadataที่ไม่ sensitiveเข้ารายงาน ไม่แก้ dirty flagให้ผ่าน

หลักฐานหลัก [entry.json](diagnostics/phase_i_preflight_20261107_v2/entry.json)
และ [clean H readiness](diagnostics/phase_i_preflight_20261107_v2/clean_h_readiness.json)
บันทึกที่12:36UTC /19:36 Asia/Bangkok วันที่7พฤศจิกายน2026:

| รายการ | ผล |
| --- | --- |
| Branch | `experiment/stream-prada-order` |
| Clean entry commit | `8d32d46bb1496862ddf36017b7eea811c01dc51c` |
| Git statusก่อน/หลัง preflight | clean=true |
| main | `5fb5e07d750a73a0a663a174433bab931ae7568a` ไม่เปลี่ยน |
| G/H manifests |39และ46 referenced filesตรง SHA256ทั้งหมด; ตัวmanifestตรงต้นฉบับใน H commitด้วย |
| Runtime code digest | `d163635f0a490a016b7a1fc4a0ce378d464577cd91ec99fe8f08804f9cd6dc87` |
| Qwen model/tokenizer revision | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` ทั้งคู่ |

Phase I เพิ่มเฉพาะ checker/tests/reports/technical receipts หลัง clean checkนี้
เมื่อ commitรายงานแล้ว HEADจะใหม่ จึงต้อง bind manifest/grantกับ **HEAD ที่จะ
executeจริง** ไม่ใช้8d32d46เป็น collector_revision แบบค้างไว้โดยอัตโนมัติ

## 2. Cache inspection ที่ทำจริง

[cache_inventory.json](diagnostics/phase_i_preflight_20261107_v2/cache_inventory.json):
ตรวจ allowlisted envใน Conda senior: HF_HOME, HF_HUB_CACHE,
HUGGINGFACE_HUB_CACHE, XDG_CACHE_HOME และสาม legacy Transformers/PyTorch cache
variables **ทั้งหมด unset** ไม่มี user-provided model locationเพิ่มเติมใน taskนี้

Effective/default rootที่ตรวจ:

```text
C:\Users\varic\.cache\huggingface\hub
  models--Qwen--Qwen2.5-1.5B-Instruct\snapshots\
  989aa7980e4cf806f80c7fef2b1adb7bc71aa306
```

Hub directoryมีอยู่ แต่ Qwen model directoryและ exact snapshotไม่มี
จึงอ่าน/hash local model tensors **0bytes**; local snapshot hashesยังไม่ verified
เป็น missing ไม่ใช่ observed hash mismatch หรือหลักฐานว่า weightsเสีย

ไม่ได้ crawl drives/โฟลเดอร์อื่น, อ่าน private logs, token stores หรือ private
approval records ไม่สรุปว่าเครื่องทั้งเครื่องไม่มีQwen หากมี alternate location
ต้องระบุ explicitผ่าน --model-location/--cache-root เพื่อให้ตรวจได้ในรอบใหม่

Checkerเคารพ installed Hub cache precedence และตรวจ explicitly-set legacy
pathsด้วย; frozen H defaultยังคงเดิม ถ้าอนาคตเจอsnapshotนอกH default ต้องส่ง
--snapshotที่ผ่านhashให้ H readiness/adapter โดยชัดเจน ไม่เปลี่ยนH code/envเงียบ ๆ

## 3. Environment และ resources

[CPU import probe](diagnostics/phase_i_preflight_20261107_v2/cpu_import_probe.json)
แยก process, CPU-only/offline, gate45s/1GiB ผ่านใน **16.406s**, observed peak
**785,035,264bytes** Import Torch, AutoTokenizer, Qwen2ForCausalLM,
GenerationConfig, tokenizers/safetensors/jinja2 สำเร็จ โดย **ไม่ instantiate
model/tokenizer**, CUDA initialized=false, kernels/weights/requests0

นี่แก้ข้อไม่ทราบเรื่อง **CPU class/DLL imports** จาก Phase H บางส่วน แต่ไม่
พิสูจน์ CUDA-driver/kernel/BF16 compatibility, peak VRAM, cached-load time หรือ
generationจริง ไม่ใช้ CPU-hidden CUDA visibility ไปอ้างว่า GPUใช้งานไม่ได้

| รายการ | ผลปัจจุบัน |
| --- | --- |
| Python/OS | senior, Python3.11.17, Windows |
| Torch / build CUDA |2.14.1+cu132 /13.2 จาก imported package metadata |
| Transformers / tokenizers |5.20.2 /0.23.3 |
| Hub / safetensors |1.33.0 /0.8.0 |
| NumPy / psutil / jinja2 |2.4.6 /7.2.2 /3.1.6 |
| Pinned package/static API checks |ผ่าน ไม่มี environment installation/update |
| pip check |exit0, No broken requirements found; [receipt](diagnostics/phase_i_preflight_20261107_v2/pip_check.json) |
| GPU metadata |RTX4060Ti, driver617.42; free6,400MiB ณ12:36UTC |
| Available RAM |37,538,820,096bytes ณreadiness snapshot |
| Workspace/proposed-download D: free |ประมาณ1,026,627,870,720bytes |
| Default cache C: free |199,102,238,720bytes |

Resource metadataผ่าน pre-load numeric gates ณเวลาตรวจ แต่ต้องวัดใหม่ก่อน
execution โดยเฉพาะ GPU freeที่เปลี่ยนได้ Probe memoryเป็น observed process
peakกับsampled stop guard ไม่ใช่ OS memory quota หรือ cumulative tree peak

## 4. Exact download plan — เสนอเท่านั้น ไม่ execute

[download_plan.json](diagnostics/phase_i_preflight_20261107_v2/download_plan.json)
มี source URLและทุก expected hash/sizeจาก frozen
[snapshot_lock_v1.json](traffic_runtime/snapshot_lock_v1.json) ไม่เลือกlatest/main

Base URL: `https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/resolve/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/`

| Required file | Expected bytes | Verification |
| --- | ---: | --- |
| LICENSE |11,343 |Git blob SHA1 |
| config.json |660 |Git blob SHA1 |
| generation_config.json |242 |Git blob SHA1 |
| merges.txt |1,671,839 |Git blob SHA1 |
| model.safetensors |3,087,467,144 |actual file SHA256 |
| tokenizer.json |7,031,645 |Git blob SHA1 |
| tokenizer_config.json |7,305 |Git blob SHA1 |
| vocab.json |2,776,833 |Git blob SHA1 |
| **รวม8ไฟล์** | **3,098,967,011** |ประมาณ3.10GB decimal |

Weight SHA256:
`dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`
Small-file Git blob IDsหมายถึง SHA1 ของ `blob <byte-length>\0<file-bytes>`
ไม่ใช่ plain file SHA1 ส่วน model Git blob IDเป็น LFS pointer identity ห้ามใช้
แทน SHA256 ของ3GB tensors

License evidence: [frozen upstream LICENSE](traffic_runtime/QWEN_LICENSE.txt)
เป็น Apache2.0, SHA256
`832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e`
พร้อม [source revision](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/LICENSE)
และ Phase H metadata provenanceที่ตรวจhashตรงแล้ว ไม่ถือmodel licenseเป็น
permissionใช้ participant/source-query data หรือ execution grant

เสนอปลายทางใน checkoutเดียวกัน:

```text
stream_prada_order/traffic_local/qwen_snapshots/<exact-revision>/
```

**ต้องมี acquisition authorizationแยกก่อน**: sequential8 logical file GETs,
retry0, <=3redirect hops/file (<=32HTTPtransactions), payload+metadata wire cap
**3,115,744,227bytes**, wall<=1,200s, storage<=8GiB, free disk>=9GiBก่อนเริ่ม
รองรับ conservative staging+final **6,197,934,022bytes** บวกmetadataภายในcap
Bandwidth/latencyจริงไม่วัด จึงไม่รับรองว่าจะจบภายใน20นาที

Approve source/redirect allowlistก่อน transfer; ไม่ follow hostที่ไม่ review
ไม่รัน downloaderใน Phase I และไม่ได้ตรวจ live URL/CDN availabilityผ่านnetwork
ใช้ frozen provenanceเท่านั้น ไม่มี download function/CLIใน checker
หากต่อเครือข่ายแล้วsource/ขนาด/hash/เวลา/budgetผิด ให้หยุดและเก็บpartial receipt
ไม่ retry/resumeโดย reset budgetหรือขยายgateอัตโนมัติ

เก็บ headers/partial/transfer receiptsนอก final snapshot; final directoryมีเฉพาะ
8ไฟล์ที่ผ่านhash ไม่วาง SDK .cache metadata/unreviewed codeให้ H audit reject
ไม่สร้าง triple full copiesจนเกิน8GiB และไม่ commit binaries/cacheเข้Git
จากนั้น offline rehashก่อนloadภายใต้8GiBอ่าน/120s gate ไม่มีweights instantiation

## 5. Reproduce offline checks

จาก repository root ใน senior **หลัง clean commit** ใช้ output directoryใหม่ที่ignored:

```powershell
conda run --no-capture-output -n senior python stream_prada_order/phase_i_check.py --output stream_prada_order/traffic_local/phase_i_recheck_new
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests -p "test_phase_i*.py" -v
```

Checkerมี --model-location <flat-snapshot-dir> และ --cache-root <hub-root> แบบ
explicitซ้ำได้ ไม่ค้นตำแหน่งอื่นเอง จำกัด16candidate paths, dedup actual paths,
shared inventory read budget8GiB/120s; H readiness, CPU import45s/1GiB และ
pip-check20sเป็นแยกstages ไม่อ้างว่าเวลารวมทุกstageไม่เกิน120s
ไม่มี infer/download/enable command และ refusalเมื่อcheckoutdirtyไม่ใช่bug

Sourceที่publishตรงกับ SHA ของ checkerที่executeบน clean8d32d46 ใน entry.json
[Unit tests ใหม่11รายการ](diagnostics/phase_i_unit_tests_20261107_v1.json) ผ่าน
fail/error/skip0 ตรวจ cache precedence, no unconfigured crawl, shared budgets,
plan/hash arithmetic, traversal/UNC refusal และdirty-checkout guard
ไม่ได้ rerun full174-test Phase H suiteใน Phase I; frozen runtime bytesตรงเดิม

## 6. Decision / next execution

**GO offline checks / CPU imports; NO-GO snapshot acquisitionจนอนุมัติแยก;
NO-GO real four-request pilotจนsnapshot+privacy+grant+query planครบ**
Exact operator records, pilot steps และ hard stopsอยู่ใน
[PHASE_I_BLOCKERS_TH.md](PHASE_I_BLOCKERS_TH.md)
Phase I ไม่สร้างgrant/claim/pilot store, ไม่โหลดweights/รันCUDA kernels/inference,
ไม่collectparticipants/ทำattacks/trainstudent ไม่มีdetector metricsจากmockหรือ4requests
ไม่มีpush/merge/rebase/main/PR และไม่เปลี่ยนscientific protocolเดิม
