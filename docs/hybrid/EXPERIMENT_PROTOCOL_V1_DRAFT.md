# Hybrid Detection Experimental Protocol v1 — DRAFT

วันที่ตรวจ: 11 พฤศจิกายน 2026 (Asia/Bangkok) | Task 01: repository audit และร่าง protocol เท่านั้น

**สถานะ: DRAFT เพื่อหารือร่วมกัน ยังไม่ final/frozen และไม่ใช่ authorization ให้รันการทดลอง**
ข้อเสนอหลักคือ paired comparison ของ PRADA-derived sequential CUSUM, Deep Kernel MMD และ weighted Hybrid บน common ordered query stream เดียวกัน ที่ nominal stream-level FPR 0.05 และสาม joint checkpoints เดียวกัน โดยวัด **any alert by Q250** ภายใน stream ที่บันทึกยาว 256 queries

ยังไม่มีหลักฐาน same-stream scores ที่ครบ contract ในขอบเขตที่ตรวจ จึงยังประเมิน Hybrid TPR/FPR/delay หรืออ้าง superiority ไม่ได้ เอกสารนี้ไม่แก้ detector, config, protocol หรือผลเก่า และไม่แทน scientific definitions ของ Phase F, Hybrid Fusion เดิม หรือ Deep Kernel Phase 1

## วิธีอ่านหลักฐานและขอบเขต audit

ใช้สถานะสี่ประเภทตลอดเอกสาร:

| สถานะ | ความหมาย |
| --- | --- |
| **Implemented / tested** | พบ implementation จริง; การกล่าวว่า tested อ้าง receipt เดิมที่ระบุ ไม่ใช่ผล rerun ใน Task 01 |
| **Existing results** | ผลที่รายงานไว้ก่อนงานนี้ พร้อมขอบเขต development/known-attack/replay และข้อจำกัดเดิม |
| **Proposed** | ข้อเสนอสำหรับ protocol นี้ ต้องตกลงและ lock ในงานภายหลัง ไม่ถือว่า execute แล้ว |
| **Unimplemented / unverified** | ยังไม่มี functionality/artifact หรือหลักฐานที่ตรวจไม่เพียงพอ; ไม่เติมค่าทดแทนหรือสมมติว่าทำแล้ว |

อ่าน Git objects ด้วย `git show` / `git ls-tree` โดยไม่ checkout/switch/merge branch; ตรวจ remote HEADs ด้วย `git ls-remote --heads origin` และอ่าน metadata/reports/source ที่ระบุ ไม่เปิด raw query payloads, private traffic, weights หรือ evaluation traces เพื่อวิเคราะห์ผลใหม่ ไม่รัน models, detectors หรือ scientific evaluation ไม่ค้นทุก disk หรือทุก ignored artifact

รหัสอ้างอิง path ด้านล่างผูกกับ commit ที่ตรวจ ไม่ใช่สมมติว่ามีทุกไฟล์ใน working tree ปัจจุบัน:

| รหัส | Branch / revision |
| --- | --- |
| `S` | `experiment/stream-prada-order` @ `da07fc1176b907ab2dc565823b1071fe436fa404` |
| `D` | `origin/refactor/clean-architecture` และ `origin/restructure/deepkernel` @ `e5d890703f9abd2a5a8988969579cb3a3ff0ed48` |
| `M` | `main` / `origin/main` @ `5fb5e07d750a73a0a663a174433bab931ae7568a` |

ตัวอย่าง `D:mea_detection/detection/kernels/deep.py` หมายถึง path ใน Git tree ของ D; reviewer อ่านได้ด้วย `git show e5d890703f9abd2a5a8988969579cb3a3ff0ed48:mea_detection/detection/kernels/deep.py` โดยไม่ต้องเปลี่ยน branch

## A. Research objective และ hypotheses

คำถาม: เมื่อแก้ length/format shortcuts มี native/replay provenance ที่ชัด และคุมโอกาสแจ้งเตือนกับ calibration เท่ากันแล้ว CUSUM และ MMD ให้สัญญาณเสริมกันเพียงใด และ fixed weighted Hybrid มี detection-by-Q250 / delay ต่างจากแต่ละ component อย่างไร

**Proposed hypotheses**:

1. H1 — Hybrid มี paired TPR by Q250 สูงกว่าหรือให้ detection-by-budget ดีขึ้นเมื่อเทียบ CUSUM-only และ MMD-only โดยต้องตรวจ actual held-out FPR ควบคู่กัน ไม่ถือว่า nominal alpha เท่ากันแปลว่า measured FPR เท่ากัน
2. H2 — ความแตกต่างยังคงปรากฏใน length/format-matched support และเหนือ length-only กับ non-sequential distance aggregation controls ถ้าข้อมูลไม่พอให้ข้อสรุปเป็น unresolved/negative finding
3. H3 — replay ordering อาจเปลี่ยน CUSUM state และ attack content ภายใน MMD windows แม้ full-stream membership เท่ากัน; เป็น secondary fixed-query replay sensitivity ไม่ใช่สมมติฐานว่าจำลอง native adaptive traffic ได้

ยังไม่มี preregistered superiority margin, FPR non-inferiority/equivalence margin, power หรือ multiplicity plan ดังนั้นในสถานะนี้อนุญาตเพียงการออกแบบ future descriptive paired estimates/uncertainty ไม่ประกาศยืนยัน H1–H3 หรือ novelty จากผลเดิม

## B. Existing implementation status by branch

### B1. Git snapshot และ relationships

ก่อนเริ่มแก้ไข working tree **clean**: `git status --porcelain=v1 --untracked-files=all` ว่าง ทั้ง tracked/untracked non-ignored files; ไม่ตีความว่าไม่มี ignored local resources

| Branch | HEAD ที่ตรวจ | สถานะ / ความสัมพันธ์กับ main |
| --- | --- | --- |
| `main` | `5fb5e07d750a73a0a663a174433bab931ae7568a` | มี local branch และ origin tracking ref; เป็น common ancestor ของสองสายงาน |
| `restructure/deepkernel` | `e5d890703f9abd2a5a8988969579cb3a3ff0ed48` | มี origin remote-tracking ref ไม่มี local branch ชื่อนี้; ahead main 5 commits |
| `refactor/clean-architecture` | `e5d890703f9abd2a5a8988969579cb3a3ff0ed48` | มี origin remote-tracking ref ไม่มี local branch ชื่อนี้; HEAD เดียวกับ restructure |
| `experiment/stream-prada-order` | `da07fc1176b907ab2dc565823b1071fe436fa404` | current local branch; ahead main 16 commits |

`git merge-base S D` = M; `git rev-list --left-right --count S...D` = 16 / 5 จึงเป็น divergent histories ไม่ใช่ D รวม Sequential/Hybrid แล้ว หรือ S มี active package ของ D แล้ว ไม่เรียก main ว่า latest โดยอัตโนมัติ HEAD ทั้งสี่ตรงกับผล read-only `ls-remote` ณ audit นี้ ไม่มี fetch/เปลี่ยน refs

