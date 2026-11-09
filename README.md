# verification-layers

A live, weekly measurement of what each verification layer in a coding-agent loop
costs and what it buys: hidden-test pass rate and long-horizon code quality, same
model, same problems, four arms.

| Arm | What changes |
|---|---|
| A. Plain | the agent solves the task |
| B. Run-it-live | the agent must exercise its change through the real entry point before calling it done |
| C. Run-it-live + adversarial review | B, plus a fresh reviewer that can send the work back |
| D. Tests first | the agent writes tests before the change |

Problems come from [SlopCodeBench](https://github.com/SprocketLab/slop-code-bench); the
runner is SlopCodeBench with a Vertex provider and an in-loop reviewer (both offered
upstream). Every weekly seed adds to the same results table so the confidence intervals
narrow in public.

Code and data are being moved here from a fork; the first results post links from
this README once it is live.

Development sponsored by [DeepTempo](https://deeptempo.ai).
