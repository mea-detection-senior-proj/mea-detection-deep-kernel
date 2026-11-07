# Stream PRADA Phase B — Dataset & Protocol Feasibility

วันที่ 7 พฤศจิกายน 2026 (Asia/Bangkok) | `experiment/stream-prada-order`

**คำตัดสิน:** ข้อมูลเดิมพอสำหรับ exploratory protocol pilot ที่แยก source ตาม
นิยามที่ตรวจได้ แต่ **ไม่พอและไม่สดพอสำหรับ confirmatory final test ที่อ้าง FPR
5%** พบเพิ่มเติมว่า `model_leeching` มีเพียง 30 Wikipedia articles และ Phase A
calibration/test แชร์กัน 29 บทความ จึงต้องแยก passage-disjoint ออกจาก
article-disjoint อย่างชัดเจน

อ่าน [FAILURE_ANALYSIS_TH.md](FAILURE_ANALYSIS_TH.md) และ
[NEXT_PROTOCOL_TH.md](NEXT_PROTOCOL_TH.md) ก่อนทำงาน ใช้ไฟล์เดิมแบบอ่านอย่างเดียว
ไม่มี BGE encoding, detector execution, threshold tuning หรือ full experiment
ไม่เปลี่ยนผล/configs/teammate code/main และไม่ push/merge/rebase/เปิด PR
Remote ของ checkout ยังเป็น `ASippakorn/Deep-Kernel` แม้คำขอระบุ taetaevrh;
ไม่ได้เปลี่ยน remote ใช้ baseline Phase A commit `5d9e859`

## 1. ข้อมูลจริงและระดับ source ที่ตรวจได้

| Dataset | Benign rows → unique normalized queries | Attack rows → unique normalized queries | IDs/source |
| --- | --- | --- | --- |
| model_leeching | 10,062 → **9,900** | 10,062 → **9,923** | IDs เชื่อมสอง labels และจับคู่กับ SQuAD ได้ |
| ME_BERT_boolq_wiki | 9,427 → **9,427** | 1,885 → **1,885** | IDs เป็นชื่อแถวคนละฝั่ง ไม่ใช่ shared source IDs |

ลบ exact normalized duplicates ต่อ label และไม่สร้าง query ใหม่ ไม่พบ
cross-label normalized-text collisions ในสี่ไฟล์นี้ Hash ของ inputs ทั้งสี่อยู่ใน
`diagnostics/phase_b_verified/provenance.json` ทุกไฟล์ตรงกับค่าที่ตรวจไว้

### Passage-level audit

เชื่อม components แบบ transitive ด้วย dataset-namespaced ID, normalized full
query และ normalized source passage โดยใช้กุญแจ text/passage ร่วมกันข้าม
datasets ได้ ไม่จับ `normal-0` กับ `attacker-0` ว่าเป็น source เดียวเพียงเพราะ
เลขแถวเท่ากัน ได้ 1,847 components สำหรับ model_leeching และ 9,805 สำหรับ
BoolQ pair (normal มี 7,921 unique passages; attack มี 1,884)

### Article-level audit

ดาวน์โหลดเฉพาะ official SQuAD v1.1 train/dev เพื่อจับคู่ ID/question/context
กับ article title เก็บ raw lookup นอก Git ที่ `.cache/stream-prada-phase-b`
ขนาดรวมประมาณ 35 MB ทุก model_leeching row ทั้งสองฝั่งจับคู่ได้ครบ
**20,124/20,124 rows** และมาจาก **30 titles** Source grouping เพิ่ม normalized
Wikipedia title เข้า connected components ไม่แยกย่อหน้าคนละ cohort หากอยู่
บทความเดียวกัน จำนวนนี้อ้างอิง title IDs ของ release ไม่ใช่ proof ว่า topics
หรือเนื้อหาทุกบทความมี statistical independence