Remote เดียวที่พบคือ `origin`: fetch/push = `https://github.com/ASippakorn/Deep-Kernel.git` ไม่มี separate fork remote ให้ตรวจ sync/independent review จึงยังรับรองสถานะ fork ไม่ได้ ผู้ใช้เป็นผู้จัดการ Git/fork synchronization เอง

### B2. Implementation inventory

| Branch / หลักฐาน | พฤติกรรมจริงและสถานะ |
| --- | --- |
| M และ S: `M:pilot/README.md`, `S:pilot/deep_kernel_pilot.py`, `S:pilot/protocol.py` | Exploratory known-attack pilot; learned kernel = multi-RBF × (0.1 + 0.9 learned RBF); train ด้วย 10% mixed windows และ variability-across-windows objective proxy; validation เลือก epoch รวม epoch zero ก่อน calibration/test ไม่ใช่สูตร training ของ D |
| D: `D:mea_detection/detection/kernels/deep.py`, `D:mea_detection/detection/training.py`, `D:mea_detection/detection/kernels/fixed.py` | Active Deep Kernel ตาม architecture ใหม่: learned feature map + trainable base/feature bandwidths และ epsilon; paired variance-normalized objective; score เป็น mean of all-cross unbiased MMD² จาก explicit reference draws ตรวจพบ source ไม่ได้รันใหม่ |
| D: `D:configs/experiments/deep_pure.json`, `D:configs/experiments/model_leeching_deep_pure_locked.json` | Example config: model_leeching, float64, seeds 1/20/42, windows 100/250, ratios .01/.05/.10/.25/1, reference repeats 20, calibration 500 sampled windows, test 200 ต่อ condition, target .05; pure train 100, 30×16 steps, validation 32 pairs; locked example มี protocol_lock=null จึงไม่ได้ชี้พร้อมใช้ไปยัง lock จริง |
| D: `D:mea_detection/data/windows.py`, `D:mea_detection/experiments/protocol.py`, `D:mea_detection/evaluation/windows.py` | สุ่ม windows จาก benign/attack pools ไม่ใช่ contiguous native session; no replacement ภายใน draw แต่ข้าม windows ซ้ำได้; per-window empirical higher quantile และ strict > ไม่ใช่ three-look stream-max calibration |
| M และ S: `M:PRADA/prada_stream_detector.py`, `S:stream_prada_order/experiment.py`, `S:stream_prada_order/phase_c_runner.py` | Minimum-L2/Growing Set/adaptive admission threshold/three-sigma/cumulative Shapiro W; isolated trace มี distances, order, w_steps, W; first eligible Q102; Phase C runner สร้าง controlled replay ที่มี benign prefix110 |
| S: `S:stream_prada_order/phase_d_pilot.py`, `S:stream_prada_order/phase_d_config_v1.json` | Fit position mean/SD ของ distance; CUSUM upper/lower/two-sided, k .5/1, first test Q102; curves() สร้าง arrays ชั่วคราว แต่ inspected per-stream output เก็บ maxima/first alert summaries ไม่ใช่ saved checkpoint curves |
| S: `S:stream_prada_order/hybrid_fusion.py`, `S:stream_prada_order/hybrid_fusion_config_v1.json` | Implemented offline consumer: exact-checkpoint alignment, benign ECDF, component-only/OR/AND/weighted, method-specific stream-max calibration, validity/coverage/first-alert accounting; default horizon300 และ 4 joint looks เป็น software illustration |
| S: `S:stream_prada_order/hybrid_integration.py`, `S:stream_prada_order/hybrid_integration_profiles_v1.json` | Read-only adapters/manifest validation มี explicit profile256 กับ joint Q150/200/250 แล้ว ไม่มี default profile; ไม่ generate detector scores หรือพิสูจน์ physical embeddings/source independence |

ที่ S/M ไม่มี `mea_detection/`, `configs/experiments/` หรือเอกสาร D ใน checkout/Git tree เดิม; ที่ D มี active package/configs/docs แต่ไม่มี `stream_prada_order/` ของสาย S; PRADA/pilot เดิมถูก archive ใต้ `D:old-detectors/PRADA/prada_stream_detector.py` และ `D:old-detectors/pilot/deep_kernel_pilot.py` การรวมสองสายเป็นงานอนาคต ไม่ทำใน Task 01

**Existing test evidence:** `S:stream_prada_order/HYBRID_FUSION_TEST_REPORT_TH.md` บันทึก 22 synthetic numeric tests; `S:stream_prada_order/diagnostics/hybrid_integration_20261108_v1/tests.json` บันทึก 39 ผ่าน (17 integration + 22 fusion), failures/errors/skips=0 ส่วน `D:docs/CLEAN_ARCHITECTURE_MIGRATION.md` รายงาน 37 checks ของ migration ที่ใช้ synthetic embeddings และ bounded preflight ไม่มี full real-data training grid ใหม่ Task 01 ไม่ rerun suites เหล่านี้ และไม่ใช้จำนวน tests เป็น scientific detection evidence

### B3. Existing experiment results และ scientific definitions ที่คงเดิม

| หลักฐานเดิม | สิ่งที่สรุปได้ / สิ่งที่ห้ามโอนมาเป็น Hybrid result |
| --- | --- |
| `S:stream_prada_order/PHASE_C_REPORT_TH.md` | Bounded article-cohort PRADA pilot, prefix110/onset111, 256 queries, 26/64/128 attack queries และ Random/Clustered/Interleaved; reused sources ไม่ใช่ independent native sessions; threshold เดิมเป็น linear P95 ของ 12 calibration streams ไม่ใช่ recipe ใหม่ |
| `S:stream_prada_order/PHASE_D_REPORT_TH.md` | CUSUM exploratory gains บน 3 outer development cohorts; 4 fit/8 calibration/3 validation; alpha .05 ไม่มี finite rank threshold; alpha .20/.40 เป็น diagnostics ไม่ใช่ target สำหรับ deployment |
| `S:stream_prada_order/PHASE_E_REPORT_TH.md` | Length-only endpoint แยก mixed replay ได้ 270/270 ที่ diagnostic alpha .20 กับ benign FP0/3; ไม่ใช่ population FPR0 หรือ superiority; length/format common-support failure ยังไม่แก้; non-sequential distance aggregation ใกล้ CUSUM หลายเงื่อนไข |
| `D:docs/MODEL_LEECHING_COMPARISON_TH.md` | รายงาน known-attack resampled-window Deep Kernel gains ที่ ratios บางระดับ แต่ measured benign FPR หลาย seed สูงกว่า5%; ไม่ใช่ matched-FPR superiority, unseen-family หรือ streaming result; Task 01 อ่านรายงาน ไม่ recertify ignored raw artifacts |
| `S:stream_prada_order/HYBRID_INTEGRATION_READINESS_TH.md` | NO-GO genuine same-stream integration ใน inspected scope; real joins=0 และ Hybrid scientific FPR/TPR/delay=null ไม่ได้พิสูจน์ว่า teammate ไม่มี exports ที่อื่น |

`S:stream_prada_order/PHASE_F_PROTOCOL_TH.md` ยังคง primary native matched traffic horizon256, online Q102..Q256 (155 looks), reported budgets102/128/192/256 และ secondary four-budget schedule ที่ calibrate แยก; ไม่เปลี่ยนเป็นสาม looks ในเอกสารนี้

