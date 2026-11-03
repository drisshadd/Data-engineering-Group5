-- Member 2 baseline verification: same source of truth used by dashboard and handoff.
-- Run after the two-batch reference dataset is loaded and dbt models are built.
-- Expected: 866, 8123, 8034, 89, 79, 977, 1788710.02, 436, 853, 61, 419540.
SELECT
    (SELECT COUNT(*) FROM SKYHOP.SILVER.SILVER_FLIGHTS) AS silver_flights,
    (SELECT COUNT(*) FROM SKYHOP.SILVER.SILVER_BOOKINGS) AS silver_bookings,
    (SELECT SUM(bookings_sold) FROM SKYHOP.GOLD.FLIGHT_PERFORMANCE) AS bookings_sold,
    (SELECT SUM(bookings_refunded) FROM SKYHOP.GOLD.FLIGHT_PERFORMANCE) AS refunds,
    (SELECT COUNT(*) FROM SKYHOP.QUARANTINE.FLIGHTS) AS quarantined_flights,
    (SELECT COUNT(*) FROM SKYHOP.QUARANTINE.BOOKINGS) AS quarantined_bookings,
    (SELECT ROUND(SUM(net_revenue_gbp), 2) FROM SKYHOP.GOLD.FLIGHT_PERFORMANCE) AS net_revenue_gbp,
    (SELECT COUNT(*) FROM SKYHOP.GOLD.DAILY_OTP) AS daily_otp_rows,
    (SELECT SUM(flights_with_delay) FROM SKYHOP.GOLD.DAILY_OTP) AS flights_with_delay,
    (SELECT SUM(on_time_flights) FROM SKYHOP.GOLD.DAILY_OTP) AS on_time_flights,
    (SELECT SUM(uk261_exposure_gbp) FROM SKYHOP.GOLD.FLIGHT_PERFORMANCE) AS uk261_exposure_gbp;
