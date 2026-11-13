package cost_test

import data.cost
import rego.v1

plan(type, itype, tags) := {"resource_changes": [{"address": "aws_instance.a", "type": "aws_instance",
	"change": {"actions": ["create"], "after": {"instance_type": itype, "tags": tags}}}]}

ok_tags := {"owner": "data", "cost-center": "42"}

test_tagged_small_instance_passes if {
	count(cost.deny) == 0 with input as plan("aws_instance", "m6i.large", ok_tags)
}

test_missing_tag_denied if {
	count(cost.deny) == 1 with input as plan("aws_instance", "m6i.large", {"owner": "data"})
}

test_expensive_family_needs_exception if {
	count(cost.deny) == 1 with input as plan("aws_instance", "p5.48xlarge", ok_tags)
	count(cost.deny) == 0 with input as plan("aws_instance", "p5.48xlarge", object.union(ok_tags, {"cost-exception": "CHG1"}))
}

test_infracost_delta_over_limit_denied if {
	count(cost.deny) == 1 with input as {"diffTotalMonthlyCost": "750.25"}
	count(cost.deny) == 0 with input as {"diffTotalMonthlyCost": "120"}
}
