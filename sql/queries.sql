-- name: cost_by_service
SELECT ProviderName, ServiceName, ROUND(SUM(EffectiveCost), 2) AS cost
FROM focus GROUP BY 1, 2 ORDER BY cost DESC;

-- name: untagged_spend
-- Spend with no owner tag. json_extract is SQLite and BigQuery has JSON_VALUE, Azure SQL has JSON_VALUE.
SELECT ProviderName, ROUND(SUM(EffectiveCost), 2) AS cost,
       ROUND(100.0 * SUM(EffectiveCost) / (SELECT SUM(EffectiveCost) FROM focus), 1) AS pct
FROM focus WHERE json_extract(Tags, '$.owner') IS NULL GROUP BY 1;

-- name: effective_savings_rate
-- Share of list price avoided by discounts and commitments.
SELECT ProviderName, ROUND(100.0 * (1 - SUM(EffectiveCost) / SUM(ListCost)), 1) AS esr_pct
FROM focus GROUP BY 1;

-- name: commitment_coverage
-- Share of spend that ran under a commitment.
SELECT ProviderName,
       ROUND(100.0 * SUM(CASE WHEN CommitmentDiscountStatus = 'Used' THEN ListCost END) / SUM(ListCost), 1) AS coverage_pct
FROM focus GROUP BY 1;

-- name: daily_spike
-- Days more than 2 standard deviations over the mean for their service.
WITH daily AS (
  SELECT ServiceName, substr(ChargePeriodStart, 1, 10) AS day, SUM(EffectiveCost) AS cost
  FROM focus GROUP BY 1, 2
), stats AS (
  SELECT ServiceName, AVG(cost) AS mean,
         SQRT(AVG(cost * cost) - AVG(cost) * AVG(cost)) AS sd
  FROM daily GROUP BY 1
)
SELECT d.ServiceName, d.day, ROUND(d.cost, 2) AS cost
FROM daily d JOIN stats s USING (ServiceName)
WHERE s.sd > 0 AND d.cost > s.mean + 2 * s.sd ORDER BY d.day;
