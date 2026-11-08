# Phase J — การรับ Qwen Model Snapshot

วันที่ 8 พฤศจิกายน 2026 (Asia/Bangkok) | branch `experiment/stream-prada-order`

**GO สำหรับ acquisition: เสร็จสมบูรณ์และตรวจ integrity ผ่าน; NO-GO สำหรับ inference pilot จนกว่าจะได้รับอนุมัติแยก**

รับ `Qwen/Qwen2.5-1.5B-Instruct` revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` ครบเฉพาะ 8 ไฟล์
รวม **3,098,967,011 bytes** ไม่โหลดโมเดล/tokenizer ไม่สร้างคำตอบ ไม่เรียก victim API
ไม่มี extraction, student training หรือ participant traffic และไม่เปลี่ยน detector หรือหลักฐานเดิม

## ขอบเขตและ authorization

อ่าน Phase I readiness/blockers, Phase H readiness และ frozen Phase I download plan ก่อนดำเนินการ
ตรวจซ้ำหลังผู้ใช้อนุมัติ acquisition โดยตรงในวันที่ 8 พฤศจิกายน 2026
[บันทึกข้อความอนุมัติจริง](diagnostics/phase_j_acquisition_20261108_v1/operator_approval.json) ผูกกับ canonical plan SHA256
`fd3f1d8685a0ccfb6efc6912962016da53f5929047259d29ff4771b716a18e9f`
และ source SHA256 `52ba92344a96c9ac682173e99946029bda71cefed273cc6ca4c18d70e4642740`
บันทึกนี้ไม่ใช่ cryptographic operator signature และไม่ใช่ execution grant ของ Phase H

ตรวจ preflight และ postflight บน **clean HEAD `9d3467275e2d8f1a82a3d58454f306fdfa97662a`** ขณะไฟล์ Phase J
ยังอยู่ใน ignored storage ทั้งหมด main คงเดิม `5fb5e07d750a73a0a663a174433bab931ae7568a`
G/H manifests และ Phase I manifest ผ่าน; runtime code digest เดิม `d163635f0a490a016b7a1fc4a0ce378d464577cd91ec99fe8f08804f9cd6dc87`
หลังตรวจแล้วจึงเผยแพร่เฉพาะ code/tests/reports/receipts นี้ ไม่อ้างว่ารัน readiness บน commit ที่ยังไม่เกิด

## แหล่งที่มาและตำแหน่ง

configured HF cache variables ไม่ได้ตั้งค่า; ตรวจ effective cache
`C:/Users/varic/.cache/huggingface/hub` และ destination ที่ Phase I กำหนด ไม่พบ exact snapshot ก่อนรับ
ไม่มีการค้นทั้งดิสก์หรืออ่าน private logs และไม่ได้อ้างว่าเครื่องนี้ไม่มี snapshot ในตำแหน่งอื่น
[authorized preflight](diagnostics/phase_j_acquisition_20261108_v1/authorized_preflight.json)

แหล่ง official [revision files](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306)
และ [Apache-2.0 LICENSE](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/LICENSE)
ใช้ sizes/Git blob IDs/LFS SHA256 จาก frozen lock เดิม ไม่สร้าง expected hashes จากไฟล์ที่เพิ่งรับ
license SHA256 `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e`
public/ungated เป็น metadata ณ 7 พฤศจิกายน ไม่ใช่คำรับรองว่าข้อกำหนดจะไม่เปลี่ยน

ปลายทางจริง: `stream_prada_order/traffic_local/qwen_snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
เป็น ignored local storage เก็บ weights นอก Git; run receipts ต้นฉบับอยู่ใน ignored
`traffic_local/phase_j_acquisition_20261107_v1` ชื่อ directory ถูกตรึงจาก preparation วันที่ 7
แต่การรับจริงเกิดวันที่ 8 พฤศจิกายน ไม่มีการเขียนทับ cache/หลักฐานเดิม

## Resource gates และการใช้จริง

| รายการ | Gate | วัดได้จริง |
| --- | --- | --- |
| External wall clock | ≤1,200 s | 91.468 s; worker 89.266 s |
| Logical artifact GET / HTTP transactions | 8 / ≤32 | 8 / 16 |
| Retry | 0 | 0 |
| Artifact response body | 3,098,967,011 bytes | 3,098,967,011 bytes |
| HTTP accounted bytes | ≤3,115,744,227 | 3,098,989,685 |
| Serialized headers + status allowance | รวมใน HTTP cap | 22,674 bytes |
| Storage | ≤8 GiB | snapshot 3,098,967,011 bytes; worker final receipt 3,098,986,116 bytes |
| Free disk ก่อนเริ่ม | ≥9 GiB | 1,026,630,656,000 bytes |
| Free disk หลังตรวจ | ไม่ต่ำกว่า running reserve | 1,023,531,634,688 bytes |
| Worker RAM | Windows Job aggregate committed cap 512 MiB | sampled peak working set 33,259,520 bytes |
| Integrity offline audit | read ≤8 GiB, hash ≤120 s | 3,098,967,011 bytes; readiness รวม static checks 2.687 s |

