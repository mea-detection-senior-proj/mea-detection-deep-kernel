---
date: "2026-11-03"
baseline_ref: "main"
baseline_commit: "5fb5e07d750a73a0a663a174433bab931ae7568a"
target_ref: "restructure/deepkernel"
target_commit: "961414da045d1ea4f562c62d59285644f7cd1f80"
comparison_mode: "direct-tree"
merge_base_commit: null
include_working_changes: true
scope: "MMD/Deep Kernel source, configurations, tests, protocols and recorded results; all changed paths accounted for; generated report excluded from research changes."
---

# Deep Kernel — Changes from main

This compares local `main` directly with the current checkout, including committed, unstaged and untracked files. It is not a changes-since-divergence comparison. The inventory capture and per-file content hashes below identify working changes that the target commit alone cannot reproduce.

The baseline already contains Deep Kernel training, validation-only checkpoint selection, source-grouped partitions and matched reference repeats in `main:pilot/deep_kernel_pilot.py` and `main:pilot/protocol.py`. The target contains **two distinct implementations**: a modular continuation of that pilot and a new pure-training workflow. Their shared method name does not make their protocols or scores interchangeable. [P], [K], [T], [D], [L]

## 1. Summary of Changes

| Status | Topic | Baseline | Target | Impact | Evidence |
|---|---|---|---|---|---|
| New | Independent experiment workflow | Pilot orchestrates training and evaluation | `detectors`, `data_pipeline`, `evaluation`, `experiments` separate responsibilities | New protocol alongside the legacy scripts | [R], [L], [W] |
| New | Pure-training Deep Kernel | Pilot learns features using 10% mixed windows | Pure benign versus pure attacker pairs; learnable base/feature bandwidths and mixture weight | Changes the research method, not just file organization | [K], [T], [P] |
| New | Locked comparison | Pilot regenerates draws from RNG | Materialized embeddings, pools, splits and draws; hashes and lock ID checked by consumers | Separate runs can use the same evaluation plan | [L] `prepare`, `verify_lock`, `run_locked` |
| New | Capacity audit and folder datasets | Pilot initially permits only model_leeching | Main workflow discovers standard data folders and infers available context policy | More datasets accepted, with explicit provenance limits | [D] `load_dataset`; [A] |
| New | Results and comparison tools | Existing pilot reports | Additional pilot results plus locked-run summaries, AUROC and paired rate differences | Recorded evidence for distinct protocols; no general improvement guarantee | [S], [H], [I] |
| Modified | Pilot architecture | Monolithic pilot, importing original detector and assigning its globals | `pilot.deep_mmd` package; old import/script paths wrap package | Removes pilot dependence on original detector globals while preserving core formulas | [P], [PM] |
| Modified | Pilot dataset extension | Strict model_leeching context requirement | Declarative adapters, custom field mapping, inspected SST-2 specs | ID/text-only specs do not establish independent sources | [PD] |
| Modified | Pilot batch runner | One reference repeat by inherited default | `run_known_pilot.py` defaults to 20 repeats, accepts dataset and records it | Batch-run defaults differ; single-run CLI still defaults to one repeat | [PR], [PC] |
| Modified | New workflow calibration and counting | Pilot linear 95th quantile; Python `round` | `higher` quantile; half-up attacker counts and actual-ratio metadata | Finite scores/decisions and mixtures can differ | [E], [N], [PE] |
| Modified | Documentation/artifact handling | Original README and ignores | New manuals, configs, ignored `/artifacts/`, two more ignored datasets | Source/config/docs remain reviewable; outputs remain local | [G], [U] |
| Unchanged | Pilot estimator and model selection | All-cross unbiased MMD; fixed validation; epoch zero eligible; freeze | Same core behavior in modular pilot | Refactoring is distinct from pure-training changes | [PM], validation below |
| Unchanged | Original paper detector | `MMD_detection/mmd_detector_gpu.py` | No net change to that path | New workflow does not replace or reproduce the original protocol | [O]; net inventory below |

No inventoried path is deleted. The large removals in pilot files are implementation extraction plus wrappers, not removal of Deep Kernel support.

## 2. Architecture & File Mapping

| Baseline path/symbol | Target path/symbol | Responsibility and interpretation |
|---|---|---|
| `pilot/deep_kernel_pilot.py:main` | [pilot/deep_kernel_pilot.py](../../pilot/deep_kernel_pilot.py), [cli.py](../../pilot/deep_mmd/cli.py):`main`, [experiment.py](../../pilot/deep_mmd/experiment.py):`run` | Compatibility entry point delegates configuration and orchestration |
| Same file: sampling functions | [sampling.py](../../pilot/deep_mmd/sampling.py) | Reference draws and 10% training mixtures |
| Same file: `mmd`, original detector helpers | [kernels.py](../../pilot/deep_mmd/kernels.py), [embeddings.py](../../pilot/deep_mmd/embeddings.py) | Local implementations of kernels, bandwidth and frozen encoder cache |
| Same file: `fit_kernel`, `standardized_mmd` | [training.py](../../pilot/deep_mmd/training.py) | Historical mixed-window proxy training |
| Same file: scoring/evaluation | [evaluation.py](../../pilot/deep_mmd/evaluation.py) | Historical linear-quantile calibration and shared draws |
| `pilot/protocol.py` | [protocol wrapper](../../pilot/protocol.py), [datasets/protocol.py](../../pilot/deep_mmd/datasets/protocol.py), [registry.py](../../pilot/deep_mmd/datasets/registry.py) | Grouped splits plus dataset specifications |
| `pilot/test_protocol.py`, `pilot/test_training.py` | Compatibility imports of [pilot/tests](../../pilot/tests/) | Old unittest import paths retained |
| No equivalent independent module | [detector.py](../../detectors/mmd/detector.py), [model.py](../../detectors/deep_kernel_mmd/model.py), [training.py](../../detectors/deep_kernel_mmd/training.py) | New fixed and learned detector mathematics |
| No five-pool pilot equivalent | [datasets.py](../../data_pipeline/datasets.py), [windows.py](../../data_pipeline/windows.py), [embeddings.py](../../data_pipeline/embeddings.py) | New data protocol and content-addressed encoder identity |
| Pilot orchestration only | [cli.py](../../experiments/cli.py) → [workflow.py](../../experiments/workflow.py) → [locked.py](../../experiments/locked.py) → [evaluation](../../evaluation/windows.py) → [summarizer](../../experiments/summarize_comparison.py) | Current public `python -m experiments.run` path |

