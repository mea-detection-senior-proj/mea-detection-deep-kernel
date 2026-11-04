"""Audit and run two inspected datasets; combine them with the existing results."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pilot.protocol import make_partitions, normalize, read_rows
from pilot.summarize_main import result_table, summarize

DATASETS = ('Meaeq_SST-2', 'ME_BERT_sst2_wiki')


def audit_data():
    report, benign_sets = {}, {}
    for dataset in DATASETS:
        normal = read_rows(ROOT / 'data' / dataset / 'normal/queries.jsonl')
        attack = read_rows(ROOT / 'data' / dataset / 'attacker/queries.jsonl')
        benign_sets[dataset] = {normalize(r['query']) for r in normal}
        report[dataset] = {}
        for seed in (1, 20, 42):
            partitions, audit = make_partitions(normal, attack, seed, dataset)
            sizes = {part: {label: len(rows) for label, rows in classes.items()}
                     for part, classes in partitions.items()}
            # The 500-query setting is the largest requested evaluation window.
            needed = {'train': {'benign': 500, 'attack': 10},
                      'validation': {'benign': 190, 'attack': 10},
                      'calibration': {'benign': 500}, 'test': {'benign': 500, 'attack': 50}}
            for part, classes in needed.items():
                for label, minimum in classes.items():
                    if sizes[part][label] < minimum:
                        raise ValueError(f'{dataset}/{seed}: insufficient {part}/{label}')
            report[dataset][seed] = {'sizes': sizes, 'audit': audit}
            print(dataset, seed, sizes, flush=True)
    report['cross_dataset_benign_normalized_overlap'] = len(benign_sets[DATASETS[0]] & benign_sets[DATASETS[1]])
    (ROOT / 'pilot/ADDITIONAL_DATA_AUDIT.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


def combine():
    rows = []
    for dataset in ('model_leeching', *DATASETS):
        folder = ROOT / 'pilot/outputs' / f'main_{dataset}_repeats20'
        with (folder / 'validated_runs.csv').open(newline='', encoding='utf-8') as stream:
            for row in csv.DictReader(stream):
                row['dataset'] = dataset
                rows.append(row)
    lines = ['# ผลทดลอง Deep MMD: 3 datasets', '', *result_table(rows), '',
             '## ค่าเฉลี่ยข้าม seeds 1, 20, 42', '',
             '| Method | Dataset | Window | FPR | TPR 5% | TPR 10% |',
             '|---|---|---:|---:|---:|---:|']
    labels = {'rbf': 'RBF', 'multi_rbf': 'Multi-RBF', 'deep_kernel': 'Deep Kernel'}
    for dataset in ('model_leeching', *DATASETS):
        for window in ('250', '500'):
            for method in labels:
                selected = [r for r in rows if r['dataset'] == dataset and str(r['window']) == window and r['method'] == method]
                values = [sum(float(r[m]) for r in selected)/len(selected) for m in ('fpr', 'tpr_5pct', 'tpr_10pct')]
                lines.append(f'| {labels[method]} | {dataset} | {window} | ' + ' | '.join(f'{v:.1%}' for v in values) + ' |')
    audit = json.loads((ROOT / 'pilot/ADDITIONAL_DATA_AUDIT.json').read_text(encoding='utf-8'))
    lines += ['', '## เงื่อนไขและข้อจำกัด', '',
              '- ฝึกและประเมินแยกแต่ละ dataset; ไม่รวมข้อมูลและไม่ใช่ unseen-family evaluation',
              '- ตรึง BGE-small; 20 reference repeats ทั้ง calibration/test; 200 calibration windows; 100 test windows ต่อเงื่อนไข',
              '- ฝึก 20 epochs, 8 windows/epoch, train window 100, attack 10%; เลือกจาก 32 fixed validation windows',
              '- แบ่งกลุ่ม 40/20/20/20 เป็น train/validation/calibration/test; thresholds ใช้ percentile 95 ของ benign calibration แยกวิธี',
              '- model_leeching แบ่งตาม ID/ข้อความ/attack context; สอง dataset เพิ่มเติมแบ่งตาม ID/ข้อความ เนื่องจากไม่มี source-passage identifiers',
              '- ID ของสองชุดเพิ่มเป็น synthetic row IDs จึงไม่ยืนยัน source independence หรือกัน paraphrases ได้',
              f"- สองชุด SST-2 มี benign normalized texts ซ้ำข้าม dataset {audit['cross_dataset_benign_normalized_overlap']:,} ข้อความ จึงไม่ใช่หลักฐานจาก benign sources ที่อิสระกัน",
              '- หน้าต่างใช้ queries ซ้ำข้ามหน้าต่างได้; ผลเป็นสถิติเชิงพรรณนา; ไม่อ้างความมีนัยสำคัญ',
              '- TPR ต้องอ่านคู่ FPR; ไม่สรุปว่าดีกว่าที่ FPR เท่ากันเมื่อ FPR จริงต่างกัน',
              '- Window 250 ที่ระบุ attack 5% ใช้จริง 12/250 = 4.8%',
              '- ไม่ใช้ test เลือก checkpoint หรือปรับ threshold; Deep Kernel ใช้ attack labels ฝึก ส่วน fixed kernels ไม่ใช้',
              '- Objective เป็น exploratory signal-to-noise proxy; ความต่างความยาว/รูปแบบยังเป็นข้อจำกัดของข้อมูล', '',
              '## รายงานแยก dataset', '']
    for dataset in ('model_leeching', *DATASETS):
        lines.append(f'- [{dataset}](outputs/main_{dataset}_repeats20/REPORT.md)')
    lines += ['', 'แหล่งข้อมูล: [Hugging Face](https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data)',
              'เวอร์ชันและ SHA256 ของไฟล์ที่ดาวน์โหลด: ADDITIONAL_DATA_PROVENANCE.json; ผลตรวจการแบ่งข้อมูล: ADDITIONAL_DATA_AUDIT.json']
    (ROOT / 'pilot/MULTI_DATASET_RESULTS_TH.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    with (ROOT / 'pilot/outputs/multi_dataset_runs.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print('Combined', len(rows), 'method results', flush=True)


def main():
    audit_data()
    if '--audit-only' in sys.argv:
        return
    for dataset in DATASETS:
        output = ROOT / 'pilot/outputs' / f'main_{dataset}_repeats20'
        subprocess.run([sys.executable, '-u', 'pilot/run_known_pilot.py', '--dataset', dataset,
                        '--output', str(output)], cwd=ROOT, check=True)
        summarize(output, dataset)
        snapshot = output / 'source_snapshot'
        snapshot.mkdir()
        hashes = {}
        for name in ('protocol.py', 'deep_kernel_pilot.py', 'run_known_pilot.py', 'run_additional.py', 'summarize_main.py'):
            path = ROOT / 'pilot' / name
            shutil.copy2(path, snapshot / name)
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        # Entry points now import the package; archive its implementation and
        # dataset/experiment specifications as well for reproducibility.
        for folder in ('deep_mmd', 'configs'):
            for path in sorted((ROOT / 'pilot' / folder).rglob('*')):
                if not path.is_file() or path.suffix not in ('.py', '.json'):
                    continue
                relative = path.relative_to(ROOT / 'pilot')
                destination = snapshot / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                hashes[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        (snapshot / 'sha256.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    combine()


if __name__ == '__main__':
    main()