ไม่มี gate failure, timeout หรือ hash mismatch. Parent watchdog แยกจาก worker และ attach Windows Job
ก่อน BOOT; per-block guards ตรวจ disk/storage/time/HTTP budget; default TLS validation และปิด proxy
redirect hosts ที่อนุญาต/พบจริงมีเพียง `huggingface.co`, `us.aws.cdn.hf.co`
staging แบบ append/new-only, fsync, stream hash ก่อน atomic directory publication บน Windows
ไม่ retry/resume และไม่เปิด network fetch ใน readiness

HTTP counter วัด body ที่อ่านกับ serialized response headers/status allowance เท่านั้น
ไม่ได้วัด TLS/TCP/link-layer/retransmission หรือ body ของ redirect ที่ปิดโดยไม่อ่าน จึงไม่อ้างว่าเป็น physical wire bytes
storage counter เป็นผลรวม file sizes ไม่ใช่ filesystem allocation quota และค่าใน result ถูกรวมก่อนเขียน receipt สุดท้าย
RAM peak เป็น working set ที่ supervisor เก็บ ไม่ใช่ค่าที่วัด peak committed memory; committed cap เป็น OS gate
[result](diagnostics/phase_j_acquisition_20261108_v1/result.json), [supervisor](diagnostics/phase_j_acquisition_20261108_v1/supervisor.json), [event trace](diagnostics/phase_j_acquisition_20261108_v1/events.jsonl)
ไม่มี signed URLs/credentials ใน public logs

ก่อนอนุมัติมี preparation แยก: official catalog metadata GET 1 ครั้ง 8,389 bytes และ HEAD 16 transactions
ใช้เวลา 5 s โดยไม่ได้อ่าน artifact bodies ไม่รวมเป็น acquisition transfer counters
[preparation metadata](diagnostics/phase_j_acquisition_20261108_v1/official_metadata.json), [HEAD receipt](diagnostics/phase_j_acquisition_20261108_v1/head_preflight.json)

## Offline readiness และสิ่งที่ยังต้องทำ

[clean-HEAD readiness](diagnostics/phase_j_acquisition_20261108_v1/post_acquisition_readiness.json): snapshot ทั้ง 8 ผ่าน,
static package/API checks ผ่าน, real_execution_enabled=false และ weights loaded/victim requests=0
status ยังคง **BLOCKED** ด้วย `explicit_private_storage_required` และ
`valid_explicit_approval_and_evidence_required` ซึ่งหมายถึงสิทธิ์ inference ไม่ใช่ acquisition ที่เพิ่งได้รับ
GPU/RAM เป็น OS metadata เท่านั้น ไม่ได้พิสูจน์ CUDA/BF16/kernel/load/generation compatibility

ก่อน pilot ต้องมี: (1) explicit benign-only runtime approval แยกพร้อม hash-bound one-shot grant
และ license/source/privacy evidence จริง (2) operator-owned legitimate queries 1–4 รายการจาก native session จริง
พร้อม order/hash/document/task provenance ไม่มี participant data (3) dedicated fresh ignored private store,
ACL/retention/backup/HMAC key review และ grant claim registry (4) clean branch HEAD และ frozen bindings
ที่ตรง grant; ใช้ snapshot นี้แบบ local-only พร้อมตรวจ integrity ใหม่ก่อนโหลด
(5) อนุมัติ tiny CUDA/BF16 probe และ cached load ภายใต้ Phase H 120 s / RAM 8 GiB /
GPU ก่อนโหลด ≥6 GiB / allocator ≤5.5 GiB / batch1 / input≤2048 output≤128 ต่อคำขอ / รวม≤4 dispatch / retry0
ต้องอ่าน Phase H/G gate ฉบับเต็ม ไม่ขยาย budget หรือลด settings อัตโนมัติเมื่อ failure

acquisition ไม่ทำให้ได้ independent traffic, horizon256 หรือ FPR/TPR/detection-delay evidence
ผล mock tests ไม่ใช่ model performance หรือ detector improvement
ไม่มี push/merge/rebase/PR/main modification และจะหยุดหลัง local commit
