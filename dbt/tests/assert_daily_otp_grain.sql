-- One row per London business day and origin airport; catches duplicate/missing aggregates.
SELECT business_date, origin_airport, COUNT(*) AS duplicate_rows
FROM {{ ref('daily_otp') }}
GROUP BY 1,2
HAVING COUNT(*) > 1
