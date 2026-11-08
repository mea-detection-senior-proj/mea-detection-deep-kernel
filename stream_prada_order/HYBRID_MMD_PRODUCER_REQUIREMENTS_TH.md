# Same-stream score producer requirements — สำหรับทีม MMD

8 พฤศจิกายน 2026 | ส่งต่อเป็นเอกสาร ไม่ได้ส่งข้อความหรือแก้ implementation ของทีม
ใช้ร่วมกับ [contract เดิม](HYBRID_MMD_CONTRACT_TH.md) และ [readiness report](HYBRID_INTEGRATION_READINESS_TH.md)

**ต้องส่ง actual unthresholded scores พร้อม sidecars ด้านล่าง**
ชื่อ dataset/model/window_id ตรงกันไม่พอ ส่วน thresholds/p-values ของ random batches ใช้แทน hybrid joint calibration ไม่ได้
adapter อยู่ [hybrid_integration.py](hybrid_integration.py) ไม่มี MMD/encoder/training call

## 1. Common stream manifest: `hybrid-common-stream-v1`

| Field | ข้อกำหนด |
| --- | --- |
|schema_version|hybrid-common-stream-v1|
|session_id / outer_group|session/run ID จริงและ connected user/source/run-lineage group ที่ audit แล้ว|
|split / label|fit/calibration/validation/development/final_test และ benign/attack จาก frozen manifest|
|chronology_kind|native หรือ fixed_query_replay ตามจริง; ห้ามนำ retrospective order มาเรียก native|
|dataset_revision / victim_revision|immutable acquisition/content/task/victim condition ที่ตรงทั้งสอง producer|
|grouping_certificate_sha256|canonical fingerprint ของ certificate ในข้อ3|
|representation|encoder_id, encoder_revision, tokenizer_revision, preprocessing_sha256, normalized, dimension, dtype, embedding_artifact_sha256|
|queries|รายการครบ horizon ตามลำดับ; ทุก row มี query_index, request_id, text_sha256, embedding_row, embedding_row_sha256, source_group_sha256|

