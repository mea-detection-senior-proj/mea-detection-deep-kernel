# Phase F — Matched Traffic Experimental Protocol (แผน ยังไม่ execute)

วันที่ 7 พฤศจิกายน 2026 | `experiment/stream-prada-order`
ใช้คู่กับ [DATA PLAN](PHASE_F_DATA_PLAN_TH.md) และ
[FEASIBILITY](PHASE_F_FEASIBILITY_TH.md)

## 1. คำถามและขอบเขต

Sequential statistic เพิ่มข้อมูลเหนือ length/format และ distance aggregation
ในการตรวจ extraction traffic ที่มี intent provenance หรือไม่ ที่ information
budget และ stream false-alarm operating point เดียวกัน
Phase A–E เป็น development evidence ทั้งหมด ไม่เพิ่ม optimization จากชุดเดิม
ไม่รับรอง novelty/generalization หรือแต่งตั้ง detector ที่ดีที่สุดใน Phase F

Main track: authorized owned/consented traffic บน victim/task/rendering เดียวกัน
Public WildChat เป็น secondary domain-shift sensitivity track ไม่ pool threshold/
FPR กับ main track โดยไม่มี calibration cohorts ของตนเองครบ
MEA pool เป็น source candidate จน license, chronology และ run lineage ผ่าน

## 2. Units, native chronology และ eligibility

Outer unit = connected actor/user–source-document–attack-run-lineage **bundle**
หนึ่ง bundle อาจมีหนึ่ง benign stream และหนึ่ง attack stream ที่ matched กัน
แต่ยังเป็น observation cluster เดียว Shared seed/transcript/query pool/descendant
runs อยู่ bundle เดียว ไม่เพิ่ม n ด้วย reorderings หรือหลาย training methods

Link source-bearing repeated templates/content; generic chat wrapper ที่ใช้ร่วม
ทุกคนเป็น format stratum ไม่ union ทุกคนเข้ากลุ่มเดียวเพียงเพราะมี role header
ถ้า operator/actor เดียวหรือ source corpus ซ้ำเชื่อมทุก run เป็น component ใหญ่
ต้องรายงาน actual n ที่ลดลง ไม่ split graph เพื่อให้ครบ quotas

Primary proposed horizon **256 actual user/victim requests** ต่อ stream;
counter เริ่ม request1 โดยเก็บช่วงต่อเนื่องที่กำหนดไว้ก่อน scoring ไม่ข้าม
requests ที่ไม่ alert/ไม่เข้ากับ matching และไม่เลือก segment จาก detector score
Original PRADA warm-up ไม่เปลี่ยน: first eligible statistic ที่ query102

Native sessions สั้นกว่า102 ไม่ eligible สำหรับ Original PRADA ต้องรายงาน
coverage ไม่บันทึกเป็น true negatives/zero FPR ของ detector
หากไม่มี native windows256 เพียงพอ ให้ NO-GO ของ horizon นี้ หรือเสนอ revision
horizon128 ก่อน scoring ใด ๆ พร้อม recalibration/quotasใหม่ ไม่ลด warm-up,
ต่อ unrelated conversations หรือ padding ให้พอดี

Sessionization สำหรับ prospective owned logs: actor+application/session ID,
idle gapเกิน30นาทีแยก session; run boundary แยกเสมอ ระบุ UTC event ordering
และ dedup ด้วย request IDs ส่วน retries ที่ victim เห็นจริงคงเป็น exposure
ไม่รวมหลาย unrelated conversations แม้เวลาใกล้กัน ถ้า public timestamps/
actor keys ไม่พอ ให้ downgrade provenance ไม่เดา arrival order

Native attack run ที่ attack เริ่ม request1: onset1 และ pre-attack alarmsเป็น
**not applicable/null** ไม่รายงาน zero ว่า prefix control ผ่าน
ถ้ามี genuine benign prelude ให้ freeze true onset จาก run log ก่อน score
การใช้ common prefix110/onset111 ทำได้เฉพาะ prospective controlled session
ที่บันทึกการเปลี่ยน condition จริง เป็น secondary ablation ไม่ใช่ concatenated
native trace และไม่เพิ่ม independent bundles จากการแชร์ prefix

## 3. Traffic matching และ positivity gate

