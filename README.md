# verification-layers

A live, weekly measurement of what each verification layer in a coding-agent loop
costs and what it buys: hidden-test pass rate and long-horizon code quality, same
model, same problems, four arms.

| Arm | What changes | Run config | Prompt | Reviewer |
|---|---|---|---|---|
| A. Plain | the agent solves the task | `configs/runs/vl-a-plain.yaml` | `just-solve` (SlopCodeBench's own, unchanged) | none |
| B. Run-it-live | the agent must exercise its change through the real entry point before calling it done | `configs/runs/vl-b-conveyor.yaml` | `vl-conveyor` | none |
| C. Run-it-live + adversarial review | B, plus a fresh reviewer that can send the work back, at most twice | `configs/runs/vl-c-review.yaml` | `vl-conveyor` | in loop, 2 rounds |
| D. Tests first | the agent writes a pytest suite before the change and keeps it green | `configs/runs/vl-d-tests.yaml` | `vl-tests` | none |

Problems come from [SlopCodeBench](https://github.com/SprocketLab/slop-code-bench)
(catalog v1.0, 20 of the 36 problems: `random.Random(42).sample(sorted(names), 20)`);
the agent extends its own code across checkpoints as the spec changes, and hidden
tests grade each checkpoint. The runner is SlopCodeBench with a Vertex provider and an
in-loop reviewer (both offered upstream). Agent: Claude Code 2.1.318
(`configs/agents/claude_code_vl.yaml`). Model: `sonnet-5.5` on Vertex, medium effort.
Every weekly seed adds to the same results table so the confidence intervals narrow in
public.

A shadow reviewer (C's reviewer, read-only, nothing sent back) runs on every checkpoint
of every arm, which gives the reviewer's precision and recall against the hidden tests
on all four arms. Details of each piece: [`docs/instrument.md`](docs/instrument.md).

## Results

- **Seed 1 (2026-11-06):** [`results/seed-1/table.md`](results/seed-1/table.md). Review
  cost +52% per checkpoint with no measurable hidden-test gain (95% upper bound +0.5pp);
  run-it-live about the same as plain; tests-first lowered structural erosion in
  production code and did not change the pass rate. One seed, one model, 20 greenfield
  problems; costs at Anthropic list price.
- Full traces for seed 1: release
  [`seed-1`](https://github.com/samarmstrong/verification-layers/releases/tag/seed-1)
  (`vl-seed-1-traces.tar.zst`, 32 MB).

The first results post links from here once it is live.

## Setup

Needs `uv`, Docker (the agent and the hidden tests run in
`ghcr.io/astral-sh/uv:python3.12-trixie-slim`), the Claude Code CLI at the version
pinned in `configs/agents/claude_code_vl.yaml`, and a GCP project with Claude on
Vertex AI enabled plus a service account that has `roles/aiplatform.user` and nothing
else. Generate a dedicated key for it; the runner mounts it read-only into the agent
container outside `~/.claude`, so it never lands in the traces.

```bash
git clone https://github.com/samarmstrong/verification-layers && cd verification-layers
uv sync                                     # installs slop-code-bench from the pinned fork commit
uv run python scripts/vl_link_configs.py    # points the installed runner at ./configs (see rough edges)
uv run slop-code sync v1.0                  # the problem catalog, into ~/.cache/scbench

export GOOGLE_APPLICATION_CREDENTIALS=/path/to/vertex-only-key.json
export ANTHROPIC_VERTEX_PROJECT_ID=<your-gcp-project>
export CLOUD_ML_REGION=global               # the default
# The Docker SDK asks every credHelper in ~/.docker/config.json for credentials on
# build; an expired gcloud login breaks it. Point it at a config with no GCP/ECR helpers.
export DOCKER_CONFIG=~/.config/scbench-docker

uv run slop-code run -c configs/runs/vl-a-plain.yaml --problem file_backup   # smoke test, one problem
```

## Run a seed

```bash
scripts/vl_seed.sh [workers_per_arm]        # default 2
```

One command, several hours, about $190 at list price for seed 1. It runs the four arms
in parallel, then the shadow reviewer on every arm, then the cross-family judge
(Gemini, final checkpoint of each problem, capped), then the results table:

- `outputs/vl/<arm>/sonnet-5.5_medium/<stamp>/` per arm: SlopCodeBench's run directory
  (per-checkpoint snapshots, traces, `inference_result`, evaluation, `review.json` and
  `shadow_review.json`). This is what the release tarballs contain.
- `outputs/vl/seed-<stamp>.md` the results table, `outputs/vl/seed-<stamp>.csv` one row
  per (arm, problem, checkpoint), `outputs/vl/seed-<stamp>-logs/` one log per step.

To publish a seed, copy the `.md`, `.csv` and logs into `results/seed-N/` and attach
`outputs/vl/{a-plain,b-conveyor,c-review,d-tests}` as a `tar.zst` release asset.

The pieces can also run alone: `scripts/vl_shadow_review.py <run_dir>`,
`scripts/vl_cross_judge.py <run_dirs...> --judge gemini --max-usd N`, and
`scripts/vl_table.py A=<run_dir> B=<run_dir> C=<run_dir> D=<run_dir> --price-model
sonnet-5.5 --no-tests-quality D`, which prints per-arm rows and paired deltas against A
with 95% bootstrap intervals resampled over problems. Every cost is re-priced from
tokens with `configs/models/sonnet-5.5.yaml`, so agent and reviewer share one price
list.

## Data files

`results/seed-N/`:

- `table.md`: the per-arm table and the paired deltas against arm A, as printed by
  `scripts/vl_table.py`.
- `checkpoints.csv`: one row per (arm, problem, checkpoint). Columns: `agent_cost`
  (re-priced from tokens), `agent_cost_cli_reported`, `review_cost` (in-loop rounds),
  `shadow_cost`, `total_cost`; `test_pass` (hidden-test fraction) and `strict_solved`;
  `erosion`, `verbosity` and their `_no_tests` variants (arm D re-scored with its test
  files removed); `in_loop_first_verdict`, `in_loop_rounds`, `shadow_verdict`.
- `logs/`: stdout and stderr of each arm's run and shadow review.

Seed 1's `checkpoints.csv` omits the judge columns the raw run produced: its judges
(Gemini 3.1 Pro, gpt-oss-120b) were out of date and that section was dropped before
publication. The seed script now judges with Gemini 4 Argon.

The release asset per seed holds the four run directories: every checkpoint's workspace
snapshot, the Claude Code trace, the reviewer's requests and verdicts, and the hidden-test
results. Traces were generated with dedicated keys and scrubbed; they name the GCP
project that ran them, which is fine.

## Layout

```
configs/      agents/, prompts/, environments/, models/, runs/, providers.yaml
scripts/      vl_seed.sh, vl_table.py, vl_shadow_review.py, vl_cross_judge.py, vl_link_configs.py
docs/         instrument.md: the runner additions, shadow review, cross-family judging, caveats
results/      one directory per published seed
```

`configs/` keeps SlopCodeBench's layout so its loader finds everything by bare name.
The instrument's own files are `agents/claude_code_vl.yaml`, `prompts/vl-*.jinja`,
`runs/vl-*.yaml`, `models/sonnet-5.5.yaml` and `models/gpt-oss-120b.yaml`. The rest
(`prompts/just-solve.jinja`, `environments/docker-python3.12-uv.yaml`,
`models/gpt-6.1-sol.yaml`, `providers.yaml`) are byte-for-byte copies from
SlopCodeBench, present because the installed runner has none of its own (next section).

The runner is pinned in `pyproject.toml` as a uv git dependency on
`samarmstrong/slop-code-bench@65d76b2`, the fork commit that adds the Vertex provider
and the in-loop reviewer. The pin moves to `SprocketLab/slop-code-bench` when those
land upstream.

## Known rough edges

- **The installed runner has no configs.** SlopCodeBench resolves prompts, agents,
  environments, the model catalog and `providers.yaml` relative to its own source
  tree (`<checkout>/configs`), its wheel ships none of them, and its loader's
  working-directory fallback looks in `./<category>/` rather than `./configs/`. There
  is no environment variable or flag for it. `scripts/vl_link_configs.py` therefore
  symlinks the path the installed package looks at (`<venv>/lib/python3.12/configs`)
  to this repo's `configs/`. `scripts/vl_seed.sh` runs it on every start; run it by
  hand after `uv sync` before using `slop-code` directly. If the package is ever
  installed editable from a checkout, the script leaves the checkout's `configs/` alone.
- `slop-code run --dry-run` creates the run's `outputs/` directory before it stops.
- Costs use the first-party pricing in the model file, not Vertex's partner rates. Check
  against the billing export before publishing a cost number.
- Arm D keeps its tests in `tests/`; the quality metrics do not exclude them, so the
  table reports D's erosion and verbosity both with and without `tests/`.
- Arm B's prompt includes conveyor's "subagent review when a change is large or
  subtle". That is conveyor as shipped; arm C is the separate, mandatory reviewer.

Development sponsored by [DeepTempo](https://deeptempo.ai).
