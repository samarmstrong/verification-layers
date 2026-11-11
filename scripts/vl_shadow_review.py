"""Shadow-review every checkpoint snapshot of a finished run.

The same reviewer the adversarial-review arm uses in the loop, run after the
fact with nothing sent back to the agent. On a run that already had an in-loop
reviewer it reviews the final snapshot, which is what the hidden tests scored.

Writes ``shadow_review.json`` next to each checkpoint's snapshot and skips
checkpoints that already have one, so it can be re-run after a partial pass.

    uv run python scripts/vl_shadow_review.py outputs/<run_dir> \\
        --model sonnet-5 --provider vertex --effort medium
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from slop_code import problem_catalog
from slop_code.agent_runner.credentials import API_KEY_STORE
from slop_code.agent_runner.review import ReviewConfig
from slop_code.agent_runner.review import Reviewer
from slop_code.agent_runner.review import specs_through
from slop_code.common import SNAPSHOT_DIR_NAME
from slop_code.common.llms import ModelCatalog
from slop_code.evaluation.config import ProblemConfig


def _jobs(run_dir: Path, problem_root: Path):
    for problem_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        config_path = problem_root / problem_dir.name
        if not config_path.exists():
            continue
        problem = ProblemConfig.from_yaml(config_path)
        for name, _ in problem.iterate_checkpoint_items():
            checkpoint_dir = problem_dir / name
            snapshot = checkpoint_dir / SNAPSHOT_DIR_NAME
            out = checkpoint_dir / "shadow_review.json"
            if snapshot.is_dir() and not out.exists():
                yield problem, name, snapshot, out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--model", required=True, help="Model catalog name")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--effort", default=None)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    model_def = ModelCatalog.get(args.model)
    if model_def is None:
        raise SystemExit(f"Model {args.model!r} not in the catalog")
    reviewer = Reviewer(
        ReviewConfig(effort=args.effort),
        model_def=model_def,
        credential=API_KEY_STORE.resolve(args.provider),
        thinking_preset=None,
    )
    home = problem_catalog.get_scbench_home()
    problem_root = problem_catalog.get_problem_root(home, bootstrap=False)
    jobs = list(_jobs(args.run_dir, problem_root))
    print(f"{len(jobs)} snapshots to review")

    def run(job) -> float:
        problem, name, snapshot, out = job
        # The reviewer's reply sometimes fails to parse (a finding without `evidence`,
        # or a string where an object belongs) and Reviewer.review raises. Retry, then
        # record the checkpoint as an error so one bad reply does not stop the pass.
        # Errors are excluded from the shadow rates, as with the cross-family judge.
        for attempt in range(3):
            try:
                result = reviewer.review(specs_through(problem, name), snapshot)
                break
            except (TypeError, ValueError) as exc:  # pydantic ValidationError is a ValueError
                print(f"{problem.name}/{name}: reply did not parse (attempt {attempt + 1}): {type(exc).__name__}")
        else:
            out.write_text(json.dumps({"mode": "shadow", "verdict": "error", "cost": 0.0}, indent=2))
            print(f"{problem.name}/{name}: error after 3 attempts")
            return 0.0
        out.write_text(
            json.dumps(
                {"mode": "shadow", **result.model_dump(mode="json")}, indent=2
            )
        )
        print(f"{problem.name}/{name}: {result.verdict} (${result.cost:.3f})")
        return result.cost

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        total = sum(pool.map(run, jobs))
    print(f"shadow review cost: ${total:.2f}")


if __name__ == "__main__":
    main()
