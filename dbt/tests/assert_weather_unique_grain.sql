-- Returns a row (and fails) if the daily weather/flight join multiplies rows.
select business_date, origin_airport, count(*) as duplicate_count
from {{ ref('weather_impact') }}
group by 1,2
having count(*) > 1
