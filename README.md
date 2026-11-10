# verification-layers

Everyone is building coding-agent loops and software factories right now, and almost everyone has strong opinions on how to verify the output. Some setups run a separate code-review agent on every diff, some enforce TDD, and some ([conveyor](https://github.com/samarmstrong/conveyor) / [Vigil Factory](https://github.com/Vigil-SOC/vigil-factory), which we run at DeepTempo) skip unit tests and make the agent run the program live through its real entry point.

This repo benchmarks those rulesets against each other over multiple checkpoints so we can see what actually helps over a longer horizon and what just burns tokens. We publish the configs, raw traces, and tables from every seed so other teams don't have to spend hundreds of millions of tokens answering the same questions.

## What we test

We run four setups using the same model (`sonnet-5.5` on Vertex at medium effort) and the same agent (Claude Code `2.1.318`, configured in `configs/agents/claude_code_vl.yaml`) across 20 problems from [SlopCodeBench](https://github.com/SprocketLab/slop-code-bench) (`v1.0`, sampled with `random.Random(42).sample(sorted(names), 20)`). In each problem, the agent implements an initial spec and then extends its own code across 3 to 8 spec changes while hidden tests and code-erosion metrics grade each checkpoint.

| Arm | Rule set | Run config | Prompt | Reviewer |
|---|---|---|---|---|
| A. Plain | Default benchmark prompt ("implement the spec") | `configs/runs/vl-a-plain.yaml` | `just-solve` (unchanged from SlopCodeBench) | none |
| B. Run-it-live | Agent must run the program through its real entry point, fix what breaks, and log what it ran; no unit tests kept | `configs/runs/vl-b-conveyor.yaml` | `vl-conveyor` | none |
| C. Run-it-live + review | Same as B, plus a separate reviewer that can kick work back up to twice | `configs/runs/vl-c-review.yaml` | `vl-conveyor` | in loop, max 2 rounds |
| D. Tests first | Agent writes a pytest suite before changing code and keeps it green | `configs/runs/vl-d-tests.yaml` | `vl-tests` | none |

We also run C's reviewer in read-only shadow mode (`vl_shadow_review.py`) across every checkpoint of all four setups to measure how well the reviewer's verdicts line up with hidden-test failures. More detail on the runner changes and metrics is in [`docs/instrument.md`](docs/instrument.md).

## Results so far

Seed 1 (2026-11-06) results are in [`results/seed-1/table.md`](results/seed-1/table.md):

- Because SlopCodeBench works from detailed, known-good specs with worked examples, the plain agent already ran its own program in 89% of checkpoints without being told to.
- Adding an in-loop code reviewer (Arm C) added 52% to the cost per checkpoint with no measurable gain on hidden tests (−0.6pp vs plain; 95% upper bound +0.5pp).
- Conveyor's live-check rule (Arm B) finished roughly flat against plain (−1.7pp).
- Writing pytest first (Arm D) had the same pass rate (−1.7pp) but kept production code cleaner over time, lowering structural erosion from 0.853 to 0.770.
- Full traces and workspace snapshots for Seed 1 are attached to the [`seed-1` release](https://github.com/samarmstrong/verification-layers/releases/tag/seed-1) (`vl-seed-1-traces.tar.zst`, 32 MB).

## Running it yourself

You will need:
- `uv` and Docker (both the agent and hidden tests run inside `ghcr.io/astral-sh/uv:python3.12-trixie-slim`)
- The Claude Code CLI at the version pinned in `configs/agents/claude_code_vl.yaml`
- A GCP project with Claude enabled on Vertex AI, plus a dedicated service-account key with `roles/aiplatform.user` only. The runner mounts this key read-only into the container outside `~/.claude` so it never leaks into saved traces.

```bash
git clone https://github.com/samarmstrong/verification-layers && cd verification-layers
uv sync                                     # installs slop-code-bench from our pinned fork commit
uv run python scripts/vl_link_configs.py    # symlinks ./configs into the venv (see notes below)
uv run slop-code sync v1.0                  # downloads the problem catalog into ~/.cache/scbench

export GOOGLE_APPLICATION_CREDENTIALS=/path/to/vertex-only-key.json
export ANTHROPIC_VERTEX_PROJECT_ID=<your-gcp-project>
export CLOUD_ML_REGION=global
# Docker's Python SDK queries every credHelper in ~/.docker/config.json during image builds,
# so an expired gcloud login will break the build. Point it at a clean config directory:
export DOCKER_CONFIG=~/.config/scbench-docker

# Smoke test on a single problem
uv run slop-code run -c configs/runs/vl-a-plain.yaml --problem file_backup
```

### Running a full seed

```bash
scripts/vl_seed.sh [workers_per_arm]        # defaults to 2
```

A full seed takes a few hours and costs around $190 at Anthropic list prices. The script runs all four arms in parallel, runs the shadow reviewer across all checkpoints, runs a cross-family judge (Gemini 3.8 Flash on the final checkpoint of each problem), and builds the summary table and CSV:

- `outputs/vl/<arm>/sonnet-5.5_medium/<stamp>/`: SlopCodeBench's raw run directory per arm (workspace snapshots, Claude Code traces, `inference_result`, hidden-test evaluation, `review.json`, and `shadow_review.json`). This is what gets packed into each GitHub release tarball.
- `outputs/vl/seed-<stamp>.md`: Summary table with paired deltas against Arm A.
- `outputs/vl/seed-<stamp>.csv`: One row per `(arm, problem, checkpoint)`.
- `outputs/vl/seed-<stamp>-logs/`: Execution logs for each step.

You can also run the post-processing steps individually:
- `scripts/vl_shadow_review.py <run_dir>`
- `scripts/vl_cross_judge.py <run_dirs...> --judge gemini-flash --max-usd N`
- `scripts/vl_table.py A=<run_dir> B=<run_dir> C=<run_dir> D=<run_dir> --price-model sonnet-5.5 --no-tests-quality D` (computes per-arm stats and paired deltas against Arm A with 95% bootstrap confidence intervals resampled by problem; re-prices all token usage from `configs/models/sonnet-5.5.yaml`).

## What's in `results/seed-N/`

- `table.md`: Output of `scripts/vl_table.py`.
- `checkpoints.csv`: Per-checkpoint metrics: token-repriced `agent_cost`, `agent_cost_cli_reported`, `review_cost`, `shadow_cost`, and `total_cost`; `test_pass` and `strict_solved`; `erosion` and `verbosity` alongside `_no_tests` variants (which score Arm D after stripping its `tests/` folder); and reviewer columns (`in_loop_first_verdict`, `in_loop_rounds`, `shadow_verdict`).
- `logs/`: Full stdout/stderr logs from the run and shadow review.

*(Note: Seed 1's CSV strips out the initial cross-judge columns because the judge models we configured on that first run were outdated. Starting with Seed 2, `vl_seed.sh` uses Gemini 3.8 Flash.)*

## Repo layout and quirks

```
configs/      agents/, prompts/, environments/, models/, runs/, providers.yaml
scripts/      vl_seed.sh, vl_table.py, vl_shadow_review.py, vl_cross_judge.py, vl_link_configs.py
docs/         instrument.md (runner changes, shadow reviewer, metrics, caveats)
results/      committed tables and CSVs (plus logs) for each seed
```

`pyproject.toml` pins `samarmstrong/slop-code-bench@65d76b2`, which adds the Vertex AI provider and the in-loop reviewer hook to SlopCodeBench. Once those land upstream in `SprocketLab/slop-code-bench`, we will point the dependency back upstream.

A few quirks worth knowing if you poke around:

- SlopCodeBench looks up its prompt and model config files relative to its own package directory (`<venv>/lib/python3.12/configs`), but its wheel doesn't package those files and there is no CLI flag or env var to override the config root. `scripts/vl_link_configs.py` symlinks that venv path to `./configs` in this repo (and leaves editable checkouts alone). `vl_seed.sh` runs it automatically, and `configs/` includes unmodified copies of SlopCodeBench's base files (`prompts/just-solve.jinja`, `environments/docker-python3.12-uv.yaml`, `providers.yaml`) alongside our `vl-*` configs so the loader finds everything in one place.
- `slop-code run --dry-run` still creates an empty `outputs/` run folder before exiting.
- All reported dollar figures are calculated from token counts using Anthropic's public list prices in `configs/models/sonnet-5.5.yaml`, not Vertex AI partner billing rates.
- Arm D writes test files into `tests/`. SlopCodeBench's complexity metrics scan the whole workspace by default, and test files dilute the per-function complexity numbers. Always look at the `_no_tests` (production code only) erosion numbers when comparing Arm D.
- Conveyor's real prompt lets the implementer spin up a subagent to look over a large diff, so we kept that in Arm B. Arm C adds the mandatory, separate reviewer loop on top.

Development sponsored by [DeepTempo](https://deeptempo.ai).
