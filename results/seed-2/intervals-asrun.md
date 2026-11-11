# Paired intervals: seed-1, seed-2

Mean paired difference on the same (seed, problem, checkpoint); 95% percentile bootstrap over problems (2000 resamples, a problem's checkpoints and seeds resampled together). Arm D's erosion and verbosity are scored without its tests/. Cost ratio is sum(arm cost) / sum(A cost) − 1 on the same pairs.

## 1. Arms against A (primary contrast: C − A)

| Contrast | Seeds | Pairs | Δ cost / ckpt | Δ hidden-test pass | Δ strict solve | Δ erosion | Δ verbosity | Cost ratio |
|---|---|---|---|---|---|---|---|---|
| C − A | seed-1 | 101 | +0.150 [+0.116, +0.203] | -0.6pp [-1.9, +0.5] | +0.0pp [-6.4, +5.2] | -0.003 [-0.031, +0.028] | +0.007 [-0.076, +0.099] | +51% [+28, +86] |
| C − A | seed-2 | 91 | +0.152 [+0.097, +0.224] | -1.9pp [-3.7, -0.4] | -5.5pp [-17.2, +4.1] | -0.057 [-0.098, -0.021] | +0.006 [-0.107, +0.133] | +54% [+38, +81] |
| C − A | pooled | 192 | +0.151 [+0.115, +0.197] | -1.2pp [-2.4, -0.2] | -2.6pp [-10.6, +3.1] | -0.028 [-0.054, -0.002] | +0.007 [-0.067, +0.090] | +53% [+36, +78] |
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
| forge | +0.1 | -3.9 | -0.7 | +0.117 |
| log_query | +0.2 | +0.3 | +0.3 | +0.103 |
| metric_transform_lang | +0.0 | +0.8 | +0.4 | +0.415 |
| migrate_configs | +1.2 | +2.5 | +1.9 | +0.148 |
| rejector | +0.4 | +0.0 | +0.3 | +0.183 |
| textdrop | +1.0 | +1.4 | +1.2 | +0.086 |
| trajectory_api | -1.8 | -6.3 | -4.1 | +0.140 |
| xjq | -2.9 | -1.4 | -2.2 | +0.086 |

C ahead on 8 problems, behind on 12, tied on 0.

## 3. Rerun noise: each arm against itself, later seed − earlier seed

| Arm | Seeds | Pairs | Strict-solve flips | Mean abs Δ pass | Δ hidden-test pass | Δ cost / ckpt |
|---|---|---|---|---|---|---|
| A | seed-2 vs seed-1 | 101 | 7.9% | 2.0pp | +0.4pp [-0.7, +1.6] | -0.022 [-0.073, +0.010] |
| B | seed-2 vs seed-1 | 101 | 7.9% | 2.6pp | -0.2pp [-2.1, +1.3] | -0.009 [-0.032, +0.008] |
| C | seed-2 vs seed-1 | 91 | 9.9% | 2.4pp | -0.7pp [-2.3, +0.6] | -0.028 [-0.079, +0.014] |
| D | seed-2 vs seed-1 | 101 | 10.9% | 2.8pp | +1.6pp [+0.2, +3.5] | +0.037 [-0.017, +0.134] |

## 4. Exploratory: stripped specs (worked I/O examples removed)

Within seeds that ran the stripped arms: seed-2.

| Contrast | Problems | Pairs | Δ hidden-test pass | Δ strict solve | Δ cost / ckpt |
|---|---|---|---|---|---|
| As − A | all problems | 101 | -7.0pp [-11.8, -3.3] | -5.0pp [-14.4, +1.1] | +0.000 [-0.017, +0.027] |
| Cs − C | all problems | 88 | -3.6pp [-7.5, -0.5] | +0.0pp [-4.8, +6.4] | +0.000 [-0.095, +0.073] |
| Cs − As | all problems | 97 | +1.7pp [-1.7, +5.3] | +0.0pp [-3.2, +3.0] | +0.157 [+0.082, +0.232] |
| C − A | all problems | 91 | -1.9pp [-3.7, -0.4] | -5.5pp [-17.2, +4.1] | +0.152 [+0.097, +0.224] |
| (Cs − As) − (C − A) | all problems | 20 problems | +3.5pp [+0.2, +7.4] | | |
| As − A | ≥10% of spec removed (14 problems) | 69 | -8.8pp [-14.6, -4.0] | -1.4pp [-6.3, +3.1] | +0.008 [-0.016, +0.045] |
| Cs − C | ≥10% of spec removed (14 problems) | 62 | -5.5pp [-10.6, -1.8] | -1.6pp [-6.1, +0.0] | +0.006 [-0.131, +0.114] |
| Cs − As | ≥10% of spec removed (14 problems) | 66 | +1.1pp [-3.1, +5.8] | -1.5pp [-5.1, +0.0] | +0.158 [+0.062, +0.253] |
| C − A | ≥10% of spec removed (14 problems) | 65 | -2.2pp [-4.4, -0.3] | -1.5pp [-5.1, +0.0] | +0.151 [+0.080, +0.239] |
| (Cs − As) − (C − A) | ≥10% of spec removed (14 problems) | 14 problems | +3.2pp [-1.2, +8.0] | | |
