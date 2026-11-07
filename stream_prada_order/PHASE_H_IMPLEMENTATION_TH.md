# Phase H — Local Qwen Inference Readiness Implementation

วันที่ 7 พฤศจิกายน 2026 | branch `experiment/stream-prada-order`
Base: `3b2d291ca5c6dea7a86e2aa6ad944a13e5715dd0`

**Implement runtime bridge และตรวจด้วย mocks แล้ว; ยังไม่รับรอง inference จริง**
ผล regression รอบสุดท้ายผ่าน **174 tests** รวม Phase H ใหม่44 และ Phase A–G
เดิม130 รายการ ไม่มี failures/errors/skips ใช้เวลา worker24.035วินาที
ไม่มีการโหลด weights/tokenizer จริง, victim/API requests, extraction, student
training หรือ participant collection ใน Phase H

อ่าน Phase G implementation/test/next-pilot และ Phase F protocol ฉบับเต็มก่อน
ออกแบบ [PHASE_H_DESIGN_V1.md](PHASE_H_DESIGN_V1.md) กำหนด choices และ resource
gate ก่อนทดสอบ ไม่ใช้ detector outcomes เพื่อเลือก settings

## 1. แยก implementation และคง evidence เดิม

Package ใหม่ [traffic_runtime/](traffic_runtime/README.md) ใช้ Phase G EventStore,
event/manifest schema v1, private blobs, views และ recovery เดิมโดยไม่แก้ source
เดิม `RuntimeCollector` เป็น sibling ที่สืบทอด session/close behavior และเพิ่ม
admission/collection path ของ H; ไม่ monkeypatch mock gate หรือปลอม `is_mock`
ให้ real adapter ผ่าน ส่วน GCollector/Qwen descriptor เดิมยัง mock-only/disabled

ทุกไฟล์ของ Phase H เป็น additions ไม่มีการแก้ detector, PRADA/CUSUM/MMD,
threshold, config หรือผลทดลอง Phase A–G ตรวจ frozen Phase G manifest และ
tracked bytes ก่อน/หลัง tests ตรงกัน รวมถึง main reference เดิม

| Module | หน้าที่ |
| --- | --- |
| `policy.py` | pinned bindings, benign plan, expiring grant, clean-checkout validation, one-shot grant registry |
| `backend.py` | lazy native Transformers load/probe/prepare/generate; exact token IDs/usage |
| `adapter.py` | disabled-default public adapter, admission และ private receipts |
| `collector.py` | bounded request/attempt logging บน G schema, no retry และ fail-stop |
| `supervisor.py`, `winjob.py`, `worker.py` | contained process, external wall watchdog, resource sampler และ bounded JSON IPC |
| `storage.py`, `audit.py` | physical/logical headroom, immutable receipts, receipt↔collector validation |
| `readiness.py`, `__main__.py` | offline hashes/environment/resources/approval inspection; ไม่มี inference CLI |
| `profile_v1.json`, snapshot/environment locks | settings และ exact file/package identities ที่ freeze |

## 2. Authorization และ provenance

Real path ต้องมี `execution_authorized=True` **พร้อม** valid grant/evidence;
default False, flag อย่างเดียวไม่พอ และ mock grant ใช้เปิด real path ไม่ได้
ตรวจ branch, clean tracked/untracked Git state และ manifest collector revision
ต้องตรง HEAD ที่อนุมัติ ไม่อ่าน environment flag เป็นการอนุญาต execute

Grant `qwen-execution-grant-v1` bind runtime+G code digest, profile, snapshot lock,
environment lock, exact run manifest และ ordered query plan หมดอายุได้และมีอายุ
ไม่เกิน24ชั่วโมง ตรวจไฟล์ approval กับ SHA256 ที่ operator ส่งแยก และอ่านเฉพาะ
evidence hashes ที่ระบุ explicit สำหรับ operator/model/source/privacy
หลักฐาน authorization ต้องตรง reference ใน run manifest

Claim ถูกสร้างแบบ exclusive ใน ignored `traffic_local/execution_grants/`;
หนึ่ง grant เปิดได้หนึ่ง pilot และหนึ่ง worker เท่านั้น แม้ boot ล้มเหลวก็ไม่
ลบ claim ไม่ reset budget ด้วยการย้าย store/copy approval ไปอีก folder ใน checkout
การ copy ทั้ง checkout/registry หรือ malicious administrator ยังอยู่นอก security
guarantee ต้องควบคุม ACL/operator records แยก ไม่อ้าง hashes ว่าเป็น consent/signature

Real grants ถูกตรวจซ้ำก่อน boot และก่อนทุก request; code/config เปลี่ยนหลัง
อนุมัติจะทำให้ bindings ไม่ตรง Immutable claim ใช้เก็บ failed attempt ไม่ใช่
เพิ่มสิทธิ์หรือการอนุมัติเริ่ม pilot ในงานนี้

