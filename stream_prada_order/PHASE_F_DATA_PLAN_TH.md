# Phase F — New Traffic Dataset Preparation: แผนข้อมูล

วันที่ 7 พฤศจิกายน 2026 | branch `experiment/stream-prada-order`
ฐานก่อนงาน: `9394f6e440c74122f9bb3bbe921830733e38b51d`

อ่าน PHASE_E_REPORT_TH.md, PHASE_E_NEW_DATA_FEASIBILITY_TH.md และ
PHASE_E_NEXT_PROTOCOL_TH.md ก่อนเริ่ม **งานนี้เตรียมแผนและตรวจ metadata เท่านั้น**
ไม่ได้สร้าง dataset ที่พร้อมทดลอง ไม่อ่าน private logs ไม่อ่าน corpus rows/
query-pool payload ไม่รัน extraction/training และไม่ optimize detector จากข้อมูลเดิม

**คำตัดสิน: GO สำหรับ public metadata/schema assessment; NO-GO สำหรับเริ่ม
รับ data payload/เก็บ traffic หรือทดลองเปรียบเทียบ จน prerequisites ท้ายเอกสารครบ**
แผน [PROTOCOL](PHASE_F_PROTOCOL_TH.md) และ [FEASIBILITY](PHASE_F_FEASIBILITY_TH.md)
แยก research quotas ออกจาก budget metadata และ authorization ของงานถัดไป

## 1. หลักฐานและ revision ที่ตรวจจริง

ตรวจ public APIs/cards และ GitHub ผ่าน read-only connector; metadata HF
สาม responses ที่เก็บหลักฐานรวม **18,592 bytes** ไม่ใช่ dataset download
ตัวเลขจำนวน rows/ขนาดจากผู้เผยแพร่เป็น declared metadata ไม่ใช่จำนวน independent
cohorts ที่เราได้ตรวจรับแล้ว หลักฐานอยู่ใน
[public_metadata.json](diagnostics/phase_f_preparation/public_metadata.json),
[pinned_document_provenance.json](diagnostics/phase_f_preparation/pinned_document_provenance.json)
และ [GitHub source register](diagnostics/phase_f_preparation/github_source_register.json)

| Candidate | Exact revision ที่ pin | สิ่งที่ยังไม่มี |
| --- | --- | --- |
| WildChat-1M | `7d6490e462285cf85d91eabea0f9a954fbddcd1f` | จำนวน eligible natural sessions/users/common-support cohorts |
| MEA-Bench code | `947c5d7988a5ffd4cc425dfbae3532fd2c160a5b` | verified run artifacts และ native request chronology |
| MEA query dataset | `5c6ca3a6992fabab30d54b1f08e7445ea2826701` | query-data license, full schema, run/source independence |
| Authorized local traffic | **ยังไม่มี traffic artifact/revision/run ID: null** | authorization, collector commit, source documents, actual runs |
| Small local victim candidate (ไม่ใช่ traffic dataset) | Qwen2.5-1.5B-Instruct `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` | runtime/load test และการอนุมัติใช้ใน acquisition protocol |

Exact code/model revisions ไม่ใช่ revision ของ traffic ที่ยังไม่ได้เกิด
ต้องเก็บ source-data revisions และ run IDs เพิ่มก่อนนับ locally acquired cohorts

## 2. WildChat-1M: real conversations แต่ไม่ใช่ certified benign sessions

