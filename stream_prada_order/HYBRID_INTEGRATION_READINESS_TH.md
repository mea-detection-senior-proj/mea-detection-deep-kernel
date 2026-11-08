# Hybrid Same-Stream Integration Readiness

8 พฤศจิกายน 2026 | base `87fefe4242afeaaee2b032f7b7a74a7d4e37ddca` | `experiment/stream-prada-order`

**GO สำหรับ isolated adapters และ numeric contract tests; NO-GO สำหรับ genuine same-stream integration ในหลักฐานที่ตรวจ**
พบ metadata ที่ขาดจริง จึงหยุดก่อน export/join real scores ไม่เดา chronology และไม่สร้าง native sessions
ไม่รัน inference, embeddings, extraction, training, detector recomputation หรือ full scientific evaluation
ไม่แก้ implementations ของทีม, hybrid v1, prior protocol/config/results หรือ main

อ่าน HYBRID_FUSION_DESIGN_TH.md, HYBRID_MMD_CONTRACT_TH.md, HYBRID_FUSION_TEST_REPORT_TH.md
และ inspect Sequential/Deep Kernel/MMD source + explicit saved output metadata ก่อนลงมือ
หลักฐานที่ทำซ้ำได้: [producer_audit.json](diagnostics/hybrid_integration_20261108_v1/producer_audit.json)
audit อ่าน metadata/header/shape ของ validation control เท่านั้น ไม่เปิด Phase C held-out evaluation outcomes

## 1. Producer/output inspection และ exact gaps

| ฝั่ง | พบจริง | ขาดอะไร / consequence |
| --- | --- | --- |
|Original PRADA: experiment.trace(), phase_c_runner.score()|saved order, w_steps, w, distances; control_trace_12 มี256indices,155W ที่ Q102–256|ไม่มี genuine request/session chronology หรือ availability; order เป็น cohort-local reservoir indices ต้อง map ไป actual shared embedding rows|
|Phase C embedding metadata|BGE revision5c38ec7..., normalized/max_length512 ใน source/config; aggregate query/text order hashes และ embedding_sha256 ของ4224 vectors|ไม่มี common per-request manifest/per-row vector hashes/local→common row map; aggregate hashไม่พอรับรองแต่ละ window|
|Phase C source grouping|certificate hashตรงconfig 25970769... และ historical article/cohort allocation|ไม่ใช่ native actor/source/run certificate; exact submitted-text identity กับ normalized query identity ต้อง map จริง|
|Phase D CUSUM producer|curves() สร้าง per-query arrays ชั่วคราว; per_stream.csv.gz เก็บ max_score, first_alert, prefix/delay summaries|ไม่ได้ persist CUSUM query curve ในไฟล์นี้; max/first alertสร้างคะแนน checkpointกลับไม่ได้โดยไม่มี recomputation|
|Deep Kernel: pilot/deep_kernel_pilot.py|mmd()/repeated_score(); learned kernel=multi-RBF×(0.1+0.9 learned RBF), frozen epoch selectionก่อนcalibration; score CSV schemaตาม sampled window_id|pilot/outputs ไม่มีใน checkout นี้ จึงยังไม่มี actual Deep Kernel score/checkpoint handoff ที่ตรวจได้; ไม่ค้นทุกdisk/remote logs|
|Existing MMD result exemplar|experiment_result/main/seed=42/MMD/model_leeching_bge_bs1500: batch_scores.csv และ metadata.json; batch_size1500,reference_repeats20|เป็น MMD batch output ไม่ใช่หลักฐาน Deep Kernel checkpoint; ไม่มี session/order/window membership/availability/reference draw IDs; ขนาด1500ใช้แทนwindow100ไม่ได้|

ชื่อ embedding_model ใน existing MMD metadata เป็น BAAI/bge-small-en-v1.5 แต่ไม่มี exact encoder/tokenizer revision,
per-row artifact identity หรือ max-length/preprocessing completeness ที่ยืนยัน parity กับ Phase C ได้
embed_texts() ของ existing MMD ใช้ SentenceTransformer(model_name) และ cache key ที่ไม่ผูก exact encoder revision/max_length
ข้อสรุปคือ **parity ยังไม่ verified** ไม่ใช่การพบว่า embeddings ต่างกันจริงหรือไฟล์เสีย
CSV batch_id/window_id ไม่ใช่ request/session ID; label/attacker_ratio ไม่ใช่ native chronology
old MMD batch thresholds/null p-values ไม่ใช่ hybrid stream-level calibration

