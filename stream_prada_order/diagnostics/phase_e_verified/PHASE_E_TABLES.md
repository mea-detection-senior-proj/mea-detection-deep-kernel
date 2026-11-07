# Phase E diagnostic tables

Development only: 3 outer source cohorts; 10 conditional schedules each. Counts have denominator 30.
Surrogate rows are offline score-path crossings, not measured attack TPR or real detection delays.
Endpoint controls decide at Q256 only; alpha .05 has infinite thresholds for every candidate.

## Nominal alpha 0.2

| Candidate | Benign FP/3 | Attack26 R/C/I | Attack64 R/C/I | Attack128 R/C/I |
| --- | --- | --- | --- | --- |
| original | 0/3 | 0 / 1 / 0 | 1 / 1 / 0 | 11 / 21 / 13 |
| length_endpoint | 0/3 | 30 / 30 / 30 | 30 / 30 / 30 | 30 / 30 / 30 |
| distance_mean_endpoint | 0/3 | 0 / 0 / 0 | 18 / 18 / 17 | 22 / 25 / 25 |
| cusum_k0.5 | 0/3 | 0 / 0 / 0 | 19 / 21 / 17 | 23 / 25 / 23 |
| length_adjusted_k0.5 | 0/3 | 0 / 0 / 0 | 17 / 20 / 16 | 20 / 25 / 20 |
| prefix_centered_k0.5 | 1/3 | 10 / 23 / 13 | 28 / 30 / 28 | 30 / 30 / 30 |
| combined_k0.5 | 0/3 | 6 / 19 / 5 | 23 / 30 / 27 | 30 / 30 / 30 |
| surrogate_reverse_k0.5 | 0/3 | 0 / 0 / 0 | 19 / 21 / 19 | 23 / 27 / 23 |
| surrogate_shuffle17_k0.5 | 0/3 | 0 / 0 / 0 | 19 / 18 / 17 | 22 / 25 / 23 |
| surrogate_shuffle29_k0.5 | 0/3 | 0 / 0 / 0 | 19 / 18 / 17 | 22 / 24 / 23 |
| cusum_k1.0 | 0/3 | 0 / 3 / 1 | 14 / 23 / 16 | 23 / 25 / 22 |
| length_adjusted_k1.0 | 0/3 | 0 / 4 / 0 | 12 / 22 / 11 | 20 / 25 / 20 |
| prefix_centered_k1.0 | 1/3 | 5 / 16 / 7 | 18 / 30 / 16 | 30 / 30 / 30 |
| combined_k1.0 | 0/3 | 4 / 13 / 3 | 13 / 30 / 10 | 30 / 30 / 29 |
| surrogate_reverse_k1.0 | 0/3 | 0 / 3 / 1 | 16 / 23 / 16 | 23 / 25 / 22 |
| surrogate_shuffle17_k1.0 | 0/3 | 2 / 4 / 0 | 19 / 22 / 19 | 23 / 25 / 24 |
| surrogate_shuffle29_k1.0 | 0/3 | 2 / 0 / 2 | 17 / 20 / 19 | 21 / 24 / 23 |

| Candidate | Attack128 median detected delay R/C/I | Changed detections RC/RI/CI /30 |
| --- | --- | --- |
| original | 108.0 / 98.0 / 104.0 | 12 / 8 / 8 |
| length_endpoint | 145.0 / 145.0 / 145.0 | 0 / 0 / 0 |
| distance_mean_endpoint | 145.0 / 145.0 / 145.0 | 3 / 3 / 0 |
| cusum_k0.5 | 56.0 / 56.0 / 59.0 | 2 / 2 / 2 |
| length_adjusted_k0.5 | 57.5 / 57.0 / 60.5 | 5 / 0 / 5 |
| prefix_centered_k0.5 | 22.0 / 20.0 / 21.5 | 0 / 0 / 0 |
| combined_k0.5 | 26.0 / 22.0 / 22.5 | 0 / 0 / 0 |
| cusum_k1.0 | 49.0 / 43.0 / 46.0 | 2 / 3 / 3 |
| length_adjusted_k1.0 | 47.0 / 43.0 / 44.5 | 5 / 0 / 5 |
| prefix_centered_k1.0 | 26.0 / 22.0 / 24.5 | 0 / 0 / 0 |
| combined_k1.0 | 43.0 / 25.0 / 26.0 | 0 / 1 / 1 |

