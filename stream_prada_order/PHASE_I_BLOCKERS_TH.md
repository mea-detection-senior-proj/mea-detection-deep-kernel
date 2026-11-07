# Phase I — Blockers และ exact next execution requirements

อ่านคู่กับ [PHASE_I_READINESS_TH.md](PHASE_I_READINESS_TH.md),
[PHASE_H_READINESS_TH.md](PHASE_H_READINESS_TH.md) และ
[PHASE_G_NEXT_PILOT_TH.md](PHASE_G_NEXT_PILOT_TH.md)

**ปัจจุบัน NO-GO สำหรับ real inference pilot**
Phase I เป็น offline preflight ไม่ใช่สิทธิ์ download/load/query และไม่ได้รับรอง
native CUDA/BF16/generation compatibilityจากเพียง CPU importsที่ผ่าน

## 1. อะไรปิดได้แล้ว / อะไรยังไม่ผ่าน

| ID | สถานะจากหลักฐานจริง | สิ่งที่ต้องทำถัดไป |
| --- | --- | --- |
| R01 clean/frozen checkout |ผ่านบน H8d32d46; G/H frozen filesตรงทุกhash, mainเดิม |หลัง Phase I commitและก่อนpilotตรวจ clean HEADซ้ำ; bind collector_revisionกับ HEADจริง |
| R02 package/dependency/imports |senior versionsตรงlock, pip check exit0, CPU class importsผ่าน, CUDAไม่ initialized |ไม่ต้องinstall/updateเพื่อแก้ปัญหาที่ไม่พบ; freezeenvironmentเดิม |
| R03 GPU/RAM/disk metadata |ผ่านnumeric preload gatesเฉพาะsnapshotเวลาตรวจ |วัดใหม่ก่อนstartและmonitorระหว่างrun ไม่ใช้free VRAMเก่ารับรอง |
| B01 exact local model snapshot |ไม่พบใน configured cache; ไม่มีalternate locationที่supplied |อนุมัติ acquisitionตาม exactplanหรือระบุlocal snapshotที่มีอยู่; ผ่านครบ8size/hashก่อนload |
| B02 private storage/privacy |มีเพียงignored technical-preflight output; ไม่ใช่ approvedpilot store/ACL |จัด dedicatedstoreใหม่/ACL/retention/backup/read-onlysnapshot/key management และ reviewหลักฐาน |
| B03 real grant/query/source records |ยังไม่มี supplied/validated records; ไม่ค้นprivate approvalsเอง |operatorอนุมัติscopeและจัดmanifest/queryplan/evidence/grantตามข้อ2 |
| B04 native runtime/kernel/load |unverified; Phase Iไม่executeGPU kernels/weights/generate |หลัง B01–03ครบต้องอนุมัติtinyprobe/cachedload/<=4benignrequestsภายในgateเดียวกัน |

ไม่ได้สรุปว่าไม่มีโมเดลหรือapprovalอยู่ที่อื่นบนเครื่อง; ตรวจเพียงlocationsที่ระบุ
ไม่มี hash mismatchที่พบในlocalweights เพราะไม่มีsnapshotให้hash

## 2. Operator records และ storage setupที่ยังต้องมี

1. **Acquisition approvalแยกจากinference:** ยืนยัน model/revision8file list,
   source/redirect allowlist, destination, 8GiBstorage/9GiBfree, <=1,200s,
   <=8logicalGETs/retry0/<=32HTTPtransactions/wirecap3,115,744,227bytes
   ไม่ใช้ H execution grantเพื่อเปิด downloader และไม่โหลดweightsหลังdownloadเอง
2. **Actual benign requests:** operator-owned legitimate work1native session,
   planned1–4requestsตาม chronologyเดิม ไม่มีprivateparticipant trafficหรือfake
   sessions; source/task/license/provenance referencesและquery hashesจริง
   HMAC actor/native-session keysกับsecretนอกGit ไม่ใช้ numeric test fixturesแทน
3. **Run manifest:** traffic-manifest-v1, traffic_kind=real, label=benign,
   split=development, acquisition=null, victim/tokenizerexactrevision,
   collector_revision=clean HEADที่จะexecute, source/task allowlists, actual
   operator authorization evidence reference และ budgetsที่ไม่เกินHprofile
4. **Ordered plan:** qwen-query-plan-v1, run/session/native-key IDsตรงmanifest,
   ordered request IDs, exact latest-query hashes, document IDs/task/formatครบ
   ไม่เปลี่ยนquery/orderหรือเลือกqueryถัดไปจากresponses
5. **Private evidence:** ไฟล์ <sha256>.private สำหรับ operator_authorization,
   model_license, source_authorization และ privacy_review ภายใต้explicitevidence
   root; คนที่มีอำนาจต้องตรวจเนื้อหา ไม่ถือSHAรูปแบบถูกต้องเป็นconsent/signature
6. **Execution grant:** qwen-execution-grant-v1, purpose=four_request_benign_readiness,
   traffic_kind=real, execution_authorized=true พร้อมissued/expires UTCอายุ<=24h,
   exact limitsจากprofile และ bindings ของcode/profile/snapshot/environment/
   manifest/queryplan ตัวgrantมีexpected SHAส่งโดยoperatorแยก
7. **Private folders:** เสนอ approvals/<pilot-id>/ กับ evidence/ ใต้ ignored
   traffic_local; pilot storeต้องใหม่/ว่าง เช่น pilots/<run-id>/ ไม่ใช้ technical
   preflightdirectoryหรือrecovered storeซ้ำ Snapshot finalมี8approvedfilesเท่านั้น
   ตั้ง Windows ACL, retention/deletion authority, backup/encryptionตามreview
   และread-only/integritycontrolsป้องกันsnapshotเปลี่ยนระหว่างhashกับload