แหล่ง: [pinned dataset tree](https://huggingface.co/datasets/allenai/WildChat-1M/tree/7d6490e462285cf85d91eabea0f9a954fbddcd1f)
และ [pinned card](https://huggingface.co/datasets/allenai/WildChat-1M/blob/7d6490e462285cf85d91eabea0f9a954fbddcd1f/README.md)

- API ระบุ public, not gated; card ประกาศ train **837,989 rows**, Parquet14 shards
  รวม **3,360,836,020 bytes** สำหรับ data files ไม่ได้ดาวน์โหลด shards
- License ของ revision: [ODC-BY notice](https://huggingface.co/datasets/allenai/WildChat-1M/blob/7d6490e462285cf85d91eabea0f9a954fbddcd1f/LICENSE.md)
  ตรวจเนื้อหา public license แล้ว ไม่ใช้ code license มาแทน data license
- Declared schema: conversation_hash, model, timestamp, conversation, turn,
  language, moderation/toxic/redacted, hashed_ip, header และ region fields
  turn มี role/content/timestamp/turn_identifier และ pseudonymous metadata
  **ตรวจ declared schema แล้ว แต่ยังไม่ได้ validate actual rows**
- ลำดับภายใน conversation เป็น candidate chronology; ต้องลบ repeated prefix
  snapshots ด้วย turn identifiers/content hashes และตรวจ ordering ก่อนนับ requests
  last-conversation timestamp หรือ assistant-response timestamp ไม่ใช่หลักฐาน
  user-request arrival time ทุกจุด; latency อาจยังวัดไม่ได้
- conversation_hash ไม่ unique และ hashed IP ไม่ใช่ verified person: NAT/proxy/
  missing IDs ทำให้ under/over-group ได้ หาก certify user grouping ไม่ได้
  รายงานได้เพียง conversation-disjoint sensitivity ห้ามเรียก user-independent
- Toxicity/PII filtering ไม่ใช่ benign-intent label; benign truth ยัง **unverified**
  ต้องมี label audit โดยไม่ใช้ length/format เป็นเกณฑ์กำหนด benign

ใช้เป็น **secondary public-traffic sensitivity source** ก่อน ไม่ผสมกับ owned
attack traffic แล้วอ้าง common population FPR ต้องตรวจ domain/victim/rendering
และ native length ≥102/256 requests จริง ไม่ต่อ unrelated conversations ให้ยาวพอ
ODC-BY มีขอบเขต database attribution; สิทธิ์ content/ข้อจำกัดอื่นต้องตรวจแยก
ตาม [license text](https://opendatacommons.org/licenses/by/1-0/) ก่อนเผยแพร่ข้อมูล

## 3. MEA-Bench: แยก code, query pool และ executed attack run

แหล่ง: [pinned README](https://github.com/sliu11-byte/MEA-Bench/blob/947c5d7988a5ffd4cc425dfbae3532fd2c160a5b/README.md),
[registry](https://github.com/sliu11-byte/MEA-Bench/blob/947c5d7988a5ffd4cc425dfbae3532fd2c160a5b/benchmark/registry.py)
และ [manifest utility](https://github.com/sliu11-byte/MEA-Bench/blob/947c5d7988a5ffd4cc425dfbae3532fd2c160a5b/benchmark/manifests.py)

Code/docs ใช้ [MIT](https://github.com/sliu11-byte/MEA-Bench/blob/947c5d7988a5ffd4cc425dfbae3532fd2c160a5b/LICENSE)
แต่คง third-party dataset/model terms แยกกัน Registry แสดง:

| Acquisition role | Methods ที่พบ | Consequence ต่อ independent traffic |
| --- | --- | --- |
| ใช้ shared offline teacher transcript | SeqKD, LoRD, SODA, GAD | training methods ต่างกันอาจเห็น query traffic เดียวกัน นับเป็น independent acquisition families หลายชุดไม่ได้ |
| method-specific acquisition | QEDKS, Model Leeching | เป็น candidates ของ traffic diversity แต่ยังต้องตรวจ actual run/source/selection dependencies |

Run ID ที่มี timestamp ไม่ได้ยืนยัน per-request chronology หรือ independence
generic manifest utility มี schema identifier `mea_experiment_manifest_v1`
แต่ version check ไม่ใช่ full field/content validation ต้องตรวจ artifacts จริง

ที่ [pinned HF dataset](https://huggingface.co/datasets/watermarkproject/lord-mea-benchmark/tree/5c6ca3a6992fabab30d54b1f08e7445ea2826701)
API แสดง10 files รวม **325,826,217 bytes**, ไม่พบ README/LICENSE และ cardData=null
มี query_pool_100/1000/10000/50000/100000, query/LoRD/logprob artifacts
แต่ **ชื่อไฟล์ไม่พิสูจน์ schema, native order หรือ successful extraction**
ไม่ดาวน์โหลดแม้ query_pool_100.json ขนาด48,782 bytes เพราะ data terms ยังไม่ชัด

Viewer เคยเผย schema-cast error จึงไม่ใช้ preview เป็น schema ที่รับรองแล้ว
Fields เช่น query_id/run_id/method/victim/request/source_row หากพบในภายหลัง
ต้องตรวจ non-null meaning, keys, sequence และ request-response links จริง
`paper_faithful` flag เพียงอย่างเดียวไม่พิสูจน์ intent/fidelity หรือครบ extraction
Code revision กับ data revision เป็นคนละ release ห้ามอนุมานว่าเข้าคู่กันอัตโนมัติ

**สถานะ: GO อ่าน public code/schema metadata; NO-GO ใช้ query payload เป็น
main attack dataset** จน license และ run provenance ผ่าน ไม่มี verified independent
attack cohorts ที่นับเพิ่มจากการอ่าน README ในรอบนี้

## 4. Authorized local traffic: แหล่งหลักที่ควบคุม confounding ได้

เสนอ owned/consented benign sessions กับ extractor ที่ได้รับอนุญาต บน victim,
task domain และ request rendering เดียวกัน เป็น main comparison track
ต่างจาก public conversations ที่ยังมี deployment/model-domain shift
ยังไม่มี local traffic artifact ใหม่ จึงไม่มี revision หรือจำนวน cohorts ให้รับรอง

Candidate victim ขนาดเล็ก: [pinned Qwen card/license](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306)
API/license ระบุ Apache-2.0 และ not gated เป็น **feasibility candidate เท่านั้น**
ไม่ได้ดาวน์โหลด/โหลด/ยิง query และไม่เท่ากับ paper-profile victim ของ MEA-Bench
ยังไม่เลือก student/source corpus หรือรับรอง output-data rights ทุกส่วน

ก่อน collect ต้อง freeze exact collector/attack commit+dirty state, model/
tokenizer/system-template hash, authorized source documents, participant/run IDs,
operator, request ordering/dependencies, retries, actual token/query counters และ
UTC request/response times เก็บ credentials/identifiers นอก Git ไม่อ่าน private logs

Intent verify จาก authorized extraction plan + executed acquisition trace และ
การเชื่อม requests กับ algorithm decisions ไม่ติด label ตามความยาวหรือ context
แยก **intent-confirmed acquisition traffic** ออกจาก **successful extraction**:
ถ้ายังไม่มี student training/fidelity evaluation ให้ success=null ไม่แต่งผลแทน
หาก method ต้องมี trained student/feedback/warmup ห้ามตัดขั้นนั้นแล้วเรียก faithful
ตอนนี้ไม่มี authorization สำหรับ execution/training ตามขอบเขต Phase F

Repeated seeds, budgets, operator หรือ source pool เดียวกันไม่เพิ่ม outer n
เมื่อ union actor/source/run lineage แล้วเหลือหนึ่ง component ต้องนับหนึ่ง
ไม่สร้าง account/session ID ใหม่เพื่อเพิ่ม independence จำนวน samples ที่เก็บได้
ต้องผ่าน audit นี้ก่อนเทียบกับ quotas ใน protocol

## 5. Matched traffic acquisition conditions

| Condition ที่ต้องมีจริง | Benign counterpart | Attack counterpart |
| --- | --- | --- |
| สั้น/question-only | legitimate short task requests | short queries จาก acquisition mechanism ที่รองรับจริง |
| ยาว/มี context | legitimate long-context/RAG/document tasks | actual context-bearing extraction queries ใน domain/format เดียวกัน |
| ซ้ำ/ระยะต่ำ | legitimate repetitive follow-ups หรือ repeated work | extraction ที่มี repetition โดยมี intent provenance |
| หลาย acquisition mechanisms | benign frame เดียวกันของแต่ละ task/source bundle | เป้าหมาย SeqKD-style offline collection, QEDKS และ Model Leeching เมื่อ adapter/provenance ผ่าน |

เป็นคำอธิบายเงื่อนไข ไม่ใช่ synthetic research prompts ที่สร้างในงานนี้
ไม่ใช้ LoRD/SODA ที่แชร์ transcripts มาเติมจำนวน traffic families อย่างหลอก ๆ
ถ้า family ใดไม่รองรับบาง format โดยธรรมชาติ ให้ระบุ structural zero และจำกัด
estimand ไว้ที่ common support ไม่ rewrite queries จนเปลี่ยน defining attack

Match **whole native sessions/streams/bundles** ตาม rules ใน protocol โดยคง
ลำดับจริงและเก็บ repeated requests ที่เกิดจริง ห้าม query-match แล้ว stitch
เป็น sessions ใหม่ ห้าม truncate/pad/สลับให้ label หลุดจาก length หลังเห็น scores
การสร้าง prospective controlled mixed session ต้องมี protocol แยกและบอกชัดว่า
เป็น controlled run ไม่อ้างว่าเป็น natural user conversation

## 6. Prerequisites ที่ต้องครบก่อนเริ่ม data acquisition

1. เลือก source track/revisions/file allowlist และ exact schema ที่ยอมรับ;
   MEA query data ต้องมี applicable data terms/attribution จาก upstream ครบ
   ส่วน WildChat ต้องยืนยันสิทธิ์ use/retention/derived release และ label policy
2. Owned traffic ต้องมี victim/source-data/participant authorization และ retention
   policy, exact collector/attack/model revisions ไม่ถือคำขอเตรียมแผนเป็นสิทธิ์ยิง API
3. Freeze native session definition, grouping/linkage/duplicate/exposure rules;
   มี incident/retry log และตรวจ Phase A–E/source pools overlap ก่อน final lock
4. Freeze length/format overlap rules และ verify declared versus actual fields
   ด้วย bounded payload sample protocol ที่ได้รับอนุญาตแยก; หาก common support
   หรือ chronology ไม่พอให้ NO-GO ไม่แต่ง controls/เติม sessions
5. ยอมรับ bounded byte/storage/time/request budgets และ fail-closed downloader
   ตาม feasibility; ยังห้าม victim/student calls, attack commands และ model loading
6. ก่อน actual traffic collection ต้องมี separate resource/model execution gate
   และพิสูจน์ method faithfulness; quotas ใน protocol เป็น post-grouping targets
   ไม่ใช่สิ่งที่ available แล้ว ไม่ขยาย collection/full experiment อัตโนมัติ

**GO: ทำ metadata-only preparation ต่อได้** บน sources ที่เปิดสาธารณะ
**NO-GO: data acquisition/traffic collection และ full experiment ในตอนนี้**
ต้องปิด prerequisites1–6 ตามขอบเขต stage ที่จะเริ่มก่อน ไม่ต้องให้ผู้ใช้อนุมัติ
เอกสารที่ยังไม่เสร็จเพื่อทำงาน Phase F นี้ให้ครบ
