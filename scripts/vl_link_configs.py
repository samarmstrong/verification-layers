"""Point the installed slop-code-bench at this repo's configs/.

slop-code-bench finds its prompts, agents, environments, model catalog and
providers.yaml relative to its own source file (``<checkout>/configs``). Its
wheel ships none of them, so when it is installed as a dependency the lookup
lands on ``<venv>/lib/pythonX.Y/configs``, which does not exist. This script
symlinks that path to ``configs/`` here. Idempotent; run it after ``uv sync``
(``scripts/vl_seed.sh`` does).

    uv run python scripts/vl_link_configs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import slop_code


def main() -> int:
    source = Path(__file__).resolve().parents[1] / "configs"
    target = Path(slop_code.__file__).resolve().parents[2] / "configs"
    if target.is_symlink():
        if target.resolve() == source:
            print(f"ok: {target} -> {source}")
            return 0
        target.unlink()
    elif target.exists():
        # An editable checkout of slop-code-bench has its own configs/.
        print(f"leaving {target} alone: it is not a symlink")
        return 0
    target.symlink_to(source, target_is_directory=True)
    print(f"linked: {target} -> {source}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
