-- One row per London business date, matching the validated Snowflake dashboard contract.
select business_date,
 count(*) as total_flights,
 sum(is_on_time) as on_time_flights,
 round(100.0*sum(is_on_time)/nullif(count(*),0),2) as otp_pct,
 round(avg(delay_min),2) as avg_delay_min,
 sum(booking_count) as total_bookings,
 sum(revenue_gbp)::number(18,2) as total_revenue_gbp
from {{ ref('flight_performance') }}
group by business_date
