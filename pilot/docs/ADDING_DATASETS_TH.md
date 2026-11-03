# เพิ่ม dataset โดยไม่แก้โมเดล

## 1. เตรียมข้อมูล

แยก benign และ attack เป็น JSONL เช่น:

```text
data/my_dataset/normal/queries.jsonl
data/my_dataset/attacker/queries.jsonl
```

แต่ละบรรทัดต้องมี ID และข้อความเป็น string ไม่ว่าง:

```json
{"id": "sample-001", "query": "Example query"}
```

CSV/Parquet ต้องแปลงเป็น JSONL ก่อน หากต้องอ่าน format อื่นโดยตรงในอนาคต
ให้เพิ่ม adapter ใน `deep_mmd/datasets/` ที่คืน rows รูปแบบเดียวกัน

## 2. สร้าง specification

สร้าง `pilot/configs/datasets/my_dataset.json`:

```json
{
  "name": "my_dataset",
  "benign_path": "my_dataset/normal/queries.jsonl",
  "attack_path": "my_dataset/attacker/queries.jsonl",
  "id_field": "id",
  "text_field": "query",
  "grouping_policy": "id-text-only",
  "provenance_notes": "Describe the source, revision, meaning of IDs and known overlaps."
}
```

`id_field`/`text_field` เปลี่ยนเป็นคอลัมน์จริงได้ เช่น `sample_id`/`prompt`
ระบุแหล่งข้อมูลและข้อจำกัดจริงใน `provenance_notes` ก่อนใช้ผลในการวิจัย
ถ้า ID ตรงกันระหว่าง benign/attack ระบบถือว่าอยู่กลุ่มเดียวกัน จึงต้องตรวจความหมาย ID

| Policy | การใช้งาน |
|---|---|
| `id-text-only` | เชื่อม ID/normalized text ที่ซ้ำกัน; ไม่ยืนยัน source independence |
| `id-text-attack-context` | เพิ่มการเชื่อม parsed attack source context และบังคับ parse attack ได้ทุกแถว |

parser ปัจจุบันรองรับ `Given this context: ... Can you answer this question briefly: ...`
หากข้อมูลมี source/session/document IDs หรือ prompt คนละรูปแบบ ต้องเพิ่มการอ่านและ
audit grouping key ให้เหมาะสมใน `datasets/protocol.py` ก่อนอ้างการแยกตาม source
เพื่อคงพฤติกรรมเดิม policy แบบ ID/text ยังเชื่อม attack context ที่ parser เดิมอ่านได้ด้วย

dataset ใหม่ต้องมี config ชัดเจน รายการ `SUPPORTED_DATASETS` ที่คงไว้รองรับ imports เก่า
หมายถึงสามชุดที่ตรวจไว้เดิม การค้นหา dataset ใหม่ใช้ไฟล์ config โดยไม่ต้องเพิ่มชื่อใน tuple

## 3. รันจากราก repository

```powershell
.\.venv\Scripts\python.exe -m pilot.deep_mmd `
  --config pilot/configs/experiments/known_attack.json `
  --dataset my_dataset `
  --output pilot/outputs/my_dataset/run_001
```

ใช้ specification ภายนอกได้ด้วย `--dataset-config path/to/my_dataset.json`
ถ้าใช้ร่วมกับ experiment config ที่มี dataset เดิม ให้ส่ง `--dataset my_dataset`
เพื่อ override ชื่อให้ตรงกันด้วย
path ของไฟล์ข้อมูลอ้างจาก `--data-root` ส่วน path อื่นอ้างจาก working directory
ระบบแจ้งเมื่อข้อมูลใน partition ไม่พอสำหรับขนาด window ที่ตั้งไว้
การแบ่งตาม connected groups ไม่รับประกันจำนวน rows แต่ละ label เท่ากันทุก partition

## 4. อ่านผล

| ไฟล์ใน output | เนื้อหา |
|---|---|
| `metadata.json` | arguments จริง, dataset spec, split audit/hashes, thresholds, rates, training history |
| `scores.csv` | คะแนนและการตรวจจับแต่ละ test window |
| `calibration_scores.csv` | คะแนน benign calibration และ threshold |
| `deep_kernel.pt` | state dict ของ network ที่เลือกจาก validation |

checkpoint คง format เดิม: สร้าง network จาก `models.build_feature_network` และอ่าน
bandwidth/encoder จาก metadata ยังไม่มี detector ที่บรรจุ reference pool สำหรับโหลดไปใช้จริง
`summarize_main.py` ใช้เฉพาะ protocol เดิม ไม่รองรับ run ที่เปลี่ยนจำนวน epochs/windows