ใช้ actual user-message text ที่ submit (หลัง strip ขอบตาม preprocessing ที่
freeze) เป็น primary BGE query ไม่ปน assistant outputs เป็น query features
เก็บ full victim chat/context-token length แยกเพื่อไม่สับสน latest message กับ
serialized conversation และ freeze system/template revision

Predeclared descriptors: whitespace words, characters, frozen BGE tokenizer
pre-truncation tokens, victim-input tokens, context/role/format structure,
repetition rate และ source/task domain; length bins **1–32,33–128,129–512,
>512 words** เป็น metadata strata ไม่ใช่ label และไม่เลือก bins จาก TPR
คง BGE revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, normalized,
max_length512, no query prefix และ Original upstream state เดิม

Proposed matching acceptance ก่อน scoring:

- exact match domain/task/rendering class และ BGE-truncation-status strata;
  ทั้งสอง labels ต้องมี legitimate long-context, short และ repetitive requests
  ใน support ที่ใช้เปรียบเทียบ ไม่ force family ให้ทำ query format ที่ไม่ faithful
- match whole windows ด้วย length-histogram proportionsต่างกันไม่เกิน0.10
  ต่อ occupied bin, format proportionsต่างกันไม่เกิน0.05, median word/BGE-token
  length ratio อยู่0.9–1.1 และ absolute SMD ของ log-lengthไม่เกิน0.10
  SMD เป็น balance descriptor ของ clustered data ไม่ใช้ query-level p-value
- required **final-test comparison cell** (domain×format×length bin ที่มี
  support ไม่ใช่ทุก family×bin combination) ต้องมีอย่างน้อย10 distinct bundles
  ต่อ label; fit/intake ใช้ตรวจ feasibility ไม่อ้าง performance ต่อ cell
  final attack-family strataต้องอย่างน้อย20 retained bundles ต่อ family
  และ overall quotas ต้องครบหลัง grouping/matching ไม่ใช่ก่อนคัด
- รายงาน retained fraction/coverage; ถ้าต้องทิ้งเกิน20% ต่อ label/frame หรือ
  format/lengthทำนาย label ได้แบบ structural separation ให้ NO-GO หรือจำกัด
  estimand ใหม่ก่อน score ห้ามเปลี่ยน caliper หลังเห็น detection outcomes
- ไม่จัดเรียง/ตัด queryเป็นชิ้นเพื่อทำให้ overlap ผ่าน รายงาน truncated content
  และ label balance ของ truncation แยก ไม่ถือ word count เป็น BGE token count

Balanced designed mixture ไม่ใช่ traffic prevalence ของ deployment ต้องประกาศ
weights/strata ก่อน calibration และรายงาน FPR ใน legitimate long/repetitive
hard negatives แยก ไม่ hide strataที่มี false alarms สูงไว้ใน pooled rate

## 4. Fit / calibration / validation / final-test cohorts

**Planning targets หลัง union/grouping และ matching** ไม่ใช่ observed availability
หรือผล power calculation ที่รับรองว่าจะพบ improvement:

| Split | Outer bundles | Benign streams | Attack streams | ใช้ทำอะไร |
| --- | ---: | ---: | ---: | --- |
| Fit | 20 | 20 | 12 (4ต่อ acquisition family) | nuisance/length-balance metadata; detector nuisance fit benignเท่านั้น |
| Calibration | 100 | 100 | 0 | stream-level threshold ต่อ statistic/observation schedule |
| Validation | 40 | 40 | 30 (10ต่อ family) | preregistered quality/feasibility checks ไม่เลือก best detector |
| Final test | 200 | 200 | 150 (50ต่อ family) | once-only fixed comparisons และ uncertainty |
| รวม | **360** | **360** | **192** | **552 streams แต่360 outer bundles** |

Attack streamsเป็น subsetของ paired bundles ในแต่ละ split ไม่บวกเป็น
independent actor/source units เพิ่ม ครอบ3 acquisition mechanismsที่มี
verified actual query traffic ต่างกัน ไม่เอา shared transcriptมาเติม family quota
Source/user/run components ไม่ทับข้าม splits; common victim คงที่เป็น condition
ไม่ใช่เหตุให้ถือทุก request เป็น independent observation

