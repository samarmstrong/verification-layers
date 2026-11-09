# Verification-layers instrument

What does each verification layer in an agent loop cost, and what does it buy in
correctness and in long-horizon code quality? Four arms, same model, effort,
agent version, environment and problems. This is the reference for the pieces;
the [README](../README.md) covers setup, running a seed and the data files.

| Arm | Run config | Prompt | Reviewer |
|---|---|---|---|
| A. Plain | `configs/runs/vl-a-plain.yaml` | `just-solve` (upstream, unchanged) | none |
| B. Conveyor | `configs/runs/vl-b-conveyor.yaml` | `vl-conveyor` | none |
| C. Conveyor + adversarial review | `configs/runs/vl-c-review.yaml` | `vl-conveyor` | in loop, 2 rounds |
| D. Tests | `configs/runs/vl-d-tests.yaml` | `vl-tests` | none |

Problems: 20 of the 36 in catalog v1.0, `random.Random(42).sample(sorted(names), 20)`.
Agent: `configs/agents/claude_code_vl.yaml` (Claude Code 2.1.318). Model: `sonnet-5.5`
(`configs/models/sonnet-5.5.yaml`) on Vertex `global`, medium effort.

## What the runner adds

The runner is [SlopCodeBench](https://github.com/SprocketLab/slop-code-bench) with two
additions, carried on the `samarmstrong/slop-code-bench` fork and offered upstream:

- **Vertex provider for Claude Code** (`provider: vertex`). `GOOGLE_APPLICATION_CREDENTIALS`
  points at a service-account key; it is mounted read-only at
  `/run/secrets/gcp-vertex-key.json`, outside `~/.claude`, so it never lands in the
  copied traces. Needs `ANTHROPIC_VERTEX_PROJECT_ID`; `CLOUD_ML_REGION` defaults to
  `global`. Every model Claude Code may pick, including the small/fast background
  model, is pinned to the run model.
- **In-loop reviewer** (`review:` block in a run config; `src/slop_code/agent_runner/review.py`).
  After a checkpoint, a fresh model call reads the workspace against every spec so
  far and approves or rejects with findings (correctness / spec / quality). A
  rejection goes back into the same Claude Code session (`--continue`). Each round is
  saved to `<checkpoint>/review.json` with its cost, which is kept out of the agent's
  own usage. The reviewer reads code; it does not run it.
- **Shadow review** (`scripts/vl_shadow_review.py`): the same reviewer on finished
  snapshots, nothing sent back. Run it on arms A, B and D to get the reviewer's
  precision and recall against the hidden tests on every arm.
- **Cross-family judging** (`scripts/vl_cross_judge.py`): the shadow reviewer's prompt,
  verbatim, put to other model families: `gemini` (Gemini 3.1 Pro on Vertex, about $0.30 a
  judgment, so by default each problem's final checkpoint only) and `gpt-oss`
  (gpt-oss-120b on Vertex, under a cent, so run it with `--checkpoints all`), and `gpt`
  (GPT-6.1-sol from Vertex Model Garden, once enabled; `VL_GPT_VERTEX_MODEL` overrides
  the model ID). `gpt-oss` is an OpenAI-family judge but a much weaker one. The table reports each
  family's rejection rate per arm, pairwise Cohen's κ, and the arm ranking under every
  judge. Method from `vulnbench-cross-judge`: verbatim prompts, resumable output, a hard
  `--max-usd` cap, judge errors excluded from denominators.
- **Seed runner** (`scripts/vl_seed.sh`) and **results table** (`scripts/vl_table.py`).

## Running

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/vertex-only-key.json  # a service account with aiplatform.user only
export ANTHROPIC_VERTEX_PROJECT_ID=<your-gcp-project>
# The Docker SDK asks every credHelper in ~/.docker/config.json for credentials on
# build; an expired gcloud login breaks it. This config has no GCP/ECR helpers.
export DOCKER_CONFIG=~/.config/scbench-docker
uv run python scripts/vl_link_configs.py   # once after uv sync; see README "Known rough edges"
uv run slop-code run -c configs/runs/vl-a-plain.yaml --problem file_backup   # smoke test
for arm in a-plain b-conveyor c-review d-tests; do
  uv run slop-code run -c configs/runs/vl-$arm.yaml -n 4
done
for arm in a-plain b-conveyor c-review d-tests; do
  uv run python scripts/vl_shadow_review.py outputs/vl/$arm/sonnet-5.5_medium/<ts> \
    --model sonnet-5.5 --provider vertex --effort medium
done
uv run python scripts/vl_cross_judge.py outputs/vl/*/sonnet-5.5_medium/<ts> --judge gemini --max-usd 30
uv run python scripts/vl_cross_judge.py outputs/vl/*/sonnet-5.5_medium/<ts> --judge gpt-oss --checkpoints all --max-usd 5
uv run python scripts/vl_table.py A=outputs/vl/a-plain/... B=outputs/vl/b-conveyor/... \
  C=outputs/vl/c-review/... D=outputs/vl/d-tests/... --price-model sonnet-5.5 \
  --no-tests-quality D --csv vl_rows.csv
```

`vl_table.py` prints one row per arm and a table of deltas against arm A, each paired
on the same (problem, checkpoint), with a 95% bootstrap interval resampled over
problems. Cost per checkpoint is read from each checkpoint's `inference_result`;
the bench's live progress line over-reports it.

## Known caveats

- Arm D keeps its tests in `tests/`. The quality metrics do not exclude them, so
  report arm D's verbosity and erosion both with and without `tests/`.
- Arm B's prompt includes conveyor's "subagent review when a change is large or
  subtle". That is conveyor as shipped; arm C is the separate, mandatory reviewer.
- Every cost uses the model file's first-party pricing, not Vertex's partner rates.
  Check against the GCP billing export before publishing a cost number.