`S:stream_prada_order/HYBRID_FUSION_DESIGN_TH.md` ยังคง illustrative horizon300, joint150/200/250/300, ECDF เดิม, OR=max/AND=min/weighted, strict stream-max calibration และ complete-pair policy สำหรับ fusion; draft นี้ยืม recipe โดยระบุ profile ใหม่ ไม่เขียนทับ config300 หรือโอน thresholds มา

`D:docs/adr/0001-query-efficiency-and-unseen-attack-evaluation.md` กำหนด Deep Kernel Phase 1 เป็น five-method known-attack benchmark มี primary windows100/200/500/1500 และ query-efficiency endpoint TPR≥90% พร้อม measured FPR≤5%; window250 เป็น exploratory history ทั้ง grid และ endpoint นี้ไม่ถูกแทนด้วย Hybrid three-method/three-look endpoint การมี implementation สาม methods ใน D ไม่เท่ากับทำ five-method benchmark ครบแล้ว

## C. Dataset และ source provenance

**Implemented / existing evidence:** pilot grouping จาก `S:pilot/protocol.py` และ D grouping จาก `D:mea_detection/data/datasets.py` เชื่อม ID/normalized text/recognized attack context ตาม policy; ไม่เท่ากับพิสูจน์ user/run independence หรือ native chronology ข้อมูลเก่า model_leeching และ article-cohort replay เป็น development-exposed ไม่ใช่ untouched confirmation แม้สร้าง splits/windows ใหม่

`D:mea_detection/data/provenance/ADDITIONAL_DATA_PROVENANCE.json` บันทึก source repo `ShuzeLiu11/mmd-llm-mea-detection-data` revision `7f96e886b424cc8cd384190f65c0cf0c6ea90d94` พร้อม file hashes ของ Meaeq_SST-2 และ ME_BERT_sst2_wiki; ไม่ใช่ใบรับรอง chronology หรือใบอนุญาตของ dataset ทุกตัว

สำหรับ local model_leeching และ historical article-cohort inputs งานนี้อ่าน grouping/config/report provenance เท่านั้น ไม่ตรวจ raw payloads หรือรับรอง original acquisition revision, data-use rights และ native run IDs ใหม่ หากจะนำไปทดลองต้องส่ง source manifest และตรวจสิทธิ์เฉพาะข้อมูลจริงอีกครั้ง ไม่ใช้ provenance ของสอง additional datasets ข้างต้นแทนกัน

`S:stream_prada_order/PHASE_F_DATA_PLAN_TH.md` เสนอ owned/consented traffic บน victim/task/rendering เดียวกันเป็น main track; WildChat และ MEA query pools เป็น candidates ที่มีข้อจำกัดด้าน benign intent, licenses, chronology, run lineage และ source independence ข้อความ license/availability ในแผนเป็น historical metadata assessment งานนี้ไม่ได้ตรวจ live upstream ซ้ำหรือรับ dataset payload เพิ่ม

`S:stream_prada_order/PHASE_K_PREPARATION_TH.md` ยังระบุ offline preparation และไม่มี authorized real request pilot; model snapshot integrity ใน `S:stream_prada_order/PHASE_J_INTEGRITY_TH.md` ไม่ใช่ native traffic acquisition หรือหลักฐานว่า runtime/experiment พร้อมใช้งาน

**Proposed:** ก่อน scoring ต้องมี immutable acquisition/data manifest ระบุ owner/permission/license review, exact source revision/content hashes, request IDs, submitted query view, event order, victim/task/model revisions, intent-label evidence, source-document/user/actor/run ancestry และ split assignment; successful extraction ต้องมี fidelity/training evidence แยก ถ้าไม่มีให้ success=null ห้ามใช้ชื่อ dataset หรือ unusual text แทน intent

Native track และ fixed-query replay track มีคนละ estimand ต้องแยก tables, calibration cohorts และ claims; ห้าม pool domain-shift traffic แล้วอ้างเป็น deployment FPR โดยไม่กำหนด target population/weights ใหม่ Short/insufficient native sessions ต้องรายงาน coverage/NO-GO ไม่ concatenate unrelated conversations, padding หรือผลิต synthetic research sentences เพื่อให้ครบ horizon

## D. Common ordered query-stream definition

**Proposed baseline:** หนึ่ง stream มี **256 actual requests** ตาม manifest, indices 1..256 แบบ 1-based inclusive ไม่ใช่ 256 unique texts เสมอไป; repeated requests ที่เกิดจริงคงไว้และใช้ request IDs แยก HTTP retries ที่ victim เห็นจริงต้องมี exposure policy ชัด

สอง detector ต้องอ้าง ordered list เดียวกันทุกตำแหน่ง พร้อม exact-text hash และ physical embedding-row mapping เดียวกัน; common victim/query view/encoder/tokenizer/preprocessing/dtype/dimension/normalization ต้องตรงกัน การอ้าง BGE ชื่อเดียวไม่พอ Phase C/F pin BGE revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, max_length512, normalized, no query prefix แต่ MMD parity กับ artifacts จริง **ยัง unverified**

Native chronology ต้องมี actual session/run boundary และ arrival order receipts ตาม source; แนวทาง sessionization ของ Phase F คือ actor+application/session ID, idle gap>30 นาทีแยกและ run boundary แยกเสมอ ต้องยืนยันเหมาะกับ source ก่อนใช้ ถ้าไม่มี order/timestamps ให้ระบุ `fixed_query_replay` ตามจริง ไม่ตั้ง cohort-local indices เป็น native request times

**ห้ามถือ native chronology กับ synthetic replay chronology ว่าเทียบเท่ากัน** replay ในที่นี้คือจัดลำดับ actual frozen queries ใหม่ ไม่ใช่สร้าง query texts และไม่เท่ากับ executed adaptive attack ที่ responses มีผลต่อ next request

## E. Cold start และ CUSUM warm-up

**Proposed baseline:** ไม่มี guaranteed benign prefix; attack อาจเริ่ม Q1 ต้องบันทึก true onset จาก provenance ก่อน scoring ไม่ reset onset เป็น Q102/Q150 เพื่อทำ delay ให้สั้น และไม่ใช้ labels เพื่อ reset detector

**Implemented:** upstream คำนวณ distance ตั้งแต่ Q2 และ Growing Set ตั้งแต่ Q1; cumulative Shapiro ต้องมีมากกว่า100 distances จึงได้ W แรก Q102 ใน `S:stream_prada_order/experiment.py` สำหรับ CUSUM ใน `S:stream_prada_order/phase_d_pilot.py` ฟังก์ชัน curves() standardize distance ตาม position แล้วใช้ `[100:]` ซึ่งตรง Q102..Q256; state เริ่ม0ก่อน Q102 ไม่สะสม CUSUM Q2..Q101 แต่ upstream state เห็นช่วงดังกล่าวแล้ว

ดังนั้น Q1..Q101 เป็น blind/warm-up period ของ eligible sequential statistic ไม่ได้เป็น benign training prefix และ first eligible Q102 ไม่ใช่ first joint decision ซึ่งเป็น Q150; initial traffic ที่เป็น attack อาจเปลี่ยน Growing Set ตลอดเส้นทาง ไม่มี cold-start robustness measurement ใน baseline นี้