หากทุก stream256 จะมีสูงสุด **141,312 recorded request events** ในแผนนี้
เป็น arithmetic illustration ไม่ใช่ authorization/budget acquisition ที่ได้รับแล้ว
ต้องเพิ่ม recruitment เท่าที่จำเป็นให้ quotaหลัง matchingครบภายใต้ gateใหม่
ไม่ใช่เปลี่ยน quotaภายหลัง; ยังไม่ยืนยันว่าหา360 independent bundlesได้จริง

Final data manifest/content เก็บแยกสิทธิ์; analystเห็นเพียง locked IDs/counts
ก่อน validation gate ห้ามดู final detector scores เลือก thresholds/parameters
Fit metadataสำหรับ matchingและเทียบ length ใช้ fit/intakeเท่านั้น สุ่ม assign
componentsด้วย seedที่ freeze ก่อน outcomes และ stratify acquisition family/domain

## 5. Fixed methods และ equal information budgets

1. Original Stream PRADA: unchanged minimum distance/Growing Set/three-sigma/
   cumulative Shapiro W และ warm-up ใช้ current threshold recipe จาก calibration
2. Lower-distance CUSUM: k=.5 และ1.0 ที่ประกาศไว้แล้วทั้งคู่ ไม่มี gridเพิ่ม/
   best-k selection; position mean/SD fitจาก20 benign fit cohorts, floor0.01
   accumulationเริ่ม Q102 ตาม definitionเดิม ไม่ resetตาม onsetที่รู้ภายหลัง
3. Non-sequential statistic baseline: negative meanของ observed minimum
   distances Q2..t ณ budget t ไม่มี reset/change recursion
   แต่ minimum distancesขึ้นกับ Growing Set/orderอยู่แล้ว จึงเป็น non-sequential
   **aggregation** บน upstreamเดียวกัน ไม่อ้าง representation order-invariant
4. Length-only negative control: two-sided standardized deviationของ mean
   log1p(words Q1..t) จาก position-specific benign fit mean/SD, floor0.01
   ไม่มี embeddings/labels; สูตรนี้ freezeก่อนข้อมูลใหม่ ไม่เลือกทิศจากผล final

Primary online comparison: ทุก methodใช้ first t requestsเหมือนกัน และตัดสิน
ที่ทุก t=102..256 รวม155 looks; bag statisticคำนวณใหม่จาก prefix ณ t
แม้ monitorซ้ำก็ยังเป็น bag-statistic baseline ไม่ใช่ CUSUM recursion
เก็บ behaviorหลัง alertเพื่อ audit แต่ primary first-alert eventไม่ถูกลบ

รายงานที่ fixed budgets **102,128,192,256** จาก primary paths โดยใช้ threshold
เดียวของ full horizon เพื่อไม่เลือก thresholdที่แต่ละ checkpointแล้วอ้าง online FPR
Secondary checkpoint-only schedule ใช้4 looksเท่ากันทุก methodและ calibration
ใหม่สำหรับ maxเหนือ4 looks; แยก estimand ไม่เลือก scheduleที่ให้ผลดีที่สุด
ไม่เทียบ online medianกับ endpoint-only256แล้วเรียก sequential benefitทันที

หากจะแยก upstream-state order effectจากstatistic effect ให้เพิ่ม frozen-reference-
bank distance ablationใน protocol/resource gateอื่น โดยไม่แก้ Original baseline
Phase F ไม่ implement detector/encoder/reference bank ใหม่

## 6. Stream-level false-alarm calibration และ comparison rules

Primary nominal alpha=.05, horizon256; ต่อ method/scheduleใช้100 benign
calibration stream maxima S และ rank ceil((100+1)×.95)=**96**,
strict score>96th smallest ไม่มี per-query p-value thresholdหรือtail extrapolation
ถ้า scoresไม่ tie จะมี4/100 in-sample exceedances ไม่ใช่5%พอดี
ภายใต้ exchangeability marginal bound=5/101≈4.95%; ไม่อ้าง conditional
guaranteeบน calibrationนี้ หรือจริงเมื่อ user/source/deployment distributionต่างกัน

ขั้นต่ำ n_cal19 ให้ finite thresholdที่5%เท่านั้น ไม่ใช่ sufficient precision
ใช้ planned100เพื่อลด discreteness แต่ยังรายงาน calibration uncertainty
matched nominal alphaไม่เท่ากับ matched actual FPR ต้องแสดง control vectors,
paired FPR differences และ intervalsบน validation/finalแยกกัน

