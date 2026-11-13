# finops-policy-lab

Normalize cloud bills to the FOCUS column set, query them with SQL, size commitments, and stop expensive changes before apply.

| Piece | Files |
|---|---|
| Billing data engineering | `finops/focus.py` maps AWS CUR, Azure, and GCP export rows to FOCUS columns (`BilledCost`, `EffectiveCost`, `ListCost`, `CommitmentDiscountId`, `Tags`) |
| SQL | `sql/queries.sql`: cost by service, untagged spend, effective savings rate, commitment coverage, daily spike detection |
| Commitments | `finops/commitment.py` sizes a savings plan or committed use discount from hourly spend: commit to a low percentile, report utilization and saving, show what over-committing costs |
| OPA | `policy/cost.rego` and tests: required tags, expensive instance families need an exception, block a plan that raises monthly cost over a limit (Infracost output) |
| Sentinel | `policy/cost.sentinel`: the same tag rule for HCP Terraform |
| Infracost | `infracost.yml`, `scripts/check-plan.sh`: price the plan, then run the OPA policy on plan and cost together |
| Azure and GCP budgets | `terraform/main.tf`: monthly budgets with actual and forecast alerts |

```bash
python -m pytest -q tests
opa test policy -v
```

## Verified
- 8 pytest tests pass. They load AWS, Azure, and GCP rows into SQLite and run every query.
- 4 OPA tests pass (opa 1.22). `shellcheck` and `terraform fmt` are clean.

## Not verified
- The Sentinel policy was not run (no Sentinel CLI). The Infracost step and `check-plan.sh` were not run (no Infracost CLI or cloud credentials).
- The SQL runs on SQLite. `json_extract` and the `SQRT` call need small changes on BigQuery and Azure SQL (`JSON_VALUE`, `SQRT` is available on both).
- The provider rows are shaped from the documented export fields, not from a real export file. Real exports have more columns, and FOCUS 1.x has more required columns than this subset.
- `terraform validate` was not run (the provider plugin did not start in time on this machine). The budgets were not applied.
- The commitment model ignores term length, upfront payment, and regional or instance-family limits.
