select * from {{ ref('silver_flights') }} where (delay_min is not null and delay_min not between 0 and 1440) or (seats is not null and seats not between 50 and 400)
