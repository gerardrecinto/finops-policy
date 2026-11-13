"""Size a savings plan or committed use discount from hourly on-demand spend."""


def percentile(values, p):
    s = sorted(values)
    k = (len(s) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def evaluate(hourly_od, commit_per_hour, discount):
    """Cost of covering `commit_per_hour` of on-demand spend with a commitment at `discount` off.

    The commitment bills every hour whether used or not. Usage above it stays on-demand.
    Returns total cost with the commitment, the saving against all on-demand, and utilization.
    """
    committed_price = commit_per_hour  # what the commitment costs per hour
    covers_od = commit_per_hour / (1 - discount)  # on-demand spend it can absorb per hour
    total = 0.0
    used = 0.0
    for od in hourly_od:
        absorbed = min(od, covers_od)
        total += committed_price + (od - absorbed)
        used += absorbed
    on_demand = sum(hourly_od)
    return {
        "cost": round(total, 2),
        "saving": round(on_demand - total, 2),
        "utilization": round(used / (covers_od * len(hourly_od)), 3),
    }


def recommend(hourly_od, discount, floor_percentile=0.1):
    """Commit to the spend level you almost never go below, not the average."""
    floor = percentile(hourly_od, floor_percentile)
    commit = round(floor * (1 - discount), 4)
    return commit, evaluate(hourly_od, commit, discount)
