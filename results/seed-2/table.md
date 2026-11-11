| Arm | Checkpoints | Cost / ckpt (agent + review) | Hidden-test pass | Strict solve | Erosion | Erosion slope | Verbosity | Verbosity slope | In-loop reject (1st round) | Shadow reject | Shadow precision | Shadow recall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 101 | $0.269 ($0.000 review) | 92.4% | 19.8% | 0.870 | 0.008 | 0.451 | 0.001 | — | 69.3% | 87.1% | 75.3% |
| B | 101 | $0.294 ($0.000 review) | 90.1% | 8.9% | 0.830 | 0.027 | 0.438 | -0.013 | — | 57.4% | 94.8% | 59.8% |
| C | 101 | $0.413 ($0.076 review) | 90.5% | 13.9% | 0.817 | 0.030 | 0.432 | -0.005 | 45.5% | 38.6% | 97.4% | 43.7% |
| D | 101 | $0.342 ($0.000 review) | 91.9% | 18.8% | 0.628 | 0.026 | 0.255 | 0.003 | — | 53.5% | 88.9% | 58.5% |
| D without tests/ | | | | | 0.780 | 0.031 | 0.383 | 0.006 | | | | |
| As | 101 | $0.269 ($0.000 review) | 85.4% | 14.9% | 0.852 | 0.017 | 0.462 | -0.013 | — | 69.3% | 91.4% | 74.4% |
| Cs | 101 | $0.429 ($0.075 review) | 87.4% | 11.9% | 0.840 | 0.020 | 0.461 | 0.003 | 61.4% | 51.5% | 90.4% | 52.8% |

Paired against A (same problem and checkpoint; 95% bootstrap CI over problems):

| Arm | Δ cost / ckpt | Δ hidden-test pass | Δ strict solve | Δ erosion | Δ verbosity | Extra $ per +1pp pass |
|---|---|---|---|---|---|---|
| B | +0.026 [+0.013, +0.039] | -2.4pp [-4.5, -0.5] | -10.9pp [-22.0, -1.1] | -0.040 [-0.083, -0.001] | -0.013 [-0.124, +0.090] | — |
| C | +0.145 [+0.096, +0.209] | -1.9pp [-3.6, -0.6] | -5.9pp [-16.0, +2.9] | -0.052 [-0.090, -0.019] | -0.019 [-0.115, +0.099] | — |
| D | +0.074 [+0.029, +0.143] | -0.5pp [-1.5, +0.5] | -1.0pp [-13.2, +11.3] | -0.242 [-0.298, -0.189] | -0.196 [-0.288, -0.108] | — |
| As | +0.000 [-0.017, +0.027] | -7.0pp [-11.8, -3.3] | -5.0pp [-14.4, +1.1] | -0.017 [-0.074, +0.021] | +0.011 [-0.037, +0.063] | — |
| Cs | +0.160 [+0.116, +0.219] | -5.0pp [-8.6, -2.3] | -7.9pp [-17.7, +0.0] | -0.030 [-0.068, +0.001] | +0.010 [-0.089, +0.108] | — |

Judge agreement (reject = would send back). Rejection rate per arm under each judge family, on the snapshots that family judged:

| Arm | claude | gemini-flash |
|---|---|---|
| A | 69% (n=101) | 78% (n=18) |
| B | 57% (n=101) | 92% (n=12) |
| C | 39% (n=101) | 75% (n=16) |
| D | 53% (n=101) | 60% (n=15) |
| As | 69% (n=101) | — |
| Cs | 51% (n=101) | — |

| Judges | Snapshots both judged | Cohen's κ |
|---|---|---|
| claude vs gemini-flash | 61 | 0.029 |

Arms ordered from fewest to most rejections, per judge: claude: C < Cs < D < B < A < As; gemini-flash: D < C < A < B
