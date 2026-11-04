# ผลทดลอง Deep MMD: 3 datasets

| Method | Dataset | Seed | Window | FPR | TPR 5% | TPR 10% |
|---|---|---:|---:|---:|---:|---:|
| RBF | model_leeching | 1 | 250 | 0% | 2% | 51% |
| Multi-RBF | model_leeching | 1 | 250 | 0% | 2% | 71% |
| Deep Kernel | model_leeching | 1 | 250 | 0% | 40% | 100% |
| RBF | model_leeching | 1 | 500 | 0% | 4% | 99% |
| Multi-RBF | model_leeching | 1 | 500 | 0% | 5% | 99% |
| Deep Kernel | model_leeching | 1 | 500 | 0% | 91% | 100% |
| RBF | model_leeching | 20 | 250 | 0% | 5% | 85% |
| Multi-RBF | model_leeching | 20 | 250 | 0% | 5% | 94% |
| Deep Kernel | model_leeching | 20 | 250 | 0% | 74% | 100% |
| RBF | model_leeching | 20 | 500 | 1% | 5% | 100% |
| Multi-RBF | model_leeching | 20 | 500 | 1% | 7% | 100% |
| Deep Kernel | model_leeching | 20 | 500 | 1% | 99% | 100% |
| RBF | model_leeching | 42 | 250 | 18% | 37% | 100% |
| Multi-RBF | model_leeching | 42 | 250 | 23% | 48% | 100% |
| Deep Kernel | model_leeching | 42 | 250 | 24% | 95% | 100% |
| RBF | model_leeching | 42 | 500 | 21% | 85% | 100% |
| Multi-RBF | model_leeching | 42 | 500 | 28% | 92% | 100% |
| Deep Kernel | model_leeching | 42 | 500 | 35% | 100% | 100% |
| RBF | Meaeq_SST-2 | 1 | 250 | 7% | 19% | 88% |
| Multi-RBF | Meaeq_SST-2 | 1 | 250 | 8% | 20% | 89% |
| Deep Kernel | Meaeq_SST-2 | 1 | 250 | 0% | 41% | 99% |
| RBF | Meaeq_SST-2 | 1 | 500 | 4% | 41% | 100% |
| Multi-RBF | Meaeq_SST-2 | 1 | 500 | 5% | 41% | 100% |
| Deep Kernel | Meaeq_SST-2 | 1 | 500 | 0% | 83% | 100% |
| RBF | Meaeq_SST-2 | 20 | 250 | 5% | 27% | 92% |
| Multi-RBF | Meaeq_SST-2 | 20 | 250 | 5% | 22% | 88% |
| Deep Kernel | Meaeq_SST-2 | 20 | 250 | 4% | 69% | 100% |
| RBF | Meaeq_SST-2 | 20 | 500 | 6% | 70% | 100% |
| Multi-RBF | Meaeq_SST-2 | 20 | 500 | 5% | 68% | 100% |
| Deep Kernel | Meaeq_SST-2 | 20 | 500 | 5% | 100% | 100% |
| RBF | Meaeq_SST-2 | 42 | 250 | 5% | 8% | 70% |
| Multi-RBF | Meaeq_SST-2 | 42 | 250 | 5% | 8% | 69% |
| Deep Kernel | Meaeq_SST-2 | 42 | 250 | 8% | 36% | 100% |
| RBF | Meaeq_SST-2 | 42 | 500 | 1% | 14% | 99% |
| Multi-RBF | Meaeq_SST-2 | 42 | 500 | 1% | 12% | 98% |
| Deep Kernel | Meaeq_SST-2 | 42 | 500 | 1% | 77% | 100% |
| RBF | ME_BERT_sst2_wiki | 1 | 250 | 6% | 11% | 64% |
| Multi-RBF | ME_BERT_sst2_wiki | 1 | 250 | 7% | 11% | 64% |
| Deep Kernel | ME_BERT_sst2_wiki | 1 | 250 | 7% | 29% | 90% |
| RBF | ME_BERT_sst2_wiki | 1 | 500 | 2% | 21% | 99% |
| Multi-RBF | ME_BERT_sst2_wiki | 1 | 500 | 2% | 17% | 99% |
| Deep Kernel | ME_BERT_sst2_wiki | 1 | 500 | 2% | 38% | 100% |
| RBF | ME_BERT_sst2_wiki | 20 | 250 | 4% | 13% | 62% |
| Multi-RBF | ME_BERT_sst2_wiki | 20 | 250 | 4% | 13% | 58% |
| Deep Kernel | ME_BERT_sst2_wiki | 20 | 250 | 3% | 21% | 95% |
| RBF | ME_BERT_sst2_wiki | 20 | 500 | 1% | 23% | 97% |
| Multi-RBF | ME_BERT_sst2_wiki | 20 | 500 | 2% | 20% | 95% |
| Deep Kernel | ME_BERT_sst2_wiki | 20 | 500 | 3% | 53% | 100% |
| RBF | ME_BERT_sst2_wiki | 42 | 250 | 6% | 13% | 75% |
| Multi-RBF | ME_BERT_sst2_wiki | 42 | 250 | 5% | 13% | 64% |
| Deep Kernel | ME_BERT_sst2_wiki | 42 | 250 | 6% | 30% | 99% |
| RBF | ME_BERT_sst2_wiki | 42 | 500 | 8% | 27% | 99% |
| Multi-RBF | ME_BERT_sst2_wiki | 42 | 500 | 7% | 24% | 99% |
| Deep Kernel | ME_BERT_sst2_wiki | 42 | 500 | 3% | 69% | 100% |

