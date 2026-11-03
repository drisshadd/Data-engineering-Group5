select * from {{ ref('silver_flights') }} where origin_airport=destination_airport