**Proposed sequential definition:** lower-distance CUSUM ตาม Phase F โดย position-specific mean/SD fit จาก independent benign fit เท่านั้น, sigma floor .01:

```text
d_t = minimum L2 distance ถึง current Growing Set ก่อน admission ณ Q_t
z_t = (d_t - mu_t_fit) / max(sigma_t_fit, 0.01)
C_101 = 0
C_t = max(0, C_(t-1) - z_t - k), t = 102..256
```

Phase F ระบุ k=.5 และ1.0 แบบ fixed comparisons ทั้งคู่ไม่เลือก best-k จาก final; draft นี้ยังต้องตกลงว่าใช้ทั้งสองเป็น prespecified variants (แต่ละ variant มี Hybrid/threshold ของตนเอง) หรือเลือก primary k ด้วยเหตุผลล่วงหน้า ห้ามอ้างว่า user baseline ได้เลือก k แล้ว ไม่ใช้ prefix-centered variant ที่สมมติ benign prefix โดยไม่ออก protocol ใหม่

**Compatibility gap:** historical runners/summaries ผูก prefix110/onset111 และ horizon256; trace/statistic primitive มีอยู่ แต่ end-to-end no-prefix producer กับ authentic per-query CUSUM curve exports ยังไม่ได้ตรวจรับ

## F. MMD windowing และ checkpoint schedule

**Proposed integration baseline ทั้งสาม methods ใช้ decision opportunities เท่ากัน:**

| Joint checkpoint t | Sequential current score | MMD window (inclusive) | ข้อมูล evaluation ที่อนุญาต |
| ---: | --- | --- | --- |
| Q150 | C_150 | [51,150] จำนวน100 | requests ≤150 เท่านั้น |
| Q200 | C_200 | [101,200] จำนวน100 | requests ≤200 เท่านั้น |
| Q250 | C_250 | [151,250] จำนวน100 | requests ≤250 เท่านั้น |

Stream horizon256, MMD size100/stride50, joint T={150,200,250}; grid มี window[1,100] แต่ Q100 ยังไม่ผ่าน sequential eligibility จึงไม่ใช่ joint look ไม่จำเป็นต้องใช้ score นี้เพื่อ primary comparison และห้ามนำมาเป็น standalone early alert ใน paired primary

**Q251–Q256 ไม่ถูก jointly evaluated ใน initial schedule นี้; รายงาน “detection by Q250” เท่านั้น ไม่ใช่ “detection by Q256”** ไม่เพิ่ม terminal window[157,256] ซึ่ง off-grid, ไม่ interpolate, ไม่ carry forward Q250 เป็น decision Q256 และไม่ใช้ Q251..Q256 ช่วยแก้ reference/normalizer/score ย้อนหลัง

Sequential state อัปเดตจาก prefix ตามเวลา แต่ statistic ณ checkpoint คือ **current C_t** ไม่ใช่ max ของ CUSUM ก่อน t ไม่ latch alarms ระหว่าง looks; max ใช้ภายหลังเฉพาะ stream-level calibration/event summary ของสาม looks

Exact MMD score ต้องจบ t และพร้อมใช้ที่ t: `computed_through=t`, `available_at=t`; ถ้า late/invalid/missing ให้ abstain พร้อม reason ไม่ backdate, ใช้ stale window หรือแทน0 query-position availability ไม่พิสูจน์ latency เป็นวินาที ต้องมี timestamps เพิ่มจึงรายงาน wall-clock ได้

## G. CUSUM-only, MMD-only และ Hybrid scores

Raw sequential score s_t=C_t ตาม E; Original PRADA เป็น optional unchanged control ไม่ใช่ CUSUM: adapter ใช้ -W_t เพื่อให้ higher-is-more-anomalous ขณะที่ historical `1-W_t`/`1-min W` มีคนละ representation ต้องใช้ revision/calibration ของตน ไม่เอา thresholds สลับกัน

Raw MMD score m_t คือ mean ของ all-cross unbiased MMD² เหนือ R frozen benign reference draws ต่อ evaluation window Y_t:

```text
MMD_u²(X,Y) = sum_(i!=j) k(x_i,x_j)/(a(a-1))
             + sum_(i!=j) k(y_i,y_j)/(b(b-1))
             - 2 sum_(i,j) k(x_i,y_j)/(a*b)
m_t = mean_(r=1..R) MMD_u²(X_ref,r,t, Y_t)
```

ค่าติดลบจาก unbiased estimate valid ได้ ห้าม clip/กลับ sign ตาม test outcomes Reference bank frozen จาก permitted benign fit subpartition; draw100 rows แบบ without replacement ต่อ repeat ตาม current integration contract และส่ง exact draws/seed policy ไม่ใช้ future test queries/labels เป็น reference

**ต้องตกลง kernel producer ก่อน:** D ใช้ `((1-epsilon)*kappa_learned + epsilon)*q_base` ที่ bandwidths/epsilon trainable และ pure-training variance objective; S pilot ใช้ fixed multi-RBF base กับ fixed .1/.9 mixture และ mixed-window proxy objective สูตรสองสายนี้ไม่ใช่ model revision เดียวกัน Existing contract ที่อธิบาย pilot ไม่ recertify D โดยอัตโนมัติ Draft เสนอพิจารณา active D เป็น candidate แต่ยังไม่เลือก checkpoint/โอน model หรือ train อะไร

R=20 เป็น existing D experiment setting และตัวเลือกสำหรับหารือ ไม่ใช่ค่าที่ user baseline ระบุแล้ว ต้อง lock R/reference membership/checkpoint/kernel source/config/dtype/backend ก่อน score/calculate thresholds Equal observed prefix budget ไม่ใช่ equal memory/reference/compute budget ต้องรายงานแยก

หลัง normalization ให้ CUSUM-only=u_t, MMD-only=v_t และ Hybrid=h_t=.5u_t+.5v_t ทุกวิธี calibrate ของตนใหม่ตาม J ไม่ใช้ raw CUSUM+raw MMD หรือ p_value/old suspicious columns เป็น inputs

## H. Benign-fit ECDF normalization และ weighted fusion

**Proposed; recipe implemented ใน S consumer:** freeze raw detectors/nuisance/reference/model ก่อน fit normalizer ใช้ **benign fit streams เท่านั้น** ที่ common-complete ทุกสาม checkpoints; pooled checkpoint scores ของแต่ละ component:

```text
F_seq(x) = (1 + number of benign-fit sequential checkpoint scores <= x)/(m_seq+1)
F_mmd(x) = (1 + number of benign-fit MMD checkpoint scores <= x)/(m_mmd+1)
u_t = F_seq(s_t); v_t = F_mmd(m_t)
h_t = 0.5*u_t + 0.5*v_t
```

Right-continuous smoothed ECDF คง ties และ saturation ไม่มี refit จาก calibration/test scores; m คือจำนวน checkpoint values ไม่ใช่จำนวน independent streams การใช้ pooled positions เป็น proposed recipe เดิมไม่ใช่การรับรอง stationarity หรือ two-component independence ECDF ไม่ใช่ calibrated attack probability/per-query p-value

