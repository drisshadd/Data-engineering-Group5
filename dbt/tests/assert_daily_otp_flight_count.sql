-- Aggregate daily x airport row count must equal the flight-grain count.
SELECT 1 AS error
WHERE (SELECT COALESCE(SUM(flights_operated), 0) FROM {{ ref('daily_otp') }})
  <> (SELECT COUNT(*) FROM {{ ref('flight_performance') }})