8. **Grant registry:** traffic_local/execution_grants/ ต้องprotected และมีone-shot
   accounting ห้ามลบclaims/copyregistryเพื่อresetbudget Grantที่claimedแล้วต้องไม่
   reuseแม้workerยังไม่ถึงinference; failureต้องมีoperatorตัดสินใจ/grantใหม่

Phase I ไม่สร้างหรือแต่งเนื้อหา approvals, ไม่แก้ACL และไม่อ่านprivatequery/
participant logsเพื่อเติมplan การขาดsuppliedrecordsเป็นblocker ไม่ใช่เหตุให้เดาintent

## 3. Bounded four-request procedure — หลังอนุมัติเท่านั้น

1. **Offline preflightก่อนเริ่ม:** clean experiment branch/mainเดิม, manifests/
   source/model/tokenizer/template/environment/hash bindingsครบ, H code digest
   ตรง frozen version, actual8snapshotfilesผ่าน byte hashes โหลดweights0ในstepนี้
   ถ้าใช้alternatepath ส่ง --snapshot ชัดเจนให้ H readiness/adapter
2. **Review records/resources:** ตรวจexplicitgrant/evidence/queryplan/private
   store; H readinessอาจเป็นSTATIC_READY_RUNTIME_UNVERIFIED ซึ่งยังไม่พิสูจน์
   CUDA/model execution ต้องมีseparateoperatorauthorizationสำหรับขั้นต่อไป
3. **Authorized library entryเท่านั้น:** RuntimeStore→LocalQwenAdapter→
   RuntimeCollector ตาม H implementation พร้อม explicitexecutionflag+validgrant
   ไม่ใช้ backend/supervisorinternalsข้ามadmission path ไม่มีinference CLIใน I
4. **Contained native start:** one-shotclaim/worker, Job Objectattachก่อนboot,
   deadline120sเริ่มจากworkerlaunch ครอบ rehash/import/tinyCUDA-BF16probe/
   cachedload/inference/logging/normalclose Tinyprobeต้องผ่านก่อนweights;
   import/kernel/loadfailให้หยุดตามstage ไม่รับqueryเพื่อทดแทน
5. **Submitplannedbenignrequestsเท่านั้น:** 1native session, <=4logicalrequests/
   dispatchintentionsรวมrun, oneattempt/request, retry0; preserveactualrequest/
   response chronologyและfullrenderedinput/outputIDreceiptsในprivate storage
6. **Audit/accept:** G journal+H receiptintegrity, exactusage, sessionboundaries,
   no unknown/clock anomaly/invalid response, approvedplannedrequestsครบ และ
   normalclose/loggingเสร็จภายในdeadlineจึงผ่าน instrumentation criterion

## 4. Frozen execution cap และ stop

| Resource/behavior | Cap |
| --- | --- |
| Victim |Qwen2.5-1.5B-Instruct model/tokenizer989aa7980e4cf806f80c7fef2b1adb7bc71aa306 |
| Runtime |BF16, CUDA0/eager, batch1, greedy/beams1, single-turn frozen system/chat template; no offload/quantization/sampling |
| Requests |<=4, one native session, attempts1/request, retry0 |
| Tokens |input<=2048/outputรวมEOS<=128 ต่อrequest; totals<=8192/512 |
| Bytes |query<=64KiB, decodedresponse<=16KiB/request |
| Native run |<=120sรวมcachedload+inference+normal logging/close; ไม่รวมacquisitionซึ่งต้องอนุมัติแยก |
| RAM |available>=8GiBก่อน/ระหว่างrun; Windowsjob aggregate committed cap8GiB |
| GPU |preloaddriver-free>=6GiB; ownallocator/peakreserved<=5.5GiB; running sampled globalfree>=512MiB |
| Disk |cache<=8GiB; pilotdiskfree>=1GiBพร้อมheadroom; logslogical<=4MiB/physicalfile-sizes<=20MiB |
| External work |download/externalvictimAPI/attacks/students/training/participants =0ในpilot |

Resourcevaluesเปลี่ยนได้; allocator capไม่รวมทุกdriverallocation และperiodic
GPU/diskguardsไม่ใช่OS-wideperfectquota ต้องใช้dedicatedresourcesและหยุดเมื่อguardfail
ห้ามretune/quantize/offload/เพิ่มtimeoutเพียงเพื่อให้ผ่านโดยไม่มีprotocol/approvalใหม่

Snapshot/hash/source/approval/branch/env mismatch, timeout/OOM/disk/token cap,
partial/invalidoutput หรือunknown delivery ให้หยุดทั้งrunและรักษาหลักฐาน/claims
ไม่resendเมื่อไม่ทราบว่าvictimรับงานหรือไม่; outputusageที่ไม่ทราบเป็นnull
Recoveryหลังdeadlineทำได้เพื่อเก็บfailure แต่ไม่เรียกrunนั้นว่าsuccessใน120s
DurableHresultแต่Gcommitไม่ครบต้องรักษาunknownตามrecovery ไม่promoteเงียบ ๆ

**4 requestsไม่ถึง Original PRADA Q102** จึงไม่ใช่detector experiment ไม่รายงาน
FPR/TPR/delay/generalization หรืออ้างhorizon256/independent cohortsจากpilotนี้
ถ้าขยายdataset/acquisition/attack/full experiment ต้องมีprotocol+resourcegateใหม่

Next actionที่เสนอคือ **อนุมัติsnapshot acquisitionหรือระบุexistinglocalpath**
ตามexactplan แล้วตรวจhash/recordsก่อนขอเปิดpilot ไม่มีการdownload/pushหรือ
เปิดstageถัดไปจากรายงานนี้โดยอัตโนมัติ
