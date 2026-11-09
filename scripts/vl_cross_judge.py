"""Cross-family judging of finished checkpoint snapshots.

The shadow reviewer (Claude) is one judge family. This script puts the same
system prompt and the same request in front of other families and records an
approve or reject per snapshot, so the results table can report whether judges
agree (Cohen's kappa) and whether the arm ranking survives every judge. The
method follows vulnbench-cross-judge: verbatim prompts, resume-aware output,
a hard spending cap, and judge errors excluded from denominators.

    uv run python scripts/vl_cross_judge.py outputs/vl/a-plain/<model>/<ts> \\
        --judge gemini --max-usd 20

Judges (keep them current; anything older than about three months is stale):
  gemini        gemini-4-argon on Vertex (GOOGLE_APPLICATION_CREDENTIALS,
                ANTHROPIC_VERTEX_PROJECT_ID; region global)
  gemini-flash  gemini-3.8-flash on Vertex
  gpt     gpt-6.1-sol on Vertex Model Garden (OpenAI-compatible endpoint;
          VL_GPT_VERTEX_MODEL overrides the model ID)
  gpt-oss gpt-oss-120b on Vertex (open-weight; cheap enough for every checkpoint)

Writes ``cross_judge_<judge>.json`` next to each checkpoint snapshot.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import litellm

from slop_code import problem_catalog
from slop_code.agent_runner.review import REVIEW_SYSTEM_PROMPT
from slop_code.agent_runner.review import collect_workspace
from slop_code.agent_runner.review import render_review_request
from slop_code.agent_runner.review import specs_through
from slop_code.common import SNAPSHOT_DIR_NAME
from slop_code.common.llms import ModelCatalog
from slop_code.common.llms import TokenUsage
from slop_code.evaluation.config import ProblemConfig

JUDGES: dict[str, dict[str, str]] = {
    # Keep judges current (released in the last ~3 months). No catalog entry means
    # no price on file yet: the judgment records tokens and a null cost.
    "gemini": {"catalog": None, "litellm": "vertex_ai/gemini-4-argon"},
    "gemini-flash": {"catalog": None, "litellm": "vertex_ai/gemini-3.8-flash"},
    # Frontier GPT through Vertex Model Garden's OpenAI-compatible endpoint.
    # VL_GPT_VERTEX_MODEL overrides the model ID if Model Garden names it differently.
    "gpt": {
        "catalog": "gpt-6.1-sol",
        "litellm": "openai/" + os.environ.get("VL_GPT_VERTEX_MODEL", "openai/gpt-6.1-sol"),
    },
    # OpenAI's open-weight model (August 2025): out of date, kept only so old
    # results can be re-scored. Use "gpt" once GPT-6 is enabled on Vertex.
    "gpt-oss": {"catalog": "gpt-oss-120b", "litellm": "openai/openai/gpt-oss-120b-maas"},
}
_MAX_TOKENS = {"gpt-oss": 16_000}  # 131k context; leave room for the workspace
_token_lock = threading.Lock()
_vertex_creds: Any = None


def _vertex_token() -> str:
    """Short-lived token for Vertex's OpenAI-compatible endpoint, refreshed as needed."""
    global _vertex_creds  # noqa: PLW0603 - one credential object per process
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    with _token_lock:
        if _vertex_creds is None:
            _vertex_creds = service_account.Credentials.from_service_account_file(
                Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).expanduser(),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        if not _vertex_creds.valid:
            _vertex_creds.refresh(Request())
        return _vertex_creds.token

# The Claude reviewer reports through a tool; these judges return the same
# fields as one JSON object, so the instruction is restated in that form.
JSON_INSTRUCTION = """

Instead of a tool call, end your answer with one JSON object and nothing after it:
{"verdict": "approve" | "reject", "findings": [{"category": "correctness" | "spec" | "quality", "location": "...", "problem": "...", "evidence": "..."}]}"""


def _extract_json(text: str) -> dict[str, Any]:
    matches = re.findall(r"\{.*\}", text, flags=re.DOTALL)
    for candidate in reversed(matches):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if payload.get("verdict") in {"approve", "reject"}:
            return payload
    raise ValueError("no verdict JSON in judge response")


