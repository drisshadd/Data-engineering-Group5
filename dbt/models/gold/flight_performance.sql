-- One row per valid flight. Legacy dashboard columns and dbt analytical columns coexist.
with bookings as (
 select flight_id, count(*) as booking_count,
 count_if(not is_refund) as bookings_sold,
 count_if(is_refund) as bookings_refunded,
 sum(iff(not is_refund,fare_gbp,0)) as net_revenue_gbp,
 sum(iff(is_refund,fare_gbp,0)) as refunded_gbp
 from {{ ref('silver_bookings') }} group by flight_id
)
select f.flight_id,f.flight_number,f.origin_airport,f.destination_airport,
 f.scheduled_departure_utc,f.business_date,f.delay_min,f.seats,
 coalesce(b.booking_count,0) as booking_count,
 coalesce(b.bookings_sold,0) as bookings_sold,
 coalesce(b.bookings_refunded,0) as bookings_refunded,
 coalesce(b.net_revenue_gbp,0)::number(18,2) as revenue_gbp,
 coalesce(b.net_revenue_gbp,0)::number(18,2) as net_revenue_gbp,
 coalesce(b.refunded_gbp,0)::number(18,2) as refunded_gbp,
 iff(f.delay_min<=15,1,0) as is_on_time,
 round(100.0*coalesce(b.bookings_sold,0)/nullif(f.seats,0),2) as load_factor_pct,
 iff(f.delay_min>=180,220*coalesce(b.bookings_sold,0),0) as uk261_exposure_gbp
from {{ ref('silver_flights') }} f left join bookings b on f.flight_id=b.flight_id
