-- Dashboard-compatible grain: London business date x origin airport.
SELECT
    f.business_date,
    f.origin_airport,
    MAX(a.city) AS origin_city,
    COUNT(*) AS flights_operated,
    COUNT(f.delay_min) AS flights_with_delay,
    COALESCE(COUNT_IF(f.delay_min <= 15), 0) AS on_time_flights,
    ROUND(
        100.0 * COUNT_IF(f.delay_min <= 15)
        / NULLIF(COUNT(f.delay_min), 0), 2
    ) AS otp15_pct,
    ROUND(AVG(f.delay_min), 2) AS avg_delay_min,
    COALESCE(COUNT_IF(f.delay_min >= 180), 0) AS flights_delayed_3h_plus,

    -- Additional columns retained for reconciliation.
    COUNT(*) AS total_flights,
    ROUND(
        100.0 * COUNT_IF(f.delay_min <= 15)
        / NULLIF(COUNT(f.delay_min), 0), 2
    ) AS otp_pct,
    SUM(f.booking_count) AS total_bookings,
    SUM(f.revenue_gbp)::NUMBER(18,2) AS total_revenue_gbp
FROM {{ ref('flight_performance') }} f
LEFT JOIN {{ ref('silver_airports') }} a
    ON f.origin_airport = a.airport_code
GROUP BY f.business_date, f.origin_airport
