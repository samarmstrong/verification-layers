#!/usr/bin/env bash
# One seed of the verification-layers instrument: all four arms in parallel,
# then shadow review on every arm, then the results table.
#
#   scripts/vl_seed.sh [workers_per_arm]      (default 2)
#
# Needs GOOGLE_APPLICATION_CREDENTIALS (Vertex-only key), ANTHROPIC_VERTEX_PROJECT_ID
# and DOCKER_CONFIG; see README.md. Writes outputs/vl/seed-<stamp>.md.
set -euo pipefail
cd "$(dirname "$0")/.."

# The installed slop-code-bench has no configs of its own; point it at ours.
uv run python scripts/vl_link_configs.py >/dev/null

: "${GOOGLE_APPLICATION_CREDENTIALS:?set to the Vertex-only service-account key}"
: "${ANTHROPIC_VERTEX_PROJECT_ID:?set to the Vertex project}"
export CLOUD_ML_REGION="${CLOUD_ML_REGION:-global}"

workers="${1:-2}"
model=sonnet-5.5
stamp="$(date +%Y%m%dT%H%M)"
arms=(a-plain b-conveyor c-review d-tests)
logs="outputs/vl/seed-$stamp-logs"
mkdir -p "$logs"

pids=()
for arm in "${arms[@]}"; do
  uv run slop-code run -c "configs/runs/vl-$arm.yaml" -n "$workers" --no-live-progress \
    "save_template=vl/$arm/\${model.name}_\${thinking}/$stamp" \
    >"$logs/$arm.log" 2>&1 &
  pids+=("$!")
done
status=0
for i in "${!arms[@]}"; do
  if ! wait "${pids[$i]}"; then
    echo "arm ${arms[$i]} exited non-zero; see $logs/${arms[$i]}.log" >&2
    status=1
  fi
done

table_args=()
for arm in "${arms[@]}"; do
  run_dir="outputs/vl/$arm/${model}_medium/$stamp"
  [[ -d "$run_dir" ]] || continue
  uv run python scripts/vl_shadow_review.py "$run_dir" --model "$model" \
    --provider vertex --effort medium >"$logs/$arm-shadow.log" 2>&1 || status=1
  label="$(printf '%s' "${arm:0:1}" | tr '[:lower:]' '[:upper:]')"
  table_args+=("$label=$run_dir")
done

# Cross-family judge (Gemini 4 Argon) on each problem's final checkpoint.
run_dirs=()
for arm in "${arms[@]}"; do
  [[ -d "outputs/vl/$arm/${model}_medium/$stamp" ]] && run_dirs+=("outputs/vl/$arm/${model}_medium/$stamp")
done
uv run python scripts/vl_cross_judge.py "${run_dirs[@]}" --judge gemini --max-calls 120 \
  --max-usd 35 --workers 4 >"$logs/judge-gemini.log" 2>&1 || status=1

uv run python scripts/vl_table.py "${table_args[@]}" --price-model "$model" \
  --no-tests-quality D --csv "outputs/vl/seed-$stamp.csv" \
  | tee "outputs/vl/seed-$stamp.md"
exit "$status"
