# Phase D detailed diagnostic tables

Development only: 3 reused cohorts, 10 schedules per cohort. Each TPR cell has 30 schedules.
Columns show post-onset first detections/all schedules; all prefix alarms were zero in this run.
Nominal alpha is not an established matched population FPR. Alpha 0.05 has infinite thresholds.

## Nominal alpha 0.2

| Candidate | FP / 3 | TPR26 R/C/I | TPR64 R/C/I | TPR128 R/C/I |
| --- | --- | --- | --- | --- |
| original | 0/3 | 0/30 / 1/30 / 0/30 | 1/30 / 1/30 / 0/30 | 11/30 / 21/30 / 13/30 |
| rolling_32 | 0/3 | 0/30 / 4/30 / 0/30 | 1/30 / 7/30 / 1/30 | 12/30 / 17/30 / 12/30 |
| rolling_64 | 1/3 | 0/30 / 5/30 / 1/30 | 2/30 / 16/30 / 2/30 | 21/30 / 21/30 / 23/30 |
| rolling_100 | 1/3 | 0/30 / 2/30 / 1/30 | 2/30 / 9/30 / 3/30 | 22/30 / 24/30 / 24/30 |
| cusum_upper_k0.5 | 1/3 | 3/30 / 6/30 / 1/30 | 0/30 / 10/30 / 0/30 | 0/30 / 0/30 / 0/30 |
| cusum_lower_k0.5 | 0/3 | 0/30 / 0/30 / 0/30 | 19/30 / 21/30 / 17/30 | 23/30 / 25/30 / 23/30 |
| cusum_two_sided_k0.5 | 0/3 | 0/30 / 0/30 / 0/30 | 19/30 / 21/30 / 17/30 | 23/30 / 25/30 / 23/30 |
| cusum_upper_k1.0 | 0/3 | 1/30 / 4/30 / 1/30 | 0/30 / 7/30 / 0/30 | 0/30 / 0/30 / 0/30 |
| cusum_lower_k1.0 | 0/3 | 0/30 / 3/30 / 1/30 | 14/30 / 23/30 / 16/30 | 23/30 / 25/30 / 22/30 |
| cusum_two_sided_k1.0 | 0/3 | 0/30 / 3/30 / 1/30 | 14/30 / 23/30 / 16/30 | 23/30 / 25/30 / 22/30 |

| Candidate | 50% median detected delay R/C/I | 50% changed detection pairs RC/RI/CI |
| --- | --- | --- |
| original | 108.0 / 98.0 / 104.0 | 12/30 / 8/30 / 8/30 |
| rolling_32 | 62.0 / 93.0 / 70.0 | 11/30 / 10/30 / 11/30 |
| rolling_64 | 68.0 / 101.0 / 55.0 | 8/30 / 6/30 / 6/30 |
| rolling_100 | 85.0 / 76.0 / 81.5 | 2/30 / 2/30 / 0/30 |
| cusum_upper_k0.5 | null / null / null | 0/30 / 0/30 / 0/30 |
| cusum_lower_k0.5 | 56.0 / 56.0 / 59.0 | 2/30 / 2/30 / 2/30 |
| cusum_two_sided_k0.5 | 56.0 / 56.0 / 59.0 | 2/30 / 2/30 / 2/30 |
| cusum_upper_k1.0 | null / null / null | 0/30 / 0/30 / 0/30 |
| cusum_lower_k1.0 | 49.0 / 43.0 / 46.0 | 2/30 / 3/30 / 3/30 |
| cusum_two_sided_k1.0 | 49.0 / 43.0 / 46.0 | 2/30 / 3/30 / 3/30 |

## Nominal alpha 0.4

| Candidate | FP / 3 | TPR26 R/C/I | TPR64 R/C/I | TPR128 R/C/I |
| --- | --- | --- | --- | --- |
| original | 0/3 | 7/30 / 3/30 / 1/30 | 6/30 / 14/30 / 8/30 | 28/30 / 30/30 / 29/30 |
| rolling_32 | 1/3 | 9/30 / 25/30 / 6/30 | 8/30 / 28/30 / 6/30 | 26/30 / 26/30 / 27/30 |
| rolling_64 | 2/3 | 4/30 / 19/30 / 9/30 | 9/30 / 30/30 / 8/30 | 27/30 / 28/30 / 27/30 |
| rolling_100 | 2/3 | 9/30 / 18/30 / 12/30 | 11/30 / 23/30 / 10/30 | 28/30 / 28/30 / 26/30 |
| cusum_upper_k0.5 | 1/3 | 10/30 / 10/30 / 8/30 | 1/30 / 10/30 / 1/30 | 0/30 / 2/30 / 0/30 |
| cusum_lower_k0.5 | 2/3 | 19/30 / 20/30 / 19/30 | 20/30 / 30/30 / 20/30 | 30/30 / 30/30 / 30/30 |
| cusum_two_sided_k0.5 | 2/3 | 19/30 / 20/30 / 19/30 | 20/30 / 30/30 / 20/30 | 30/30 / 30/30 / 30/30 |
| cusum_upper_k1.0 | 1/3 | 10/30 / 10/30 / 7/30 | 4/30 / 16/30 / 0/30 | 1/30 / 1/30 / 0/30 |
| cusum_lower_k1.0 | 1/3 | 10/30 / 21/30 / 14/30 | 20/30 / 29/30 / 21/30 | 28/30 / 30/30 / 26/30 |
| cusum_two_sided_k1.0 | 1/3 | 10/30 / 21/30 / 14/30 | 20/30 / 29/30 / 21/30 | 28/30 / 30/30 / 26/30 |

| Candidate | 50% median detected delay R/C/I | 50% changed detection pairs RC/RI/CI |
| --- | --- | --- |
| original | 87.5 / 67.0 / 78.0 | 2/30 / 3/30 / 1/30 |
| rolling_32 | 47.0 / 75.0 / 50.0 | 6/30 / 5/30 / 1/30 |
| rolling_64 | 52.0 / 45.0 / 50.0 | 3/30 / 4/30 / 1/30 |
| rolling_100 | 71.5 / 59.0 / 62.0 | 2/30 / 2/30 / 2/30 |
| cusum_upper_k0.5 | null / 140.5 / null | 2/30 / 0/30 / 2/30 |
| cusum_lower_k0.5 | 23.5 / 20.0 / 21.5 | 0/30 / 0/30 / 0/30 |
| cusum_two_sided_k0.5 | 23.5 / 20.0 / 21.5 | 0/30 / 0/30 / 0/30 |
| cusum_upper_k1.0 | 124.0 / 145.0 / null | 2/30 / 1/30 / 1/30 |
| cusum_lower_k1.0 | 22.5 / 21.5 / 20.0 | 2/30 / 2/30 / 4/30 |
| cusum_two_sided_k1.0 | 22.5 / 21.5 / 20.0 | 2/30 / 2/30 / 4/30 |
