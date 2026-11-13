# Checks a Terraform plan (terraform show -json) before apply. Run: opa eval -d policy -i plan.json "data.cost.deny"
package cost

import rego.v1

required_tags := {"owner", "cost-center"}

deny contains msg if {
	some rc in input.resource_changes
	rc.change.actions[_] in {"create", "update"}
	startswith(rc.type, "aws_instance")
	missing := required_tags - {t | rc.change.after.tags[t]}
	count(missing) > 0
	msg := sprintf("%s is missing tags: %v", [rc.address, sort(missing)])
}

# Instance families that need an approved exception.
expensive := {"p4d", "p5", "x2", "u-"}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_instance"
	rc.change.actions[_] == "create"
	some prefix in expensive
	startswith(rc.change.after.instance_type, prefix)
	not rc.change.after.tags["cost-exception"]
	msg := sprintf("%s uses %s without a cost-exception tag", [rc.address, rc.change.after.instance_type])
}

# Infracost JSON: block a change that adds more than the budget per month.
max_monthly_increase := 500

deny contains msg if {
	delta := to_number(input.diffTotalMonthlyCost)
	delta > max_monthly_increase
	msg := sprintf("monthly cost rises by %v, limit is %v", [delta, max_monthly_increase])
}