## ค่าเฉลี่ยข้าม seeds 1, 20, 42

| Method | Dataset | Window | FPR | TPR 5% | TPR 10% |
|---|---|---:|---:|---:|---:|
| RBF | model_leeching | 250 | 6.0% | 14.7% | 78.7% |
| Multi-RBF | model_leeching | 250 | 7.7% | 18.3% | 88.3% |
| Deep Kernel | model_leeching | 250 | 8.0% | 69.7% | 100.0% |
| RBF | model_leeching | 500 | 7.3% | 31.3% | 99.7% |
| Multi-RBF | model_leeching | 500 | 9.7% | 34.7% | 99.7% |
| Deep Kernel | model_leeching | 500 | 12.0% | 96.7% | 100.0% |
| RBF | Meaeq_SST-2 | 250 | 5.7% | 18.0% | 83.3% |
| Multi-RBF | Meaeq_SST-2 | 250 | 6.0% | 16.7% | 82.0% |
| Deep Kernel | Meaeq_SST-2 | 250 | 4.0% | 48.7% | 99.7% |
| RBF | Meaeq_SST-2 | 500 | 3.7% | 41.7% | 99.7% |
| Multi-RBF | Meaeq_SST-2 | 500 | 3.7% | 40.3% | 99.3% |
| Deep Kernel | Meaeq_SST-2 | 500 | 2.0% | 86.7% | 100.0% |
| RBF | ME_BERT_sst2_wiki | 250 | 5.3% | 12.3% | 67.0% |
| Multi-RBF | ME_BERT_sst2_wiki | 250 | 5.3% | 12.3% | 62.0% |
| Deep Kernel | ME_BERT_sst2_wiki | 250 | 5.3% | 26.7% | 94.7% |
| RBF | ME_BERT_sst2_wiki | 500 | 3.7% | 23.7% | 98.3% |
| Multi-RBF | ME_BERT_sst2_wiki | 500 | 3.7% | 20.3% | 97.7% |
| Deep Kernel | ME_BERT_sst2_wiki | 500 | 2.7% | 53.3% | 100.0% |

## เงื่อนไขและข้อจำกัด

- ฝึกและประเมินแยกแต่ละ dataset; ไม่รวมข้อมูลและไม่ใช่ unseen-family evaluation
- ตรึง BGE-small; 20 reference repeats ทั้ง calibration/test; 200 calibration windows; 100 test windows ต่อเงื่อนไข
- ฝึก 20 epochs, 8 windows/epoch, train window 100, attack 10%; เลือกจาก 32 fixed validation windows
- แบ่งกลุ่ม 40/20/20/20 เป็น train/validation/calibration/test; thresholds ใช้ percentile 95 ของ benign calibration แยกวิธี
- model_leeching แบ่งตาม ID/ข้อความ/attack context; สอง dataset เพิ่มเติมแบ่งตาม ID/ข้อความ เนื่องจากไม่มี source-passage identifiers
- ID ของสองชุดเพิ่มเป็น synthetic row IDs จึงไม่ยืนยัน source independence หรือกัน paraphrases ได้
- สองชุด SST-2 มี benign normalized texts ซ้ำข้าม dataset 9,629 ข้อความ จึงไม่ใช่หลักฐานจาก benign sources ที่อิสระกัน
- หน้าต่างใช้ queries ซ้ำข้ามหน้าต่างได้; ผลเป็นสถิติเชิงพรรณนา; ไม่อ้างความมีนัยสำคัญ
- TPR ต้องอ่านคู่ FPR; ไม่สรุปว่าดีกว่าที่ FPR เท่ากันเมื่อ FPR จริงต่างกัน
- Window 250 ที่ระบุ attack 5% ใช้จริง 12/250 = 4.8%
- ไม่ใช้ test เลือก checkpoint หรือปรับ threshold; Deep Kernel ใช้ attack labels ฝึก ส่วน fixed kernels ไม่ใช้
- Objective เป็น exploratory signal-to-noise proxy; ความต่างความยาว/รูปแบบยังเป็นข้อจำกัดของข้อมูล

## รายงานแยก dataset

- [model_leeching](outputs/main_model_leeching_repeats20/REPORT.md)
- [Meaeq_SST-2](outputs/main_Meaeq_SST-2_repeats20/REPORT.md)
- [ME_BERT_sst2_wiki](outputs/main_ME_BERT_sst2_wiki_repeats20/REPORT.md)

แหล่งข้อมูล: [Hugging Face](https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data)
เวอร์ชันและ SHA256 ของไฟล์ที่ดาวน์โหลด: ADDITIONAL_DATA_PROVENANCE.json; ผลตรวจการแบ่งข้อมูล: ADDITIONAL_DATA_AUDIT.json
