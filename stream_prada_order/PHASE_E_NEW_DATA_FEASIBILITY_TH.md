# Phase E — ความเป็นไปได้ของข้อมูลใหม่

ตรวจ primary source metadata/pages ณ 7 พฤศจิกายน 2026 ไม่มี corpus download,
การยอมรับข้อตกลงแทนผู้ใช้, victim API calls หรือ model training ในงานนี้
นี่เป็นแผน acquisition ไม่ใช่การรับรองข้อมูลที่ยังไม่ได้ audit

## ข้อกำหนดจากผล Phase E

ข้อมูลใหม่ต้องมี benign ที่ยาว/แนบ context และ attack ที่สั้น/question-only
รวมทั้ง benign ที่มีความซ้ำ/ระยะต่ำและ attack ที่หลากหลาย จึงจะไม่ผูก label
กับ length, format, source หรือ geometry เพียงอย่างเดียว ต้องเก็บ order/time
จริงและ grouping ของผู้ใช้/session/attack run; ไม่ต่อ independent conversations
สั้น ๆ ให้เป็น user session ยาว 256 โดยไม่มีหลักฐาน

Public dataset ที่เราไม่เคยอ่านอาจยังมี content ซ้ำกับ Phase A–E หรือ benchmark
ที่ใช้ใน extraction ได้ จึงใช้คำว่า **candidate fresh cohort** จน dedup/exposure
audit ผ่าน ไม่ใช้ dataset name หรือ advertised row counts เป็นหลักฐาน freshness

## ทางเลือกและสถานะ access/license/provenance