The public CLI runs capacity preflight, prepares or reuses a lock, runs methods into `output/results/`, and summarizes into `output/report/`. The callable `experiments.run.run(config)` also retains an older unlocked fixed-kernel path; this is not the path selected by the current CLI. Deep Kernel through that callable requires `protocol_lock`. [R], [W]

Full path coverage and working-state hashes appear at the end of this section. Namespace `__init__.py` files are package markers; `pilot/deep_mmd/__main__.py` invokes the pilot CLI. The skill file is workflow input, excluded from detector behavior. The generated report is explicitly excluded from research-change counts.

### Captured Git inventory

Captured: `2026-11-03T22:56:02+07:00` (Asia/Bangkok, UTC+07:00).

Inventory: **77 unique input paths**; committed versus main: 12; staged: 0; unstaged: 8; net tracked versus main: 14; untracked inputs: 63. Counts overlap by path; they must not be added. No committed/staged/unstaged path cancels to the baseline in this capture.

States: `C` committed versus baseline, `S` staged versus HEAD, `W` unstaged versus index, `N` net tracked versus baseline, `U` untracked. `A`/`M` are Git add/modify status. SHA256 fingerprints the current file bytes; it is not a stored copy.

| Path | Git state | Coverage / exclusion | Working-file SHA256 |
|---|---|---|---|
| [.agents/skills/deep-kernel-doc-generator/SKILL.md](../../.agents/skills/deep-kernel-doc-generator/SKILL.md) | U | Excluded: skill/workflow input; no detector behavior | `0c7249f7fd69154efe4eb9fb161e4d1788f391bece9a6f6d9b83a3b99ce8de70` |
| [.gitignore](../../.gitignore) | C:M, W:M, N:M | Sections 1, 7: usage and artifact handling | `dd0633f2f188235769dd02322f214eb333129f2bf84d7cf53624154cd38d22e2` |
| [README.md](../../README.md) | W:M, N:M | Sections 1, 7: usage and artifact handling | `64612844b42c4bb0883fe5c2da49a212e27b7116f49f204fa5ee8f056abc1d30` |
| [configs/experiments/deep_pure.json](../../configs/experiments/deep_pure.json) | U | Sections 5, 7: experiment settings | `c3a278606eb1f2ab2a1cdf60d8ca2246a7c8f4cfabe2968405f2d09bcfcac380` |
| [configs/experiments/mmd_comparison.json](../../configs/experiments/mmd_comparison.json) | U | Sections 5, 7: experiment settings | `3fe7b33ae5ca169b302748adca4a0d903b8a0bbe43af4895db8a322efa69771c` |
| [configs/experiments/mmd_smoke.json](../../configs/experiments/mmd_smoke.json) | U | Sections 5, 7: experiment settings | `6d487b5f8f5899d9b74a3735756e88cf7d4ab36872c22081103ac347ffb37ce7` |
| [configs/experiments/model_leeching_baseline_locked.json](../../configs/experiments/model_leeching_baseline_locked.json) | U | Sections 5, 7: experiment settings | `8dafa1a69fce50507d14ccff1750daac6d308557f1579b674afef76e50966ddb` |
| [configs/experiments/model_leeching_deep_pure_locked.json](../../configs/experiments/model_leeching_deep_pure_locked.json) | U | Sections 5, 7: experiment settings | `dafb4b4b986c13f5a5aaf6ba36d29fb1d323536430bacf907672f749ceb10a48` |
| [data_pipeline/__init__.py](../../data_pipeline/__init__.py) | U | Sections 4, 6: data, encoder and windows | `a533ec5afc8784f89675d17902b740be041a270ca096ee34263a7135d27d5973` |
| [data_pipeline/datasets.py](../../data_pipeline/datasets.py) | U | Sections 4, 6: data, encoder and windows | `d9b3e6fe7007e4bbc4ef8232b8d6b3dde7788a1d4ef63841ee7f0ab70c7c4c35` |
| [data_pipeline/embeddings.py](../../data_pipeline/embeddings.py) | U | Sections 4, 6: data, encoder and windows | `b82052db448fe1e9921398227a6aa1ff29a465141a78032effafbd252f55e947` |
| [data_pipeline/windows.py](../../data_pipeline/windows.py) | U | Sections 4, 6: data, encoder and windows | `5da27ea9d1d580b167ceb2ef2acd449328865076aebe1b9b252eb43099651199` |
| [detectors/__init__.py](../../detectors/__init__.py) | U | Sections 3, 5, 6: kernel, training and score | `0c2d4fe97ce22637e0a92afbb1a8f65a79e563f7f9568cca89fc3d105ffa9042` |
| [detectors/deep_kernel_mmd/__init__.py](../../detectors/deep_kernel_mmd/__init__.py) | U | Sections 3, 5, 6: kernel, training and score | `7cdae3e2d4acd66dc2188af4b2cd64b4ceeeb64036ea1df835bee5cd0c750ec3` |
| [detectors/deep_kernel_mmd/model.py](../../detectors/deep_kernel_mmd/model.py) | U | Sections 3, 5, 6: kernel, training and score | `b64699a3cd662bf09178a9861eb3abf154ddcea3f2439722dbfd756b0d8b7b25` |
| [detectors/deep_kernel_mmd/training.py](../../detectors/deep_kernel_mmd/training.py) | U | Sections 3, 5, 6: kernel, training and score | `e63585d92e92c1b70c2c5cf18de0bc675dd39b2c067346eda9460172e0d46d76` |
| [detectors/mmd/__init__.py](../../detectors/mmd/__init__.py) | U | Sections 3, 5, 6: kernel, training and score | `728215818b8a764d43436b59d99e0c22644b5fcee6097398985357e498d08ffa` |
| [detectors/mmd/detector.py](../../detectors/mmd/detector.py) | U | Sections 3, 5, 6: kernel, training and score | `92bcce9013a8daae36fbc7441b3dbe52c9e6e6142aa98c3c7f06ff151146c966` |
| [docs/BASELINE_WORKFLOW_TH.md](../../docs/BASELINE_WORKFLOW_TH.md) | U | Sections 4, 7, 8: existing protocols/plans/results | `412b6cae9b59cfb15a38dfc942151110aa45ef3f928b6a9a1b9f91bc7fc2651e` |
| [docs/DATA_READINESS_TH.md](../../docs/DATA_READINESS_TH.md) | U | Sections 4, 7, 8: existing protocols/plans/results | `f3946cb46a23dfa8ec2d91a2da1e25fd610f8ef2efa04201a05db599ea7db9ec` |
| [docs/DEEP_KERNEL_PROTOCOL_TH.md](../../docs/DEEP_KERNEL_PROTOCOL_TH.md) | U | Sections 4, 7, 8: existing protocols/plans/results | `88fbbf24b6097ec2c79a08654fe50aace5dd8fa774b33191b46b7f4452808163` |
| [docs/MODEL_LEECHING_COMPARISON_TH.md](../../docs/MODEL_LEECHING_COMPARISON_TH.md) | U | Sections 4, 7, 8: existing protocols/plans/results | `ea24b663eb44eef2915a9f688d5537a291b86d4d0c7ea33ba2698eb5ed254387` |
| [docs/RESTRUCTURING_PLAN_TH.md](../../docs/RESTRUCTURING_PLAN_TH.md) | U | Sections 4, 7, 8: existing protocols/plans/results | `47cde0b724d58d3ce8abb80d323d5b9590a3410c9402827aea463143a1cf5d72` |
| [docs/RUN_EXPERIMENTS_TH.md](../../docs/RUN_EXPERIMENTS_TH.md) | U | Sections 4, 7, 8: existing protocols/plans/results | `2a02ff8bfdcb3060e8d4ef18de62c4d3e4e454b039f65e2c2f334d806948b40f` |
| [evaluation/__init__.py](../../evaluation/__init__.py) | U | Section 6: threshold, decisions and rates | `9f0ce6d4b132d74cd3d57986e9a62dbc71c84f5a4fb4d136180df764a7dbbf6e` |
| [evaluation/windows.py](../../evaluation/windows.py) | U | Section 6: threshold, decisions and rates | `6b020ec9657ff07fa08ca853897192aa7bfc7b0081ac10b9cc4eb7b96babdf9b` |
| [experiments/__init__.py](../../experiments/__init__.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `41c254071e288a418f489dc2d3cd5d829bb064826cd2cf54495a0236c0468862` |
| [experiments/artifacts.py](../../experiments/artifacts.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `2903b06c6d3907a5401d5ecfca40d114bc735f82464660a6021c6104418bfa66` |
| [experiments/audit_data.py](../../experiments/audit_data.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `4b75030f4a4cff227f8cbf5b90c4a17c7c2fd2f728053234feeb5f1d06872250` |
| [experiments/cli.py](../../experiments/cli.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `f5eb870bc909361769fc5aefa121187426652033d287716e9c8224471824d82d` |
| [experiments/configuration.py](../../experiments/configuration.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `d428e1d0c62380d432cc299a05a4f67c5e139d3ce0271d8a397e01f86284d429` |
| [experiments/locked.py](../../experiments/locked.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `52be2e90288562d396af4623647fa2b16e797d5dbb6475dec6c51768a9f5f5ff` |
| [experiments/prepare.py](../../experiments/prepare.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `ead51271dac121fc8a5ab157b0ff2f0d70ab2e7fb3a28ef3f18c5363f4ae0157` |
| [experiments/run.py](../../experiments/run.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `7c9e0b90a841008109ec574ebe78ad74d46485e556a2dc47cb559518411b12fb` |
| [experiments/summarize_comparison.py](../../experiments/summarize_comparison.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `a8ef3a2ca2977f740f39c1ef9b88dc6f906475cb065c2a6a065696bc5124e5b4` |
| [experiments/workflow.py](../../experiments/workflow.py) | U | Sections 2, 4-8: orchestration, locks, audit and summaries | `43f1a24399029881cd38e3d50921919bf4dab89e76e7e43b41cde10cf31ba96a` |
| [pilot/ADDITIONAL_DATA_AUDIT.json](../../pilot/ADDITIONAL_DATA_AUDIT.json) | C:A, N:A | Sections 4, 8: recorded data audit/provenance | `770a270e1df7a0e657a56818d3fb89962a540b2ab493a1a595a5bcfe7531d50b` |
| [pilot/ADDITIONAL_DATA_PROVENANCE.json](../../pilot/ADDITIONAL_DATA_PROVENANCE.json) | C:A, N:A | Sections 4, 8: recorded data audit/provenance | `fab3f40597dd066d46618b6e015a6906ae7c0a0674fb35ae050c63cfd9a25d2d` |
| [pilot/MAIN_RESULTS_TH.md](../../pilot/MAIN_RESULTS_TH.md) | C:A, N:A | Section 8: recorded pilot results | `1286625aa3c055defa4f3e0ce73cec2f1d95b7f52e8592f03a3c43b8831fceaf` |
| [pilot/MULTI_DATASET_RESULTS_TH.md](../../pilot/MULTI_DATASET_RESULTS_TH.md) | C:A, N:A | Section 8: recorded pilot results | `23ca9eb33fb78f6414b292f230e4c94edc6fda5881dade962794817cd305a8c9` |
| [pilot/README.md](../../pilot/README.md) | C:M, W:M, N:M | Sections 1, 7: usage and artifact handling | `c842c672b14fba569b7da7b1d3432770a323f3535a954e8f5f4ed813f6c6855b` |
| [pilot/__init__.py](../../pilot/__init__.py) | U | Section 2: package marker | `4b81a7be18d5152ec021290242609180f3ad8509699b9b269310caf6736d005a` |
| [pilot/configs/datasets/ME_BERT_sst2_wiki.json](../../pilot/configs/datasets/ME_BERT_sst2_wiki.json) | U | Sections 4, 7: pilot specifications | `ab5b4fecea943d76f80692fda1f6608afedb4aa041bccbde1ca8cf290fcd97e8` |
| [pilot/configs/datasets/Meaeq_SST-2.json](../../pilot/configs/datasets/Meaeq_SST-2.json) | U | Sections 4, 7: pilot specifications | `7a3793266e24785f9a3448cfaf3cf2be47da63560e39cfcdf35666e49ec9441b` |
| [pilot/configs/datasets/model_leeching.json](../../pilot/configs/datasets/model_leeching.json) | U | Sections 4, 7: pilot specifications | `880763f0056c2c92bee03556502d8702543697757a0d873e9befd4ce033bfcb6` |
| [pilot/configs/experiments/known_attack.json](../../pilot/configs/experiments/known_attack.json) | U | Sections 4, 7: pilot specifications | `51813344eebe3f160505fb8a3bb2153d1a9fa35b11c58736042fdd460afd8e5e` |
| [pilot/deep_kernel_pilot.py](../../pilot/deep_kernel_pilot.py) | C:M, W:M, N:M | Section 2: compatibility wrapper | `427fc07e032da81bda3837154297801d4edb4c8ff318f603292cbc590f400b05` |
| [pilot/deep_mmd/__init__.py](../../pilot/deep_mmd/__init__.py) | U | Sections 2-6: modular historical pilot | `f4475227206ab1cda1db49f210e1c8841f7b932f99b40e4e9067c95d9381e575` |
| [pilot/deep_mmd/__main__.py](../../pilot/deep_mmd/__main__.py) | U | Sections 2-6: modular historical pilot | `c13eb66970ae37b8b044f428b309e67868814b90a8bb408806f3316ce4dfbc5b` |
| [pilot/deep_mmd/cli.py](../../pilot/deep_mmd/cli.py) | U | Sections 2-6: modular historical pilot | `c75633522dd89fbbfa2fb80e029627e57429ed994e381c287b8f67617ee0b1cf` |
| [pilot/deep_mmd/datasets/__init__.py](../../pilot/deep_mmd/datasets/__init__.py) | U | Sections 2-6: modular historical pilot | `66694cf401ef04b528c8bc59965028d1f4a67c3bf589ec0a5499ea823f0ca694` |
| [pilot/deep_mmd/datasets/protocol.py](../../pilot/deep_mmd/datasets/protocol.py) | U | Sections 2-6: modular historical pilot | `b24c1d5d66b6d98e0feabda6b824f68146b371b50e144f579a27174268fade9c` |
| [pilot/deep_mmd/datasets/registry.py](../../pilot/deep_mmd/datasets/registry.py) | U | Sections 2-6: modular historical pilot | `0298eb431d39400eb98869ab709af65534f3ae1b9ca69a7ecb84931579124c64` |
| [pilot/deep_mmd/embeddings.py](../../pilot/deep_mmd/embeddings.py) | U | Sections 2-6: modular historical pilot | `132dcc16fea038c86cc48c73d226fed63ea5fe7b620da5c6153f7825ae8a992c` |
| [pilot/deep_mmd/evaluation.py](../../pilot/deep_mmd/evaluation.py) | U | Sections 2-6: modular historical pilot | `6276e8b22c6048b40b86d86017aaebd901a413145a66bb66d591bf103f5a6a97` |
| [pilot/deep_mmd/experiment.py](../../pilot/deep_mmd/experiment.py) | U | Sections 2-6: modular historical pilot | `e7fee7eca2a207aa00dc8526a0d3184210363d076f83a63d98e68a3f81b0e77c` |
| [pilot/deep_mmd/kernels.py](../../pilot/deep_mmd/kernels.py) | U | Sections 2-6: modular historical pilot | `1d526da7292a688d07ba10b7d96d255fb31414d0a9839ad417b63070ce1e787c` |
| [pilot/deep_mmd/models.py](../../pilot/deep_mmd/models.py) | U | Sections 2-6: modular historical pilot | `f7e46c5c6e09b66b31d8428ab768e26d1c7f8b75810db23bd016f4aba7b65b57` |
| [pilot/deep_mmd/sampling.py](../../pilot/deep_mmd/sampling.py) | U | Sections 2-6: modular historical pilot | `2e7da6a6917b896d140e66a8cf5db01d5502e7fbe793739cae9193cd29ff12b4` |
| [pilot/deep_mmd/training.py](../../pilot/deep_mmd/training.py) | U | Sections 2-6: modular historical pilot | `0b4360d3fb29ac26e05b35bcffba8a2d734e58229da64dea105926d4af21084f` |
| [pilot/docs/ADDING_DATASETS_TH.md](../../pilot/docs/ADDING_DATASETS_TH.md) | U | Sections 2, 4, 7: pilot manuals | `d43271acef6dca459189be7f4ce986099c2096c9c73915966c309a9e7b20fa04` |
| [pilot/docs/ARCHITECTURE_TH.md](../../pilot/docs/ARCHITECTURE_TH.md) | U | Sections 2, 4, 7: pilot manuals | `784be59ca147482293986b06ae236851fef6f62c089095e0e2947688ca7daf16` |
| [pilot/protocol.py](../../pilot/protocol.py) | C:M, W:M, N:M | Section 2: compatibility wrapper | `10fb1fb94b911f028383dfb25789031d4c4dd3a1dbfdf37e79c998bc45ec34ff` |
| [pilot/run_additional.py](../../pilot/run_additional.py) | C:A, W:M, N:A | Sections 4, 8: additional datasets; package/config snapshot | `d31de2f8f2a30da81febf5c8fe7ab5c5e30c1d7f6ce82af46ad2facd10f906d2` |
| [pilot/run_known_pilot.py](../../pilot/run_known_pilot.py) | C:M, N:M | Sections 1, 5, 7: batch-run defaults | `35dfc5ad8b767f3b34502c4d5ef5cf1a77c11438a68bc948122482ab2f79d733` |
| [pilot/summarize_main.py](../../pilot/summarize_main.py) | C:A, N:A | Sections 6, 8: pilot result validation/summary | `cdf21bea613af1fc5e75bdf3ddb1293e861796275729b140fd9d752643deed3b` |
| [pilot/test_protocol.py](../../pilot/test_protocol.py) | C:M, W:M, N:M | Sections 2, 8: pilot tests/compatibility | `821030b259eabfa21c388e1b918e36259104d35caa7cbd1b5307d3bf2a7036d0` |
| [pilot/test_training.py](../../pilot/test_training.py) | W:M, N:M | Sections 2, 8: pilot tests/compatibility | `d414e48d1c00bb9ccf0a238cd504acc9c66f32da25dcba664176dda75d4656fe` |
| [pilot/tests/__init__.py](../../pilot/tests/__init__.py) | U | Sections 2, 8: pilot tests/compatibility | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [pilot/tests/test_dataset_extension.py](../../pilot/tests/test_dataset_extension.py) | U | Sections 2, 8: pilot tests/compatibility | `f373861e0ad89653ae2b9272ba8641d94dda02ff42a27e6c32811461ed882244` |
| [pilot/tests/test_protocol.py](../../pilot/tests/test_protocol.py) | U | Sections 2, 8: pilot tests/compatibility | `0bfcaf5b0963526f8d689e9150016134a62aaf3a645775ec4c70cb0080651dce` |
| [pilot/tests/test_training.py](../../pilot/tests/test_training.py) | U | Sections 2, 8: pilot tests/compatibility | `046b7d49fd7fa089e9d3fff726fa7e6d656e0949458f6a053b03bc1e9b649038` |
| [tests/test_data_readiness.py](../../tests/test_data_readiness.py) | U | Section 8: current workflow validation | `3bb4a4b77e940cdffb95dd3364e128a90e798992c83982c31eca57472e265638` |
| [tests/test_dataset_folders.py](../../tests/test_dataset_folders.py) | U | Section 8: current workflow validation | `c84da86eee92a27baa3fcfc45996e61f087611d8b3f63201f5cefa7287084758` |
| [tests/test_deep_kernel.py](../../tests/test_deep_kernel.py) | U | Section 8: current workflow validation | `c133003cc13ef40cc08d657795c289cae9a0e4fb23338ab88ae0478d3d8e01fe` |
| [tests/test_experiment_cli.py](../../tests/test_experiment_cli.py) | U | Section 8: current workflow validation | `d342b8084221316799b79dec668170ecec87b10cb650a8688fa5f07b6cd9fa9b` |
| [tests/test_mmd_pipeline.py](../../tests/test_mmd_pipeline.py) | U | Section 8: current workflow validation | `b8d5973271531f78c3e3495bc6676f8e42622b3c5aafed46792c0620fdf23dda` |
| `docs/deep-kernel/Deep Kernel Changes 2026-11-03.md` | U; generated after source inspection | Excluded: this generated report, not a research change | Self-hash omitted |

All listed untracked code/config/doc files are included as target content even though absent from HEAD. No files were staged by this workflow.


## 3. Kernel & Training Objective

Let `z` be a frozen sentence embedding and `g` the trainable feature network. Fixed kernels use

$$k_\sigma(x,y)=\exp(-\|x-y\|^2/(2\sigma^2)).$$

Single-RBF uses one bandwidth; Multi-RBF averages bandwidths `{0.5σ, σ, 2σ, 4σ}` equally. In the pilot, σ comes from benign training; in the new workflow, it comes from the separate benign reference pool. [PM] `experiment.run`; [K] `rbf_kernel`; [L] `prepare`

| Property | Baseline and modular pilot | New workflow |
|---|---|---|
| Kernel | Multi-RBF base × `(0.1 + 0.9 exp(-||g(x)-g(y)||²/2))` | Single-RBF base × `((1-ε) exp(-||g(x)-g(y)||²/(2σf²)) + ε)` |
| Network | input → 128 → ReLU → 32 | input → 128 → ReLU → 64 by default; dimensions configurable |
| Learned parameters | MLP only | MLP, log base bandwidth, log feature bandwidth, epsilon logit |
| Initialization | Fixed multi-bandwidth set and feature bandwidth 1; epsilon fixed 0.1 | Base bandwidth from benign reference median; feature bandwidth reset to mapped benign training median (up to 512 rows); epsilon initialized near 0.1 |
| Parameter transforms | No learned bandwidth/epsilon | Exponential bandwidths; sigmoid epsilon |
| Objective | Mean of mixed-window MMDs / sqrt(population variance across those MMDs + `1e-6`) | Paired MMD numerator / sqrt(regularized row-mean variance of H) |
| Evidence | [PM] `kernels.mmd`, `models.build_feature_network`, `training.standardized_mmd` | [K] `DeepKernelMMD`; [T] `power_objective`, `fit_kernel` |

For equal pure batches of size n, the new training implementation computes:

$$H_{ij}=k(x_i,x_j)+k(y_i,y_j)-k(x_i,y_j)-k(y_i,x_j),$$
$$M=\frac{\sum_{i\ne j}H_{ij}}{n(n-1)},\quad V=4\operatorname{Var}_{\mathrm{population}}\left(\frac1n\sum_jH_{ij}\right),\quad J=\frac{M}{\sqrt{V+10^{-8}}}.$$

`H` includes its diagonal in V and excludes it in M. V is not the variance across traffic windows and is not divided by n afterward. The regularizer is configurable. These statements describe executable code and scalar-reference tests; this report does not independently validate attribution to external paper equations. [T] `power_objective`; [TK] `test_objective_matches_scalar_variance_formula`

Detection uses the all-cross unbiased MMD² estimator in both workflows:

$$\widehat{\mathrm{MMD}}^2=\frac{\sum_{i\ne j}k(x_i,x_j)}{m(m-1)}+\frac{\sum_{i\ne j}k(y_i,y_j)}{n(n-1)}-\frac{2\sum_{ij}k(x_i,y_j)}{mn}.$$

The new training numerator excludes paired cross-diagonal terms, whereas detection includes all cross pairs. Their finite-sample values need not agree. Negative unbiased MMD² scores are possible. The new batched reference scorer averages per-draw MMD² scores; it does not pool references into a single enlarged sample. [K] `mmd2_unbiased`, `mean_reference_mmd`; [T] `power_objective`; [TM]

## 4. Data Preparation & Splits

The baseline model_leeching pilot joins equal IDs, NFKC/casefold/whitespace-normalized texts and parsed attack contexts transitively; removes cross-label text collisions; deduplicates per label; and splits connected groups 40/20/20/20 into train/validation/calibration/test. It requires the recognized context format for every attack. The modular pilot keeps this model_leeching behavior and adds dataset specs and custom `id_field`/`text_field`. Its ID/text policy still groups any recognized attack contexts; the strict policy additionally requires complete parsing. [P], [PD]

The new workflow instead splits groups **20/10/25/20/25** into train/validation/reference/calibration/test. Fractions refer to groups, not class row counts; the final partition receives rounding remainder. Reference and calibration attack rows are not used to calibrate benign thresholds. Unlike the pilot, the new workflow does not use benign training as the evaluation reference pool. [D] `PARTITIONS`, `FRACTIONS`, `split_rows`; [L] `prepare`

`data/<dataset>/normal/queries.jsonl` and `attacker/queries.jsonl` are discovered directly. Both require nonempty string `id` and `query`. All, some, or no recognized attack contexts select strict, available-context, or ID/text-only grouping respectively. Thus a changed model_leeching prompt format can weaken inferred grouping rather than fail under the historical strict pilot rule. The returned provenance notes explicitly leave true source/user independence unverified. Legacy `dataset_config` remains supported with a stricter fixed schema; it does not expose the pilot's custom column adapter. [D] `read_rows`, `load_dataset`, `split_rows`

Both paths use frozen, normalized embeddings and canonical text order. The new cache hashes encoder identity, revision, prefix, normalization and text content; local encoder identity hashes file contents (excluding `.cache`). Remote encoders require a 40-character revision in configuration. The pilot retains its older model-name-based cache format; equivalent cache filenames do not prove equivalent encoder file contents. [B], [PB], [C]

[Data readiness](../DATA_READINESS_TH.md) records local row counts, split capacities, overlap and provenance limits; it is historical evidence rather than an audit rerun today. [ADDITIONAL_DATA_PROVENANCE.json](../../pilot/ADDITIONAL_DATA_PROVENANCE.json) records dataset revision `7f96e886b424cc8cd384190f65c0cf0c6ea90d94` and four SST-2 file hashes. This report does not independently verify that remote revision. Synthetic IDs, semantic duplicates and shared SST-2 benign texts limit source-independence and cross-dataset claims. [A], [PD], [I]

## 5. Training & Model Selection

| Setting | Baseline/modular pilot | New pure workflow |
|---|---|---|
| Training pair | Benign reference vs 10%-attacker mixture; benign rows disjoint within the pair | Pure benign vs pure known attacker |
| Default batch/window | 100 | 100 |
| Epochs and updates | 20 epochs; 8 sampled pairs combined into one objective/update per epoch | 30 epochs; 16 optimizer updates per epoch |
| Optimizer | Adam, lr 0.001, weight decay 0.0001 | Same defaults, configurable |
| Gradient clipping | 10 | 10, configurable |
| Validation | Proxy over 32 fixed mixed pairs | Mean J over 32 fixed pure pairs |
| Checkpoint policy | Strictly better validation objective, including epoch zero; freeze afterward | Same policy with the new validation objective |
| Evidence | [PM] `fit_kernel`, `training_pair`; [PC] | [T] `DEFAULT_TRAINING`, `fit_kernel`; [L] `run_locked` |

The pilot spawns five RNG streams for bandwidth/training/validation/calibration/test from the experiment seed and initializes Torch from that seed. The new workflow uses `[seed,0]` for reference bandwidth; `[seed,size,1]` to spawn calibration/test generators; `[seed,7]` to spawn feature-bandwidth/training/validation generators; and `torch.manual_seed(seed)` before model construction. New locked runs request deterministic algorithms and disable TF32. This supports repeatability within the captured runtime, not universal bitwise equality across hardware/software. [PM] `experiment.run`; [L] `runtime`, `prepare`, `run_locked`; [T] `fit_kernel`

The training interfaces accept only training/validation embeddings. The new runner trains once per seed, saves the selected checkpoint and history, and evaluates it across requested window sizes. New checkpoints include state, dimensions, training config, initial base bandwidth and lock ID; pilot checkpoints remain bare network state dictionaries. Pure workflow validation rejects mixed training mode; mixed training in the planning documents remains future work for this implementation. [T], [L], [PM], [U]

## 6. Calibration & Evaluation

All compared methods within a case share incoming windows and reference-index draws, and calibration/test both average the same per-reference scoring statistic. The baseline already did this; matching reference repeats is not new functionality introduced by the refactor. [P], [PE], [E], [L]

| Setting | Pilot | New workflow |
|---|---|---|
| Reference pool | Benign train | Separate benign reference |
| Threshold | `np.quantile(cal, .95)` (default linear) | `np.quantile(null, 1-target_fpr, method="higher")` |
| Decision | score > threshold | score > threshold |
| Mixtures | Benign, requested 5% and 10% | Benign plus configurable positive ratios up to pure attack |
| Counts | `max(1, round(size*ratio))` | Half-up; interior ratios clamped to `[1,size-1]`; endpoints exact |
| Default evaluation | Window 250; calibration 200; test 100 per condition | Default grid 100/250/500/1500; calibration 200; test 100; ratios 1/5/10/25/100% |
| Repeats | Single-run default 1; batch runner/config 20 | Default 20; smoke config 2 |
| Per-row metadata | Score, threshold, detected | Adds count, requested/actual ratio and empirical p-value |
| Evidence | [PC], [PR], [PE] | [N], [E], [C], [F] |

At window 250 and requested 5%, pilot rounding gives **12/250 = 4.8%**, while the new workflow gives **13/250 = 5.2%**. This alone prevents treating the conditions as identical. The empirical p-value is `(1 + count(null >= score))/(Ncal + 1)`; the suspicious flag still uses the strict score threshold, not a p-value test. [N] `attacker_count`; [E] `evaluate`; [PM] `sampling.mixed`

FPR is the alert fraction on held-out benign windows; TPR is the alert fraction on an attacker/mixed condition. The summarizer computes AUROC against held-out benign scores per condition, sample standard deviation across seeds, and seed-paired Deep Kernel minus baseline rate differences. It requires complete runs, matching lock IDs, matching case/draw hashes, no duplicate method/seed/window/split results, and identical conditions across methods. [E], [S] `summarize`

Sampling is without replacement **within a draw**; windows and reference repeats may overlap. A nominal 5% calibration target does not guarantee 5% held-out FPR or sequential false-alarm control. Hash locks check consistency rather than provide access control or prove that nobody inspected test scores. [N], [R], [L]; [U] protocol limitations

## 7. Commands & Configuration

Run from the repository root in PowerShell. Commands below use the existing environment. The first three commands were executed successfully during this report; the remaining experiment examples were **not executed**.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m unittest discover -s pilot/tests -v
.\.venv\Scripts\python.exe -m experiments.run --config configs/experiments/deep_pure.json --window 250 --seed 42 --reference-repeats 20 --calibration-windows 200 --test-windows 500 --output artifacts/doc_check_20261103 --dry-run
```

The dry run verified seed 42 capacity for all three methods, 200 calibration windows and 3,000 total test windows across six conditions. It printed actual attacker counts `3/13/25/63/250`, kept training window 100, and did not create its output directory. It did not allocate/check CUDA or load an encoder. [W] `preflight`, `execute`

Migration from the pilot to the modular pilot retains the historical protocol:

```powershell
# Not executed: the config sets 20 reference repeats; choose a fresh output.
.\.venv\Scripts\python.exe -m pilot.deep_mmd --config pilot/configs/experiments/known_attack.json --output pilot/outputs/known_attack_20261103
```

Migration to the new protocol is a deliberate experimental change:

```powershell
# Not executed: full training/evaluation, with a new protocol under this output.
.\.venv\Scripts\python.exe -m experiments.run --config configs/experiments/deep_pure.json --output artifacts/deep_pure_20261103

# Not executed: baseline-only reuse of that exact protocol.
.\.venv\Scripts\python.exe -m experiments.run --config configs/experiments/deep_pure.json --methods rbf multi_rbf --protocol-lock artifacts/deep_pure_20261103/protocol --output artifacts/baseline_reuse_20261103

# Not executed: combine current CLI results directories, not their parent folders.
.\.venv\Scripts\python.exe -m experiments.summarize_comparison --runs artifacts/model_leeching_baseline_v1/results artifacts/model_leeching_deep_pure_v1/results --output artifacts/comparison_new_layout
```

The last command illustrates the **current CLI layout** and requires runs created with that layout; historical v1 runs are directly under their original directories and must be supplied without `/results`. Combining a three-method run with its baseline-only rerun would produce duplicate results and is intentionally rejected. [W], [S]

CLI overrides only explicitly supplied flags; `--window` changes evaluation window sizes, `--train-window` changes training size, and `--epochs` merges into training settings. Dataset flags override legacy selectors. Changing locked protocol settings requires a new lock. All real output paths must be fresh; failed runs keep failure status rather than resume automatically. [C], [Q], [W], [L]

`deep_pure.json` selects float64, CUDA, local BGE encoder, windows 100/250, 500 calibration and 200 test windows per condition. These differ from generic defaults. `mmd_smoke.json` uses 8 calibration/4 test windows and is for execution checks, not performance conclusions; `mmd_comparison.json` and smoke need a local encoder override or pinned remote revision. The two locked configs share evaluation settings but select separate baseline and Deep Kernel methods. [F], [C]

See [current command guide](../RUN_EXPERIMENTS_TH.md), [Deep Kernel protocol](../DEEP_KERNEL_PROTOCOL_TH.md), and [pilot dataset extension guide](../../pilot/docs/ADDING_DATASETS_TH.md) for full manuals.

## 8. Validation & Limitations

### Checks executed for this capture

| Check | Outcome and scope |
|---|---|
| Five required Git inventory commands; ref resolution; content inspection with `git show` and working files | Committed, staged, unstaged, net and untracked paths captured below; baseline already has Deep Kernel |
| `python -m unittest discover -s tests -v` | **23 passed**, 5.687 seconds reported by unittest; numerical kernel/MMD/variance, gradients, splitting, locked-run fixtures, CLI overrides, dry-run and failure handling |
| `python -m unittest discover -s pilot/tests -v` | **11 passed**, 3.264 seconds; fixed kernel, gradient, checkpoint, grouped splitting and custom dataset fixture |
| Capacity-only command in §7 | Exit 0; capacity passed; no encoder/GPU/full experiment |
| Static AST comparison to baseline | `draw`, `draw_reference_indices`, `mixed`, `training_pair`, `standardized_mmd`, `fit_kernel`, `score`, `repeated_score` are AST-identical after extraction; `mmd` changes helper references from `original.*` to local functions |
| Recorded artifact inspection | Read existing verification JSON and run metadata; did not replay historical checkpoints or recompute all historical CSV metrics |

Tests operate on small fixtures and mocked encoder outputs where appropriate. Their small optimization loops validate implementation; no new dataset-scale training, download or performance experiment was run. Baseline tests were not rerun at `main`; current passing tests do not establish all historical behaviors are identical. [TK], [TM], [TX], [PT]

### Recorded results, kept separate from today's checks

The committed [pilot main report](../../pilot/MAIN_RESULTS_TH.md) records six model_leeching cases on 1 November 2026: seeds 1/20/42, windows 250/500, 20 repeats, 200 calibration and 100 test windows per condition. At window 250 it reports Deep Kernel mean TPR 69.7% at requested 5%, with FPR 8.0%; at window 500, 96.7% TPR with FPR 12.0%. Its statement that seven tests and a GPU smoke passed belongs to that historical pilot scope, not today's 34 tests or the modular checkout. That report does not supply a complete source commit identity; source snapshots are linked there and were not revalidated here. [H]

The untracked [new comparison report](../MODEL_LEECHING_COMPARISON_TH.md) records the pure-training protocol: three seeds, windows 100/250, 500 calibration and 200 test windows per condition, 20 repeats, and the locked config. It reports Deep Kernel mean TPR 100% at requested 5% for both window sizes, alongside mean benign FPR **5.50% / 11.50%**. These are recorded within-protocol results, not a newly executed experiment or evidence that pure training improves on the pilot at matched FPR. [I]

Existing local [verification.json](../../artifacts/model_leeching_comparison_v1/verification.json) says 15 tests passed and records 18 CPU/GPU checkpoint replay comparisons, maximum score difference `4.440892098500626e-16`, six unchanged raw files, 16 core files matching its pretraining snapshot, and Deep Kernel threshold/selection checks. These are **historical recorded checks**, not repeated here. Its matching lock ID is `28329d08d302b40af78cc8377b657ebcacbfaceac1b6cdcc0e276abac1a26067`. [HV]

Both [baseline run metadata](../../artifacts/model_leeching_baseline_v1/metadata.json) and [Deep run metadata](../../artifacts/model_leeching_deep_pure_v1/metadata.json) record Git HEAD `961414da045d1ea4f562c62d59285644f7cd1f80`, Torch `2.11.0+cu128`, NumPy `2.5.4`, CUDA `12.8`, and that lock ID. Their pipeline source hashes differ: baseline `8357d3e6b1de1a1b8e0dcfbfb1fe3c160a9b417ad4dc01abce971f93d3217196`, Deep `0d97dbd5474b95f8c03c52278c5d6bcbfd522286a0eb428818e9aa1ffb464292`. The recorded core snapshot check does not mean the full source trees or today's working files are identical. Exact equivalence of those full snapshots is **unverified** in this report. [HV]

The pilot and pure results differ in group fractions, reference pool, learned kernel, objective, training data mixture, feature dimensions, optimizer-update budget, windows, actual ratios, calibration policy and sample counts. They cannot isolate the benefit of any one change. Neither establishes matched-FPR superiority, unseen-family performance, cross-dataset generalization, paper reproduction, independent-window confidence intervals or streaming guarantees. [H], [I], §§3–6

The existing [multi-dataset pilot report](../../pilot/MULTI_DATASET_RESULTS_TH.md) uses separate dataset runs and flags synthetic IDs/shared benign texts. It is not an unseen-family test. Original experiment-result trees outside the inventory were not scanned indiscriminately. Ignored files were consulted only at the named metadata/verification paths above. [I2]

### Documentation inconsistencies and unresolved evidence

- [BASELINE_WORKFLOW_TH.md](../BASELINE_WORKFLOW_TH.md) and [RESTRUCTURING_PLAN_TH.md](../RESTRUCTURING_PLAN_TH.md) retain some future-tense Deep Kernel design steps and historical output layouts despite newer status notes. Current code and [RUN_EXPERIMENTS_TH.md](../RUN_EXPERIMENTS_TH.md) govern the CLI layout. These existing manuals were not edited.
- The separate-command example in [DEEP_KERNEL_PROTOCOL_TH.md](../DEEP_KERNEL_PROTOCOL_TH.md) retains historical direct result paths for summarization, even though its current `experiments.run` CLI writes under `results/`. §7 distinguishes those layouts.
- External dataset provenance, actual source/user independence, semantic near-duplicate isolation and full historical source equivalence remain unverified. No network lookup was needed to document local implementation evidence.
- The hashes below fingerprint the captured files but do not archive their bytes. Reproducing this working state requires preserving those files as well as the committed tree.

## 9. References

Baseline evidence was read using `git show main:<path>` at the full baseline hash in the front matter. For stable baseline access without switching the checkout:

```powershell
git show 5fb5e07d750a73a0a663a174433bab931ae7568a:pilot/deep_kernel_pilot.py
git show 5fb5e07d750a73a0a663a174433bab931ae7568a:pilot/protocol.py
git show 5fb5e07d750a73a0a663a174433bab931ae7568a:MMD_detection/mmd_detector_gpu.py
```

- [P] Baseline `pilot/deep_kernel_pilot.py` (`mmd`, `fit_kernel`, `main`) and `pilot/protocol.py` (`make_partitions`); target [entry point](../../pilot/deep_kernel_pilot.py) and [protocol wrapper](../../pilot/protocol.py).
- [PM] Modular pilot [kernels](../../pilot/deep_mmd/kernels.py), [models](../../pilot/deep_mmd/models.py), [training](../../pilot/deep_mmd/training.py), [sampling](../../pilot/deep_mmd/sampling.py), [experiment](../../pilot/deep_mmd/experiment.py).
- [PD] Pilot [registry](../../pilot/deep_mmd/datasets/registry.py), [protocol](../../pilot/deep_mmd/datasets/protocol.py), [dataset specs](../../pilot/configs/datasets/).
- [PC] Pilot [CLI](../../pilot/deep_mmd/cli.py); [PR] [batch runner](../../pilot/run_known_pilot.py); [PE] [evaluation](../../pilot/deep_mmd/evaluation.py); [PB] [encoder/cache](../../pilot/deep_mmd/embeddings.py).
- [K] Fixed [detector](../../detectors/mmd/detector.py) and learned [model](../../detectors/deep_kernel_mmd/model.py); [T] pure [training](../../detectors/deep_kernel_mmd/training.py).
- [D] [datasets](../../data_pipeline/datasets.py); [B] [embeddings](../../data_pipeline/embeddings.py); [N] [windows](../../data_pipeline/windows.py); [E] [evaluation](../../evaluation/windows.py).
- [R] [run](../../experiments/run.py); [L] [locked protocol](../../experiments/locked.py); [W] [workflow](../../experiments/workflow.py); [Q] [CLI](../../experiments/cli.py); [C] [configuration](../../experiments/configuration.py).
- [A] [audit_data](../../experiments/audit_data.py); [S] [summarize_comparison](../../experiments/summarize_comparison.py); [F] [experiment configs](../../configs/experiments/), [pilot config](../../pilot/configs/experiments/known_attack.json).
- [TK] [deep tests](../../tests/test_deep_kernel.py); [TM] [MMD pipeline tests](../../tests/test_mmd_pipeline.py); [TX] [CLI tests](../../tests/test_experiment_cli.py); [PT] [pilot tests](../../pilot/tests/).
- [H] [pilot main results](../../pilot/MAIN_RESULTS_TH.md); [I] [pure comparison](../MODEL_LEECHING_COMPARISON_TH.md); [I2] [multi-dataset results](../../pilot/MULTI_DATASET_RESULTS_TH.md).
- [HV] [historical verification](../../artifacts/model_leeching_comparison_v1/verification.json), [baseline metadata](../../artifacts/model_leeching_baseline_v1/metadata.json), [Deep metadata](../../artifacts/model_leeching_deep_pure_v1/metadata.json). These artifacts are ignored local files and may not exist in a fresh checkout.
- [U] [protocol](../DEEP_KERNEL_PROTOCOL_TH.md), [workflow manual](../BASELINE_WORKFLOW_TH.md), [restructuring plan](../RESTRUCTURING_PLAN_TH.md), [command guide](../RUN_EXPERIMENTS_TH.md), [pilot architecture](../../pilot/docs/ARCHITECTURE_TH.md).
- [O] [original detector](../../MMD_detection/mmd_detector_gpu.py); [G] [README](../../README.md), [.gitignore](../../.gitignore).