ขอบเขต inspection: producer sources ที่ระบุ, configured pilot output location,
หนึ่ง MMD model_leeching exemplar, Phase C development metadata/control12 และ Phase D output header
ไม่อ้างว่าเครื่องทั้งเครื่อง/ทุก teammate branch ไม่มี compatible scores หากมี export อื่นต้องส่ง explicit path/sidecars

## 2. Isolated read-only implementation ที่เสร็จแล้ว

[hybrid_integration.py](hybrid_integration.py) ใช้ standard library + frozen hybrid v1 interface เท่านั้น
ไม่มี import PRADA, phase_d_pilot, MMD_detection, pilot detector, numpy/torch/encoder
functions รับ already computed records/JSON bytes และคืน immutable hybrid Score/Aligned ไม่เขียนไฟล์ต้นทาง

- validate_manifest(): exact schema, positions/request IDs, declared encoder/tokenizer/view contract,
  embedding artifact/index/row-hash consistency และ source→outer-group/split certificate
- export_scores(): PRADA W→-W, CUSUM curve pass-through, signed MMD pass-through;
  ตรวจ source/model/config/provenance revision, membership slices, computed-through/availability และ reference provenance
- export_prada_trace(): อ่าน existing W bytes แบบ authenticated adapter ได้เฉพาะเมื่อ binding/raw hash/order/common index/availability ครบ
  ไม่คำนวณ Shapiro–Wilk/Growing Set/CUSUM ใหม่ และไม่ invent score ที่ไม่มี
- align_exports(): ตรวจ manifests/embedding indices สองฝั่งเท่ากันก่อนเรียก unchanged hybrid aligner
  missing/late/invalid ไม่ถูกเติมหรือ fallback; ไม่มี raw historical score joining ในงานนี้
- [hybrid_integration_audit.py](hybrid_integration_audit.py): bounded read-only metadata/header audit เขียนเฉพาะ report ใหม่

การ validate เป็น **consistency ของ declared evidence** ไม่ใช่ physical vector rehash หรือการพิสูจน์ independence/native intent
ต้องมี actual artifacts/content audit/authorization ก่อนเรียกว่า ready; metadata hashes ที่กรอกเองไม่ใช่ proof of acquisition
script audit ไม่สร้าง common manifests จาก outputs เก่าเพียงเพื่อให้ adapter ผ่าน

## 3. Reconcile 300-query software กับ 256-query research

เพิ่ม [profiles v1](hybrid_integration_profiles_v1.json) แยกชื่อและ **ไม่มี default profile**
ไม่แก้ hybrid_fusion_config_v1.json, Schedule defaults หรือ PHASE_F_PROTOCOL_TH.md

| Profile / protocol | Horizon | Decision schedule | สถานะ |
| --- | ---: | --- | --- |
|illustrative_300_v1|300|Q150/200/250/300; window100/stride50|ตัวอย่าง software เดิม|
|research_256_grid_proposal_v1|256|Q150/200/250; window100/stride50|ข้อเสนอสำหรับ integration fixtures เท่านั้น ยังไม่แทน research protocol|
|Phase F primary เดิม|256|ทุกquery Q102..Q256; reported budgets102/128/192/256|คงเดิม ไม่แก้ scientific estimand|

ข้อเสนอ grid256 มี3 joint looks ไม่ใช่4 และไม่มี joint decision ในช่วง Q251–256
MMD window [157,256] เพื่อ endpoint256 เป็น off-grid กับ frozen v1 จึง **reject** ไม่เพิ่มโดยเงียบ ๆ
ถ้าต้องการ endpoint256 หรือ joint looksตาม Phase F budgets ต้องมี explicit schedule/aligner protocol revision แยก
ไม่ rename Q250เป็นQ256 ไม่ต่อ/pad256ให้ครบ300 ไม่ truncate300โดยไม่ประกาศ
normalizer fit และ calibration thresholds ต้องผูก exact profile/look count ใหม่; ห้าม transfer threshold300→256
checkpoint-only comparison ไม่ได้พิสูจน์ performance เท่ากับ Original PRADA online155looks

