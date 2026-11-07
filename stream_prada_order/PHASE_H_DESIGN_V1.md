# Phase H — frozen implementation design / offline gate v1

วันที่ 7 พฤศจิกายน 2026; base `3b2d291ca5c6dea7a86e2aa6ad944a13e5715dd0`
อ่าน Phase G implementation/test/next-pilot และ Phase F protocol ก่อนออกแบบ

งานนี้อนุญาตเฉพาะ implementation, metadata inspection และ mock tests:
real inference/model load/tokenizer load/download weights/victim APIs/attacks/
student training/participant traffic = 0 ไม่เปลี่ยน detector หรือ evidence เดิม

## Frozen choices before tests

- เพิ่ม package `traffic_runtime` แยกจาก Phase G ใช้ EventStore/schema/recovery
  เดิมโดยไม่เปลี่ยน source hashes เดิม; collector รุ่น H รับ supervised adapter
  ผ่าน interface เดิมและใช้ native run/session/request events เดิม
- Qwen model/tokenizer exact revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`;
  native Transformers, BF16, CUDA0, eager attention, batch1, greedy, beams1,
  no sampling, output<=128, no quantization/offload/remote/custom code
- Freeze upstream tokenizer chat template hash กับ explicit system message
  `You are Qwen, created by Alibaba Cloud. You are a helpful assistant.`
  Single-turn requests: system+current user only ไม่แอบเติม previous responses
  chronology/session identity ยังเป็นของจริง แต่ไม่อ้าง conversational memory
- Input usage = exact full rendered input IDs; output usage = generated suffix
  รวม special/EOS tokens ไม่ re-tokenize decoded text; เก็บ IDs/rendered prompt
  เป็น ignored private provenance artifacts แยกจาก latest-user query
- Fail closed โดยไม่มี explicit execution grant ที่ bind code/config/environment/
  snapshot/run/query-plan/privacy/source approvals และหมดอายุได้ ไม่มี enable CLI
  mock grant ไม่เปิด real backend และ schema validity ไม่เท่ากับ human consent
- External process supervisor: Windows Job Object kill-on-close/process-tree
  containment, independent wall-time watchdog, periodic resource checks และ
  preflight token/budget checks; non-Windows real runtime unsupportedในรุ่นนี้
- Native inference worker เริ่มหลัง containment+authorization เท่านั้น, local
  files only, offline environment/network guard; no silent retries after unknown
  delivery. Requests not admitted are not_sent; generate started+lost result unknown
- Readiness เป็น metadata/byte-hash/static API audit ไม่ import torch/transformers,
  ไม่ instantiate tokenizer/model และไม่พิสูจน์ CUDA/kernel/BF16 execution

## Bounded work in Phase H

Public configuration metadata เท่านั้น: <=4 GETs ไป exact Qwen revision,
<=1MiB/response, <=4MiB total, <=120s; ไม่ fetch vocab/tokenizer payload/weights
ใช้ Phase F pinned file manifest สำหรับ expected Git/LFS hashes เมื่อมีครบ

Local offline readiness: explicit Qwen cache snapshot/metadata เท่านั้น,
read budget<=8GiB, wall<=120s, process RAM review<=512MiB; no private traffic scan
Mock verification: full legacy+new testsใน CPU-only worker, <=120s/round,
worker RAM review<=2GiB; preserve failed/earlier receipts, ไม่เพิ่ม gateเงียบ ๆ

## Proposed later pilot (not authorized here)

หนึ่ง benign native session, <=4 requests/dispatch intentions, one attempt/request,
input<=2048/output<=128 tokens/request และ totals<=8192/512, whole run<=120s
รวม cached load/inference/logging. RAM available>=8GiB, worker tree cap8GiB,
driver-free VRAM>=6GiB, reserved cap5.5GiB, cache<=8GiB, logs logical<=4MiB/
physical<=20MiB, input/output<=64/16KiB. No attack/train/download/API/participant.

หาก cache/approval/static compatibility ไม่ครบ ให้รายงาน NO-GO ไม่โหลดโมเดล
หรือเปลี่ยน environment; mock tests ยังทำได้แต่ไม่ใช้ certify real runtime
Kernel/BF16/actual generation readiness ยังเป็น prerequisite ของ separate pilot
และต้องไม่อ้าง FPR/TPR/delay/generalization จาก4 requestsหรือmocks