## Nominal alpha 0.4

| Candidate | Benign FP/3 | Attack26 R/C/I | Attack64 R/C/I | Attack128 R/C/I |
| --- | --- | --- | --- | --- |
| original | 0/3 | 7 / 3 / 1 | 6 / 14 / 8 | 28 / 30 / 29 |
| length_endpoint | 2/3 | 30 / 30 / 30 | 30 / 30 / 30 | 30 / 30 / 30 |
| distance_mean_endpoint | 1/3 | 19 / 17 / 17 | 20 / 20 / 20 | 30 / 30 / 30 |
| cusum_k0.5 | 2/3 | 19 / 20 / 19 | 20 / 30 / 20 | 30 / 30 / 30 |
| length_adjusted_k0.5 | 1/3 | 19 / 20 / 19 | 20 / 29 / 20 | 30 / 30 / 29 |
| prefix_centered_k0.5 | 1/3 | 13 / 30 / 20 | 28 / 30 / 30 | 30 / 30 / 30 |
| combined_k0.5 | 1/3 | 13 / 29 / 20 | 28 / 30 / 29 | 30 / 30 / 30 |
| surrogate_reverse_k0.5 | 2/3 | 19 / 20 / 19 | 20 / 30 / 20 | 30 / 30 / 30 |
| surrogate_shuffle17_k0.5 | 1/3 | 18 / 20 / 18 | 20 / 24 / 20 | 30 / 30 / 30 |
| surrogate_shuffle29_k0.5 | 2/3 | 19 / 19 / 17 | 20 / 23 / 20 | 30 / 30 / 30 |
| cusum_k1.0 | 1/3 | 10 / 21 / 14 | 20 / 29 / 21 | 28 / 30 / 26 |
| length_adjusted_k1.0 | 1/3 | 10 / 18 / 10 | 19 / 27 / 21 | 26 / 28 / 25 |
| prefix_centered_k1.0 | 1/3 | 13 / 27 / 21 | 26 / 30 / 25 | 30 / 30 / 30 |
| combined_k1.0 | 1/3 | 16 / 28 / 20 | 26 / 30 / 27 | 30 / 30 / 30 |
| surrogate_reverse_k1.0 | 1/3 | 11 / 20 / 14 | 20 / 29 / 21 | 28 / 30 / 26 |
| surrogate_shuffle17_k1.0 | 1/3 | 17 / 21 / 20 | 22 / 27 / 23 | 30 / 30 / 29 |
| surrogate_shuffle29_k1.0 | 1/3 | 20 / 19 / 22 | 24 / 26 / 25 | 30 / 29 / 29 |

| Candidate | Attack128 median detected delay R/C/I | Changed detections RC/RI/CI /30 |
| --- | --- | --- |
| original | 87.5 / 67.0 / 78.0 | 2 / 3 / 1 |
| length_endpoint | 145.0 / 145.0 / 145.0 | 0 / 0 / 0 |
| distance_mean_endpoint | 145.0 / 145.0 / 145.0 | 0 / 0 / 0 |
| cusum_k0.5 | 23.5 / 20.0 / 21.5 | 0 / 0 / 0 |
| length_adjusted_k0.5 | 25.5 / 22.0 / 22.0 | 0 / 1 / 1 |
| prefix_centered_k0.5 | 20.0 / 18.0 / 19.5 | 0 / 0 / 0 |
| combined_k0.5 | 20.0 / 18.0 / 19.0 | 0 / 0 / 0 |
| cusum_k1.0 | 22.5 / 21.5 / 20.0 | 2 / 2 / 4 |
| length_adjusted_k1.0 | 22.0 / 21.0 / 21.0 | 2 / 3 / 3 |
| prefix_centered_k1.0 | 22.0 / 18.0 / 20.5 | 0 / 0 / 0 |
| combined_k1.0 | 21.0 / 18.0 / 20.0 | 0 / 0 / 0 |
