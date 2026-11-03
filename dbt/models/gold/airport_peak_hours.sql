-- Scheduled departures, not measured airport congestion.
select origin_airport as airport_code,business_date,
 hour(convert_timezone('Europe/London',scheduled_departure_utc)) as departure_hour_uk,
 count(*) as scheduled_departures,
 sum(booking_count) as booked_passengers_proxy,
 round(avg(delay_min),2) as avg_delay_min,
 count_if(delay_min>15) as delayed_departures,
 round(100.0*avg(is_on_time),2) as on_time_pct
from {{ ref('flight_performance') }}
group by origin_airport,business_date,hour(convert_timezone('Europe/London',scheduled_departure_utc))
