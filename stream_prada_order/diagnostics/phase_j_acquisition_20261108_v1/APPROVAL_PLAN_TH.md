# Phase J — แผนพร้อมขออนุมัติ (ยังไม่ download)

Repository `taetaevrh/Deep-Kernel`, branch `experiment/stream-prada-order`
clean entry HEAD `9d3467275e2d8f1a82a3d58454f306fdfa97662a`; mainไม่เปลี่ยน

ตรวจ configured cacheและ proposed destinationแล้วไม่พบ exact snapshot
Official Hugging Face metadataของ exact revisionยืนยัน sizes/Git/LFS identities
ตรง frozen lockทั้ง8ไฟล์; private=false, gated=false, license=apache-2.0
HEAD-onlyตรวจ16transactions ใช้5วินาที ไม่อ่าน artifact bodies

## ขอบเขตที่จะขออนุมัติ

- `Qwen/Qwen2.5-1.5B-Instruct` revision
  `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` เท่านั้น
- รับ8allowlisted files ตาม Phase I: LICENSE/config/generation_config/merges/
  model.safetensors/tokenizer.json/tokenizer_config/vocab รวม **3,098,967,011bytes**
- Official sources/redirect hostsเฉพาะ **huggingface.co** และ **us.aws.cdn.hf.co**
  HTTPS certificate validation, ไม่มี credentials/mirror/automatic retry
- ปลายทางใต้ repo เดียวกัน:
  `D:\MU\Y3S3-Y4S1\Senior Project\Deep-Kernel\stream_prada_order\traffic_local\qwen_snapshots\989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
  ทั้งweights/staging/approval/receiptsอยู่ignored local storage ไม่มี model filesในGit

## Recorded resource limits

| รายการ | Hard gate |
| --- | --- |
| File GETs / retries |<=8logical GETs, retry0 |
| HTTP transactions / redirects |<=32transactions, <=3redirects/file |
| Deadline |<=1,200s รวมcontainedworker/transfer/integrity/publish; timeoutหยุด ไม่เพิ่มgate |
| HTTP-accounted received bytes |<=3,115,744,227bytes (body+serializedresponseheaders/status allowance) |
| Controlled storage |<=8GiB; free disk>=9GiBก่อนเริ่ม, >=1GiB+writeheadroomระหว่างrun |
| Worker RAM |<=512MiB, Windows Job Objectและexternal supervisor |
| Verification |streaming exactsizes/SHA256หรือGitblobSHA1ก่อนpublish; offline H auditซ้ำหลังรับครบ |

ข้อชี้แจง measurement: Byte ceilingคงตัวเลขใน Phase I และ enforceกับ HTTP
application-body/header accounting ที่implementationวัดได้ **ไม่ใช่** total NIC/
TLS/TCP/link-layer/retransmission bytes; ตัวหลังไม่ได้instrumentและจะไม่รายงาน
ว่าเป็นค่าที่วัดแล้ว ไม่มีการรับรองnetworkwallbytesจริงว่าเท่ากับpayload

Hash/size/host/HTTPstatus/disk/RAM/deadlineผิดจะหยุด พร้อมเก็บpartialและreceipt
ห้ามoverwrite snapshotเดิม/resume/retryโดยresetbudget Source codeถูกfreezeใน
acquisition_plan.json และผ่าน numeric mocked HTTP tests17รายการ

## สิ่งที่ไม่ได้รับอนุญาตจากการอนุมัตินี้

ไม่load weights/tokenizerสำหรับinference ไม่generate ไม่เรียกvictim API
ไม่รันGPU kernels/extraction/student training/participant collection
ไม่push/merge/rebase/แก้main สิทธิ์four-requestpilotยังต้องแยกภายหลัง

Operator approvalต้องเป็นคำตอบจริงต่อแผนนี้ ไม่ใช้taskเดิม/fixture/threshold
หรือSHAที่ไม่มีคำอนุมัติมาแทน ถ้ายังไม่มีคำตอบชัดเจน acquisitionจะไม่เริ่ม