| แหล่ง | ใช้ทำอะไรได้ | Access และ license ที่ตรวจ | ข้อจำกัด / เงื่อนไขก่อนนับ cohorts |
| --- | --- | --- | --- |
| [WildChat-1M official card](https://huggingface.co/datasets/allenai/WildChat-1M) | real conversation candidates สำหรับ benign sensitivity | public card; ODC-BY; full toxic version ต้องขอ approval | ไม่มี guaranteed benign/extraction-intent labels; ต้องตรวจจริงว่ามี user requests พอใน natural horizon |
| [LMSYS-Chat-1M official card/agreement](https://huggingface.co/datasets/lmsys/lmsys-chat-1m) | real user conversations อีกแหล่ง | login และ accept agreement/share HF account information; custom license จำกัด transfer และต้องรักษา model-output terms | ยังไม่ accept/access files; ไม่เหมาะกับ raw-data redistribution; ไม่อ้าง unseen benchmarks เพราะ card ระบุไม่ decontaminate |
| [MEA-Bench official repository](https://github.com/sliu11-byte/MEA-Bench) และ [query artifact](https://huggingface.co/datasets/watermarkproject/lord-mea-benchmark) | attack-family candidates และ run/manifest schema | code/docs MIT; query pool public ตาม README; third-party terms แยก และยังไม่ยืนยัน blanket data license | ต้องหา exact source revision/run/budget/adaptive order/license; query pool ไม่ใช่ independent attack sessions โดยอัตโนมัติ |
| เก็บ benign sessions ใหม่บนระบบที่ทีมเป็นเจ้าของ | main route สำหรับ chronological benign ที่เหมาะกับ victim/task จริง | ต้องมีสิทธิ์ระบบ/consent/นโยบายเก็บและใช้ข้อมูลตามกระบวนการมหาวิทยาลัย; data license ยังต้องกำหนด | ยังไม่มี corpus/จำนวนผู้เข้าร่วมที่ยืนยัน; ห้ามใช้ private logs โดยไม่มีสิทธิ์; ไม่สร้าง fake benign sessions |
| รัน extractor ที่ได้รับอนุญาตกับ victim ที่ทีมควบคุม | main route สำหรับ actual attack traffic ที่มี intent/order/response provenance | ตรวจ exact attack-code/model/source-data/output terms ก่อน; ยังไม่กำหนด victim รุ่นและยังไม่มี execution authorization | ต้องแยก source corpus/attack family/run/operator/seed; ทำ extraction objective จริง ไม่ติดป้าย context prompts ว่า successful extraction |

WildChat มี conversation/turn identifiers, timestamps และ hashed IP metadata
ใช้ grouping แบบ pseudonymous ภายใน audit ตามสิทธิ์ ไม่พยายามระบุตัวบุคคล
conversation_hash ไม่ unique; duplicate/prefix copies และหลาย sessions ของคนเดิม
ต้องอยู่ split เดียวกัน หาก user grouping เชื่อถือไม่ได้ให้ downgrade เป็น
conversation-disjoint เท่านั้น ไม่อ้าง user independence
รายละเอียด fields/license/access มาจาก [official card](https://huggingface.co/datasets/allenai/WildChat-1M)

[ODC-BY](https://opendatacommons.org/licenses/by/1-0/) ครอบคลุม database rights
และ attribution โดยไม่ได้แก้สิทธิ์ content แต่ละชิ้นทั้งหมด ต้องคง notices/
attribution และตรวจสิทธิ์เผยแพร่ derived/raw text ตาม exact release ก่อน
อย่าถือว่า public access เท่ากับสิทธิ์เผยแพร่ข้อความทุกส่วน

LMSYS ระบุ average 2 turns ต่อ conversation จึงไม่ควรคาดว่า 1M conversations
จะให้ 1M streams ยาว 256 หรือให้ 256 independent requests ต่อ user ได้
ต้องเลือก natural shorter horizon ล่วงหน้า หรือจัด session windows ตาม
observed user/time ที่มีสิทธิ์ตรวจเท่านั้น คง non-identification และ transfer
restrictions ตาม [agreement](https://huggingface.co/datasets/lmsys/lmsys-chat-1m#lmsys-chat-1m-dataset-license-agreement)

MEA-Bench README รองรับ run metadata/manifests และหลาย attack families แต่
เป็นหลักฐานความสามารถของ repository ไม่ใช่การรับรองว่า rows ใน artifact
มี chronology/independent runs หรือ license ที่พร้อมใช้ทั้งหมด
Card preview พบ schema-cast/viewer error; ในรอบนี้ไม่ใช้ viewer failure เป็น
ข้อสรุปว่า raw files ไม่มีข้อมูล ต้อง audit manifest/schema ใน bounded step ใหม่
Code MIT ไม่ relicense datasets ตาม [license section](https://github.com/sliu11-byte/MEA-Bench#license)

## ขั้นจัดหาแบบมี gates (ข้อเสนอ ยังไม่รัน)

1. **Metadata-only intake:** freeze release/commit/license URLs, access mode,
   schema, file sizes และ upstream notices ก่อน data request เก็บ source register
   ไม่ต้องมี credentials ใน Git; หาก license/run provenance ไม่ครบให้ hold
2. **Separate bounded sample protocol:** ระบุ sources, sample rule, byte/row cap,
   query accounting และเวลา/RAM จริงก่อนอนุมัติ เช่นเสนอเพดาน 20 MB/200 records
   สำหรับ schema/access audit เท่านั้น ไม่เปิด full corpus และไม่วัด detector
   ตัวเลขนี้เป็น proposed cap ไม่ใช่ measured download cost หรือ permission
3. **Fresh owned traffic collection pilot:** บันทึก benign chronology จากผู้ใช้
   ที่มีสิทธิ์และ attack requests จาก extractor ต่อ victim ที่ได้รับอนุญาต
   กำหนด hard request/token/output/VRAM/runtime caps ใน protocol ใหม่ก่อนเรียก
   ยังประเมิน latency/VRAM/ค่าใช้จ่ายแบบตัวเลขไม่ได้จนเลือก victim/provider/
   attack implementation แล้ววัด dry-run/preflight; ห้ามใช้เวลา E 7 s เป็น proxy
4. **Cohort feasibility audit ก่อน score:** นับ source/user/run components และ
   common length/format support จริง หากไม่พอให้หยุด ไม่เพิ่ม pseudo-cohorts
5. **Freeze final-test access:** เก็บ final manifest/data แยกสิทธิ์ ก่อน fit/
   calibration/selection แล้วเปิดได้ครั้งเดียวตาม next protocol

ยังไม่นับ WildChat/LMSYS/MEA-Bench เป็น cohorts ที่ available จริงสำหรับ main
confirmatory study และไม่ใช้ public QA expansion แทน real benign sessions
ข้อมูลใหม่ที่มีแต่ benign ก็ไม่แก้ attack-family/run independence bottleneck

## Provenance schema ที่ต้องมี

แต่ละ source/release: URL/revision, downloaded bytes/hash/time, access/license
text/hash, attribution, upstream source corpus/model terms และ exposure ledger
แต่ละ session/run: pseudonymous actor/component ID, native session/run ID,
UTC timestamps/ordering/retries, victim/model/tokenizer revision, system/template
hash, request IDs, input/output tokens, attack algorithm/config/commit/budget,
response-dependent decisions, source-document IDs, content hashes และ role labels
ไม่เผย raw account identifiers/credentials หรือ raw private user text ลง Git

Benign ground truth ต้องระบุว่าเป็น observed legitimate use ตาม sampling frame
และ audit ความเสี่ยง label contamination; attack ground truth ต้องอ้าง run
ที่มี extraction objective ไม่ใช่ความยาวหรือชื่อชุดข้อมูล และแยก detection
of intent/traffic ออกจาก successful extraction ที่วัดด้วย student fidelity

## Leakage และ independence controls

- ใช้ connected components ครอบ user/actor, repeated sessions, source document/
  article, source corpus versions, exact/NFKC text, near duplicates และ template
  families ก่อน split; หนึ่ง actor/run/source ไม่ถูกแบ่งเป็นหลาย independent units
- เทียบ hash/near-duplicate/exposure กับ Phase A–E และ candidate query pools
  ทั้งหมดก่อน final-test lock ไม่ใช้ final scores เลือกส่วนที่ไม่ทับ
- แยก adaptive attack descendants/seed siblings/source documents อยู่ group
  เดียวกัน Seed ต่างกันไม่เพียงพอให้อ้าง independent attack evidence
- Public benign กับ controlled attacks ต้องใช้ rendering/victim/task/channel
  ที่เปรียบเทียบได้ ถ้าคนละ domain ให้รายงาน transfer strata แยก ไม่ pool FPR
- Threshold/length-bin/matching/horizon selection ใช้ fit/calibration/validation
  เท่านั้น บันทึกทุก rejected/failed run ไม่เปลี่ยน final set หลังเห็นผล

## คำตัดสิน feasibility

**ทำต่อได้ในรูป metadata/sample acquisition plan** แต่ **ยัง no-go สำหรับ
fresh confirmatory experiment**: license/query-run provenance และจำนวน natural
independent benign/attack cohorts ยังไม่ยืนยัน ต้องผ่าน gates แยกก่อน
ข้อเสนอหลักคือ owned/consented traffic ที่ balance format/length และมี actual
extraction runs; public conversation/pool data เป็น sensitivity candidates
ไม่มีการเลือก detector หรือเริ่มเก็บข้อมูลใหม่จากรายงานนี้