ไม่มี detector selectionบน validation ใช้ fixed comparator setครบและหยุดหาก
data/chronology/invalid-output gates fail ไม่ retuneแล้วใช้ finalsetเดิม
Primary alpha .05เพียงจุดเดียว ไม่เปลี่ยนเป็น20/40%เพื่อให้ powerดูดี
หากทำ descriptive operating curves เพิ่มต้อง predeclare calibration-only
thresholdsและ multiple-comparison reportingก่อน lock ไม่เลือกจาก final outcomes

ยังไม่ออกแบบการทดสอบ superiorityที่มี powerพอจาก Phase E n=3
การอ้าง improvementในอนาคตต้องมี preregistered paired FPR equivalence/non-
inferiority margin, powerและ multiplicity planสำหรับสอง k contrasts ก่อน final
หากยังไม่มีให้รายงาน fixed effect estimates/uncertaintyเท่านั้น ไม่ declare winner
TPRสูงขึ้นพร้อม FPRสูงขึ้นไม่ถือ improvement

## 7. Evaluation: events, uncertainty และ ordering

- FPR: any alarmใน all-benign horizonต่อ outer bundle, exact95% binomial
  intervalเมื่อมีหนึ่ง Bernoulli eventต่อ independent bundleตามสมมติฐาน;
  paired methodsและหลายstreamsในbundleใช้ cluster accounting ไม่เพิ่ม n
- TPR: detected-by-budget/all attack bundles และ at-risk post-onset rate
  แยกกัน; intent-confirmed versus successful-extraction label คนละ outcome
  ยังไม่มี training/fidelityจึง successต้องnull ไม่อ้างโจมตีสำเร็จ
- Pre-attack alarm: first alarmก่อนknown onset; ถ้าalertก่อนonsetให้ ineligible
  สำหรับ first attack detection ไม่เรียกTP Delay=first eligible alert−onset,
  nondetectionเป็นright censoringที่horizon ไม่แทนmissด้วยmean/median detected
- Onsetก่อนwarm-up: รายงาน detector blind period/left warm-up constraint
  ไม่ตั้ง onsetใหม่ที่Q102เพื่อให้ delayสั้น; native onset1ไม่มีprefix denominators
- รายงาน detected delay พร้อมn, unconditional detection-by-budget curves,
  censored survival/descriptive time-to-event และ false alarmsต่อexposure
  elapsed secondsใช้ได้ต่อเมื่อ request-arrival timestampsเชื่อถือได้
- Native chronologyเป็นprimary; random/cluster/interleaveเป็นsecondary offline
  ablationsเฉพาะ acquisitionที่ requestsไม่ขึ้นกับresponsesในอดีต หรือชื่อชัดว่า
  fixed-query replaystatistic ไม่อ้างreordered adaptive runยังfaithful
  reorderingต้องrecompute upstreamstateจากembeddings มิใช่shuffle saveddistances
- Reorderingsเป็นwithin-bundle repeated measurements ใช้paired disagreements/
  cohort summaries ไม่ใช้permutationsเป็นnประชากร ไม่อ้าง invarianceจากearlyFP

Final benign200ที่FP10จะมี exact two-sided95% interval **2.42–9.00%**;
per-family attack50ที่detect25 interval **35.53–64.47%** จึงยังอาจกว้างมาก
Quotasไม่ใช่ power guarantee โดยเฉพาะเมื่อactor/source clustersลดeffective n
การพบzeroFPใน59 independent cohortsให้one-sided95%upper≈4.95% แต่
P(zero | true FPR5%)≈4.85% จึงไม่ใช้59เป็นแผนที่รับรองว่าจะยืนยันtargetได้

## 8. Acquisition GO/NO-GO และ stop

**GO metadata-only**; **NO-GO data/model/attack executionในขณะนี้**
ก่อนเปลี่ยนstageต้องผ่าน license/authorization, declared-versus-actual schema,
chronology/intent/run/source grouping, common support และ quota feasibility
พร้อม separate byte/request/token/time/VRAM gate ตาม feasibility
หากไม่ครบให้รายงานblocked/limited estimand ไม่ optimizeข้อมูลเดิมหรือเติม
independent sessionsที่ไม่มีจริง ไม่แตะmain/merge/rebase/PR/pushอัตโนมัติ
