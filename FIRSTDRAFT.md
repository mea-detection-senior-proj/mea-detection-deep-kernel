# Senior Project Proposal

## Project Title

**Power-Optimized Deep Kernel MMD for Low-Query Detection of LLM Model Extraction Attacks**

**ชื่อภาษาไทย:** การเพิ่มประสิทธิภาพการตรวจจับการโจมตีเพื่อขโมยโมเดลภาษาภายใต้จำนวนคำถามจำกัดด้วย Deep Kernel Maximum Mean Discrepancy

**Project Type:** Machine Learning / AI Security / Experimental Research

**Duration:** 12–16 Weeks (1 Semester)

**Team Size:** 2–3 Students

**Computing Resources:** GPU or Google Colab

---

## 1. Background and Problem Statement

Large Language Models (LLMs) are increasingly provided through APIs. Although users cannot directly access the model parameters, malicious actors may repeatedly query a target model and collect query–response pairs to train a substitute model. This behavior is known as a Model Extraction Attack.

Traditional detection approaches attempt to identify suspicious queries using anomalies, query patterns, or distribution differences.

Maximum Mean Discrepancy (MMD) is a statistical method used to compare two probability distributions. Recent work has demonstrated that MMD over semantic query embeddings can detect model extraction behavior in LLM API traffic.

However, detection remains challenging when attack queries are semantically similar to legitimate queries, when attackers contribute only a small fraction of traffic, or when few queries are available for analysis.

Deep Kernel Learning offers a possible solution by learning a task-adapted kernel through a neural network. Rather than relying entirely on a fixed RBF kernel, the system can learn a representation that improves statistical test power.

This project investigates whether Deep Kernel MMD can improve the detection of LLM model extraction attacks under limited query budgets compared with conventional MMD approaches.

## 2. Project Objectives

### Primary Objective

To develop and evaluate a Deep Kernel MMD-based model extraction detection framework and compare its statistical detection performance with fixed-kernel MMD baselines.

### Specific Objectives

1. Implement RBF MMD and Multi-RBF MMD as baseline detectors.
2. Develop a Deep Kernel MMD model using a trainable neural network over frozen text embeddings.
3. Train the Deep Kernel using a test-power-oriented optimization objective.
4. Evaluate detection performance across different query-window sizes and attack-query proportions.
5. Investigate generalization to at least one unseen attack family.
6. Develop an offline traffic-monitoring demonstration that visualizes detection scores and alerts.

## 3. Research Questions

**RQ1: Detection Performance**

Does Deep Kernel MMD improve the detection rate of LLM model extraction traffic compared with fixed RBF and Multi-RBF MMD under the same false-positive constraint?

**RQ2: Limited-Query Detection**

Can Deep Kernel MMD detect model extraction attacks with fewer observed queries than the baseline methods?

**RQ3: Generalization**

How well does a Deep Kernel trained on known extraction strategies generalize to an extraction strategy excluded from training?

### Research Hypotheses

- **H1:** Deep Kernel MMD achieves higher True Positive Rate (TPR) than fixed-kernel MMD at a matched False Positive Rate (FPR) in at least some low-query scenarios.
- **H2:** Deep Kernel MMD reduces the query-window size required to reach a target detection rate.
- **H3:** The performance advantage, if any, can be evaluated on unseen extraction strategies rather than only on training attack patterns.

These are hypotheses to be tested, not guaranteed outcomes.

## 4. Project Scope

### 4.1 In Scope

- Text-only LLM API queries
- Offline simulation of incoming query traffic
- Query-window-level detection
- Pretrained sentence embeddings
- RBF MMD and Multi-RBF MMD baselines
- Neural network-based Deep Kernel Learning
- Benign-only decision-threshold calibration
- Statistical performance evaluation
- Experimental comparison across query budgets
- Offline detection dashboard or visualization

### 4.2 Out of Scope

