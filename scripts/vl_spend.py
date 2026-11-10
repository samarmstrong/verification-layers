"""Running spend of one seed, re-priced from tokens like the results table.

Sums, over every run directory of the seed (``outputs/vl/*/<model>_medium/<stamp>``):
each finished checkpoint's Claude Code calls, in-loop review rounds, shadow
reviews and cross-family judgments. A checkpoint still in flight is not counted
until it finishes, so the figure trails the bill by at most one checkpoint per
worker (about $0.50 each on seed 1).

    uv run python scripts/vl_spend.py 20261110T1900            # prints the total
    uv run python scripts/vl_spend.py 20261110T1900 --max-usd 300   # exit 3 above cap
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from slop_code.common.llms import ModelCatalog  # noqa: E402
from vl_table import agent_cost_from_tokens  # noqa: E402


def _cost(path: Path, key: str) -> float:
    try:
        return float(json.loads(path.read_text()).get(key) or 0.0)
    except (OSError, ValueError):
        return 0.0


def seed_spend(outputs: Path, stamp: str, model: str) -> dict[str, float]:
    pricing = ModelCatalog.get(model).pricing
    by_arm: dict[str, float] = {}
    for run_dir in sorted(outputs.glob(f"vl/*/{model}_*/{stamp}")):
        total = 0.0
        for stdout in run_dir.glob("*/*/agent/stdout.jsonl"):
            total += agent_cost_from_tokens(stdout.parent.parent, pricing) or 0.0
        for review in run_dir.glob("*/*/review.json"):
            total += _cost(review, "review_cost")
        for shadow in run_dir.glob("*/*/shadow_review.json"):
            total += _cost(shadow, "cost")
        for judged in run_dir.glob("*/*/cross_judge_*.json"):
            total += _cost(judged, "cost")
        by_arm[run_dir.parts[-3]] = total
    return by_arm


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stamp")
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--model", default="sonnet-5.5")
    parser.add_argument("--max-usd", type=float, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    by_arm = seed_spend(args.outputs, args.stamp, args.model)
    total = sum(by_arm.values())
    if args.json:
        print(json.dumps({"stamp": args.stamp, "total": round(total, 2), "by_arm": by_arm}))
    else:
        for arm, usd in by_arm.items():
            print(f"{arm:22} ${usd:8.2f}")
        print(f"{'total':22} ${total:8.2f}")
    if args.max_usd is not None and total > args.max_usd:
        sys.exit(3)


if __name__ == "__main__":
    main()