ECDF saturation อาจทำให้ threshold=1 และไม่มีคะแนนใหม่ข้ามแม้ rank finite ต้องรายงาน useful power ยังไม่ทราบ ไม่เปลี่ยน transform หลังเห็น final การเปลี่ยน per-position ECDF/weights เป็น protocol revision พร้อม fit/calibrate ใหม่

Existing OR=max(u,v), AND=min(u,v) ยังอยู่ใน Hybrid Fusion เดิม; อาจทำ secondary baselines เมื่อ preregister ไม่แทน weighted primary ไม่ใช้ independent component cutoffs แล้วอ้าง combined FPR=.05 โดยอัตโนมัติ AND ต้องข้ามพร้อม checkpoint เดียวกันและ calibrate max_t min(u_t,v_t)

## I. Independent benign fit / calibration / test splits

Outer unit เป็น connected actor/user–source-document–attack-run-lineage bundle ตาม Phase F; shared query pools/transcripts/descendant runs ต้องอยู่ group เดียวกัน ทั้งสอง labels ของ matched pair อยู่ split เดียวกัน และ permutations เป็น repeated measurements ใน bundle ไม่เพิ่ม n

**Proposed separation:**

| Purpose | ใช้ข้อมูลใด | ห้ามใช้เพื่อ |
| --- | --- | --- |
| Kernel train / model-selection validation | permitted known-attack + benign development subpartitions ที่แยกไว้ | ดู benign calibration/final เพื่อเลือก checkpoint หรือเปลี่ยน family holdout |
| Benign nuisance fit | position mean/SD สำหรับ CUSUM | estimate nuisance จาก attack/test/current supposed-benign prefix |
| Benign reference bank | frozen disjoint fit-reference source units | reference ที่ทับ query/outer group ของ stream ที่กำลัง score |
| Benign ECDF fit streams | complete fit streams ที่ไม่ทับ reference outer groups | fit ECDF จาก calibration/test หรือใช้ checkpoint count เป็น independent n |
| Benign calibration | independent complete streams | tune kernel, k, weight, windows หรือ attack-driven threshold |
| Validation | independent quality/coverage/matching gate ตาม preregistered plan | เลือก winner แล้วยังเรียก final test เดิม untouched |
| Final test | untouched benign + attack bundles | ปรับ threshold/weights/schedule หรือเลือกเผยแพร่เฉพาะ cells ที่ดี |

D ใช้ train/validation/reference/calibration/test partitions; integration contract ใช้ `split=fit` สำหรับ reference ต้องมี explicit mapping ของ D reference→hybrid fit subpartition พร้อม global grouping audit ไม่ rename split เพื่อหลบ leakage guard; kernel selection validation และ Hybrid validation เป็นคนละ purpose ต้องตั้ง IDs ชัด

Phase F planning targets เดิมคือ fit20 / calibration100 / validation40 / final200 outer bundles รวม360 (มี paired attack streams เป็น subset) ไม่ใช่ verified availability หรือ power calculation Draft นี้ยังไม่ได้ยืนยัน quotas หลังแยก fit-reference/ECDF/training เพิ่ม หรือว่ามี natural256 sessions เพียงพอ ต้องตกลง allocations ใหม่ก่อน execution ห้ามลด quotas/prefix/warm-up เพื่อให้ข้อมูลผ่าน

Minimum n_cal19 ที่ alpha .05 ให้ finite rank เท่านั้น ไม่ใช่ sample-size adequacy; historical n_cal8 ของ Phase D/E ไม่พอ independent benign calibration ห้ามเพิ่ม n ด้วย windows, permutations หรือ reference repeats

## J. Threshold calculation และ target FPR

**Proposed target:** nominal alpha=.05 ต่อ method บน any-alert event ของสาม looks T เดียวกัน สำหรับ benign calibration stream i:

```text
M_i,CUSUM = max_(t in {150,200,250}) u_i,t
M_i,MMD = max_(t in {150,200,250}) v_i,t
M_i,Hybrid = max_(t in {150,200,250}) (.5*u_i,t + .5*v_i,t)
k_rank = ceil((n_cal+1)*(1-.05))
theta_method = kth-smallest(M_i,method), ถ้า k_rank <= n_cal
alert_method(t) = statistic_method(t) > theta_method
```

ถ้า k_rank>n_cal threshold.value=null หมายถึง +infinity/no-alert ไม่ใช่ missing threshold ให้ extrapolate tail; strict > คง ties ตามเดิม ถ้า n_cal100 rank96 เป็นตัวอย่าง arithmetic ไม่ใช่ artifact ที่สร้างใน Task 01 ภายใต้ exchangeability ของ calibration/test outer streams และ frozen fit marginal exceedance bound เป็น5/101≈4.95% ไม่ใช่ conditional guarantee หรือ empirical held-out FPR ที่วัดแล้ว

ทั้งสามวิธีใช้ independent benign calibration **ชุดเดียวกันและสาม checkpoints เดียวกัน** แต่ thresholds แยกตาม method/variant การซ้อนทับ MMD windows ไม่เพิ่ม independent n และไม่ต้องแกล้งถือสาม looks independent เพราะ calibrate stream maximum โดยตรง

ห้ามใช้ per-window higher quantile ของ D, pilot linear quantile, Phase C P95 หรือ Hybrid horizon300 thresholds มาแทน ต้อง refit ECDF และ stream-max calibration ผูก profile256 นี้ใหม่ เก็บ frozen receipts ก่อน validation/final หาก incomplete calibration stream ให้หยุด quality gate ไม่ drop เงียบแล้วเปลี่ยน target population

## K. Attack fractions และ query ordering

ให้ a_i∈{0,1} เป็น provenance label ของ request i:

```text
full_stream_fraction = sum_(i=1..256) a_i / 256
evaluated_prefix_fraction = sum_(i=1..250) a_i / 250
window_fraction(t) = sum_(i=t-99..t) a_i / 100, t=150,200,250
```

ต้อง export requested fraction (ถ้ามี), actual integer count และ actual fraction ทั้งสามระดับแยกกัน ห้ามติด label “25% attack” แล้วสมมติทุก MMD window มี25% โดยเฉพาะเมื่อ onset/ordering เปลี่ยน

**ตัวอย่าง arithmetic เท่านั้น ไม่ใช่ experimental result:** ถ้า attack64 queries อยู่ Q1..Q64, full-stream=64/256=25%, evaluated-prefix=64/250=25.6% แต่ window[51,150] มี14%, [101,200] และ[151,250] มี0% จึงอาจประเมิน retrospective sequential evidence หลังโจมตีจบแล้ว ไม่ใช่ทุก checkpoint เห็น attack mixture เดียวกัน Attack ที่เริ่ม Q251..Q256 ไม่มี post-onset joint look ต้องแยกเป็นไม่มี observable post-onset opportunity ไม่ปนกับ primary post-onset detection denominator