## 4. Contract tests และ reproducibility

**39 tests ผ่าน (ใหม่17 + hybrid v1 regression22), failures/errors/skips=0**
actual unittest runtime0.351s บน Conda senior; CPU numeric metadata/score fixtures ไม่มี model/traffic execution
ตรวจ config/profile boundaries, common query manifest/index/grouping, repetitive legitimate-query support,
source/model/context mismatch, strict JSON, reference leakage/draw IDs, invalid/late/future scores,
legacy byte binding/order/availability, summary-only output rejection และ full300 versus256 behavior
fixture hashes เป็นตัวเลขสังเคราะห์ ไม่ใช่ actual text/vector/session evidence และไม่รายงาน synthetic detection performance
เริ่มด้วย failing import test ก่อนมี module; implementationผ่าน15tests แล้วเพิ่ม strict JSON/300-path testsและrunร่วม regressionครบ39

```powershell
conda run --no-capture-output -n senior python -m unittest stream_prada_order.tests.test_hybrid_integration stream_prada_order.tests.test_hybrid_fusion -v
conda run --no-capture-output -n senior python stream_prada_order/hybrid_integration_audit.py --output stream_prada_order/diagnostics/hybrid_integration_recheck_new.json
```

ผล tests อยู่ [tests.json](diagnostics/hybrid_integration_20261108_v1/tests.json)
audit ใช้ per-file cap4MiB (selected gzip trace/schema cap1MiB), ไม่อ่าน model weights/vectors/private traffic
ไม่มี measured GPU/RAM benchmark ในงานนี้; ไม่ใช้ผล software tests เป็น resource estimate ของ actual MMD run
ตรวจ prior manifests/source bytes แยกใน final_checks และเก็บ new-only outputs ไม่ overwrite results เก่า

## 5. Confirmed blockers และ exact next handoff

1. **Common manifest/embedding evidence ขาด:** ยังไม่มี request/text-to-row mapping/per-row hashes/availability ที่คู่ scores ใช้ร่วมกัน
2. **Actual Deep Kernel outputs/checkpoint provenance ไม่พร้อมใน inspected configured location:** ทีมต้องส่ง actual source/checkpoint/config/score exports กับ reference draws
3. **CUSUM query curves ไม่ได้ persist ใน inspected summary:** ต้องมี authentic saved curve หรือเสนอ separately gated numeric detector recomputation; งานนี้ไม่ทำ
4. **Research schedule ยังต้องตัดสินแบบ explicit:** grid256 proposal ไม่แทน Phase F; ต้อง freeze schedule และ recalibration ก่อน scientific scoring
5. **Native chronology/source independence/common-support ยังไม่ได้ยืนยัน:** ข้อมูลเก่าเป็น reused development/replay และ Phase E length/format confounding ยังไม่ถูกแก้

รายการ fields/sidecars วิธี hash และ handoff checklist สำหรับทีมอยู่
[HYBRID_MMD_PRODUCER_REQUIREMENTS_TH.md](HYBRID_MMD_PRODUCER_REQUIREMENTS_TH.md)
เก็บ real exports/IDs/texts/weights/vectors ใน ignored local storage และให้เฉพาะ explicit paths ที่ได้รับอนุญาตอ่าน
ก่อน future calibration/evaluation ต้องมี independent benign cohorts/split integrity, fixed weights/operating point,
common-complete coverage และ paired FPR uncertainty ตาม protocol ไม่ใช้ permutations เพิ่ม n

**หยุดที่ blocker: real score exports=0, real joins=0, scientific FPR/TPR/delay=null**
ไม่ได้ยืนยันว่า compatible traffic ไม่มีอยู่ที่อื่น แต่ไม่มีคู่ที่ผ่าน contract จากหลักฐานในขอบเขตนี้
ไม่มี detector/MMD/baseline changes, model inference, extraction/training/acquisition/full evaluation
ไม่แก้main/merge/rebase/PR/push และหยุดหลัง local commit
