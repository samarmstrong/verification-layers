"""Paired intervals across seeds, as preregistered in docs/preregistration-seed-2.md.

Reads the per-checkpoint CSVs that ``vl_table.py --csv`` writes, one per seed, and
prints a Markdown report:

1. Primary contrast (C vs A) and the other arms vs A: the mean paired difference
   on the same (seed, problem, checkpoint), per seed and pooled, with a 95%
   percentile bootstrap interval that resamples problems (all of a problem's
   checkpoints and seeds move together, since they are not independent).
2. Per-problem paired deltas for the primary contrast.
3. Rerun noise: each arm against itself across seeds (strict-solve flip rate,
   mean absolute change in hidden-test pass, and the paired delta).
4. Exploratory stripped-spec arms (As, Cs): the manipulation check (As vs A), the
   reviewer effect without worked examples (Cs vs As), and the difference in
   differences (Cs - As) - (C - A), all within the seeds that ran them.

With one seed and the default settings, section 1 reproduces the paired table
that ``vl_table.py`` printed for that seed.

    uv run python scripts/vl_intervals.py seed-1=results/seed-1/checkpoints.csv \\
        seed-2=results/seed-2/checkpoints.csv \\
        --strip-manifest results/seed-2/problems-stripped.strip_manifest.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

BOOTSTRAP_SAMPLES = 2000
METRICS = [
    ("total_cost", "Δ cost / ckpt", "money"),
    ("test_pass", "Δ hidden-test pass", "pp"),
    ("strict_solved", "Δ strict solve", "pp"),
    ("erosion", "Δ erosion", "num"),
    ("verbosity", "Δ verbosity", "num"),
]
Row = dict[str, object]
Key = tuple[str, str, str]  # seed, problem, checkpoint


def _num(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    if value in {"True", "False"}:
        return 1.0 if value == "True" else 0.0
    return float(value)


def load(specs: list[str]) -> dict[str, dict[Key, Row]]:
    """arm -> (seed, problem, checkpoint) -> row."""
    arms: dict[str, dict[Key, Row]] = defaultdict(dict)
    for spec in specs:
        seed, _, path = spec.partition("=")
        with Path(path).open() as f:
            for r in csv.DictReader(f):
                row: Row = {k: _num(v) if k not in {"arm", "problem", "checkpoint"} else v
                            for k, v in r.items()
                            if k not in {"in_loop_first_verdict", "shadow_verdict"} and not k.startswith("judge_")}
                row["seed"] = seed
                # Arm D is compared on production code only (tests/ stripped).
                if r.get("erosion_no_tests"):
                    row["erosion"] = _num(r["erosion_no_tests"])
                    row["verbosity"] = _num(r["verbosity_no_tests"])
                arms[r["arm"]][(seed, r["problem"], r["checkpoint"])] = row
    return arms


def diffs_by_problem(
    base: dict[Key, Row], arm: dict[Key, Row], key: str, seeds: set[str] | None = None
) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(list)
    for k, r in arm.items():
        if seeds is not None and k[0] not in seeds:
            continue
        b = base.get(k)
        if b is None or r.get(key) is None or b.get(key) is None:
            continue
        out[k[1]].append(float(r[key]) - float(b[key]))  # type: ignore[arg-type]
    return out


def bootstrap(
    diffs: dict[str, list[float]], *, samples: int, seed: int = 0
) -> tuple[float, float, float, int] | None:
    """Checkpoint-weighted mean of the paired differences; CI resamples problems."""
    if not diffs:
        return None
    problems = sorted(diffs)
    point = statistics.fmean(d for p in problems for d in diffs[p])
    rng = random.Random(seed)  # noqa: S311 - bootstrap, not crypto
    boots = []
    for _ in range(samples):
        drawn = rng.choices(problems, k=len(problems))
        boots.append(statistics.fmean(d for p in drawn for d in diffs[p]))
    boots.sort()
    n = sum(len(v) for v in diffs.values())
    return point, boots[int(0.025 * samples)], boots[int(0.975 * samples) - 1], n


def did_bootstrap(
    first: dict[str, list[float]], second: dict[str, list[float]], *, samples: int, seed: int = 0
) -> tuple[float, float, float, int] | None:
    """(mean of second) - (mean of first), problems resampled jointly."""
    problems = sorted(set(first) & set(second))
    if not problems:
        return None

    def stat(ps: list[str]) -> float:
        return statistics.fmean(d for p in ps for d in second[p]) - statistics.fmean(
            d for p in ps for d in first[p]
        )

    rng = random.Random(seed)  # noqa: S311
    boots = sorted(stat(rng.choices(problems, k=len(problems))) for _ in range(samples))
    return stat(problems), boots[int(0.025 * samples)], boots[int(0.975 * samples) - 1], len(problems)


def ratio_bootstrap(
    base: dict[Key, Row], arm: dict[Key, Row], key: str, *, samples: int, seed: int = 0
) -> tuple[float, float, float] | None:
    """Ratio of means arm/base on paired checkpoints (e.g. +52% cost), problems resampled."""
    pairs: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for k, r in arm.items():
        b = base.get(k)
        if b and r.get(key) is not None and b.get(key) is not None:
            pairs[k[1]].append((float(b[key]), float(r[key])))  # type: ignore[arg-type]
    if not pairs:
        return None
    problems = sorted(pairs)

    def stat(ps: list[str]) -> float:
        bs = [x for p in ps for x, _ in pairs[p]]
        ar = [y for p in ps for _, y in pairs[p]]
        return sum(ar) / sum(bs) - 1

    rng = random.Random(seed)  # noqa: S311
    boots = sorted(stat(rng.choices(problems, k=len(problems))) for _ in range(samples))
    return stat(problems), boots[int(0.025 * samples)], boots[int(0.975 * samples) - 1]


def fmt(d: tuple | None, kind: str) -> str:
    if d is None:
        return "—"
    point, lo, hi = d[0], d[1], d[2]
    if kind == "pp":
        return f"{point * 100:+.1f}pp [{lo * 100:+.1f}, {hi * 100:+.1f}]"
    if kind == "pct":
        return f"{point * 100:+.0f}% [{lo * 100:+.0f}, {hi * 100:+.0f}]"
    return f"{point:+.3f} [{lo:+.3f}, {hi:+.3f}]"


def rekey(rows: dict[Key, Row], seed_map: dict[str, str]) -> dict[Key, Row]:
    """Move rows from one seed label to another, so an arm can be paired with itself."""
    return {(seed_map[k[0]], k[1], k[2]): r for k, r in rows.items() if k[0] in seed_map}


def contrast_table(
    arms: dict[str, dict[Key, Row]], pairs: list[tuple[str, str]], seed_sets: list[tuple[str, set[str] | None]],
    samples: int,
) -> list[str]:
    lines = [
        "| Contrast | Seeds | Pairs | " + " | ".join(label for _, label, _ in METRICS) + " | Cost ratio |",
        "|---|---|---|" + "---|" * (len(METRICS) + 1),
    ]
    for base_name, arm_name in pairs:
        if base_name not in arms or arm_name not in arms:
            continue
        base, arm = arms[base_name], arms[arm_name]
        for label, seeds in seed_sets:
            cells, n = [], 0
            for key, _, kind in METRICS:
                d = bootstrap(diffs_by_problem(base, arm, key, seeds), samples=samples)
                n = max(n, d[3] if d else 0)
                cells.append(fmt(d, kind))
            if n == 0:
                continue
            sub_b = {k: v for k, v in base.items() if seeds is None or k[0] in seeds}
            sub_a = {k: v for k, v in arm.items() if seeds is None or k[0] in seeds}
            ratio = ratio_bootstrap(sub_b, sub_a, "total_cost", samples=samples)
            lines.append(
                f"| {arm_name} − {base_name} | {label} | {n} | " + " | ".join(cells) + f" | {fmt(ratio, 'pct')} |"
            )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("seeds", nargs="+", help="LABEL=checkpoints.csv, in seed order")
    parser.add_argument("--samples", type=int, default=BOOTSTRAP_SAMPLES)
    parser.add_argument("--strip-manifest", type=Path, default=None,
                        help="strip_manifest.json, for the subset where examples were removed")
    parser.add_argument("--min-removed", type=float, default=0.10,
                        help="Stripped-spec subset: problems with at least this share of spec words removed")
    args = parser.parse_args()

    arms = load(args.seeds)
    labels = [s.partition("=")[0] for s in args.seeds]
    seed_sets: list[tuple[str, set[str] | None]] = [(lab, {lab}) for lab in labels]
    if len(labels) > 1:
        seed_sets.append(("pooled", None))
    s = args.samples
    out = [
        f"# Paired intervals: {', '.join(labels)}",
        "",
        f"Mean paired difference on the same (seed, problem, checkpoint); 95% percentile bootstrap "
        f"over problems ({s} resamples, a problem's checkpoints and seeds resampled together). "
        "Arm D's erosion and verbosity are scored without its tests/. Cost ratio is "
        "sum(arm cost) / sum(A cost) − 1 on the same pairs.",
        "",
        "## 1. Arms against A (primary contrast: C − A)",
        "",
    ]
    out += contrast_table(arms, [("A", "C"), ("A", "B"), ("A", "D")], seed_sets, s)

    if "A" in arms and "C" in arms:
        out += ["", "## 2. Per-problem paired deltas, C − A (hidden-test pass, pp; cost, $/ckpt)", ""]
        out += ["| Problem | " + " | ".join(f"{lab} pass" for lab in labels) + " | pooled pass | pooled cost |",
                "|---|" + "---|" * (len(labels) + 2)]
        pooled_pass = diffs_by_problem(arms["A"], arms["C"], "test_pass")
        pooled_cost = diffs_by_problem(arms["A"], arms["C"], "total_cost")
        per_seed = {lab: diffs_by_problem(arms["A"], arms["C"], "test_pass", {lab}) for lab in labels}
        for p in sorted(pooled_pass):
            cells = [f"{statistics.fmean(per_seed[lab][p]) * 100:+.1f}" if per_seed[lab].get(p) else "—"
                     for lab in labels]
            out.append(f"| {p} | " + " | ".join(cells)
                       + f" | {statistics.fmean(pooled_pass[p]) * 100:+.1f} | {statistics.fmean(pooled_cost[p]):+.3f} |")
        wins = sum(1 for p in pooled_pass if statistics.fmean(pooled_pass[p]) > 0)
        losses = sum(1 for p in pooled_pass if statistics.fmean(pooled_pass[p]) < 0)
        out += ["", f"C ahead on {wins} problems, behind on {losses}, tied on {len(pooled_pass) - wins - losses}."]

    if len(labels) > 1:
        out += ["", "## 3. Rerun noise: each arm against itself, later seed − earlier seed", "",
                "| Arm | Seeds | Pairs | Strict-solve flips | Mean abs Δ pass | Δ hidden-test pass | Δ cost / ckpt |",
                "|---|---|---|---|---|---|---|"]
        for name in sorted(arms):
            for i, earlier in enumerate(labels):
                for later in labels[i + 1:]:
                    base = rekey({k: v for k, v in arms[name].items() if k[0] == earlier}, {earlier: "x"})
                    again = rekey({k: v for k, v in arms[name].items() if k[0] == later}, {later: "x"})
                    common = set(base) & set(again)
                    if not common:
                        continue
                    flips = sum(1 for k in common if base[k]["strict_solved"] != again[k]["strict_solved"])
                    abs_pass = [abs(float(again[k]["test_pass"]) - float(base[k]["test_pass"]))  # type: ignore[arg-type]
                                for k in common if again[k]["test_pass"] is not None and base[k]["test_pass"] is not None]
                    d_pass = bootstrap(diffs_by_problem(base, again, "test_pass"), samples=s)
                    d_cost = bootstrap(diffs_by_problem(base, again, "total_cost"), samples=s)
                    out.append(f"| {name} | {later} vs {earlier} | {len(common)} | {flips / len(common) * 100:.1f}% "
                               f"| {statistics.fmean(abs_pass) * 100:.1f}pp | {fmt(d_pass, 'pp')} | {fmt(d_cost, 'money')} |")

    if "As" in arms or "Cs" in arms:
        stripped_seeds = {k[0] for name in ("As", "Cs") for k in arms.get(name, {})}
        subsets: list[tuple[str, set[str] | None]] = [("all problems", None)]
        if args.strip_manifest:
            manifest = json.loads(args.strip_manifest.read_text())["problems"]
            keep = {p for p, v in manifest.items() if v["fraction_removed"] >= args.min_removed}
            subsets.append((f"≥{args.min_removed:.0%} of spec removed ({len(keep)} problems)", keep))
        out += ["", "## 4. Exploratory: stripped specs (worked I/O examples removed)", "",
                f"Within seeds that ran the stripped arms: {', '.join(sorted(stripped_seeds))}.", "",
                "| Contrast | Problems | Pairs | Δ hidden-test pass | Δ strict solve | Δ cost / ckpt |",
                "|---|---|---|---|---|---|"]
        for label, keep in subsets:
            def only(rows: dict[Key, Row], keep: set[str] | None = keep) -> dict[Key, Row]:
                return {k: v for k, v in rows.items() if k[0] in stripped_seeds and (keep is None or k[1] in keep)}
            for base_name, arm_name in [("A", "As"), ("C", "Cs"), ("As", "Cs"), ("A", "C")]:
                if base_name not in arms or arm_name not in arms:
                    continue
                b, a = only(arms[base_name]), only(arms[arm_name])
                d = [bootstrap(diffs_by_problem(b, a, key), samples=s) for key in ("test_pass", "strict_solved", "total_cost")]
                if d[0] is None:
                    continue
                out.append(f"| {arm_name} − {base_name} | {label} | {d[0][3]} | {fmt(d[0], 'pp')} "
                           f"| {fmt(d[1], 'pp')} | {fmt(d[2], 'money')} |")
            if all(n in arms for n in ("A", "C", "As", "Cs")):
                full = diffs_by_problem(only(arms["A"]), only(arms["C"]), "test_pass")
                bare = diffs_by_problem(only(arms["As"]), only(arms["Cs"]), "test_pass")
                did = did_bootstrap(full, bare, samples=s)
                out.append(f"| (Cs − As) − (C − A) | {label} | {did[3] if did else 0} problems "
                           f"| {fmt(did, 'pp')} | | |")
    print("\n".join(out))


if __name__ == "__main__":
    main()