Historical Phase C/D/E ใช้26/64/128 จาก256 =10.15625%/25%/50% และ prefix110/onset111 ไม่เรียก26ว่า exact10% ตัวเลือก secondary fraction grid เช่น1/5/10/25/50/100% ยังต้องตกลง รวม integer rounding/nested membership/seeds และ unsupported cells; 1% ของ256 ไม่ใช่ integer ไม่ยืม D per-window count rule มาใช้ทั้ง stream โดยไม่ประกาศ

Primary ที่มี native evidence ให้คง native request chronology ส่วน **Random, Clustered, Interleaved replay** เป็น possible secondary analyses เท่านั้น ต้อง lock algorithms/seed/onset/membership ของแต่ละ schedule ก่อน score ไม่ถือว่า traffic distribution จริง และไม่สมมติแต่ละแบบมี prefix110

Replay ต้องใช้ actual frozen query set เดียวกันสำหรับ paired comparison แล้ว recompute upstream Growing Set/distances/CUSUM/MMD windows ตาม order ใหม่ในงานที่ได้รับอนุมัติภายหลัง ห้าม shuffle saved distances/scores แทน recomputation Adaptive run ที่ next query ขึ้นกับ response ไม่รักษา native attack semantics หลัง reorder; ต้องติด label fixed-query replay statistic study โดยชัดเจน

## L. TPR, FPR, false alarms และ detection delay

**Proposed primary endpoint:** paired any alert at T={150,200,250}, ชื่อผลทุกตารางต้องระบุ **by Q250** และ recorded horizon256 ต่างหาก

| Metric | นิยาม / denominator |
| --- | --- |
| Benign stream FPR | จำนวน all-benign independent complete outer streams ที่ any alert ในสาม looks / จำนวน eligible complete benign outer streams; แสดง actual counts และ intervals |
| False alarms | any-alert count ต่อ benign stream นับครั้งเดียว แม้หลาย checkpoints ข้าม; per-checkpoint crossing counts เป็น secondary ไม่ใช่ independent alarms; rate ต่อ1000 observed requests ต้องแสดง exposure250/stream สำหรับ endpoint นี้ ไม่รวม6 queriesที่ไม่มี evaluationโดยเงียบ ๆ |
| Raw attack-stream any-alert rate | any alert by250 / complete attack streams; ถ้ามี pre-onset alert ห้ามเรียกทุก alert ว่า true detection |
| Post-onset TPR | first eligible alert ที่ t≥onset และไม่มี earlier first alert / at-risk complete attack streams ที่มี checkpoint หลัง onset≤250; รายงาน pre-onset ineligible กับ onset>250 แยก และแสดง denominator ทั้งหมด |
| Detection-by-budget | cumulative detection ที่150/200/250 ใช้ threshold ของ full three-look schedule เดียวกัน ไม่ recalibrate แต่ละ budget แล้ว pool |
| Delay | first eligible checkpoint alert − true onset ในหน่วย requests; ห้าม backdate ไปต้น window, Q102 หรือจุดที่ CUSUM ข้ามนอก checkpoint; onset1 มี warm-up/first-look delay จริง |
| Non-detection | right-censor ที่ **Q250** สำหรับ at-risk complete streams, ไม่แทน miss ด้วยdelay0 และไม่รายงาน median detected-only โดยไม่มี detected n / censor counts |
| Pre-onset alarm | first alarmก่อน known onset; onset1 ไม่มี benign prelude จึง prefix/pre-attack metric=null/not applicable ไม่ใช่0ที่พิสูจน์ผ่าน control |

**พบ implementation gap จริง:** `S:stream_prada_order/hybrid_fusion.py` evaluate() ตั้ง `censor_query=rows.spec.schedule.horizon` เมื่อไม่มี alert แม้ profile256 มี lookสุดท้าย250 จึงคืน256ได้ Draft กำหนด endpoint censor250 โดย explicit; ยังไม่ได้แก้ code ต้องมี endpoint-aware evaluation/report adapter หรือ versioned consumer revision ที่เก็บ recorded_horizon256 และ evaluation_end250 แยกกันก่อน scientific run ห้ามใช้ existing Result เป็นหลักฐานว่า jointly observed ถึง256

Missing/late/invalid score ไม่เป็น benign true negative; component-only methodใช้ componentของตนได้ตาม existing consumer แต่ primary paired effects ใช้ common-complete streams และรายงาน total/complete/incomplete/observed alarms รวม incomplete แยกกัน หาก coverage selection มีผลต้องจำกัด estimand เป็น conditional complete-case ไม่อ้าง unconditional population FPR หากไม่มี complete streams metric=null

แสดง paired method disagreements, FPR/TPR differences และ uncertainty จาก independent outer bundles; ถ้ามีหลาย streams/permutations ต่อ bundle ใช้ cluster accounting/resampling ตามแผนล่วงหน้า ไม่ naive binomial/query-level n; exact binomial intervalใช้ได้เมื่อหนึ่ง independent Bernoulli ต่อ bundle และสมมติฐานเหมาะสม Native กับ replay/attack-family/domain strata แยกกัน ไม่มี timestamps ที่เชื่อถือได้ให้ seconds delay=null

## M. Length/format shortcut controls

**Existing finding:** Phase E พบ structural separation; historical attack384/384 อยู่นอก benign fit length support หลัง capped length adjustment การ correction ไม่สร้าง common support จึงยังไม่ใช่การแก้ confounding สำเร็จ Existing exploratory CUSUM/Deep Kernel gains ไม่ใช่ confirmed Hybrid superiority

**Proposed controls อิง Phase F โดยไม่เปลี่ยนนิยามเดิม:**

1. บน victim/task/domain/rendering เดียวกัน เก็บ legitimate long-context, short และ repetitive benign รวม attack ที่ format faithful วัด words/characters/frozen-tokenizer pre-truncation tokens/victim context tokens/role-template/repetition/truncation แยกกัน ไม่ถือ word count=token count
2. ใช้ Phase F metadata matching gate ก่อน detection outcomes: exact domain/task/rendering และ truncation strata; length-bin proportionsต่าง≤.10, format proportionsต่าง≤.05, median word/token ratio .9–1.1, |SMD(log-length)|≤.10; ถ้าเปลี่ยน calipersต้องเสนอ revision ก่อน final scoring ไม่ตัด/เรียง queries เพื่อทำให้ผ่าน
3. รายงาน retained coverage/hard-negative FPR ต่อ strata ถ้า support ไม่ทับหรือทิ้งเกิน20% ต่อ label/frameตาม Phase F ให้ NO-GO/จำกัด estimand ก่อน score ไม่ hide false alarms ใน pooled rate; Phase F cell/family quotasยังต้องตรวจจริง
4. Length-only ตาม Phase F = two-sided standardized deviation ของ prefix mean log1p(words Q1..t) จาก benign position fit (floor .01); non-sequential distance aggregation = negative mean of distances Q2..t ทั้งคู่ประเมินที่สาม looksและ recalibrate maxใหม่เป็น **explicit secondary schedule adaptation** ไม่เอา Phase E endpoint-only definition มาเรียกเหมือนกัน
5. Upstream minimum distancesยังขึ้นกับ order/Growing Set แม้ไม่ใช้ CUSUM recursion จึงเรียก non-sequential aggregation ไม่ใช่ order-invariant representation; การแยก upstream state effect ต้องมี separately reviewed frozen-reference ablation

