| Arm | Checkpoints | Cost / ckpt (agent + review) | Hidden-test pass | Strict solve | Erosion | Erosion slope | Verbosity | Verbosity slope | In-loop reject (1st round) | Shadow reject | Shadow precision | Shadow recall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 101 | $0.291 ($0.000 review) | 92.0% | 13.9% | 0.853 | 0.019 | 0.423 | 0.023 | — | 66.3% | 89.6% | 69.0% |
| B | 101 | $0.304 ($0.000 review) | 90.3% | 14.9% | 0.843 | 0.018 | 0.522 | -0.009 | — | 64.4% | 90.8% | 68.6% |
| C | 101 | $0.441 ($0.079 review) | 91.4% | 13.9% | 0.850 | 0.019 | 0.430 | 0.014 | 59.0% | 58.4% | 86.4% | 58.6% |
| D | 101 | $0.305 ($0.000 review) | 90.3% | 15.8% | 0.619 | 0.026 | 0.246 | 0.006 | — | 46.5% | 91.5% | 50.6% |
| D without tests/ | | | | | 0.770 | 0.023 | 0.365 | 0.012 | | | | |

Paired against A (same problem and checkpoint; 95% bootstrap CI over problems):

| Arm | Δ cost / ckpt | Δ hidden-test pass | Δ strict solve | Δ erosion | Δ verbosity | Extra $ per +1pp pass |
|---|---|---|---|---|---|---|
| B | +0.013 [-0.031, +0.048] | -1.7pp [-4.0, +0.0] | +1.0pp [-9.9, +15.2] | -0.010 [-0.040, +0.024] | +0.099 [-0.007, +0.203] | — |
| C | +0.150 [+0.116, +0.203] | -0.6pp [-1.9, +0.5] | +0.0pp [-6.4, +5.2] | -0.003 [-0.031, +0.028] | +0.007 [-0.076, +0.099] | — |
| D | +0.014 [-0.067, +0.074] | -1.7pp [-3.8, +0.0] | +2.0pp [-7.7, +13.5] | -0.234 [-0.290, -0.182] | -0.176 [-0.283, -0.075] | — |
