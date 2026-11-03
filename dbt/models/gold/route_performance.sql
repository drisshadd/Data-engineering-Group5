select origin_airport,destination_airport,
 count(*) as total_flights, count(*) as flights_operated,
 sum(booking_count) as total_bookings, sum(bookings_sold) as bookings_sold,
 sum(revenue_gbp)::number(18,2) as total_revenue_gbp,
 sum(net_revenue_gbp)::number(18,2) as net_revenue_gbp,
 round(avg(delay_min),2) as avg_delay_min,
 round(100.0*avg(is_on_time),2) as on_time_pct,
 round(100.0*sum(booking_count)/nullif(sum(seats),0),2) as booked_load_factor_pct,
 round(avg(load_factor_pct),2) as avg_load_factor_pct
from {{ ref('flight_performance') }} group by 1,2