## N. Required producer outputs และ data contracts

ยึด `S:stream_prada_order/HYBRID_MMD_CONTRACT_TH.md` และ `S:stream_prada_order/HYBRID_MMD_PRODUCER_REQUIREMENTS_TH.md` พร้อมตรวจ physical/content provenance แยกจาก schema validation ไม่สร้าง metadata ให้ดูเข้ากันเพื่อผ่าน tests

| Artifact / schema | Required evidence และ acceptance |
| --- | --- |
| `hybrid-common-stream-v1` | session_id, outer_group, split/label, chronology_kind=native/fixed_query_replay, dataset_revision, victim_revision, grouping_certificate_sha256, representation และ queriesครบ256; ต่อ queryมี query_index/request_id/text_sha256/embedding_row/embedding_row_sha256/source_group_sha256; ทั้งสอง producersส่งเนื้อหา common manifest เท่ากัน |
| representation / `hybrid-embedding-index-v1` | exact encoder/tokenizer revisions, preprocessing_sha256, normalization/dimension/dtype, embedding artifact hash และ per-row binding; exact submitted-view UTF-8 text hash ไม่ใช่ normalized grouping hash; ต้อง independently verify physical bytes/layout little-endian contiguous float32/64 พร้อม row/matrix/container hashes แยกตาม contract |
| `hybrid-groups-v1` | source→outer_group→split assignments และ provenanceของ connected user/document/run/query-pool audit; ไม่ข้าม splits; declarationsไม่พิสูจน์ hidden shared sources/independence |
| `hybrid-reference-v1` | split=fit, actual embedding contract/artifact, source groups/rows, ≥100 rows, ไม่ทับ stream group/text; reference draws100 indices/repeat without replacement; ไม่ปลอม D reference partitionเป็นfitโดยไม่ส่ง mapping |
| `hybrid-producer-scores-v1` | kind=cusum_curve/mmd_windows (prada_wเฉพาะoptional Original control), explicit profile_id=research_256_grid_proposal_v1, manifest/representation/group certificate hashes, detector/model/config/calibration provenance, availability_basis, reference fingerprint/repeats และ rows |
| ทุก score row / `hybrid-score-v1` consumer | start/end 1-based inclusive; sequential start=end=t≥102 (singletonคือscore availability ไม่ได้แปลว่าstateใช้queryเดียว); MMD exact100/50grid; computed_through=end, available_at≥end, finite value/valid; invalid→value=null; query_slice_sha256=fingerprint(queries[start−1:end]); reference_drawsจริงสำหรับ valid MMD |
| CUSUM producer sidecar | authentic saved per-query curve Q102..Q256, exact d_t/upstream order binding, lower/upper/side, k, mu/sigma/floor/fit memberships/source hashes, state initialization และ availability; max_score/first_alert ไม่พอสร้าง C_150/C_200/C_250 |
| Deep Kernel producer sidecar | actual selected checkpoint/content digest, source/dependency/config/architecture/kernel formula, estimator, bandwidths/epsilon, precision/backend, train/model-selection memberships/objective, reference bank/draws/repeats/aggregation/RNG; raw signed score ไม่ใช้ old threshold/p-value |
| Frozen evaluation receipts | fit values/normalizer fingerprint, calibration stream maxima ต่อ method, n/rank/threshold/ties, exact three looks/weights/variant revisions, split integrity/coverage gates และ endpoint250 ที่แยกจาก horizon256; ยังไม่มี real receipts ชุดนี้ |

Canonical hashes ใช้ `S:stream_prada_order/hybrid_fusion.py` fingerprint(): sorted-key compact JSON, ASCII escaping, no NaN; `ordered_query_sha256` ผูก queries list ไม่ใช่ file-whitespace hash หรือ sorted bag และ manifest_sha256 ผูก whole object ตาม contract

สำหรับ saved W adapter `S:stream_prada_order/hybrid_integration.py` export_prada_trace() ต้องมี exact decompressed UTF-8 trace bytes/hash, order เท่ากับ common embedding_row list, steps102..256 ครบ และ availability จริง ไม่ reconstruct native session จาก cohort IDs; CUSUM summary ไม่ผ่านแทน curve

Artifacts เก่า: `pilot/outputs` **ไม่มีใน current checkout ที่ตรวจ**; historical batch/window CSV ไม่ได้มี common request membership/availability จากรายงาน readiness ดังนั้นไม่มี authentic same-stream pair ให้ join การมี locked draws ของ D ช่วย reproducibility ของ random-window experiment แต่ยังไม่ใช่ common native stream producer

เก็บ raw texts/IDs/weights/vectors/exports ใน ignored private storage ตามสิทธิ์และส่ง explicit authorized paths พร้อม expected hashes ไม่ commit ข้อมูลเหล่านี้ Numeric fixture hashes ใช้ยืนยัน software contract เท่านั้นไม่ใช่ traffic provenance

## O. Compatibility gap table, blockers และการตัดสินใจร่วมกัน

คอลัมน์ “ต้องแก้ teammate detector code?” แยก numerical algorithm จาก exporter/runner/report/consumer; เป็นแผนอนาคตทั้งหมด **ยังไม่ implement ใน Task 01**

