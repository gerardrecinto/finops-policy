#!/usr/bin/env bash
# Price a Terraform directory with Infracost, then check the diff and the plan against the OPA policy.
# Usage: check-plan.sh TF_DIR BASELINE_INFRACOST_JSON    (needs terraform, infracost, jq, opa on PATH)
set -euo pipefail
dir="$1" baseline="$2"
work="$(mktemp -d)"

terraform -chdir="$dir" plan -out="$work/plan.bin" >/dev/null
terraform -chdir="$dir" show -json "$work/plan.bin" >"$work/plan.json"
infracost diff --path "$dir" --compare-to "$baseline" --format json --out-file "$work/cost.json"

# Merge the plan and the cost diff so one policy sees both.
jq -s '.[0] + {diffTotalMonthlyCost: .[1].diffTotalMonthlyCost}' "$work/plan.json" "$work/cost.json" >"$work/input.json"
opa eval -d "$(dirname "$0")/../policy" -i "$work/input.json" --fail-defined "data.cost.deny[_]"
