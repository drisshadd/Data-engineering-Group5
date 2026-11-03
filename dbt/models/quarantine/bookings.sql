select booking_id,flight_id,passenger_id,
 fare_gbp as raw_fare_gbp,cabin_raw,booked_raw,
 quarantine_reason,hard_count,soft_count,batch_id,_source_file,_loaded_at
from {{ ref('stg_bookings_ranked') }} where hard_count>0