| Requirement | Existing implementation | Missing functionality / evidence | Suggested future task | ต้องแก้ teammate detector code? |
| --- | --- | --- | --- | --- |
| Versioned shared development base | S/D divergent 16/5; main เก่ากว่า; D สองชื่อมี HEAD เดียวกัน | shared reviewed base และ fork synchronization | ทีมระบุ upstream/fork/base revisions และ handoff workflow | ไม่ใช่ algorithm; Git integration เป็นงานผู้ใช้/ทีมแยก |
| เลือก Deep Kernel scientific identity | D active formula/variance objective ต่างจาก S pilot proxy | agreed producer/checkpoint และ contract amendment ที่อ้าง D จริง | audit/freeze model identity และ update producer contract แบบ versioned | ไม่ต้องเปลี่ยนสูตรเพื่อทำ fusion; checkpoint loader/export อาจต้องเพิ่ม |
| Actual native256 traffic / no benign prefix | Phase F เป็นแผน; historical replays มี prefix110; Phase K ยัง offline | consent/license/intent/run/session/length feasibility | metadata/acquisition feasibility gate และ prospective traffic plan | ไม่; collector/data pipeline แยก |
| Common query/embedding identity | adapters ตรวจ declared manifest/index ได้ | real request→exact text→vector mapping และ byte receipt | common stream/embedding handoff และ independent content audit | ไม่; producer metadata/export |
| Global outer-group disjointness | historical ID/text/context grouping, adapter certificates | actual actor/run/source dependencies และ purpose partitions ร่วม S/D | grouping/split audit ก่อน score | ไม่; data/split preparation |
| CUSUM current Q150/200/250 | curves() มีสถิติ; output มี maxima/first alert | persisted curve และ authentic provenance/availability; no-prefix end-to-end path | separately gated CUSUM producer export จาก actual streams | numerical CUSUM ไม่ต้องเปลี่ยน; isolated runner/export และรายงานที่ hardcode prefix ต้องปรับ |
| MMD contiguous100/stride50 | D score API รับ window+explicit refs; make_windows สุ่ม pool | same-stream causal runner และ exact draw export | เพิ่ม exporter รอบ frozen score API ไม่ฝึกใหม่ใน exporter | ไม่ต้องแก้ kernel/MMD; runner/export ต้องเพิ่ม |
| Joint schedule256/three looks | S integration profile256 และ Schedule parameter มีแล้ว; default config300 | explicit experiment driver/config/receipts สำหรับ baseline256 | เชื่อม runner กับ explicit profile ภายหลัง team agreement | ไม่; consumer/config wiring แยก |
| Benign ECDF + .5/.5 | implemented pooled-fit ECDF และ weighted fusion | real independent complete fit streams | freeze fit plan แล้ว fit normalizer ในงานทดลองภายหลัง | ไม่; offline consumer มีแล้ว |
| Stream-level FPR .05 | S มี rank-max calibration; D higher per-window; D/E n_cal8 | independent benign streams เพียงพอ และ three-look maxima | joint benign calibration และ freeze receipts ใหม่ | ไม่; ใช้ calibrator ใหม่โดยคง historical thresholds |
| Endpoint/delay/censor Q250 | evaluate() ใช้ schedule.horizon256 เป็น censor | evaluation_end250 ที่แยก recorded_horizon และ onset>250 eligibility | endpoint-aware report adapter/versioned consumer พร้อม behavior checks | ไม่แก้ detector; evaluator/report ต้องเพิ่ม/ปรับ |
| Observed availability / missingness | consumer มี abstention/strict causality | producer completion timestamps/checkpoint receipts และ coverage policy | availability/coverage audit โดยไม่ backdate | ไม่; instrumentation/export |
| Actual per-window attack fractions | D sampled window มี actual count; S มี historical global counts | common label membership และ counts ของสาม windows ใน reports | manifest-based fraction/exposure accounting | ไม่; reporting จาก frozen labels |
| Length/format controls | Phase E พบ confounding; Phase F gates/controls เป็นแผน | matched support จริง และ control outputs ตาม primary schedule | matched traffic feasibility และ prespecified controls | ไม่แก้ primary detectors; isolated controls/report |
| Paired TPR/FPR/delay/uncertainty | synthetic consumer/tests และ development reports | actual paired complete outputs, group-aware analysis, margins/power | preregister analysis/coverage/superiority plan ก่อน final | ไม่; evaluation/statistical report |
| End-to-end scientific verification | historical 39 numeric contract tests และ D migration checks | real producer acceptance และ reviewed execution/resource plan | metadata handoff → review → separate bounded experiment task | ไม่ถือ tests แทน performance; exporter/test อาจเพิ่มแยก |

### O1. Current blockers

1. ยังไม่มี authentic common ordered-stream/embedding-row/availability/outer-group evidence ที่ผูก actual CUSUM กับ Deep Kernel scores ในขอบเขตที่ตรวจ Existing summary-only CUSUM กับ random-window MMD นำมา join ย้อนหลังไม่ได้
2. D กับ S มีคนละ history และ Deep Kernel identity; ยังไม่ได้เลือก producer/model checkpoint หรือมี fork review evidence พร้อม ไม่ถือชื่อ branch หรือชื่อ Deep Kernel เป็น parity
3. Independent benign fit/reference/calibration/final traffic, native256 coverage, intent/licenses และ common-support feasibility ยังไม่รับรอง Historical n_cal8 ไม่รองรับ finite5% rank และ permutations เพิ่ม n ไม่ได้
4. Software มี profile256 แล้วแต่ scientific three-look normalization/calibration/endpoint receipts ยังไม่มี; current censor256 ไม่ตรง endpoint250 ต้องแก้ในงานแยกก่อนใช้จริง
5. Length/format confounding ยังเปิดอยู่; ไม่มีผล Hybrid จริงให้ยืนยัน complementarity/superiority/generalization

### O2. Unresolved decisions ที่ต้องตกลงก่อน protocol lock

- เลือก upstream/base/fork review process และ actual D/S producer/checkpoint identity ใด; จะ version contract ให้รองรับ D อย่างไรโดยเก็บ pilot definition เดิม
- ยอมรับ three-look by Q250 เป็น initial integration estimand ต่างจาก Phase F online256 หรือไม่; หากต้องการ Q256 ต้องเสนอ explicit schedule/aligner/calibration revision แยก ไม่แอบเปลี่ยน baseline นี้
- Main native traffic ที่มี256 requests/intent labels จริงมีเพียงพอหรือไม่; ถ้าไม่มีจะ NO-GO หรือเสนอ separate replay-only estimand; ใช้ sessionization/target benign population/domain weights ใด
- CUSUM primary k และ fixed variants/multiplicity plan; nuisance fit/source allocation และ cold-start policy ที่ไม่พึ่ง benign prefix
- Kernel training/model-selection/reference/ECDF fit/calibration/validation/final purpose allocations และ actual independent quotas; reference R/draw seeds/bank content/precision/backend ใด
- Attack families/known-versus-unseen holdout, full-stream fraction grid, integer counts, onset distribution, replay algorithms/seeds และ treatment ของ onset>250 ต้อง lock ก่อน outcomes
- Common-complete/invalid/late policy, endpoint censor250 reporting, cluster uncertainty และ FPR margin/power/multiplicity หากจะอ้าง superiority
- Length/format matching acceptance และ hard-negative coverage ผ่านได้จริงหรือไม่; ถ้าไม่ผ่านต้องจำกัด estimand ก่อน score
- ขอบเขต resource/request/reference/token/time/VRAM gate และ execution authorization ของงานภายหลัง ยังไม่มี execution grant จาก draft นี้

## หลักฐานตรวจรับ Task 01 และข้อจำกัด

Task 01 สร้างเอกสารนี้เท่านั้น ตรวจ path ที่อ้างด้วย Git tree ของ S/D/M ที่ระบุและเทียบ branch HEADs กับ remote โดย read-only ไม่ checkout/merge/rebase/cherry-pick/overwrite branch ไม่ train/run models/detectors ไม่สร้าง experimental metrics หรือแก้ existing outputs ไม่ commit/push/สร้าง PR

ผล static validation ใน Task 01: พบ branch-qualified cited paths ครบ **40/40** ใน Git objects ที่อ้าง, หัวข้อ A–O ครบ15, ไม่พบไฟล์เปลี่ยนนอก `docs/hybrid/`, และ whitespace checks ผ่านทั้ง tracked diff กับไฟล์ใหม่ ตรวจ source hashes ทั้ง4รายการใน historical integration test receipt แล้วยังตรง แต่ **ไม่ได้ rerun39tests** และไม่รับรอง scientific performance จากการตรวจ hash

การตรวจรับเป็น documentation/static provenance audit ไม่ใช่ rerun scientific experiment หรือ recertification ของ ignored artifacts รายงาน test counts และผลเก่าข้างต้นเป็น existing receipts อย่างชัดเจน Unknowns ที่พบบันทึกใน C/E/G/I/L/N/O ต้องตรวจรับ producer handoff และตกลง protocol revision ในงานถัดไปก่อน scientific execution
