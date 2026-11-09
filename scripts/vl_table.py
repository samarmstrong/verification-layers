"""Results table for the verification-layers instrument.

Reads one finished run directory per arm and prints, per arm: cost per
checkpoint (agent and reviewer), hidden-test pass rate, strict solve rate,
erosion and verbosity (level and per-checkpoint slope), reviewer rejection
rates, and the shadow reviewer's precision and recall against the hidden
tests. Every quality-and-pass comparison is paired against the baseline arm on
the same (problem, checkpoint), with a 95% bootstrap interval resampled over
problems, since checkpoints within a problem are not independent.

    uv run python scripts/vl_table.py \\
        A=outputs/vl/a-plain/<model>/<ts> B=outputs/vl/b-conveyor/<model>/<ts> \\
        C=outputs/vl/c-review/<model>/<ts> D=outputs/vl/d-tests/<model>/<ts> \\
        --csv vl_rows.csv --no-tests-quality D

``--no-tests-quality D`` re-scores arm D's erosion and verbosity on each
snapshot with its tests removed (``tests/``, ``test_*.py``, ``*_test.py``,
``conftest.py``), using the same pinned scb-check.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from slop_code.common import SNAPSHOT_DIR_NAME
from slop_code.common.llms import APIPricing
from slop_code.common.llms import ModelCatalog
from slop_code.common.llms import TokenUsage
from slop_code.metrics.checkpoint.driver import _get_scb_check_metrics

BOOTSTRAP_SAMPLES = 2000
_TEST_PATTERNS = ("test_*.py", "*_test.py", "conftest.py")


def _load_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.exists() else None


def _strip_tests(snapshot: Path, dest: Path) -> None:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {
            n
            for n in names
            if n in {"tests", ".venv", "venv"}
            or any(Path(n).match(pattern) for pattern in _TEST_PATTERNS)
        }

    shutil.copytree(snapshot, dest, ignore=ignore)


def _quality_without_tests(checkpoint_dir: Path) -> dict[str, Any]:
    snapshot = checkpoint_dir / SNAPSHOT_DIR_NAME
    if not snapshot.is_dir():
        return {}
    with tempfile.TemporaryDirectory() as tmp:
        _strip_tests(snapshot, Path(tmp) / SNAPSHOT_DIR_NAME)
        return _get_scb_check_metrics(Path(tmp))


def agent_cost_from_tokens(checkpoint_dir: Path, pricing: APIPricing) -> float | None:
    """Re-price every Claude Code call in the checkpoint from its own tokens.

    Claude Code's ``total_cost_usd`` is cumulative across ``--continue`` and uses
    the CLI's built-in price table. Re-pricing each call's token counts with the
    model file puts the agent and the reviewer on one price list.
    """
    stdout = checkpoint_dir / "agent" / "stdout.jsonl"
    if not stdout.exists():
        return None
    total = 0.0
    for line in stdout.read_text().splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") != "result":
            continue
        usage = payload.get("usage") or {}
        total += pricing.get_cost(
            TokenUsage(
                input=usage.get("input_tokens") or 0,
                output=usage.get("output_tokens") or 0,
                cache_read=usage.get("cache_read_input_tokens") or 0,
                cache_write=usage.get("cache_creation_input_tokens") or 0,
            )
        )
    return total


def load_rows(
    arm: str, run_dir: Path, *, strip_tests: bool, pricing: APIPricing | None
) -> list[dict[str, Any]]:
    rows = []
    results = run_dir / "checkpoint_results.jsonl"
    for line in results.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        checkpoint_dir = run_dir / record["problem"] / record["checkpoint"]
        in_loop = _load_json(checkpoint_dir / "review.json")
        shadow = _load_json(checkpoint_dir / "shadow_review.json")
        total = record.get("total_tests") or 0
        review_cost = in_loop["review_cost"] if in_loop else 0.0
        repriced = (
            agent_cost_from_tokens(checkpoint_dir, pricing) if pricing else None
        )
        agent_cost = repriced if repriced is not None else (record.get("cost") or 0.0)
        row = {
            "arm": arm,
            "problem": record["problem"],
            "checkpoint": record["checkpoint"],
            "idx": record["idx"],
            "agent_cost": agent_cost,
            "agent_cost_cli_reported": record.get("cost") or 0.0,
            "review_cost": review_cost,
            "total_cost": agent_cost + review_cost,
            "test_pass": (record.get("passed_tests") or 0) / total if total else None,
            "strict_solved": record.get("strict_pass_rate") == 1.0,
            "erosion": record.get("erosion"),
            "verbosity": record.get("verbosity"),
            "in_loop_first_verdict": in_loop["rounds"][0]["verdict"] if in_loop else None,
            "in_loop_rounds": len(in_loop["rounds"]) if in_loop else 0,
            "shadow_verdict": shadow["verdict"] if shadow else None,
            "shadow_cost": shadow["cost"] if shadow else 0.0,
        }
        for path in sorted(checkpoint_dir.glob("cross_judge_*.json")):
            judged = json.loads(path.read_text())
            row[f"judge_{judged['judge']}"] = judged["verdict"]
        if strip_tests:
            q = _quality_without_tests(checkpoint_dir)
            row["erosion_no_tests"] = q.get("erosion")
            row["verbosity_no_tests"] = q.get("verbosity")
        rows.append(row)
    return rows


def _mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return statistics.fmean(clean) if clean else None


def _slope(points: list[tuple[int, float]]) -> float | None:
    if len(points) < 2:
        return None
    xs, ys = zip(*points, strict=True)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in points) / den if den else None


def _mean_slope(rows: list[dict[str, Any]], key: str) -> float | None:
    by_problem: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for r in rows:
        if r.get(key) is not None:
            by_problem[r["problem"]].append((r["idx"], r[key]))
    return _mean([_slope(sorted(p)) for p in by_problem.values()])


def _rate(rows: list[dict[str, Any]], pred, base=lambda r: True) -> float | None:
    pool = [r for r in rows if base(r)]
    return sum(1 for r in pool if pred(r)) / len(pool) if pool else None


def paired_delta(
    base: list[dict[str, Any]], arm: list[dict[str, Any]], key: str, seed: int = 0
) -> tuple[float, float, float] | None:
    """Mean paired difference arm - base on `key`, bootstrap CI over problems."""
    base_by = {(r["problem"], r["checkpoint"]): r for r in base}
    diffs: dict[str, list[float]] = defaultdict(list)
    for r in arm:
        b = base_by.get((r["problem"], r["checkpoint"]))
        if b and r.get(key) is not None and b.get(key) is not None:
            diffs[r["problem"]].append(float(r[key]) - float(b[key]))
    if not diffs:
        return None
    problems = list(diffs)
    point = statistics.fmean(d for p in problems for d in diffs[p])
    rng = random.Random(seed)  # noqa: S311 - bootstrap, not crypto
    boots = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = [d for p in rng.choices(problems, k=len(problems)) for d in diffs[p]]
        boots.append(statistics.fmean(sample))
    boots.sort()
    return point, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots)) - 1]


def _fmt(value: float | None, *, pct: bool = False, money: bool = False) -> str:
    if value is None:
        return "—"
    if money:
        return f"${value:.3f}"
    return f"{value * 100:.1f}%" if pct else f"{value:.3f}"


def _fmt_delta(d: tuple[float, float, float] | None, *, pct: bool = False) -> str:
    if d is None:
        return "—"
    if pct:
        return f"{d[0] * 100:+.1f}pp [{d[1] * 100:+.1f}, {d[2] * 100:+.1f}]"
    return f"{d[0]:+.3f} [{d[1]:+.3f}, {d[2]:+.3f}]"


def cohen_kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    """Agreement between two judges' reject calls, corrected for chance."""
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(1 for a, b in pairs if a == b) / n
    pa = sum(1 for a, _ in pairs if a) / n
    pb = sum(1 for _, b in pairs if b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def judge_agreement(arms: dict[str, list[dict[str, Any]]]) -> str:
    rows = [r for rs in arms.values() for r in rs]
    judges = ["claude"] + sorted(
        {k.removeprefix("judge_") for r in rows for k in r if k.startswith("judge_")}
    )
    if len(judges) < 2:
        return ""

    def verdict(r: dict[str, Any], judge: str) -> str | None:
        v = r["shadow_verdict"] if judge == "claude" else r.get(f"judge_{judge}")
        return v if v in {"approve", "reject"} else None

    lines = [
        "",
        "Judge agreement (reject = would send back). Rejection rate per arm under each "
        "judge family, on the snapshots that family judged:",
        "",
        "| Arm | " + " | ".join(judges) + " |",
        "|---|" + "---|" * len(judges),
    ]
    for name, rs in arms.items():
        cells = []
        for judge in judges:
            calls = [verdict(r, judge) for r in rs]
            calls = [c for c in calls if c]
            cells.append(
                f"{sum(c == 'reject' for c in calls) / len(calls) * 100:.0f}% (n={len(calls)})"
                if calls
                else "—"
            )
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += ["", "| Judges | Snapshots both judged | Cohen's κ |", "|---|---|---|"]
    for i, a in enumerate(judges):
        for b in judges[i + 1 :]:
            pairs = [
                (verdict(r, a) == "reject", verdict(r, b) == "reject")
                for r in rows
                if verdict(r, a) and verdict(r, b)
            ]
            lines.append(f"| {a} vs {b} | {len(pairs)} | {_fmt(cohen_kappa(pairs))} |")
    orderings = []
    for judge in judges:
        rates = {}
        for name, rs in arms.items():
            calls = [c for c in (verdict(r, judge) for r in rs) if c]
            if calls:
                rates[name] = sum(c == "reject" for c in calls) / len(calls)
        orderings.append(
            f"{judge}: " + " < ".join(sorted(rates, key=rates.get))
        )
    lines += ["", "Arms ordered from fewest to most rejections, per judge: " + "; ".join(orderings)]
    return "\n".join(lines)


def summarize(arms: dict[str, list[dict[str, Any]]], baseline: str) -> str:
    not_solved = lambda r: not r["strict_solved"]  # noqa: E731
    lines = [
        "| Arm | Checkpoints | Cost / ckpt (agent + review) | Hidden-test pass | Strict solve | "
        "Erosion | Erosion slope | Verbosity | Verbosity slope | In-loop reject (1st round) | "
        "Shadow reject | Shadow precision | Shadow recall |",
        "|" + "---|" * 13,
    ]
    for name, rows in arms.items():
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    str(len(rows)),
                    _fmt(_mean([r["total_cost"] for r in rows]), money=True)
                    + f" ({_fmt(_mean([r['review_cost'] for r in rows]), money=True)} review)",
                    _fmt(_mean([r["test_pass"] for r in rows]), pct=True),
                    _fmt(_rate(rows, lambda r: r["strict_solved"]), pct=True),
                    _fmt(_mean([r["erosion"] for r in rows])),
                    _fmt(_mean_slope(rows, "erosion")),
                    _fmt(_mean([r["verbosity"] for r in rows])),
                    _fmt(_mean_slope(rows, "verbosity")),
                    _fmt(
                        _rate(
                            rows,
                            lambda r: r["in_loop_first_verdict"] == "reject",
                            lambda r: r["in_loop_first_verdict"] in {"approve", "reject"},
                        ),
                        pct=True,
                    ),
                    _fmt(
                        _rate(
                            rows,
                            lambda r: r["shadow_verdict"] == "reject",
                            lambda r: r["shadow_verdict"] in {"approve", "reject"},
                        ),
                        pct=True,
                    ),
                    _fmt(
                        _rate(rows, not_solved, lambda r: r["shadow_verdict"] == "reject"),
                        pct=True,
                    ),
                    _fmt(
                        _rate(
                            rows,
                            lambda r: r["shadow_verdict"] == "reject",
                            lambda r: not_solved(r) and r["shadow_verdict"] in {"approve", "reject"},
                        ),
                        pct=True,
                    ),
                ]
            )
            + " |"
        )
        if any("erosion_no_tests" in r for r in rows):
            lines.append(
                f"| {name} without tests/ | | | | | {_fmt(_mean([r.get('erosion_no_tests') for r in rows]))} "
                f"| {_fmt(_mean_slope(rows, 'erosion_no_tests'))} "
                f"| {_fmt(_mean([r.get('verbosity_no_tests') for r in rows]))} "
                f"| {_fmt(_mean_slope(rows, 'verbosity_no_tests'))} | | | | |"
            )

    base = arms.get(baseline)
    if base is not None:
        lines += [
            "",
            f"Paired against {baseline} (same problem and checkpoint; 95% bootstrap CI over problems):",
            "",
            "| Arm | Δ cost / ckpt | Δ hidden-test pass | Δ strict solve | Δ erosion | Δ verbosity | "
            "Extra $ per +1pp pass |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, rows in arms.items():
            if name == baseline:
                continue
            solved = [{**r, "strict_solved": float(r["strict_solved"])} for r in rows]
            base_solved = [{**r, "strict_solved": float(r["strict_solved"])} for r in base]
            d_cost = paired_delta(base, rows, "total_cost")
            d_pass = paired_delta(base, rows, "test_pass")
            per_point = (
                d_cost[0] / (d_pass[0] * 100)
                if d_cost and d_pass and d_pass[0] > 0
                else None
            )
            lines.append(
                f"| {name} | {_fmt_delta(d_cost)} | {_fmt_delta(d_pass, pct=True)} "
                f"| {_fmt_delta(paired_delta(base_solved, solved, 'strict_solved'), pct=True)} "
                f"| {_fmt_delta(paired_delta(base, rows, 'erosion'))} "
                f"| {_fmt_delta(paired_delta(base, rows, 'verbosity'))} "
                f"| {_fmt(per_point, money=True) if per_point else '—'} |"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("arms", nargs="+", help="NAME=run_dir, baseline first")
    parser.add_argument("--baseline", default=None, help="Defaults to the first arm")
    parser.add_argument("--csv", type=Path, default=None)
    parser.add_argument("--no-tests-quality", nargs="*", default=[])
    parser.add_argument(
        "--price-model",
        default=None,
        help="Model catalog name whose pricing re-prices every agent call "
        "(recommended: the run model). Without it, Claude Code's own figure is used.",
    )
    args = parser.parse_args()

    pricing = None
    if args.price_model:
        model_def = ModelCatalog.get(args.price_model)
        if model_def is None or model_def.pricing is None:
            raise SystemExit(f"No pricing for model {args.price_model!r}")
        pricing = model_def.pricing
    arms: dict[str, list[dict[str, Any]]] = {}
    for spec in args.arms:
        name, _, path = spec.partition("=")
        arms[name] = load_rows(
            name,
            Path(path),
            strip_tests=name in args.no_tests_quality,
            pricing=pricing,
        )
    print(summarize(arms, args.baseline or next(iter(arms))))
    print(judge_agreement(arms))
    if args.csv:
        rows = [r for rs in arms.values() for r in rs]
        fields = sorted({k for r in rows for k in r})
        with args.csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
