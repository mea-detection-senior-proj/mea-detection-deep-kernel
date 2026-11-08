# Phase J — ผลตรวจ Snapshot Integrity

8 พฤศจิกายน 2026 | **ผ่านครบ 8/8 files** | exact revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`

| ไฟล์ | bytes | Frozen digest type | Expected = received | ผล |
| --- | --- | --- | --- | --- |
| LICENSE | 11,343 | Git blob SHA1 | `6634c8cc3133b3848ec74b9f275acaaa1ea618ab` | ผ่าน |
| config.json | 660 | Git blob SHA1 | `f81ead14ab072d65a07817f83a3ee0e5a1890d10` | ผ่าน |
| generation_config.json | 242 | Git blob SHA1 | `dfc11073787daf1b0f9c0f1499487ab5f4c93738` | ผ่าน |
| merges.txt | 1,671,839 | Git blob SHA1 | `20024bfe7c83998e9aeaf98a0cd6a2ce6306c2f0` | ผ่าน |
| model.safetensors | 3,087,467,144 | SHA256 | `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee` | ผ่าน |
| tokenizer.json | 7,031,645 | Git blob SHA1 | `443909a61d429dff23010e5bddd28ff530edda00` | ผ่าน |
| tokenizer_config.json | 7,305 | Git blob SHA1 | `07bfe0640cb5a0037f9322287fbfc682806cf672` | ผ่าน |
| vocab.json | 2,776,833 | Git blob SHA1 | `4783fe10ac3adce15ac8f358ef5462739852c569` | ผ่าน |

รวม 3,098,967,011 bytes. `model.safetensors` ใช้ LFS content SHA256
ไม่ใช้ Git blob ID ของ LFS pointer; 7 ไฟล์อื่นใช้ Git blob SHA1 ของ `blob <size>\0` + file bytes
ไม่ใช่ plain SHA1. Acquisition receipt เก็บ observed content SHA256 เพิ่มด้วย แต่สำหรับไฟล์เล็ก
authority ยังคงเป็น frozen Git blob IDs ไม่ได้เปลี่ยนไปใช้ self-generated hashes

1. ตรวจ official exact-revision metadata กับ Phase I plan และ frozen snapshot lock ก่อนรับ
2. ตรวจ received exact size และ streaming digest ทุกไฟล์ก่อน publication; ไม่แทนไฟล์หรือแก้ lock
3. รัน Phase H `readiness(snapshot=...)` แยกอ่านครบทุก byte อีกครั้งหลังรับ บน clean HEAD9d346727
   read 3,098,967,011 bytes ภายใน 8 GiB/120s hash gate; snapshot status=passed, codes=[]
4. ตรวจ exact file set ไม่มี extra code, partial หรือ symlink ใน final snapshot; final directory มี 8 files เท่านั้น
5. G/H/I manifest bytes เดิมผ่าน และ prior tracked files ไม่ถูกแก้; weights อยู่ใต้ ignored storage เท่านั้น

[Per-file acquisition evidence](diagnostics/phase_j_acquisition_20261108_v1/result.json),
[Independent offline rehash/readiness](diagnostics/phase_j_acquisition_20261108_v1/post_acquisition_readiness.json),
[Plan](diagnostics/phase_j_acquisition_20261108_v1/acquisition_plan.json), [approval](diagnostics/phase_j_acquisition_20261108_v1/operator_approval.json)

## Reproduction โดยไม่รันโมเดล

รันจาก repository root ใน Conda `senior` (คำสั่งนี้อ่านไฟล์ local เท่านั้น):

```powershell
conda run --no-capture-output -n senior python -m stream_prada_order.traffic_runtime readiness --snapshot stream_prada_order/traffic_local/qwen_snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306
conda run --no-capture-output -n senior python -m unittest stream_prada_order.tests.test_phase_j_acquire -v
```

readiness ยังออก BLOCKED/exit nonzero หากไม่มี inference grant/private store ตามที่ควรเป็น
ใช้ field `snapshot.status` ประเมิน integrity และไม่ bypass blocked status เพื่อ dispatch
การตรวจซ้ำบน checkout ที่ยังมี additions จะรายงาน dirty ตามจริง

Reproducible downloader: [phase_j_acquire.py](phase_j_acquire.py) byte-identical กับ approved worker
คำสั่งที่ใช้จริง (approval record อยู่ ignored storage):

```powershell
conda run --no-capture-output -n senior python stream_prada_order/phase_j_acquire.py --plan stream_prada_order/traffic_local/phase_j_preparation_20261107_v1/acquisition_plan.json --approval stream_prada_order/traffic_local/phase_j_preparation_20261107_v1/operator_approval.json --approval-sha256 6a306cf12a6cb3f1c482c2e4189652842d4f1ca1bede0220aaa7c4d0e314eb43
```

คำสั่งจริงใช้ ignored source `traffic_local/phase_j_acquire_source.py` ที่มี bytes/hash เดียวกัน
plan ผูก HEAD9d346727 และ new-only paths ปัจจุบันจึง **ห้าม replay**: final/run paths มีอยู่แล้วและหลัง commit HEAD เปลี่ยน
หากต้องรับใหม่ต้องมี reviewed plan/authorization ใหม่ ห้ามลบ receipts/reset paths เพื่อหลบ gate
ไม่มี automatic approval creation ใน downloader

Mock transport tests 17 ผ่านก่อน acquisition; public tests ตรวจ authorization, exact sizes/hashes,
truncation/oversize/encoding, host/redirect/credential controls, privacy of URL query,
disk/time/HTTP guards, no retries และ no overwrite ใช้ numeric bytes กับ fake HTTP เท่านั้น
ดู public-source result ใน [transport_tests_public.json](diagnostics/phase_j_acquisition_20261108_v1/transport_tests_public.json)
ไม่อ้างว่าทดสอบ native Qwen execution หรือ OS-wide network/memory quota อย่างสมบูรณ์

**Readiness สุดท้าย:** snapshot acquisition/integrity GO; real inference NO-GO
ยังไม่โหลด weights/tokenizer หรือทดสอบ native model; ต้องผ่าน prerequisites ใน
[acquisition report](PHASE_J_ACQUISITION_TH.md) และ Phase H ก่อน pilot ที่ได้รับอนุมัติแยก
