"""Stripped-spec transform for the seed-2 exploratory arms.

Copies each problem in a run config from the SlopCodeBench catalog into a new
flat problems directory and removes the worked input/output examples from every
``checkpoint_N.md`` spec. Tests, solutions, static files and ``config.yaml`` are
copied unchanged, so the hidden tests grade exactly what they grade in the full-
spec arms. Point the runner at the result with ``SCBENCH_PROBLEMS_PATH``.

What counts as a worked example is fixed by four mechanical rules (see
``docs/preregistration-seed-2.md``); everything else (schemas, field tables,
format definitions, error lists, prose with "e.g.") is kept:

  R1  A heading of any level whose text contains "example(s)" is removed with
      everything under it, up to the next heading of the same or a higher level,
      except a subsection whose title starts as a format, schema, semantics or requirements
      section (eve_route_planner files its output format under "# Examples").
  R2  A line that is only bold text containing "example(s)" (``**Example 1: ...**``,
      ``**Examples**``) is removed with everything after it, up to the next
      heading or the next bold-only line that is not an example label.
  R3  A lead-in line that is only "Example:" / "Examples:" / "For example:"
      (optionally bulleted or bold), or a one-line example ending in a colon, is
      removed together with the fenced code blocks, tables and bullet lists that
      follow it.
  R4  A one-line example ("Example: `MUX(X, 0b0101, 0b0111)` -> `0b01X1`") is removed.

Writes ``strip_manifest.json`` (words before and after, and every removed span)
and ``strip.diff`` beside the problems so the cut can be audited line by line.

    uv run python scripts/vl_strip_examples.py configs/runs/vl-a-plain.yaml \\
        --out outputs/vl/problems-stripped
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
from pathlib import Path

import yaml

from slop_code import problem_catalog

_EXAMPLE = re.compile(r"\bexamples?\b", re.IGNORECASE)
_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_BOLD_ONLY = re.compile(r"^\s*\*\*([^*]+)\*\*:?\s*$")
_LEAD_IN = re.compile(
    r"^\s*(?:[*-]\s+)?(?:\*\*)?(?:for\s+)?examples?(?:\s*\(.*\))?\s*:?(?:\*\*)?:?\s*$",
    re.IGNORECASE,
)
_ONE_LINE = re.compile(r"^\s*(?:[*-]\s+)?(?:\*\*)?examples?(?:\*\*)?:(?:\*\*)?\s+\S", re.IGNORECASE)
_FENCE = re.compile(r"^\s*(```|~~~)")
_BULLET = re.compile(r"^\s*(?:[*-]|\d+[.)])\s+\S")
_KEEP = re.compile(
    r"^(?:[\d.)]+\s*)?(?:(?:input|output)\s+format|schema|semantics|requirements)\b", re.IGNORECASE
)


def _fence_mask(lines: list[str]) -> list[bool]:
    """True for every line inside (or opening/closing) a fenced code block."""
    mask, inside, marker = [], False, ""
    for line in lines:
        m = _FENCE.match(line)
        if m and (not inside or m.group(1) == marker):
            mask.append(True)
            inside, marker = (not inside), m.group(1)
            continue
        mask.append(inside)
    return mask


def _block_end(lines: list[str], fenced: list[bool], start: int) -> int:
    """Index just past the fenced block, table or bullet list at ``start``."""
    i = start
    if _FENCE.match(lines[i]):
        i += 1
        while i < len(lines) and not (fenced[i] and _FENCE.match(lines[i])):
            i += 1
        return min(i + 1, len(lines))
    prefix = "|" if lines[i].lstrip().startswith("|") else None
    while i < len(lines) and (
        lines[i].lstrip().startswith("|") if prefix else _BULLET.match(lines[i])
    ):
        i += 1
    return i


def strip_examples(text: str) -> tuple[str, list[dict]]:
    lines = text.splitlines(keepends=True)
    fenced = _fence_mask(lines)
    drop = [False] * len(lines)
    spans: list[dict] = []

    def mark(start: int, end: int, rule: str) -> None:
        if end <= start:
            return
        for k in range(start, end):
            drop[k] = True
        spans.append({"rule": rule, "lines": [start + 1, end], "first": lines[start].strip()[:100]})

    i = 0
    while i < len(lines):
        if drop[i] or fenced[i]:
            i += 1
            continue
        line = lines[i]
        heading = _HEADING.match(line)
        if heading and _EXAMPLE.search(heading.group(2)):  # R1
            level = len(heading.group(1))
            j = i + 1
            while j < len(lines):
                h = _HEADING.match(lines[j])
                if h and not fenced[j] and len(h.group(1)) <= level:
                    break
                j += 1
            # R1 carve-out: a format/schema subsection filed under an Examples
            # heading is specification, not an example; keep it.
            start = i
            k = i + 1
            while k < j:
                h = _HEADING.match(lines[k])
                if h and not fenced[k] and _KEEP.match(h.group(2)) and not _EXAMPLE.search(h.group(2)):
                    sub_level = len(h.group(1))
                    end = k + 1
                    while end < j:
                        h2 = _HEADING.match(lines[end])
                        if h2 and not fenced[end] and len(h2.group(1)) <= sub_level:
                            break
                        end += 1
                    mark(start, k, "R1")
                    spans.append({"rule": "R1-keep", "lines": [k + 1, end], "first": lines[k].strip()[:100]})
                    start = k = end
                    continue
                k += 1
            mark(start, j, "R1")
            i = j
            continue
        bold = _BOLD_ONLY.match(line)
        if bold and _EXAMPLE.search(bold.group(1)):  # R2
            j = i + 1
            while j < len(lines):
                if not fenced[j]:
                    if _HEADING.match(lines[j]):
                        break
                    b = _BOLD_ONLY.match(lines[j])
                    if b and not _EXAMPLE.search(b.group(1)):
                        break
                j += 1
            mark(i, j, "R2")
            i = j
            continue
        one_line = bool(_ONE_LINE.match(line))
        if _LEAD_IN.match(line) or (one_line and line.rstrip().endswith(":")):  # R3
            j = i + 1
            while True:
                k = j
                while k < len(lines) and not lines[k].strip():
                    k += 1
                if k < len(lines) and (
                    _FENCE.match(lines[k])
                    or lines[k].lstrip().startswith("|")
                    or _BULLET.match(lines[k])
                ):
                    j = _block_end(lines, fenced, k)
                    continue
                break
            if j > i + 1:
                mark(i, j, "R3")
                i = j
                continue
        if one_line:  # R4
            mark(i, i + 1, "R4")
        i += 1

    kept = "".join(line for line, d in zip(lines, drop, strict=True) if not d)
    kept = re.sub(r"\n{3,}", "\n\n", kept)
    return kept, spans


def _words(text: str) -> int:
    return len(text.split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_config", type=Path, help="Run config whose `problems:` list to copy")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Flat problems directory to read (default: the synced catalog)",
    )
    parser.add_argument("--force", action="store_true", help="Replace --out if it exists")
    args = parser.parse_args()

    source = args.source or problem_catalog.get_catalog_root(problem_catalog.get_scbench_home())
    manifest_path = source.parent / "manifest.json"
    catalog = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    problems = yaml.safe_load(args.run_config.read_text())["problems"]

    if args.out.exists():
        if not args.force:
            raise SystemExit(f"{args.out} exists; pass --force to replace it")
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)

    report: dict = {"catalog": catalog, "run_config": str(args.run_config), "problems": {}}
    diffs: list[str] = []
    for name in problems:
        src = source / name
        dest = args.out / name
        shutil.copytree(src, dest, symlinks=True)
        per_problem = {}
        for spec in sorted(src.glob("checkpoint_*.md"), key=lambda p: int(p.stem.split("_")[1])):
            text = spec.read_text()
            stripped, spans = strip_examples(text)
            (dest / spec.name).write_text(stripped)
            per_problem[spec.stem] = {
                "words_before": _words(text),
                "words_after": _words(stripped),
                "removed": spans,
            }
            diffs.extend(
                difflib.unified_diff(
                    text.splitlines(keepends=True),
                    stripped.splitlines(keepends=True),
                    fromfile=f"full/{name}/{spec.name}",
                    tofile=f"stripped/{name}/{spec.name}",
                )
            )
        before = sum(c["words_before"] for c in per_problem.values())
        after = sum(c["words_after"] for c in per_problem.values())
        report["problems"][name] = {
            "words_before": before,
            "words_after": after,
            "fraction_removed": round(1 - after / before, 4) if before else 0.0,
            "checkpoints": per_problem,
        }

    (args.out.parent / f"{args.out.name}.strip_manifest.json").write_text(json.dumps(report, indent=2))
    (args.out.parent / f"{args.out.name}.strip.diff").write_text("".join(diffs))
    total_b = sum(p["words_before"] for p in report["problems"].values())
    total_a = sum(p["words_after"] for p in report["problems"].values())
    print(f"{'problem':30} {'before':>7} {'after':>7} removed")
    for name, p in report["problems"].items():
        print(f"{name:30} {p['words_before']:7} {p['words_after']:7} {p['fraction_removed'] * 100:6.1f}%")
    print(f"{'total':30} {total_b:7} {total_a:7} {(1 - total_a / total_b) * 100:6.1f}%")


if __name__ == "__main__":
    main()
