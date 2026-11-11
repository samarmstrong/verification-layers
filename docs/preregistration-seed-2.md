# Seed 2 preregistration

*Written 2026-11-10, before any seed-2 run. Changes after seed 2 starts go in "Deviations" at
the bottom, dated, and do not replace the text above them.*

Post 1 ("If you have great specs, you don't need to prompt code review or live verification",
from seed 1) made three claims: an in-loop code reviewer added about 52% to the cost per
checkpoint and bought no hidden-test pass; tests-first left production code less eroded; and
the reason is that SlopCodeBench specs are detailed and come with worked input/output examples,
so the plain agent already checks its own work. The pass-rate gaps were smaller than the 23.4%
rerun flip rate the Harness Leaderboard measured, so one seed cannot carry them. Seed 2 repeats
seed 1 unchanged and adds a direct test of the mechanism.

## Hypotheses

| | Claim from post 1 | Test (pooled seeds 1 and 2 unless stated) | Contradicts the post if |
|---|---|---|---|
| **H1, primary** | The reviewer buys no hidden-test pass | C − A, hidden-test pass | the 95% interval lies entirely above 0 |
| H2 | The reviewer costs about half again as much | C − A, cost ratio | the interval's lower end is below +25% |
| H3 | Tests-first erodes production code less | D − A, structural erosion with `tests/` removed | the interval includes 0 or lies above it |
| H4 | Live-run (B) is roughly flat on pass | B − A, hidden-test pass | the interval lies entirely outside ±3pp |
| E1, exploratory | Removing worked examples hurts the plain agent | As − A, hidden-test pass, seed 2 only | (manipulation check; not a test of the post) |
| E2, exploratory | Examples are why the reviewer is redundant | (Cs − As) − (C − A), hidden-test pass, seed 2 only | E1 holds and the interval lies entirely at or below 0 |

H1 is the one contrast the replication is judged on. If its interval includes 0 but reaches
past +2pp, the result is reported as inconclusive, not as support. If E1's interval includes 0,
stripping did not change the task enough and E2 is not interpreted. E1 and E2 are one seed on 20
problems; a null there is weak evidence, and they are labelled exploratory everywhere they appear.

