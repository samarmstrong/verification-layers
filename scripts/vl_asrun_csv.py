"""Seed 2 sensitivity check (preregistration Deviation 4): C and Cs as first run.

Takes seed 2's final per-checkpoint CSV and, for the (arm, problem) runs that the
reviewer parse error stopped early and that were rerun, swaps the rerun's rows for
the as-run rows saved in ``asrun-backup/<arm-dir>/checkpoint_results.jsonl``. Only
hidden-test pass and strict solve are filled in from the backup. Cost, erosion and
verbosity are left blank for those rows (the backup has no re-priced or review cost),
so the check covers pass and strict solve only.

    python scripts/vl_asrun_csv.py results/seed-2/checkpoints.csv \\
        results/seed-2/asrun-backup > results/seed-2/checkpoints-asrun.csv
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RERUN = {"C": ("c-review", {"forge", "rejector"}),
         "Cs": ("c-review-stripped", {"forge", "eve_route_planner", "circuit_eval"})}


def main() -> None:
    final, backup = Path(sys.argv[1]), Path(sys.argv[2])
    with final.open() as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = [r for r in reader if not (r["arm"] in RERUN and r["problem"] in RERUN[r["arm"]][1])]
    for arm, (arm_dir, problems) in RERUN.items():
        for line in (backup / arm_dir / "checkpoint_results.jsonl").read_text().splitlines():
            rec = json.loads(line)
            if rec["problem"] not in problems:
                continue
            total = rec.get("total_tests") or 0
            row = dict.fromkeys(fields, "")
            row.update(arm=arm, problem=rec["problem"], checkpoint=rec["checkpoint"], idx=rec["idx"],
                       test_pass=(rec.get("passed_tests") or 0) / total if total else "",
                       strict_solved=str(rec.get("strict_pass_rate") == 1.0),
                       agent_cost_cli_reported=rec.get("cost") or 0.0)
            rows.append(row)
    w = csv.DictWriter(sys.stdout, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)


if __name__ == "__main__":
    main()