def _call_kwargs(judge: str) -> dict[str, Any]:
    if judge.startswith("gemini"):
        key_path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).expanduser()
        return {
            "vertex_project": os.environ["ANTHROPIC_VERTEX_PROJECT_ID"],
            "vertex_location": os.environ.get("CLOUD_ML_REGION", "global"),
            "vertex_credentials": key_path.read_text(),
        }
    project = os.environ["ANTHROPIC_VERTEX_PROJECT_ID"]
    return {
        "api_base": f"https://aiplatform.googleapis.com/v1/projects/{project}"
        "/locations/global/endpoints/openapi",
        "api_key": _vertex_token(),
    }


def judge_snapshot(judge: str, specs, snapshot: Path) -> dict[str, Any]:
    cfg = JUDGES[judge]
    model_def = ModelCatalog.get(cfg["catalog"]) if cfg["catalog"] else None
    workspace, truncated = collect_workspace(snapshot)
    record: dict[str, Any] = {
        "mode": "cross_judge",
        "judge": judge,
        "model": cfg["litellm"],
        "truncated_files": truncated,
    }
    try:
        response = litellm.completion(
            model=cfg["litellm"],
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT + JSON_INSTRUCTION},
                {"role": "user", "content": render_review_request(specs, workspace)},
            ],
            max_tokens=_MAX_TOKENS.get(judge, 32_000),
            timeout=900,
            **_call_kwargs(judge),
        )
        text = response.choices[0].message.content or ""
        usage = TokenUsage(
            input=response.usage.prompt_tokens or 0,
            output=response.usage.completion_tokens or 0,
        )
        record["usage"] = usage.model_dump()
        record["cost"] = (
            model_def.pricing.get_cost(usage) if model_def and model_def.pricing else None
        )
        payload = _extract_json(text)
        record["verdict"] = payload["verdict"]
        record["findings"] = payload.get("findings", [])
    except Exception as exc:  # noqa: BLE001 - a judge error is recorded, not fatal
        record["verdict"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"[:2000]
        record.setdefault("cost", 0.0)
    return record


def _jobs(run_dirs: list[Path], judge: str, problem_root: Path, *, last_only: bool):
    for run_dir in run_dirs:
        for problem_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
            config_path = problem_root / problem_dir.name
            if not config_path.exists():
                continue
            problem = ProblemConfig.from_yaml(config_path)
            names = [name for name, _ in problem.iterate_checkpoint_items()]
            for name in names[-1:] if last_only else names:
                checkpoint_dir = problem_dir / name
                snapshot = checkpoint_dir / SNAPSHOT_DIR_NAME
                out = checkpoint_dir / f"cross_judge_{judge}.json"
                if not snapshot.is_dir():
                    continue
                if out.exists() and json.loads(out.read_text()).get("verdict") != "error":
                    continue
                yield problem, name, snapshot, out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--judge", choices=sorted(JUDGES), required=True)
    parser.add_argument("--max-usd", type=float, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-calls", type=int, default=None, help="Cap for judges with no price")
    parser.add_argument(
        "--checkpoints",
        choices=["all", "last"],
        default="last",
        help="Judge every checkpoint, or only each problem's final one (default; "
        "about a fifth of the cost, and agreement does not need every checkpoint).",
    )
    args = parser.parse_args()

    litellm.suppress_debug_info = True
    root = problem_catalog.get_problem_root(
        problem_catalog.get_scbench_home(), bootstrap=False
    )
    jobs = list(
        _jobs(args.run_dirs, args.judge, root, last_only=args.checkpoints == "last")
    )
    print(f"{len(jobs)} snapshots to judge with {args.judge}, cap ${args.max_usd:.2f}")
    spent = 0.0
    calls = 0
    lock = threading.Lock()
    if JUDGES[args.judge]["catalog"] is None:
        print(f"{args.judge} has no price on file: --max-usd cannot bind, --max-calls does")

    def run(job) -> None:
        nonlocal spent, calls
        problem, name, snapshot, out = job
        with lock:
            if spent >= args.max_usd or (args.max_calls and calls >= args.max_calls):
                return
        record = judge_snapshot(args.judge, specs_through(problem, name), snapshot)
        out.write_text(json.dumps(record, indent=2))
        with lock:
            spent += record.get("cost") or 0.0
            calls += 1
            total = spent
        print(f"{snapshot.parent.parent.name}/{name}: {record['verdict']} (${total:.2f})")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(run, jobs))
    print(f"spent ${spent:.2f}{' (cap reached)' if spent >= args.max_usd else ''}")


if __name__ == "__main__":
    main()
