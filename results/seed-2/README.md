# Seed 2 results (stamp `20261110T1535`)

Run on `factory-host-1` from 2026-11-10 15:35Z to 2026-11-11 00:10Z. Sonnet 5.5, medium effort, on Vertex `global`, with Claude Code 2.1.318 and the engine pinned at `65d76b2`. Six arms on the same 20 problems, 101 checkpoints each. Re-priced spend was $232.31, plus about $4.70 for five errored runs whose traces were lost (Deviation 3), so about $237 in total against the $300 cap. The method is in [`docs/preregistration-seed-2.md`](../../docs/preregistration-seed-2.md). Read its Deviations section before using these numbers.

## Preregistered tests (pooled seeds 1 and 2; 95% bootstrap over problems)

| | Test | Result | Contradicts post 1? |
|---|---|---|---|
| **H1, primary** | C − A, hidden-test pass | **−1.3pp [−2.5, −0.3]** | No. The interval lies below 0, not above it. The reviewer does not raise pass; pooled, it lowers it slightly. |
| H2 | C − A, cost ratio | +53% [+36, +76] | No. The lower end is above +25%. |
| H3 | D − A, erosion with `tests/` removed | −0.086 [−0.121, −0.057] | No. The interval lies below 0. |
| H4 | B − A, hidden-test pass | −2.0pp [−4.0, −0.6] | No. The interval is not entirely outside ±3pp. It does exclude 0: B is measurably below A. |
| E1, exploratory | As − A, pass, seed 2 | −7.0pp [−11.8, −3.3] | Manipulation check passed: stripping the examples hurt. |
| E2, exploratory | (Cs − As) − (C − A), pass, seed 2 | +3.9pp [+0.4, +8.1] | No. The interval lies above 0, as the mechanism predicts. |

On the 14 problems where stripping removed at least 10% of the spec, E1 is −8.8pp [−14.6, −4.0] and E2 is +4.1pp [−0.6, +9.4].

The sensitivity check with C and Cs as first run (Deviation 4, [`intervals-asrun.md`](intervals-asrun.md)) gives H1 −1.2pp [−2.4, −0.2] and E2 +3.5pp [+0.2, +7.4].

## Rerun flip rate (descriptive, not preregistered; Deviation 5)

Across arms A to D, **9.2% [3.3, 15.7]** of (problem, checkpoint) units flipped strict pass between seed 1 and seed 2. Per arm the rate was 7.9% to 10.9%. At the problem level the rate was 1.2% [0.0, 3.8], but that number is near its floor, because almost no problem is strict-solved end to end. This is not the same quantity as the Harness Leaderboard's 23.4%, which is measured over their tasks with three attempts per configuration. See [`flips.md`](flips.md).

## Files

- `table.md`, `checkpoints.csv`: seed 2 alone, from `scripts/vl_table.py`.
- `intervals.md`: `scripts/vl_intervals.py` over seeds 1 and 2. This is the preregistered analysis.
- `flips.md`: `scripts/vl_flips.py`.
- `checkpoints-asrun.csv`, `intervals-asrun.md`, `asrun-backup/`: the as-run sensitivity check.
- `problems-stripped.strip_manifest.json`, `problems-stripped.strip.diff`: what the stripped arms lost, per problem.
- `logs/`: driver, per-arm, shadow-review, judge and spend logs. The first launch's per-arm agent logs were overwritten (Deviation 3). Per-problem logs are in the traces.
- Traces: release `seed-2`, `vl-seed-2-traces.tar.zst` (sha256 `c5e08817…53fd51`).

Shadow-review verdicts on 3 checkpoints needed a retry after an unparseable reply, and none ended as an error (Deviation 6). The cross-family judge (Gemini 3.8 Flash) covered only part of the final checkpoints. Its spend shows as $0.00 because the judge has no price on file, so its call cap is what limited it.
