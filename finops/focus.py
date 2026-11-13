"""Map provider billing rows to a subset of the FOCUS columns, so one SQL query works on all clouds.

Column names follow the FinOps Open Cost and Usage Specification. Only the columns the queries
in sql/ use are produced. Input rows are plain dicts shaped like each provider's export.
"""
import json

FOCUS_COLUMNS = [
    "ProviderName", "BillingAccountId", "SubAccountId", "ChargePeriodStart", "ServiceName",
    "RegionName", "ChargeCategory", "ListCost", "BilledCost", "EffectiveCost", "BillingCurrency",
    "CommitmentDiscountId", "CommitmentDiscountStatus", "Tags",
]


def from_aws(r):
    """AWS CUR line. A savings plan covered line has cost 0 and a savings_plan effective cost."""
    covered = bool(r.get("savingsPlan/SavingsPlanARN"))
    return {
        "ProviderName": "AWS",
        "BillingAccountId": r["bill/PayerAccountId"],
        "SubAccountId": r["lineItem/UsageAccountId"],
        "ChargePeriodStart": r["lineItem/UsageStartDate"],
        "ServiceName": r["product/ProductName"],
        "RegionName": r.get("product/region"),
        "ChargeCategory": "Usage",
        "ListCost": float(r["pricing/publicOnDemandCost"]),
        "BilledCost": 0.0 if covered else float(r["lineItem/UnblendedCost"]),
        "EffectiveCost": float(r["savingsPlan/SavingsPlanEffectiveCost"] if covered else r["lineItem/UnblendedCost"]),
        "BillingCurrency": "USD",
        "CommitmentDiscountId": r.get("savingsPlan/SavingsPlanARN"),
        "CommitmentDiscountStatus": "Used" if covered else None,
        "Tags": json.dumps(r.get("resourceTags", {}), sort_keys=True),
    }


def from_azure(r):
    reserved = r.get("pricingModel") == "Reservation"
    return {
        "ProviderName": "Microsoft",
        "BillingAccountId": r["billingAccountId"],
        "SubAccountId": r["subscriptionId"],
        "ChargePeriodStart": r["date"],
        "ServiceName": r["meterCategory"],
        "RegionName": r.get("resourceLocation"),
        "ChargeCategory": "Usage",
        "ListCost": float(r["paygCostInBillingCurrency"]),
        "BilledCost": float(r["costInBillingCurrency"]),
        "EffectiveCost": float(r["costInBillingCurrency"]),
        "BillingCurrency": r["billingCurrency"],
        "CommitmentDiscountId": r.get("reservationId"),
        "CommitmentDiscountStatus": "Used" if reserved else None,
        "Tags": json.dumps(r.get("tags", {}), sort_keys=True),
    }


def from_gcp(r):
    """GCP billing export row. Committed use discounts show as negative credits."""
    credit = sum(c["amount"] for c in r.get("credits", []))
    cud = [c for c in r.get("credits", []) if c["type"] == "COMMITTED_USAGE_DISCOUNT"]
    return {
        "ProviderName": "Google Cloud",
        "BillingAccountId": r["billing_account_id"],
        "SubAccountId": r["project"]["id"],
        "ChargePeriodStart": r["usage_start_time"],
        "ServiceName": r["service"]["description"],
        "RegionName": r.get("location", {}).get("region"),
        "ChargeCategory": "Usage",
        "ListCost": float(r["cost"]),
        "BilledCost": float(r["cost"]) + credit,
        "EffectiveCost": float(r["cost"]) + credit,
        "BillingCurrency": r["currency"],
        "CommitmentDiscountId": "cud" if cud else None,
        "CommitmentDiscountStatus": "Used" if cud else None,
        "Tags": json.dumps({lab["key"]: lab["value"] for lab in r.get("labels", [])}, sort_keys=True),
    }


def load(conn, rows):
    cols = ",".join(FOCUS_COLUMNS)
    marks = ",".join("?" for _ in FOCUS_COLUMNS)
    conn.execute(f"CREATE TABLE IF NOT EXISTS focus ({cols})")
    conn.executemany(f"INSERT INTO focus ({cols}) VALUES ({marks})", [[r[c] for c in FOCUS_COLUMNS] for r in rows])
