select flight_id,flight_number,origin_airport,destination_airport,
 departure_clean as scheduled_departure_utc,
 convert_timezone('Europe/London',departure_clean)::date as business_date,
 delay_min_clean as delay_min,seats_clean as seats,batch_id,_source_file,_loaded_at
from {{ ref('stg_flights_ranked') }} where rn=1 and hard_count=0