query_index ต้องต่อเนื่อง1..N; request_id ห้ามซ้ำ แต่ repeated query text/embedding row ที่เกิดจริงทำได้
text_sha256 เป็น exact UTF-8 query view ที่เข้า encoder ไม่ใช่ hash ของ normalized text โดยเดาว่าเหมือนกัน
preprocessing manifest ต้องระบุ strip/normalization/prefix/chat view/max_length/truncation และ tokenizer policy จริง
dimension/dtype/normalized ต้องตรง physical embeddings ทั้งสองฝั่ง ใช้ actual pinned encoder/tokenizer revisions ไม่ใช้ชื่อรุ่นเฉย ๆ
ข้อมูลจาก Phase C ใช้ BGE revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` แต่ไม่เป็นหลักฐานว่า MMD เดิมใช้ revision เดียวกัน

ทั้งสองฝั่งต้องส่ง **common manifest เนื้อหาเท่ากันทั้งหมด** ไม่มีการ join ด้วย index อย่างเดียว
hash ใช้ `hybrid_fusion.fingerprint()` (sorted-key compact JSON, ASCII escaping, no NaN) ที่ ship มาด้วย
manifest_sha256 คือ fingerprint ของทั้ง object; ordered_query_sha256 ใน fusion คือ fingerprint ของ queries list
ไม่ใช้ hash ของไฟล์ JSON ที่มี whitespace ต่างกันแทน canonical fingerprint โดยเงียบ ๆ

## 2. Embedding index: `hybrid-embedding-index-v1`

ต้องมี schema_version, embedding_artifact_sha256, representation_sha256 และ rows
แต่ละ row = embedding_row (0-based index), text_sha256, embedding_row_sha256
representation_sha256=fingerprint ของ representation object; embedding_artifact_sha256 ตรงกับ common manifest
แถวของ query ทุกตัวต้องมีใน index และ text/row hash ต้องตรง ห้ามใช้ cohort-local index เป็น global row โดยไม่มี mapping
row index ไม่ซ้ำใน index table แต่ query list อ้าง row ซ้ำได้สำหรับ repetition จริง

สำหรับ export ใหม่ กำหนด vector row bytes เป็น contiguous little-endian float32/float64 ตาม dtype;
embedding_row_sha256 ต้องได้จาก actual row bytes และ artifact hash ต้องอ้าง actual canonical matrix blob พร้อม layout descriptor
เก็บ artifact format/layout, row count/dimension และ byte-hash verification receipt จริงเป็น private sidecar
หาก producer ใช้ .npy/.pt file hash ให้ระบุ container hash กับ canonical matrix hash แยก ห้ามสลับกับ Phase C z.tobytes hash
adapter ตรวจ **declarations/index consistency** เท่านั้น ไม่โหลดหรือยืนยัน physical vectors เอง
ก่อน real experiment ต้องมี independent byte verification ของ embedding artifact/rows ไม่ถือ numeric test hashes เป็นหลักฐาน

Context.embedding_revision ใน fusion ผูก encoder/tokenizer/preprocessing/dimension/dtype/normalization contract
ส่วน artifact/row identities ผูกผ่าน common manifest และการเปรียบเทียบ embedding indices ของคู่ scores
จึงไม่บังคับว่าคนละ session ต้องใช้ไฟล์ vectors เดียวกัน แต่แต่ละคู่ sequential/MMD ต้องอ้าง rows/artifact เดียวกันจริง

## 3. Source grouping: `hybrid-groups-v1`

fields = schema_version, provenance_sha256, assignments
แต่ละ assignment = source_group_sha256, outer_group, split
source group ปรากฏครั้งเดียวใน certificate และ outer group เดียวห้ามข้าม splits
queries ทุกตัวต้อง map เข้ากับ outer_group/split ของ stream
certificate provenance ต้องอ้าง actual connected user/document/run/query-pool audit ไม่ใช่แค่กรอกชื่อบทความใหม่
adapter ไม่สามารถค้น hidden shared users/source paraphrases หรือพิสูจน์ statistical independence จาก certificate ลำพัง
ต้องมี global grouping/leakage audit สำหรับ fit/calibration/validation/final โดยไม่เพิ่ม n จาก permutations

## 4. Frozen reference bank: `hybrid-reference-v1`

fields = schema_version, split=fit, grouping_certificate_sha256, embedding_contract_sha256,
embedding_artifact_sha256, rows
embedding_contract_sha256 ใช้ `embedding_contract(representation)` ซึ่งไม่รวม query artifact identity
แต่ต้องตรง encoder/tokenizer/preprocessing/dtype/dimension/normalization จริง
แต่ละ reference row มี text_sha256, embedding_row_sha256, source_group_sha256, outer_group
reference sources ต้องอยู่ fit ตาม certificate, ไม่ทับ stream outer group หรือ exact query text hashes
รุ่นนี้ต้องมีอย่างน้อย100 reference rows และ draws แบบ without replacement ต่อ repeat เท่านั้น
index ไม่ซ้ำไม่ได้พิสูจน์ว่าคนละ query/source เป็น independent observation ต้อง audit bank ด้วย
หาก method ต้อง sampling with replacement ให้เสนอ explicit contract/profile revision ไม่ยัดเข้า without-replacement schema

## 5. Already computed scores: `hybrid-producer-scores-v1`

| Field | ข้อกำหนด |
| --- | --- |
|kind|prada_w / cusum_curve / mmd_windows|
|profile_id|illustrative_300_v1 หรือ research_256_grid_proposal_v1 โดยเลือกชัดเจน ไม่มี default|
|manifest_sha256 / representation_sha256 / grouping_certificate_sha256|ตรง actual sidecars ข้างต้น|
|revision|detector_revision, model_revision, configuration_revision, calibration_provenance ตาม DetectorRevision|
|availability_basis|observed_query_position หรือ declared_fixed_replay; อย่างหลังใช้ได้เฉพาะ fixed_query_replay|
|reference_manifest_sha256|actual reference fingerprint สำหรับ MMD; null สำหรับ sequential|
|reference_repeats|จำนวน repeat จริง >0 สำหรับ MMD;0 สำหรับ sequential|
|rows|รายการคะแนนที่มี fields ครบตามด้านล่าง|

ทุก score row มี start, end, available_at, computed_through, value, valid, query_slice_sha256, reference_draws
boundaries เป็น1-based inclusive; MMD window100/end100+50k; sequential start=end=query_index≥102
computed_through=end; available_at≥end และต้องมาจาก observed checkpoint boundary receipts หรือ declared replay schedule
ไม่ backdate asynchronous result: availability/index อย่างเดียวไม่รับรอง UTC latency ต้องเก็บ timestamps แยก
query_slice_sha256=fingerprint(queries[start−1:end]) ตรวจ actual contiguous membership ไม่ใช่ hash ของ sorted bag
MMD reference_draws เป็น list ของ repeats แต่ละ draw เป็น100 indices (0-based) ใน reference bank ไม่ซ้ำ/ไม่ออกนอกช่วง
invalid MMD score อาจให้ draws=null เมื่อไม่ทราบจริง แต่ valid score ห้ามไม่มี draws
value ต้อง finite; valid=false ต้อง value=null ไม่เติม0/NaN; MMDติดลบได้

MMD model_revision ต้องผูก actual Deep Kernel checkpoint hash พร้อม kernel/architecture config,
source/dependency revision, bandwidths, mixing constants, unbiased estimator, reference repetition/aggregation และ seed policy
ต้องไม่มี epoch/model/reference selection จาก final outcomes และไม่แอบ train ใน exporter
ส่ง raw score ก่อน threshold/p-value; consumer คง sign ของ MMD และ CUSUM แล้วแปลง W เป็น -W
adapter สร้าง configuration/provenance fingerprints เพิ่มเพื่อผูก adapter version, sign mapping, profile และ reference bank
เก็บ producer payload/file hashes กับ calibration receipts แยก ไม่ใช้ raw upstream thresholds หลัง transform หรือเปลี่ยน schedule

## 6. Sequential requirements ที่ต้องประสานร่วมกัน

Saved W path สามารถใช้ export_prada_trace() ได้เมื่อมี actual common manifest/index/certificate
พร้อม binding ที่ประกอบด้วย producer envelope ยกเว้น rows และเพิ่ม trace_sha256 กับ available_at list
trace_sha256 ผูก **exact decompressed UTF-8 JSON bytes** ที่ส่งเข้า function; เก็บ compressed source-file hash จาก historical artifact manifest แยกด้วย
trace.order ต้องเท่ากับ common embedding_row sequence และ w_steps ต้องครบ102..horizon; ไม่ resample/pad/truncate
raw text hash ของ Phase C certificate เป็น normalized query identifier บางส่วน จึงต้องมี exact-text/request mapping จริงก่อนใช้
ไม่มีการ infer availability อัตโนมัติจาก w_steps และไม่ใช้ cohort/key เป็น genuine native session โดยไม่มีหลักฐาน

CUSUM ต้องส่ง **saved per-query curve** พร้อม binding เดียวกันและ k/side/fit mean/SD provenance จริง
Phase D max_score/first_alert summaries ไม่พอสร้างค่า Q150/Q200/Q250; งานนี้ไม่เรียก curves()/cusum() เพื่อเติม

## 7. Handoff และ execution gate

ส่ง metadata/sidecars/score files ใน ignored storage พร้อม path ที่อนุญาตให้อ่านและ expected hashes
เก็บ private identities/raw texts/weights/vectors นอก Git; committed fixtures มีแต่ synthetic numeric metadata เท่านั้น
ลำดับ acceptance: validate_manifest ทั้งสองฝั่ง → export_scores/export_prada_trace → align_exports → coverage audit
ยังไม่ fit/calibrate/ประเมิน real streams จน common evidence, native/replay estimand, schedule และ resource gate ได้รับ review
ต้อง calibrate normalization และ joint stream-max thresholds ใหม่แยกตาม profile บน benign cohorts ที่เพียงพอ
ห้าม reuse random-window thresholds หรือเอา missingness/metadata failure ไปนับเป็น benign true negative