- Training a large Victim LLM
- Extracting proprietary commercial models
- Full production API security infrastructure
- Large-scale distributed or multi-account attack attribution
- Real-time deployment guarantees
- Complete prevention of all model extraction techniques
- Multimodal attacks involving images, audio, or video

The project focuses on detecting suspicious query-distribution shifts rather than proving malicious intent or guaranteeing extraction prevention.

## 5. Proposed System Architecture

### 5.1 System Pipeline

1. **Input Data:** Historical benign queries and simulated incoming query windows
2. **Sentence Encoder:** Convert text queries into fixed-dimensional semantic embeddings
3. **Deep Kernel Network:** Transform embeddings through a trainable multilayer perceptron (MLP)
4. **Kernel Computation:** Compute similarities using the learned kernel
5. **MMD Statistic:** Compare incoming query-window distributions against benign reference distributions
6. **Threshold Calibration:** Estimate decision thresholds using held-out benign queries
7. **Detection Output:** Produce an MMD score and suspicious/normal window-level decision

### 5.2 Proposed Model Configuration

| Component | Proposed Configuration |
|---|---|
| Text Encoder | BAAI/bge-small-en-v1.5 |
| Encoder Training | Frozen |
| Neural Network | Two-layer MLP |
| Example Dimensions | 384 → 128 → 64 |
| Activation | ReLU |
| Kernel | Deep-feature RBF combined with a base RBF kernel |
| Training Framework | PyTorch |
| Optimizer | Adam |
| Objective | Regularized MMD test-power criterion |
| Detection Unit | Query Window |

The architecture is intentionally small to minimize computational cost and reduce implementation risk.

### 5.3 Deep Kernel Training

Let the frozen sentence encoder produce:

`z = Encoder(query)`

The MLP learns a transformation:

`h = gθ(z)`

A Deep Kernel is constructed using the learned representation while retaining a base kernel on the original embedding space.

The training objective is based on maximizing the ratio between estimated squared MMD and its estimated variability.

Conceptually:

`J(θ) = MMD²(θ) / sqrt(Variance(θ) + λ)`

The optimizer minimizes:

`Loss(θ) = -J(θ)`

Training uses benign queries and known attack queries. Once training is complete, the kernel parameters are frozen for evaluation and deployment simulation.

### 5.4 Baseline Models

The project will compare at least:

1. **RBF MMD:** Fixed Gaussian RBF kernel with standard bandwidth selection.
2. **Multi-RBF MMD:** Multiple bandwidths combined without learning a neural feature transformation.
3. **Deep Kernel MMD:** Learned neural representation with a test-power-oriented objective.

A supervised classifier-based baseline is recommended if time permits, to distinguish the benefit of the MMD objective from the benefit of using labeled attack data.

## 6. Dataset

### 6.1 Primary Dataset

The project will use processed benign and attacker query datasets referenced by:

**An Embarrassingly Simple Detector for Model Extraction Attacks in Large Language Model API Traffic (EMNLP 2026).**

Source repository:

https://github.com/LabRAI/mmd-llm-mea-detection

Dataset location listed by the authors:

https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data

The source study includes query pairs from multiple extraction scenarios, including Model Leeching, MeaeQ, BERT-based API extraction, and query-efficient medical-domain extraction.

Dataset availability, sizes, licensing, duplicates, and suitability for supervised kernel training will be verified during the first two weeks.

### 6.2 Initial Dataset Scope

The minimum target is to select three distinct attack families where sufficient benign and attacker query data are available.

These will support:

- Known-attack training
- Benign-only calibration
- Held-out evaluation
- At least one unseen-attack-family experiment

If the available data support it, leave-one-attack-family-out evaluation will be used.

### 6.3 Data Preparation and Splitting

The project will separate data by purpose:

- **Kernel Training:** Benign and known-attack examples for learning neural network parameters
- **Validation:** Examples for model selection and early stopping
- **Benign Reference:** Historical benign queries used for MMD comparisons
- **Benign Calibration:** Benign queries used to determine alarm thresholds
- **Held-out Benign Test:** Independent benign examples for measuring FPR
- **Held-out Attack Test:** Attack examples for measuring detection power

Identical or near-duplicate queries will be checked across partitions. Where user or campaign identifiers are unavailable, the project will explicitly report that true user-level independence cannot be guaranteed.

The held-out attack family must not be used for kernel training, parameter tuning, or method selection.

## 7. Experimental Plan

### Experiment 1 — Baseline Reproduction

**Objective:** Establish a reliable comparison with conventional MMD.

Methods:

- RBF MMD
- Multi-RBF MMD

Tasks:

- Load and inspect query datasets
- Generate or cache text embeddings
- Construct benign and attack query windows
- Compute MMD statistics
- Calibrate thresholds using benign-only data
- Evaluate detection results

**Expected Output:** Reproducible baseline detection metrics.

### Experiment 2 — Deep Kernel Learning

**Objective:** Develop and train the proposed Deep Kernel model.

Tasks:

- Implement an MLP embedding transformation
- Implement learned kernel computation
- Implement regularized test-power training
- Monitor training and validation performance
- Freeze the kernel for held-out testing

**Expected Output:** A trained Deep Kernel MMD detector.

### Experiment 3 — Query-Window Size

**Objective:** Evaluate the effect of available query count on detection power.

Proposed window sizes:

| Window Size | Evaluation Purpose |
|---|---|
| 100 | Very limited query budget |
| 250 | Small query budget |
| 500 | Moderate query budget |
| 1,500 | Reference setting from the prior work |

The evaluation compares detection rates for the same window size, dataset, and threshold policy.

A smaller successful window size is evidence of improved low-query detection, but it is not automatically equivalent to lower real-time detection latency.

### Experiment 4 — Mixed-Traffic Detection

**Objective:** Determine whether the proposed model can detect extraction queries diluted by legitimate traffic.

Proposed attack proportions:

- 5% Attack / 95% Benign
- 10% Attack / 90% Benign
- 25% Attack / 75% Benign
- 100% Attack

An optional 1% attack setting may be included if sufficient data and evaluation time are available.

### Experiment 5 — Unseen Attack Generalization

**Objective:** Test whether the learned kernel generalizes beyond known attack strategies.

Example procedure:

1. Train using Attack Families A and B.
2. Perform model selection using data that exclude Family C.
3. Calibrate the threshold using legitimate benign samples.
4. Evaluate using previously unseen Attack Family C.
5. Rotate the held-out family when dataset coverage permits.

This experiment will be used to identify whether improvements depend mainly on previously observed attack patterns.

## 8. Evaluation Metrics

### Primary Metrics

- **TPR at matched FPR:** Compare detectors at the same benign false-positive operating point.
- **FPR:** Fraction of held-out benign windows incorrectly flagged.
- **Minimum Effective Window Size:** Smallest evaluated window that reaches a predefined target TPR at controlled FPR.
- **Generalization Gap:** Difference between performance on known and unseen attack families.

### Secondary Metrics

- AUROC
- Balanced Accuracy
- Precision and Recall when class proportions are meaningful
- Training Time
- Detection Runtime
- Sensitivity to kernel bandwidth and embedding architecture

The primary comparison will target FPR ≤ 5%, with stricter 1% FPR experiments included if the number of sufficiently independent benign evaluation windows supports reliable estimation.

Experiments will use multiple random seeds and report variability or confidence intervals where feasible.

## 9. Development Timeline