## 3. Frozen inference profile และ exact usage

Model/tokenizer: `Qwen/Qwen2.5-1.5B-Instruct` revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306` ทั้งคู่ Snapshot lock อ้าง8 required
files จาก Phase F pinned metadata: small-file Git blob IDs และ weight SHA256
ไม่ self-certify ด้วยการ hash local files แล้วถือเป็น expected values

Chat template SHA256:
`cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`
มาจาก [exact upstream tokenizer config](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/tokenizer_config.json)
System message freeze ใน profile ใช้ system+current user ต่อ request แบบ
**single-turn** ไม่เติม previous replies เป็น hidden context และไม่อ้างว่าเป็น
stateful conversation แม้ requests มาจาก native session เดียวกัน

BF16, CUDA0, eager attention, batch1, greedy/no sampling, beams1, max_new128,
no quantization/offload, local_files_only และ trust_remote_code=False
GenerationConfig/decoding flags freeze ก่อน tests ไม่ใช้ upstream sampling
defaults ที่เป็น do_sample=True/repetition_penalty1.1 ในไฟล์ต้นทาง แล้วอ้าง
generation parity โดยไม่มีการรันจริง Original detector/upstream code ไม่เปลี่ยน

Input usage = จำนวน IDs ของ **full rendered prompt** ซึ่งรวม system/chat
control tokens ไม่ใช่ word count ของ latest query; tokenize โดยไม่เพิ่ม special
tokens ซ้ำ, ไม่ padding/truncate และ reject input>2048 ก่อน generate
Output usage = generated suffix IDs รวม EOS/special tokens ตรวจ prefixตรง input
ไม่ re-tokenize decoded response ซึ่งอาจลบ EOS หรือเป็น empty text

ก่อนอนุญาต generate ต้อง persist prepared receipt ที่มี rendered prompt,
input IDs/count/template hash แล้ว ผลลัพธ์มี output IDs/count/response hash
และ peak reserved ที่ backend รายงานทั้งหมดอยู่ ignored local storage
G success events เก็บ usage/origin `adapter_reported` หรือ `mock_reported` ตามจริง
G v1 failed events ยังมี usage=null; H receipt เก็บ known input count ได้แต่
unknown/failed generated usage ไม่ถูกเดาเป็น0 ไม่มีการเปลี่ยน G schemaย้อนหลัง

## 4. Supervisor, failure semantics และ recovery

Worker ไม่ import/load model ก่อนรับ boot หลัง Windows Job Object attachment
ใช้ independent deadline thread กับ resource sampler แยกกัน ถ้า sampler ติดรอ
nvidia-smi ก็ไม่เลื่อน wall deadline; timeout terminate job/worker ภายนอก Python
inference call ไม่พึ่ง cooperative stopping criteria หรือ thread cancellation
Windows Job Object ใช้ kill-on-close และ aggregate committed-memory cap8GiB
ตาม [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
และ [job memory limit](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)

Native load path มี tiny CUDA/BF16 probe ก่อน weights ภายใน separately authorized
worker แต่ **ไม่ได้เรียกใน Phase H** Probe/import/load/generate จริงจึงยัง unverified
ตั้ง PyTorch caching-allocator fractionให้ไม่เกิน5.5GiB และตรวจ max reserved
พร้อม global free-GPU/RAM/disk monitor ไม่ใช่ cap ของ driver/display allocations
ทั้งหมด [PyTorch allocator limit](https://docs.pytorch.org/docs/2.15/generated/torch.cuda.memory.set_per_process_memory_fraction.html)
อธิบายขอบเขตนี้; ตรวจ installed torch2.14.1 source ด้วย ไม่เปลี่ยนเป็น2.15

| สถานการณ์ | Delivery / การทำงาน |
| --- | --- |
| boot/prepare/token budget ล้มเหลวก่อน generate admission | not_sent; stop ไม่ retry |
| generate รับงานแล้วและส่ง known failure | accepted; sanitized stage/OOM/resource code |
| dispatch generate แล้ว timeout/crash/transport ขาด | unknown; output usage=null; stop |
| collector request intent ยังไม่ dispatch | G recovery failed; ไม่สร้าง victim exposure |
| H outcome durable แต่ G success ยังไม่ commit | G recovery unknown; ไม่ promote/resend จากการเดา |
| G durable success แต่ request finalization ไม่ครบ | G recovery finalize success โดยไม่ call ซ้ำ |

Real pilot มี one attempt/request จึง **ไม่ retry แม้ not_sent**; legacy G retry
เฉพาะ not_sent ยังทดสอบอยู่ ไม่แก้ baseline behavior Resource/unknown/failure
หยุดทั้ง pilot และรักษาเก่าไว้; ถ้าต้องลองใหม่ต้องมี grant/run lineageใหม่

Disk guard รวม file sizes ของ SQLite/journal/blobs/receipts ใช้ headroom ก่อนเขียน
และ sampled monitor ไม่ใช่ OS filesystem quota หรือ sector-allocation measurement
อาจ overshoot ระหว่าง samples/จาก unrelated writers จึงต้องเป็น dedicated store
Git ignore/hashes ไม่แทน ACL/encryption/retention และไม่ต้าน admin ที่แก้หลักฐาน

## 5. ผลทดสอบที่ยืนยันและขอบเขต

หลักฐาน final:
[verification](diagnostics/phase_h_verification_20261107_v3/verification.json),
[test IDs/results](diagnostics/phase_h_verification_20261107_v3/test_results.json),
[preflight/source hashes](diagnostics/phase_h_verification_20261107_v3/preflight.json),
[artifact hashes](diagnostics/phase_h_verification_20261107_v3/artifact_hashes.json)

| Tests ใหม่ | จำนวน | พฤติกรรม |
| --- | ---: | --- |
| Backend | 7 | disabled/default grant gate, exact full-input/EOS usage, frozen generation, no hidden history, token cap/prefix/padding rejection |
| Integration | 10 |4 requests ตาม native order, SQLite/receipts, query plan, one session, unknown stop, no retry, immutable/corrupt receipt, crash/recover, storage caps |
| Policy | 8 | benign-only/frozen plan, bounded budget, expiring grant, evidence/hash binding, mock≠real, one-shot grant accounting |
| Readiness/CLI | 8 | missing/wrong snapshot, Git/LFS hashes, read cap, extra code rejection, resource gates, disabled CLI, sanitized errors |
| Supervisor | 11 | disabled real spawn, prepare-before-generate, external timeout, known failure/crashes, logging failure, resource abort, parent-process death, sanitized boot OOM, failed job attachment cleanup |
| รวมใหม่ / regression เดิม | **44 /130** | **174 ผ่าน, fail/error/skip0** |

Worker elapsed24.035449400020298s; peak working set646,410,240bytes รวม legacy
Torch numeric CPU tests ไม่ใช่ cumulative process-tree peak/VRAM benchmark
Gate120s และ worker-memory review2GiB ไม่ถูกเพิ่ม Native load entry counter=0;
CUDA visibilityปิด, network connect guard และ real-worker prohibition ใน children
ใช้ numeric mocks/fake tokenizer/tensors/model เท่านั้นสำหรับ inference tests

ทดสอบจริงว่า supervisor parent subprocess `os._exit(73)` ทำให้ mock workerตาย
ผ่าน Job Object และ crash-after-runtime-result ไม่ resend เมื่อ recovery
ไม่ใช่ power-loss/hardware-failure certification หรือ measured Qwen compatibility

รอบ v1 ผ่าน172 testsก่อนเพิ่ม boot-OOM classification test และแก้ stage code
รอบ v2 ผ่าน173 โดยคง v1 ไว้ รอบ v3 เพิ่ม regression ที่พบว่า empty job ไม่สามารถ
kill worker ที่ assignไม่สำเร็จได้ จึงเพิ่ม direct-kill fallbackและตรวจcleanup
กรณีนี้ fail ก่อนแก้และผ่านหลังแก้; final174ผ่าน ไม่มี detector FPR/TPR/novelty/
generalization claims

## 6. Offline readiness และคำตัดสิน

Readiness ตรวจ snapshot hashes, package metadata, AST API symbols, resource
metadata, approvals และ branch state โดยไม่ import model runtime/โหลด weights
ไม่มี infer/enable/download CLI คำสั่งและขอบเขตใน package README
ผลจริงยัง **BLOCKED / NO-GO real pilot**; exact snapshot/approval/storageยังไม่ครบ
และ native imports/kernel/load/generation compatibility ยัง unverified
รายละเอียดกับ exact first-pilot gate ใน [PHASE_H_READINESS_TH.md](PHASE_H_READINESS_TH.md)

Bounded script ขอ Qwen public configuration/license metadataสำเร็จ3 GETs รวม18,890bytes ภายใต้
gate4 GETs/1MiBต่อresponse/4MiBรวม ไม่ดาวน์โหลด vocab/tokenizer payload/weights
ตัวเลขนี้เป็น scripted metadata payloads ไม่ใช่ packet-level total ของ browser/
documentation tools หรือทุก processบนเครื่อง
config blobsตรง Phase F identities; upstream licenseอยู่ใน QWEN_LICENSE.txt
ไฟล์ทั้งหมดและ receiptsถูก hash ใน [PHASE_H_MANIFEST.json](PHASE_H_MANIFEST.json)
ไม่มีการ push/main/integration PR หรือข้ามไป real inference จากรายงานนี้
