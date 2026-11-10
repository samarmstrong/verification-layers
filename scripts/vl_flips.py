"""Same-configuration rerun flip rate between two seeds (descriptive; not preregistered).

For each of arms A to D, and pooled over them:

- Checkpoint unit: the share of (problem, checkpoint) units whose pass/fail differs
  between the two seeds. "Pass" is the checkpoint's strict pass (every hidden test
  passes; ``strict_solved`` in the CSV).
- Problem unit: the share of problems whose strict solve differs. A problem counts as
  solved in a seed when every one of its checkpoints that ran in both seeds passed.

Intervals are 95% percentile bootstraps over the 20 problems (a problem's units move
together; pooled rows resample problems once and keep all four arms of each drawn
problem). Only units present in both seeds count.

This is not the Harness Leaderboard's quantity: theirs is over their task set, with
three attempts per configuration, and a task flips when its outcome differs across
attempts. Ours is two attempts (seed 1 and seed 2) on 20 multi-checkpoint
SlopCodeBench problems.

    uv run python scripts/vl_flips.py results/seed-1/checkpoints.csv results/seed-2/checkpoints.csv
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

ARMS = ["A", "B", "C", "D"]


def load(path: Path) -> dict[tuple[str, str, str], bool]:
    with path.open() as f:
        return {(r["arm"], r["problem"], r["checkpoint"]): r["strict_solved"] == "True"
                for r in csv.DictReader(f) if r["arm"] in ARMS}


def units(s1: dict, s2: dict) -> dict[str, dict[str, list[tuple[int, int]]]]:
    """arm -> problem -> [(checkpoint flips, 1)...] plus a problem-level entry."""
    ck: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    solved: dict[str, dict[str, list[tuple[bool, bool]]]] = defaultdict(lambda: defaultdict(list))
    for key in sorted(set(s1) & set(s2)):
        arm, problem, _ = key
        ck[arm][problem].append(int(s1[key] != s2[key]))
        solved[arm][problem].append((s1[key], s2[key]))
    prob = {arm: {p: int(all(a for a, _ in v) != all(b for _, b in v)) for p, v in solved[arm].items()}
            for arm in solved}
    return {"checkpoint": ck, "problem": {a: {p: [f] for p, f in d.items()} for a, d in prob.items()}}


def share(data: dict[str, dict[str, list[int]]], arms: list[str], problems: list[str]) -> float:
    flips = sum(f for a in arms for p in problems for f in data.get(a, {}).get(p, []))
    n = sum(len(data.get(a, {}).get(p, [])) for a in arms for p in problems)
    return flips / n if n else float("nan")


def boot(data, arms, problems, samples, seed=0):
    rng = random.Random(seed)  # noqa: S311 - bootstrap
    bs = sorted(share(data, arms, rng.choices(problems, k=len(problems))) for _ in range(samples))
    return share(data, arms, problems), bs[int(0.025 * samples)], bs[int(0.975 * samples) - 1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("earlier", type=Path)
    ap.add_argument("later", type=Path)
    ap.add_argument("--samples", type=int, default=2000)
    args = ap.parse_args()
    u = units(load(args.earlier), load(args.later))
    problems = sorted({p for d in u["checkpoint"].values() for p in d})
    print("| Arm | Checkpoint units | Checkpoint pass/fail flips [95% CI] | Problems | Problem strict-solve flips [95% CI] |")
    print("|---|---|---|---|---|")
    for label, arms in [(a, [a]) for a in ARMS] + [("A–D pooled", ARMS)]:
        n_ck = sum(len(u["checkpoint"].get(a, {}).get(p, [])) for a in arms for p in problems)
        n_pr = sum(len(u["problem"].get(a, {}).get(p, [])) for a in arms for p in problems)
        c = boot(u["checkpoint"], arms, problems, args.samples)
        q = boot(u["problem"], arms, problems, args.samples)
        print(f"| {label} | {n_ck} | {c[0]*100:.1f}% [{c[1]*100:.1f}, {c[2]*100:.1f}] "
              f"| {n_pr} | {q[0]*100:.1f}% [{q[1]*100:.1f}, {q[2]*100:.1f}] |")


if __name__ == "__main__":
    main()
