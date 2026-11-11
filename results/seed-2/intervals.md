# Paired intervals: seed-1, seed-2

Mean paired difference on the same (seed, problem, checkpoint); 95% percentile bootstrap over problems (2000 resamples, a problem's checkpoints and seeds resampled together). Arm D's erosion and verbosity are scored without its tests/. Cost ratio is sum(arm cost) / sum(A cost) − 1 on the same pairs.

## 1. Arms against A (primary contrast: C − A)

| Contrast | Seeds | Pairs | Δ cost / ckpt | Δ hidden-test pass | Δ strict solve | Δ erosion | Δ verbosity | Cost ratio |
|---|---|---|---|---|---|---|---|---|
| C − A | seed-1 | 101 | +0.150 [+0.116, +0.203] | -0.6pp [-1.9, +0.5] | +0.0pp [-6.4, +5.2] | -0.003 [-0.031, +0.028] | +0.007 [-0.076, +0.099] | +51% [+28, +86] |
| C − A | seed-2 | 101 | +0.145 [+0.096, +0.209] | -1.9pp [-3.6, -0.6] | -5.9pp [-16.0, +2.9] | -0.052 [-0.090, -0.019] | -0.019 [-0.115, +0.099] | +54% [+40, +77] |
| C − A | pooled | 202 | +0.147 [+0.113, +0.192] | -1.3pp [-2.5, -0.3] | -3.0pp [-10.4, +2.6] | -0.027 [-0.052, -0.003] | -0.006 [-0.079, +0.080] | +53% [+36, +76] |
| B − A | seed-1 | 101 | +0.013 [-0.031, +0.048] | -1.7pp [-4.0, +0.0] | +1.0pp [-9.9, +15.2] | -0.010 [-0.040, +0.024] | +0.099 [-0.007, +0.203] | +4% [-7, +22] |
| B − A | seed-2 | 101 | +0.026 [+0.013, +0.039] | -2.4pp [-4.5, -0.5] | -10.9pp [-22.0, -1.1] | -0.040 [-0.083, -0.001] | -0.013 [-0.124, +0.090] | +10% [+4, +18] |
| B − A | pooled | 202 | +0.019 [-0.005, +0.039] | -2.0pp [-4.0, -0.6] | -5.0pp [-12.7, +2.1] | -0.025 [-0.049, -0.002] | +0.043 [-0.052, +0.137] | +7% [-1, +18] |
| D − A | seed-1 | 101 | +0.014 [-0.067, +0.074] | -1.7pp [-3.8, +0.0] | +2.0pp [-7.7, +13.5] | -0.083 [-0.124, -0.047] | -0.058 [-0.192, +0.067] | +5% [-15, +35] |
| D − A | seed-2 | 101 | +0.074 [+0.029, +0.143] | -0.5pp [-1.5, +0.5] | -1.0pp [-13.2, +11.3] | -0.090 [-0.141, -0.045] | -0.068 [-0.165, +0.024] | +27% [+15, +37] |
| D − A | pooled | 202 | +0.044 [+0.020, +0.075] | -1.1pp [-2.3, +0.0] | +0.5pp [-9.1, +9.4] | -0.086 [-0.121, -0.057] | -0.063 [-0.170, +0.041] | +16% [+6, +32] |

## 2. Per-problem paired deltas, C − A (hidden-test pass, pp; cost, $/ckpt)

| Problem | seed-1 pass | seed-2 pass | pooled pass | pooled cost |
|---|---|---|---|---|
| cfgpipe | -0.2 | -2.3 | -1.2 | +0.075 |
| circuit_eval | +2.4 | -0.0 | +1.2 | +0.098 |
| code_search | -1.3 | +0.4 | -0.5 | +0.240 |
| dag_execution | -7.5 | -3.1 | -5.3 | +0.133 |
| database_migration | -1.4 | -9.2 | -5.3 | +0.158 |
| dynamic_buffer | -6.3 | -7.9 | -7.1 | +0.371 |
| dynamic_config_service_api | +0.0 | +0.3 | +0.1 | +0.228 |
| eve_route_planner | +3.9 | -10.3 | -3.2 | +0.175 |
| execution_server | +1.6 | +0.1 | +0.8 | +0.086 |
| file_backup | -4.8 | +0.8 | -2.0 | +0.177 |
| file_merger | +4.0 | -6.3 | -1.1 | +0.121 |
| file_query_tool | -6.0 | +0.2 | -2.9 | +0.021 |
| forge | +0.1 | -1.7 | -0.8 | +0.092 |
| log_query | +0.2 | +0.3 | +0.3 | +0.103 |
| metric_transform_lang | +0.0 | +0.8 | +0.4 | +0.415 |
| migrate_configs | +1.2 | +2.5 | +1.9 | +0.148 |
| rejector | +0.4 | -3.8 | -1.7 | +0.164 |
| textdrop | +1.0 | +1.4 | +1.2 | +0.086 |
| trajectory_api | -1.8 | -6.3 | -4.1 | +0.140 |
| xjq | -2.9 | -1.4 | -2.2 | +0.086 |

C ahead on 7 problems, behind on 13, tied on 0.

## 3. Rerun noise: each arm against itself, later seed − earlier seed

| Arm | Seeds | Pairs | Strict-solve flips | Mean abs Δ pass | Δ hidden-test pass | Δ cost / ckpt |
|---|---|---|---|---|---|---|
| A | seed-2 vs seed-1 | 101 | 7.9% | 2.0pp | +0.4pp [-0.7, +1.6] | -0.022 [-0.073, +0.010] |
| B | seed-2 vs seed-1 | 101 | 7.9% | 2.6pp | -0.2pp [-2.1, +1.3] | -0.009 [-0.032, +0.008] |
| C | seed-2 vs seed-1 | 101 | 9.9% | 2.5pp | -0.9pp [-2.3, +0.4] | -0.027 [-0.069, +0.008] |
| D | seed-2 vs seed-1 | 101 | 10.9% | 2.8pp | +1.6pp [+0.2, +3.5] | +0.037 [-0.017, +0.134] |

## 4. Exploratory: stripped specs (worked I/O examples removed)

Within seeds that ran the stripped arms: seed-2.

| Contrast | Problems | Pairs | Δ hidden-test pass | Δ strict solve | Δ cost / ckpt |
|---|---|---|---|---|---|
| As − A | all problems | 101 | -7.0pp [-11.8, -3.3] | -5.0pp [-14.4, +1.1] | +0.000 [-0.017, +0.027] |
| Cs − C | all problems | 101 | -3.1pp [-6.4, -0.5] | -2.0pp [-6.6, +2.2] | +0.015 [-0.061, +0.073] |
| Cs − As | all problems | 101 | +2.0pp [-1.4, +6.0] | -3.0pp [-8.9, +3.3] | +0.160 [+0.102, +0.223] |
| C − A | all problems | 101 | -1.9pp [-3.6, -0.6] | -5.9pp [-16.0, +2.9] | +0.145 [+0.096, +0.209] |
| (Cs − As) − (C − A) | all problems | 20 problems | +3.9pp [+0.4, +8.1] | | |
| As − A | ≥10% of spec removed (14 problems) | 69 | -8.8pp [-14.6, -4.0] | -1.4pp [-6.3, +3.1] | +0.008 [-0.016, +0.045] |
| Cs − C | ≥10% of spec removed (14 problems) | 69 | -4.7pp [-9.1, -1.5] | -1.4pp [-7.9, +3.4] | +0.022 [-0.089, +0.104] |
| Cs − As | ≥10% of spec removed (14 problems) | 69 | +1.8pp [-2.5, +6.6] | -2.9pp [-9.5, +3.1] | +0.165 [+0.082, +0.252] |
| C − A | ≥10% of spec removed (14 problems) | 69 | -2.3pp [-4.4, -0.5] | -2.9pp [-7.4, +0.0] | +0.151 [+0.087, +0.237] |
| (Cs − As) − (C − A) | ≥10% of spec removed (14 problems) | 14 problems | +4.1pp [-0.6, +9.4] | | |
