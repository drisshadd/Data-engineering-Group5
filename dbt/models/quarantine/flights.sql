select flight_id,flight_number,origin_airport,destination_airport,
 scheduled_departure as raw_departure,delay_min as raw_delay_min,seats as raw_seats,
 quarantine_reason,hard_count,soft_count,batch_id,_source_file,_loaded_at
from {{ ref('stg_flights_ranked') }} where hard_count>0
