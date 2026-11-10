#!/usr/bin/env bash
# One seed of the verification-layers instrument: all four arms in parallel,
# then shadow review on every arm, then the results table.
#
#   scripts/vl_seed.sh [workers_per_arm]      (default 2)
#
# Needs GOOGLE_APPLICATION_CREDENTIALS (Vertex-only key), ANTHROPIC_VERTEX_PROJECT_ID
# and DOCKER_CONFIG; see README.md. Writes outputs/vl/seed-<stamp>.md.
#
# Optional:
#   VL_STRIPPED_ARMS="a-plain c-review"  also run these arms on specs with the worked
#       I/O examples removed (scripts/vl_strip_examples.py; seed 2's exploratory arms,
#       labelled As and Cs in the table). Unset: the four arms only, as in seed 1.
#   VL_MAX_USD=300  stop every arm (and the slop-code containers) once the seed's
#       re-priced spend (scripts/vl_spend.py) passes this, and skip later steps.
#   VL_STAMP=...    use this stamp instead of the current time.
#   VL_RUN_ARMS="b-conveyor a-plain-stripped"  with VL_STAMP: run the agent step for
#       these arms only (launched 90 s apart, so they don't race to build the image),
#       then shadow review, judge and table over every arm under the stamp. Shadow
#       review and the judge skip checkpoints they already did. For re-running arms
#       that failed to start; record any use under the preregistration's Deviations.
set -euo pipefail
cd "$(dirname "$0")/.."

# The installed slop-code-bench has no configs of its own; point it at ours.
uv run python scripts/vl_link_configs.py >/dev/null

: "${GOOGLE_APPLICATION_CREDENTIALS:?set to the Vertex-only service-account key}"
: "${ANTHROPIC_VERTEX_PROJECT_ID:?set to the Vertex project}"
export CLOUD_ML_REGION="${CLOUD_ML_REGION:-global}"

workers="${1:-2}"
model=sonnet-5.5
stamp="${VL_STAMP:-$(date +%Y%m%dT%H%M)}"
arms=(a-plain b-conveyor c-review d-tests)
logs="outputs/vl/seed-$stamp-logs"
mkdir -p "$logs"

# Stripped-spec arms read their specs from a transformed copy of the catalog.
stripped_root="$PWD/outputs/vl/problems-stripped-$stamp"
if [[ -n "${VL_STRIPPED_ARMS:-}" ]]; then
  uv run python scripts/vl_strip_examples.py configs/runs/vl-a-plain.yaml \
    --out "$stripped_root" --force >"$logs/strip.log"
  for base in $VL_STRIPPED_ARMS; do
    [[ -f "configs/runs/vl-$base-stripped.yaml" ]] || { echo "no config for $base-stripped" >&2; exit 2; }
    arms+=("$base-stripped")
  done
fi
problems_env() {  # env assignment for an arm: the stripped catalog for *-stripped arms
  if [[ "$1" == *-stripped ]]; then echo "SCBENCH_PROBLEMS_PATH=$stripped_root"; else echo "VL_ARM=$1"; fi
}
label_of() {  # a-plain -> A, c-review-stripped -> Cs
  local l
  l="$(printf '%s' "${1:0:1}" | tr '[:lower:]' '[:upper:]')"
  [[ "$1" == *-stripped ]] && l="${l}s"
  printf '%s' "$l"
}
over_budget() {
  [[ -n "${VL_MAX_USD:-}" ]] || return 1
  ! uv run python scripts/vl_spend.py "$stamp" --model "$model" --max-usd "$VL_MAX_USD" \
    >"$logs/spend.txt" 2>&1
}
kill_tree() {
  local child
  for child in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$child"; done
  kill -TERM "$1" 2>/dev/null || true
}
stop_everything() {
  echo "spend passed \$${VL_MAX_USD}; stopping all arms" | tee -a "$logs/spend.txt" >&2
  for pid in "${pids[@]}"; do kill_tree "$pid"; done
  # Agents run through `docker exec` inside slop-code containers, so killing the
  # runner leaves them going. Stop those containers too, and only those.
  local ids
  ids="$(docker ps -q --filter label=io.slop-code.base-image-hash 2>/dev/null || true)"
  # shellcheck disable=SC2086  # one container id per word
  [[ -z "$ids" ]] || docker stop -t 5 $ids >/dev/null || true
}

run_arms=("${arms[@]}")
if [[ -n "${VL_RUN_ARMS:-}" ]]; then
  [[ -n "${VL_STAMP:-}" ]] || { echo "VL_RUN_ARMS needs VL_STAMP" >&2; exit 2; }
  read -ra run_arms <<<"$VL_RUN_ARMS"
fi
pids=()
for arm in "${run_arms[@]}"; do
  [[ ${#pids[@]} -gt 0 && -n "${VL_RUN_ARMS:-}" ]] && sleep 90
  env "$(problems_env "$arm")" uv run slop-code run -c "configs/runs/vl-$arm.yaml" \
    -n "$workers" --no-live-progress "save_template=vl/$arm/\${model.name}_\${thinking}/$stamp" \
    >>"$logs/$arm.log" 2>&1 &
  pids+=("$!")
done

budget_stop=0
if [[ -n "${VL_MAX_USD:-}" ]]; then
  while :; do
    alive=0
    for pid in "${pids[@]}"; do kill -0 "$pid" 2>/dev/null && alive=1; done
    (( alive )) || break
    if over_budget; then stop_everything; budget_stop=1; break; fi
    sleep 60
  done
fi

status=0
for i in "${!run_arms[@]}"; do
  if ! wait "${pids[$i]}"; then
    echo "arm ${run_arms[$i]} exited non-zero; see $logs/${run_arms[$i]}.log" >&2
    status=1
  fi
done
if (( budget_stop )); then
  echo "stopped on budget; partial run dirs under outputs/vl/*/${model}_medium/$stamp" >&2
  exit 3
fi

table_args=()
for arm in "${arms[@]}"; do
  run_dir="outputs/vl/$arm/${model}_medium/$stamp"
  [[ -d "$run_dir" ]] || continue
  if over_budget; then echo "over budget before shadow review of $arm" >&2; exit 3; fi
  env "$(problems_env "$arm")" uv run python scripts/vl_shadow_review.py "$run_dir" \
    --model "$model" --provider vertex --effort medium >"$logs/$arm-shadow.log" 2>&1 || status=1
  table_args+=("$(label_of "$arm")=$run_dir")
done

# Cross-family judge (Gemini 3.8 Flash) on each problem's final checkpoint. One judge from
# another family is enough to show the reviewer's verdict is not Claude-specific; Argon
# was dropped on 2026-11-09 for cost. Add a second family with:
#   scripts/vl_cross_judge.py ... --judge gpt-oss --checkpoints all --max-usd 5
# The judge reads the full specs, so it covers the four unchanged arms only.
run_dirs=()
for arm in a-plain b-conveyor c-review d-tests; do
  [[ -d "outputs/vl/$arm/${model}_medium/$stamp" ]] && run_dirs+=("outputs/vl/$arm/${model}_medium/$stamp")
done
if over_budget; then echo "over budget before the cross-family judge" >&2; exit 3; fi
uv run python scripts/vl_cross_judge.py "${run_dirs[@]}" --judge gemini-flash --max-calls 120 \
  --max-usd 10 --workers 4 >"$logs/judge-gemini-flash.log" 2>&1 || status=1

uv run python scripts/vl_table.py "${table_args[@]}" --price-model "$model" \
  --no-tests-quality D --csv "outputs/vl/seed-$stamp.csv" \
  | tee "outputs/vl/seed-$stamp.md"
exit "$status"
