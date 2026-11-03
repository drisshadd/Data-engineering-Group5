-- API ingestion readiness only. Do not claim weather correlation until payload is mapped to airports/dates.
with api as (select count(*) as weather_api_documents_available from {{ source('bronze','api_raw') }} where lower(source) like '%meteo%')
select f.origin_airport,count(*) as flights,count(f.delay_min) as flights_with_delay,
 round(avg(f.delay_min),1) as avg_delay_min,max(api.weather_api_documents_available) as weather_api_documents_available
from {{ ref('silver_flights') }} f cross join api group by 1
