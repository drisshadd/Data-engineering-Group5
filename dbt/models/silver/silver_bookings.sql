-- Keep refunds as positive amounts; flag them separately for net-revenue exclusion.
select booking_id, flight_id, iff(unknown_passenger=1,null,passenger_id) as passenger_id,
 cabin, iff(bad_booking_time=1,null,booked_utc_raw) as booked_at_utc,
 iff(amount_raw<0,true,false) as is_refund,
 round(iff(abs(amount_raw)>=1000,abs(amount_raw)/100,abs(amount_raw)),2)::number(18,2) as fare_gbp,
 batch_id,_source_file,_loaded_at
from {{ ref('stg_bookings_ranked') }}
where rn=1 and hard_count=0
