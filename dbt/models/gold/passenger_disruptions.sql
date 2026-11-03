-- Booking exposure, not confirmed passenger count or compensation eligibility.
select business_date,
 count(*) as total_flights, sum(booking_count) as total_bookings,
 count_if(delay_min>15) as delayed_flights,
 sum(iff(delay_min>15,booking_count,0)) as disrupted_bookings,
 count_if(delay_min>=180) as severely_delayed_flights,
 sum(iff(delay_min>=180,booking_count,0)) as severely_disrupted_bookings,
 round(100.0*sum(iff(delay_min>15,booking_count,0))/nullif(sum(booking_count),0),2) as disrupted_booking_pct,
 sum(uk261_exposure_gbp) as estimated_uk261_exposure_gbp
from {{ ref('flight_performance') }} group by business_date