Official BoolQ ระบุ title เป็น metadata แต่ลิงก์ train.jsonl ของ Google bucket
ตอบ HTTP 403 ในการตรวจครั้งนี้ ไม่เดา title และไม่ bypass access
จับคู่ exact passages กับ official SQuAD ได้เพียง benign **4** และ attack **2**
rows ซึ่งไม่ได้หมายความว่าข้อมูลที่เหลือไม่มีแหล่งที่มา แต่หมายถึง **ยังตรวจ
article identity ไม่ได้** ไม่มีการดาวน์โหลด WikiText ทั้ง corpus เพื่อเดา mapping

Source/license: [SQuAD official](https://rajpurkar.github.io/SQuAD-explorer/),
[BoolQ official README](https://github.com/google-research-datasets/boolean-questions)

## 2. จำนวน cohorts ที่สร้างได้จริง

นิยาม cohort ในตารางคือ outer block ที่ไม่มี query หรือ source component
ถูกใช้ซ้ำข้าม blocks ความยาว benign/pure attack = **256** ส่วน paired block
ใช้ benign control **256** + attack reservoir **128** เพื่อรองรับ mixed ratios
10%, 25%, 50% และ share prefix 110 ภายใน block ได้

| Dataset / grouping | Pure benign cohorts | Pure attack cohorts (256) | Paired control + mixed-reservoir blocks | ระดับการรับรอง |
| --- | ---: | ---: | ---: | --- |
| model_leeching / passage | **38** | **38** | **38** | มี allocation และตรง capacity upper bound |
| model_leeching / mapped article | **23** | **23** | **23** | มี allocation; integer solver ตัด 24 ทิ้ง |
| BoolQ pair / passage | **36** | **7** | **14** | มี allocation และตรง capacity upper bound |
| BoolQ pair / mapped article เท่านั้น | **0** | **0** | **0** | mapped rows ไม่พอ; ไม่ใช่ข้อสรุปว่าจริง ๆ สร้างไม่ได้ |

**แต่ละคอลัมน์เป็นทางเลือกใช้ข้อมูลเดิม ไม่ใช่จำนวนที่บวกใช้พร้อมกันได้**
Benign/attack ใน paired block จงใจ matched source ภายใน block ไม่ใช่สอง
observations อิสระ ส่วน source groups ของ calibration กับ evaluation blocks
จะไม่แชร์กันใน certificates ของแต่ละแผน

นับ 10,062/256 แล้วปัดลงเป็น 39 เป็นเพียง raw row bound เดิม หลัง dedup
model benign เหลือ 9,900 จึงได้ passage-level maximum 38 ส่วน article-level
มีบทความใหญ่เกิน 256: อนุญาตใช้เพียงหนึ่ง cohort และทิ้งส่วนเกิน ไม่ตัด
บทความเดียวเป็นหลาย cohorts เพื่อเพิ่ม n

Allocator แบบ subset-sum สร้างได้ 23 article blocks และ capacity relaxation
เดิมให้ bound 24 จึงตรวจ feasibility ของ 24 ด้วย bounded mixed-integer solver
โดยให้หนึ่ง source group อยู่ได้ไม่เกินหนึ่ง cohort ทั้งสาม cases ถูกตัดว่า
infeasible จึงได้ optimum **23 ภายใต้ grouping/การทิ้งส่วนเกินนี้** ไม่ใช่เพียง
guess จากจำนวนแถว หลักฐานใน `article_optimality.json` ใช้เวลา solver รวม
ประมาณ 0.04 วินาที ไม่เกี่ยวกับ detector scores

Group disjointness เป็น operational independence guard ไม่รับรองว่าเป็น
independent API users/sessions หรือ independent semantic topics

## 3. ประวัติการใช้ข้อมูลและ source overlap ที่สำคัญ

เทียบ Phase A pool-query hashes กลับไปยัง official article titles ได้:

| รายการ | จำนวน Wikipedia titles |
| --- | ---: |
| model_leeching ทั้งชุด | 30 |
| Phase A calibration pool | 29 |
| Phase A benign test pool | 30 |
| Calibration ∩ test | **29** |
| Calibration ∪ test | **30** |

ข้อสรุป Phase A ว่า source groups ไม่ทับกันถูกต้องตาม **passage definition**
เดิม แต่ไม่ใช่ article-held-out split การพบ article overlap ไม่ได้พิสูจน์ว่านี่
คือ causal root cause ของ FPR 17%; เป็นข้อจำกัดของ independence claim

ถ้าตัดเฉพาะ components ที่เคยใช้ใน Phase A ออก model ยังมี 1,139 unexposed
passage groups ที่สร้างได้ 23 passage blocks แต่ **ไม่มี unexposed article
เหลือเลย** เพราะทั้ง 30 articles ถูกใช้ไปแล้ว ห้ามเรียกส่วนเหลือระดับ passage
ว่า article-unseen confirmation

BoolQ ไม่ถูกใช้ใน Stream PRADA Phase A นี้ แต่เคยมีผล MMD และ KS ใน checkout
`llm-mea` (ตรวจรายงาน PHASE2B/PHASE6A ปัจจุบันแล้ว) ทั้งสอง datasets จึงเป็น
development/reused research data ไม่ใช่ untouched final-test source
แค่เปลี่ยน seed หรือแบ่งใหม่ไม่ทำให้ประวัติการเห็นข้อมูลหายไป

การเชื่อมด้วย exact keys พบ 0 components ที่รวมสอง datasets ใน inputs นี้
แต่ **ห้ามตีความเป็น 0 shared Wikipedia articles** เพราะ BoolQ ส่วนใหญ่ยังไม่มี
article mapping จึงยังรับรอง cross-dataset article disjointness ไม่ได้

## 4. ความเพียงพอสำหรับ calibration / validation / final test

สร้าง manifests ที่ไม่มี group/query ซ้ำข้าม splits ได้จริงดังนี้ แต่ทุกแผน
ด้านล่างยังเป็น exploratory/development allocation ไม่ใช่ fresh confirmation:

| แผน | Calibration benign blocks | Validation paired blocks | Final/evaluation paired blocks | สถานะ |
| --- | ---: | ---: | ---: | --- |
| model / article | **12** | **3** | **8** | ทำได้จริง; ตัวเลือกหลักสำหรับ bounded pilot |
| model / passage | 20 | 4 | 14 | ทำได้จริง แต่แบ่งบทความข้าม splits ได้ จึงเป็น sensitivity reference |
| BoolQ / passage | 20 | 4 | 10 | ทำได้จริง แต่ article provenance ยังเป็น blocker |

Certificates พร้อม query hashes/group IDs ของแผนทั้งสาม commit ไว้ใน
`diagnostics/phase_b_plan/` ส่วน full counterfactual capacity certificates และ
full group index เก็บ local/ignored เพื่อไม่เพิ่ม large artifacts สามารถสร้าง
ใหม่ได้จาก inputs/hashes เดิมด้วย runner CPU-only ประมาณ **4.22 วินาที**
`artifact_hashes.json` ของ local run จงใจรวมไฟล์เหล่านี้ด้วย ไม่ใช่รายการว่า
ทุกไฟล์อยู่ใน Git; tracked deliverables มี manifest แยก

### ข้อจำกัด FPR และ uncertainty

| n ของ independent evaluation cohorts | ถ้า FP = 0: one-sided exact 95% upper FPR |
| --- | ---: |
| 8 | **31.23%** |
| 10 | **25.89%** |
| 14 | **19.26%** |
| 20 | **13.91%** |
| 59 | **4.95%** |
| 200 | **1.49%** |

คำนวณ `1 - 0.05^(1/n)` ภายใต้ independent identically distributed Bernoulli
cohorts หากมี dependence/population mismatch ตารางนี้ไม่ใช่ coverage guarantee
สำหรับ traffic จริง Zero FP ใน 8 cohorts จึงไม่ยืนยัน FPR ≤ 5% ต้องมีอย่างน้อย
**59 independent final benign cohorts และไม่พบ FP เลย** จึงได้ upper bound
ต่ำกว่า 5% ตามสมมติฐานนี้ ไม่ใช่บอกว่า 59 observations ทำให้ estimate 5% แม่นยำ

Calibration n=12 ใช้ linear P95 ระหว่าง order statistics ท้ายชุด และเมื่อคะแนน
ไม่ tie มักเหลือ 1 exceedance = 8.33% ไม่ใช่ 5% พอดี P95 จาก n เล็กจึงมี tail
uncertainty สูง ไม่มีการรัน calibration หรือเลือก threshold ใหม่ใน Phase B
และ permutations 1,000 ครั้งไม่เพิ่ม n ระดับ independent cohorts

เป้าหมาย 200 calibration + 200 final benign cohorts ยาว 256 ต้องมีอย่างน้อย
102,400 unique benign queries ก่อนนับ validation/group exclusions ทั้งสอง
datasets รวมมี unique benign เพียง 19,327 และห้าม pool domains อัตโนมัติ
จึงไม่มีทางรับรองเป้าหมายดังกล่าวจากข้อมูลที่มี

## 5. ใช้สอง datasets อย่างไรโดยไม่ปะปน sources

1. ใช้ model_leeching เป็น primary **article-grouped exploratory pilot** ตาม
   allocation 12/3/8; เก็บ prefix 110 เดียวกันข้าม ratios/orderings ภายใน block
   แต่ให้แต่ละ block ใช้คนละ source groups และ prefix ของตนเอง
2. ใช้ BoolQ เป็น secondary **passage-grouped sensitivity study** ได้ตามแผน
   20/4/10 เมื่ออธิบายขอบเขตนี้ชัด แต่ถ้าต้องการ strict article/source validation
   ให้หยุดจนกู้ original BoolQ/WikiText article mappings และ regroup ใหม่
3. ไม่ผสม model question-only benign กับ BoolQ passage+question benign เป็น
   distribution เดียว ไม่ใช้ common threshold จากการ pool โดยไม่มีแผนรองรับ
   หากศึกษาการ transfer ข้าม dataset ต้องตั้งเป็น domain-shift experiment
   ต่างหากและรายงาน FPR ของแต่ละ domain
4. ถ้าจะใช้ร่วมกัน ต้องตรวจ global article IDs/aliases/exact text/context ก่อน
   แบ่ง split และไม่อ้างว่าชื่อ dataset ต่างกันทำให้ sources เป็นอิสระ

## 6. Dataset เดิมเทียบกับเพิ่มข้อมูลใหม่: source และ license

ตรวจ primary source pages ณ 7 พฤศจิกายน 2026 เก็บรายการไว้ใน
[PHASE_B_SOURCES.json](PHASE_B_SOURCES.json) ไม่มีการดาวน์โหลด conversation
corpus หรือ attack benchmark ใหม่ ไม่มีการยอมรับข้อตกลงแทนผู้ใช้

| ทางเลือก | ประโยชน์ | Source / license ที่ตรวจ | ข้อจำกัดและสถานะ |
| --- | --- | --- | --- |
| สอง processed datasets เดิม | ใช้ได้ทันที, มี file hashes | [Artifact card](https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data): mixed-source research artifact; คง terms ของต้นฉบับ | ไม่ใช่ blanket MIT data license; source-group/freshness จำกัด |
| เพิ่ม SQuAD บทความที่ไม่เคยใช้ | มี article/ID/context provenance | [Official SQuAD](https://rajpurkar.github.io/SQuAD-explorer/): CC BY-SA 4.0 | QA questions เป็น proxy ไม่ใช่ chronological API traffic; ไม่เพิ่ม actual attack queries โดยอัตโนมัติ |
| กู้ BoolQ/WikiText provenance | เพิ่มการแยกระดับบทความของข้อมูลเดิม | [BoolQ README](https://github.com/google-research-datasets/boolean-questions): CC BY-SA 3.0; [WikiText card](https://huggingface.co/datasets/Salesforce/wikitext) มี license discrepancy | BoolQ title file 403; WikiText header ระบุ 3.0/GFDL แต่ narrative 4.0 ต้อง resolve exact release/notices ก่อน redistribution |
| เพิ่ม real benign LLM sessions จาก WildChat | มี user conversations/time metadata เหมาะกับ session study กว่า QA proxy | [WildChat official card](https://huggingface.co/datasets/allenai/WildChat-1M): ODC-BY; [license text](https://opendatacommons.org/licenses/by/1-0/) | ยังไม่ audit n/duplicates/benign contamination; database license ไม่ resolve สิทธิ์ content ทุกส่วน ต้อง group user/time/content ไม่ใช่ conversation_hash อย่างเดียว |
| เพิ่ม attack-query collections จาก MEA-Bench | มี query pools/manifests หลาย attack families | [Official repository](https://github.com/sliu11-byte/MEA-Bench) code/docs MIT; [data card](https://huggingface.co/datasets/watermarkproject/lord-mea-benchmark) | ยังไม่พบ blanket license ของ query data; source/license/overlap audit ต้องผ่านก่อนนับเป็น available cohorts |
| LMSYS-Chat-1M เป็นอีกตัวเลือก | real LLM conversations | [Official card/license agreement](https://huggingface.co/datasets/lmsys/lmsys-chat-1m): custom agreement | มีข้อจำกัด transfer/redistribution และ model-output terms; workflow หนักกว่า ไม่ได้เข้าถึง corpus |

อย่านับ row counts ที่ผู้เผยแพร่โฆษณาเป็น independent cohorts ที่พร้อมใช้
ต้องตรวจ operational source/user/session grouping, duplicates, exposure,
license และ clean benign/actual attack labels ก่อน การเพิ่ม benign อย่างเดียว
ไม่แก้ independent attack bottleneck และการเพิ่ม attack ต่าง domain อย่างเดียว
อาจทำให้ detector เรียนรู้ source/format แทน extraction behavior

## 7. การตัดสินใจและแผนถัดไป

**Go เฉพาะ bounded exploratory protocol pilot:** model article-grouped 12/3/8
พร้อม uncertainty กว้าง และไม่อ้าง final confirmation
**No-go สำหรับ confirmatory FPR≤5% claim บนข้อมูลเดิม**
**Hold สำหรับ BoolQ strict article-disjoint evaluation** จน provenance ครบ

รายละเอียดลำดับงาน/endpoint/resource gates อยู่ใน
[PHASE_C_PLAN_TH.md](PHASE_C_PLAN_TH.md) เป็นแผนเท่านั้น ไม่ใช่ experiment
config ที่ได้รับการรัน ไม่เปลี่ยน detector/warm-up/P95 rule

### การทำซ้ำ

ใช้ environment `senior` เดิม ต้องมี processed inputs เดิมและ official SQuAD
lookup สองไฟล์ใน cache ตาม URLs/SHA256 ใน `phase_b_feasibility.py` ไม่มี hidden
network/model call ใน runner และไม่ overwrite output directory ที่มีอยู่

```powershell
conda run --no-capture-output -n senior python stream_prada_order/phase_b_feasibility.py --output stream_prada_order/diagnostics/new_phase_b
conda run --no-capture-output -n senior python stream_prada_order/phase_b_optimality.py --audit stream_prada_order/diagnostics/new_phase_b --output stream_prada_order/diagnostics/new_phase_b/article_optimality.json
conda run --no-capture-output -n senior python stream_prada_order/phase_b_plan.py --audit stream_prada_order/diagnostics/new_phase_b --output stream_prada_order/diagnostics/new_phase_b_plan
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests -v
```

Tests ใหม่ 9 รายการและ tests เดิม 18 รวม **27 ผ่าน** มี tests ป้องกันการแบ่ง
source ใหญ่เป็นหลาย cohorts, cross-split reuse, wrong sizes, parser/provenance,
exact subset construction, unknown article certification และ binomial bound
รวม regression สำหรับ original quote ใน SQuAD context และ integer proof fixture

Initial parser เคยตัด quote ปลาย context เกิน outer wrapper จน source match
fail จึงหยุดก่อนนับ cohorts แก้ด้วย failing test และเก็บ failed attempt ไว้ใน
`diagnostics/phase_b/failure.json` รอบสำเร็จคือ `phase_b_verified` ข้อมูลเก่า
และโค้ด Phase A ไม่ถูกแก้ไข ไม่มีการฝืน mapping หรือสร้าง controls ทดแทน
