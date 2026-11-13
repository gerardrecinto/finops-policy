import re
import sqlite3
from pathlib import Path

from finops import commitment, focus


def queries():
    text = Path(__file__).parent.parent.joinpath("sql/queries.sql").read_text()
    return {m[0]: m[1] for m in re.findall(r"-- name: (\w+)\n(.*?;)", text, re.S)}


AWS = {"bill/PayerAccountId": "1", "lineItem/UsageAccountId": "2", "lineItem/UsageStartDate": "2026-11-01T00:00:00Z",
       "product/ProductName": "Amazon EC2", "product/region": "us-east-1", "pricing/publicOnDemandCost": "10",
       "lineItem/UnblendedCost": "10", "savingsPlan/SavingsPlanEffectiveCost": "6",
       "savingsPlan/SavingsPlanARN": "arn:sp", "resourceTags": {"owner": "data"}}
AZ = {"billingAccountId": "b", "subscriptionId": "s", "date": "2026-11-01", "meterCategory": "Virtual Machines",
      "paygCostInBillingCurrency": "20", "costInBillingCurrency": "20", "billingCurrency": "USD", "tags": {}}
GCP = {"billing_account_id": "g", "project": {"id": "p"}, "usage_start_time": "2026-11-01T00:00:00Z",
       "service": {"description": "Compute Engine"}, "cost": 30, "currency": "USD",
       "credits": [{"type": "COMMITTED_USAGE_DISCOUNT", "amount": -9}], "labels": [{"key": "owner", "value": "ml"}]}


def db():
    c = sqlite3.connect(":memory:")
    focus.load(c, [focus.from_aws(AWS), focus.from_azure(AZ), focus.from_gcp(GCP)])
    return c


def test_covered_aws_line_bills_zero_but_costs_effective():
    r = focus.from_aws(AWS)
    assert (r["BilledCost"], r["EffectiveCost"], r["CommitmentDiscountStatus"]) == (0.0, 6.0, "Used")


def test_gcp_credit_reduces_cost():
    assert focus.from_gcp(GCP)["EffectiveCost"] == 21


def test_untagged_spend_is_the_azure_row_only():
    rows = db().execute(queries()["untagged_spend"]).fetchall()
    assert rows == [("Microsoft", 20.0, 42.6)]  # 20 of 47 total (6 + 20 + 21)


def test_effective_savings_rate():
    rows = dict(db().execute(queries()["effective_savings_rate"]).fetchall())
    assert rows == {"AWS": 40.0, "Microsoft": 0.0, "Google Cloud": 30.0}


def test_commitment_coverage():
    rows = dict(db().execute(queries()["commitment_coverage"]).fetchall())
    assert rows["AWS"] == 100.0 and rows["Microsoft"] is None


def test_spike_query_flags_the_outlier_day():
    c = sqlite3.connect(":memory:")
    base = focus.from_azure(AZ)
    rows = [dict(base, ChargePeriodStart=f"2026-11-{d:02d}", EffectiveCost=10.0) for d in range(1, 11)]
    rows.append(dict(base, ChargePeriodStart="2026-11-11", EffectiveCost=100.0))
    focus.load(c, rows)
    assert c.execute(queries()["daily_spike"]).fetchall() == [("Virtual Machines", "2026-11-11", 100.0)]


def test_commitment_at_the_floor_saves_and_stays_fully_used():
    hourly = [100.0] * 20 + [150.0] * 80
    commit, r = commitment.recommend(hourly, discount=0.3, floor_percentile=0.1)
    assert r["utilization"] == 1.0 and r["saving"] > 0


def test_overcommitting_wastes_money():
    hourly = [100.0] * 100
    assert commitment.evaluate(hourly, 100.0, 0.3)["saving"] < commitment.evaluate(hourly, 70.0, 0.3)["saving"]
    assert commitment.evaluate(hourly, 100.0, 0.3)["utilization"] < 1
