select 1 as error where (select count(*) from {{ ref('flight_performance') }}) != (select count(*) from {{ ref('silver_flights') }})
