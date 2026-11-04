-- Complete live dashboard column contract: dashboard/app.py and dashboard/GOLD_CONTRACT.md.
-- This test returns a row for any missing column. Run after dbt has created both Gold models.
WITH required(table_name, column_name) AS (
    SELECT column1, column2 FROM VALUES
    ('DAILY_OTP','BUSINESS_DATE'),
    ('DAILY_OTP','ORIGIN_AIRPORT'),
    ('DAILY_OTP','ORIGIN_CITY'),
    ('DAILY_OTP','FLIGHTS_OPERATED'),
    ('DAILY_OTP','FLIGHTS_WITH_DELAY'),
    ('DAILY_OTP','ON_TIME_FLIGHTS'),
    ('DAILY_OTP','OTP15_PCT'),
    ('DAILY_OTP','AVG_DELAY_MIN'),
    ('DAILY_OTP','FLIGHTS_DELAYED_3H_PLUS'),
    ('FLIGHT_PERFORMANCE','FLIGHT_ID'),
    ('FLIGHT_PERFORMANCE','FLIGHT_NUMBER'),
    ('FLIGHT_PERFORMANCE','BUSINESS_DATE'),
    ('FLIGHT_PERFORMANCE','ORIGIN_AIRPORT'),
    ('FLIGHT_PERFORMANCE','DESTINATION_AIRPORT'),
    ('FLIGHT_PERFORMANCE','SEATS'),
    ('FLIGHT_PERFORMANCE','DELAY_MIN'),
    ('FLIGHT_PERFORMANCE','BOOKINGS_SOLD'),
    ('FLIGHT_PERFORMANCE','BOOKINGS_REFUNDED'),
    ('FLIGHT_PERFORMANCE','NET_REVENUE_GBP'),
    ('FLIGHT_PERFORMANCE','REFUNDED_GBP'),
    ('FLIGHT_PERFORMANCE','LOAD_FACTOR_PCT'),
    ('FLIGHT_PERFORMANCE','UK261_EXPOSURE_GBP')
)
SELECT r.table_name, r.column_name AS missing_column
FROM required r
LEFT JOIN SKYHOP.INFORMATION_SCHEMA.COLUMNS c
  ON c.table_catalog = 'SKYHOP'
 AND c.table_schema = 'GOLD'
 AND c.table_name = r.table_name
 AND c.column_name = r.column_name
WHERE c.column_name IS NULL