| Period | Main Tasks | Milestone |
|---|---|---|
| Weeks 1–2 | Literature review, dataset access, environment setup, initial reproduction | Dataset and runnable baseline |
| Weeks 3–4 | Implement and validate RBF / Multi-RBF MMD | Baseline results completed |
| Weeks 5–6 | Design MLP and Deep Kernel computation; verify loss and gradients | Working Deep Kernel implementation |
| Weeks 7–8 | Train, tune and validate Deep Kernel | Trained detector |
| Weeks 9–10 | Query-window and attack-ratio experiments | Comparative results |
| Weeks 11–12 | Unseen-attack testing, runtime, statistical analysis | Final experimental results |
| Weeks 13–14 | Dashboard, documentation, report and presentation | Completed deliverables |
| Weeks 15–16 | Buffer for debugging, repeat experiments and advisor feedback | Final revision, if available |

### Checkpoints and Contingency Plan

**End of Week 2:** If the reference dataset cannot be accessed or used, identify a smaller licensed dataset and simplify attack-family coverage.

**End of Week 4:** If the MMD baseline cannot be reproduced, prioritize establishing a correct baseline before starting kernel training.

**End of Week 8:** If the test-power objective is unstable, compare a simpler learned RBF representation and Multi-RBF baseline while documenting the limitation.

**End of Week 12:** If Deep Kernel does not outperform conventional MMD, complete a rigorous comparative analysis explaining performance, generalization, computational cost, and possible causes.

The project is designed to remain academically evaluable without assuming that the proposed method must outperform every baseline.

## 10. Team Responsibilities

For three members:

| Member | Primary Responsibility |
|---|---|
| Student A | Literature review, dataset preparation, baseline methods |
| Student B | Deep Kernel architecture, training objective, optimization |
| Student C | Experimental evaluation, statistical analysis, demo |

All members contribute to methodology, integration, validation, and documentation.

For two members, experimental evaluation and the demo can be divided between the baseline and Deep Kernel developers.

## 11. Expected Deliverables

1. Source code for RBF MMD, Multi-RBF MMD, and Deep Kernel MMD
2. A reproducible data-preparation and experimental pipeline
3. Trained Deep Kernel model checkpoint
4. Detection results and comparison plots
5. Low-query and unseen-attack evaluation
6. An offline traffic-detection demonstration
7. Final Senior Project report
8. Presentation slides and demonstration materials

## 12. Expected Contribution

The project aims to provide an empirical evaluation of whether power-optimized Deep Kernel Learning improves MMD-based detection of LLM model extraction traffic.

Its contribution will focus on three aspects:

1. Comparing fixed and learned kernels under a common detection protocol.
2. Measuring detection power when only a limited number of queries is available.
3. Evaluating whether learned kernels generalize to previously unseen attack strategies.

The expected output is a reproducible experimental framework and evidence-based conclusions about the effectiveness and limitations of Deep Kernel MMD for this security application.

## 13. Limitations and Ethical Considerations

The detector identifies distributional anomalies and does not independently establish that a user is performing model theft.

Its effectiveness depends on the quality and representativeness of benign references and on observable distributional differences between attackers and legitimate users.

The project will use publicly available or appropriately licensed research data and will not conduct unauthorized extraction against third-party services.

Any monitoring demonstration will operate on simulated or offline query traffic.

## 14. Key References

1. Liu, F., et al. (2020). *Learning Deep Kernels for Non-Parametric Two-Sample Tests*. ICML.  
   https://proceedings.mlr.press/v119/liu20m.html

2. Pal, S., et al. (2021). *Stateful Detection of Model Extraction Attacks*. arXiv.  
   https://arxiv.org/abs/2107.05166

3. Liu, S., Guo, Q., & Dong, Y. (2026). *An Embarrassingly Simple Detector for Model Extraction Attacks in Large Language Model API Traffic*. EMNLP.  
   https://aclanthology.org/2026.emnlp-main.748/

4. Biggs, F., Schrab, A., & Gretton, A. (2023). *MMD-FUSE: Learning and Combining Kernels for Two-Sample Testing Without Data Splitting*. NeurIPS.  
   https://arxiv.org/abs/2306.08777