Smallest effects the design can see (from seed 1's interval widths): about ±1.3pp on pooled
pass contrasts (H1, H4), about ±3pp on E2, and about ±10pp on strict solve, which is reported
but not tested.

## Arms

Same 20 problems as seed 1 (`random.Random(42).sample(sorted(catalog v1.0), 20)`); a new seed
is a fresh rerun of every (arm, problem), since the agent has no seed of its own.

| Arm | Config | Specs | Status |
|---|---|---|---|
| A. Plain | `configs/runs/vl-a-plain.yaml` | full | replicate, unchanged |
| B. Run-it-live | `configs/runs/vl-b-conveyor.yaml` | full | replicate, unchanged |
| C. Run-it-live + reviewer | `configs/runs/vl-c-review.yaml` | full | replicate, unchanged |
| D. Tests first | `configs/runs/vl-d-tests.yaml` | full | replicate, unchanged |
| As. Plain, stripped | `configs/runs/vl-a-plain-stripped.yaml` | worked examples removed | **exploratory**, new |
| Cs. Reviewer, stripped | `configs/runs/vl-c-review-stripped.yaml` | worked examples removed | **exploratory**, new |

Stripping (`scripts/vl_strip_examples.py`) is mechanical and fixed before the run: it removes
sections headed "Example(s)", bold "Example" labels and what follows them, "Example:" lead-ins
with the code blocks, tables or lists after them, and one-line examples. Schemas, field tables,
format and error definitions are kept, including one "Output Format" section that a spec files
under its Examples heading. It removes 23.6% of spec words overall (0% on `forge`, 1% on `xjq`,
62% on `file_query_tool`); the per-problem table and a full diff are written beside the stripped
catalog and published with the seed. Hidden tests, static files and problem configs are
unchanged. In Cs the reviewer reads the same stripped specs as the implementer, and so does the
shadow reviewer on As and Cs. The cross-family judge covers A to D only.

## Pinned

Model `sonnet-5.5` (`claude-sonnet-5-5`) on Vertex `global`, medium effort, for implementer,
reviewer and shadow reviewer. Claude Code 2.1.318 (`configs/agents/claude_code_vl.yaml`,
`bypassPermissions`, 100-step limit). Runner: `samarmstrong/slop-code-bench@65d76b2`. Problem
catalog v1.0 at `4d38d300`. Image `ghcr.io/astral-sh/uv:python3.12-trixie-slim`. Reviewer: in
loop, at most 2 rounds. Two workers per arm. Cross-family judge: Gemini 3.8 Flash, final
checkpoint of each problem. Engine: the commit that adds this file. Dollars are re-priced from
tokens at the list prices in `configs/models/sonnet-5.5.yaml`. Host: `factory-host-1` (seed 1
ran elsewhere; the host is noted in the results as a difference).

Budget: $300 for the seed. `scripts/vl_seed.sh` stops every arm once re-priced spend passes it
(`VL_MAX_USD=300`). A stopped seed is reported as partial, with the contrasts computed on the
checkpoints that finished in both arms of each pair.

## Analysis

`scripts/vl_intervals.py` over `results/seed-1/checkpoints.csv` and seed 2's CSV:

- **Per-problem paired deltas.** Each arm is paired with A on the same (seed, problem,
  checkpoint); a checkpoint missing from either side drops out of that pair. The estimate is the
  mean paired difference over all pairs (checkpoint-weighted, the same estimator as seed 1's
  table), and the report also lists every problem's own mean delta for C − A.
- **Bootstrap 95% intervals.** Percentile intervals from 2,000 resamples of the 20 problems,
  with all of a problem's checkpoints and seeds moving together, since they are not independent.
  RNG seed 0. With seed 1 alone this reproduces post 1's table exactly.
- Cost ratio: total arm cost over total A cost on the same pairs, minus 1, same resampling.
- Rerun noise: each of A to D against itself, seed 2 against seed 1: strict-solve flip rate,
  mean absolute change in pass, and the paired delta. This is our own number to put beside the
  23.4% flip rate.
- E1 and E2 are reported on all 20 problems and again on the 14 problems where stripping removed
  at least 10% of the spec words. The 20-problem figure is the one that counts.
- Per-seed results are always shown beside the pooled ones.

All of it is published whatever it shows: the table, the CSV, the logs, the traces release and
the stripping diff.

## What would contradict post 1

Post 1 is wrong in the way that matters if **H1 fails**: with two seeds pooled, the reviewer
arm passes measurably more hidden tests than plain. It is also wrong if **H2 fails** (the extra
cost was a seed-1 accident) or **H3 fails** (the erosion gap was noise). Its explanation is wrong,
even if the numbers hold, if stripping the examples hurts the plain agent (E1) but the reviewer
recovers none of that loss (E2 at or below 0). Post 2 reports whichever of these happens, first.

## Deviations

All dated 2026-11-10, written after seed 2 started.

1. **Arms B and As did not start in the first launch.** At 15:51Z both died while building
   the `slop-code:python3.12` Docker image, because another arm was building it at the
   same moment (`AlreadyExists`). A, C, D and Cs ran. The driver finished its other steps
   and then failed at the table, which needs B. This was not the $300 stop, so B and As
   were rerun under the same stamp from 20:17Z (`VL_RUN_ARMS`, added in `8ed2d11`; arms
   start 90 s apart). They are the same configs on the same problems, started about
   4.7 hours later than the other arms.
2. **Five (arm, problem) runs ended early on a reviewer parse error.** The in-loop reviewer
   sometimes returns a finding without `evidence`, or a string where an object is
   expected. `Reviewer.review` then raises, and the runner marks the problem `error` and
   stops it. This hit C on `forge` (stopped at checkpoint 2 of 7) and `rejector`
   (checkpoint 1 of 5), and Cs on `circuit_eval` (7 of 8), `eve_route_planner` (1 of 3)
   and `forge` (7 of 8). Seed 1 had no such errors. The same bug stopped shadow review
   partway through A (99 of 101) and D (37 of 101). The reviewer code was not changed.
   The runner treats errored problems as unfinished, so the rerun in deviation 1 also
   reruns these five problems from checkpoint 1 under the same stamp. Shadow review and
   the judge pick up where they stopped.
3. **The five errored runs' traces were lost.** At 20:13Z a relaunch went out by mistake
   with the old driver, because the host checkout had not updated. It was stopped after
   about 2 minutes, but the runner had already reset those five problem directories. The
   as-run per-checkpoint rows (pass, tests, CLI cost) survive in
   `results/seed-2/asrun-backup/`. The per-arm top-level logs from the first launch
   (`<arm>.log`) were also overwritten. The per-problem `infer.log` and `run_agent.log`
   files in each run directory survive. To keep the true spend under $300, the cap for
   the rerun was lowered to $295, since the wiped runs' cost of about $4.70 no longer shows
   in the re-priced total.
4. **Sensitivity check (added, not preregistered):** H1 to H4 are also reported with C and
   Cs as originally run (the five errored problems truncated where they stopped, pairs
   dropping out under the rule above), next to the rerun version. The rerun version is
   primary, because the runner reruns errored problems by design and the errors come
   from the harness, not the agent.
5. **Rerun flip rate (added, descriptive, not preregistered).** For A to D: the share of
   (problem, checkpoint) units whose strict pass differs between seed 1 and seed 2, and
   the share of problems whose strict solve differs, per arm and pooled, with a bootstrap
   over problems (`scripts/vl_flips.py`). This is not the Harness Leaderboard's 23.4%.
   Theirs is over their own task set with three attempts per configuration; ours is two
   attempts on 20 multi-checkpoint SlopCodeBench problems, with the checkpoint as the
   unit. No problem was strict-solved at every checkpoint in seed 1 (0 of 80), so the
   problem-level rate is near its floor and carries little information.
6. **Shadow review retries replies that do not parse.** The parse error in deviation 2
   also stopped shadow review partway through, on almost every pass. From `9f7683e`,
   `vl_shadow_review.py` retries a checkpoint up to three times and otherwise records it
   as `error`, which the shadow rates exclude (the cross-family judge already does the
   same). In seed 2, 3 replies needed a retry and none ended as an error. Shadow review
   is not part of H1 to H4.
