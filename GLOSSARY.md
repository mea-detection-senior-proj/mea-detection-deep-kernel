# Model Extraction Traffic Detection

Shared language for detecting model extraction in query traffic and studying learned kernels for MMD.

## Language

**Model extraction attack**:
An attempt to approximate a protected model or its capabilities by collecting responses to queries submitted to that model.
_Avoid_: Treating every unusual query as proof of extraction

**Benign traffic**:
Queries submitted for legitimate use of the protected service rather than model extraction.
_Avoid_: Normal model, clean model

**Detection window**:
A collection of incoming queries evaluated together to decide whether its traffic distribution is suspicious.
_Avoid_: Using window size and attacker fraction interchangeably

**Window size**:
The total number of queries in a detection window, including both benign and attacker queries.
_Avoid_: Attack-query count, attacker fraction

**Attacker fraction**:
The proportion of queries in a detection window that belong to extraction traffic.
_Avoid_: Low-query budget when referring only to low attacker fraction

**Low-query detection**:
Detection using a small total number of observed queries in each detection window.
_Avoid_: Treating low attacker fraction alone as evidence of low-query detection

**Minimum effective window size**:
The smallest evaluated window size that reaches a prespecified detection rate at a specified attacker fraction and false-positive budget.
_Avoid_: Guaranteed detection latency, minimum number of attacker queries

**Unseen attack family**:
An extraction strategy family excluded from kernel training, parameter tuning, and method selection, and reserved for evaluating generalization.
_Avoid_: Unseen queries from a family already used for training

**Known-attack evaluation**:
Evaluation on held-out queries from attack families represented in detector training.
_Avoid_: Evaluation on training queries, unseen-family evaluation

**Pure-attack training**:
Kernel training that compares benign groups with incoming groups made entirely of known attack queries.
_Avoid_: Assuming that benign examples are absent from training

**Mixed-traffic training**:
Kernel training that compares benign groups with incoming groups containing both benign and attack queries.
_Avoid_: Mixed-traffic evaluation

**Mixed-traffic evaluation**:
Testing a detector on incoming windows containing both benign and attack queries, regardless of how the detector was trained.
_Avoid_: Assuming that testing mixtures requires training on mixtures

**Benign reference traffic**:
Historical benign queries that define the distribution against which incoming detection windows are compared.
_Avoid_: Attacker reference, ground-truth test traffic

**Calibration target FPR**:
The intended benign-window false-positive rate used to set an alert threshold from benign calibration traffic.
_Avoid_: Guaranteed test FPR

**Measured FPR**:
The fraction of evaluated benign windows flagged by the detector at its fixed calibrated threshold.
_Avoid_: Treating the calibration target as the measured result

**Fixed-kernel MMD detector**:
A traffic-window detector that measures maximum mean discrepancy using a kernel whose comparison geometry is not learned from attacker examples.
_Avoid_: Calling it a detector with no deep encoder merely because its kernel is fixed

**Deep-kernel MMD detector**:
A traffic-window detector that measures maximum mean discrepancy using a kernel with a learned neural feature map.
_Avoid_: Equating a pretrained sentence encoder alone with learning a deep kernel
