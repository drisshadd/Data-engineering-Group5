-- UC: weather vs punctuality. Grain: local business_date x origin_airport.
-- Open-Meteo API is daily and city-level; association is descriptive, NOT causal.
with weather_raw as (
    select lower(trim(entity)) as city_key,
           payload:daily:time as days,
           payload:daily:precipitation_sum as rain,
           payload:daily:wind_speed_10m_max as wind,
           payload:daily:temperature_2m_max as temperature,
           _loaded_at
    from {{ source('bronze', 'api_raw') }}
    where lower(source) = 'open_meteo'
), weather_days as (
    select city_key,
           try_to_date(d.value::varchar) as weather_date,
           try_to_double(to_varchar(rain[d.index])) as precipitation_mm,
           try_to_double(to_varchar(wind[d.index])) as max_wind_kmh,
           try_to_double(to_varchar(temperature[d.index])) as max_temperature_c,
           _loaded_at
    from weather_raw, lateral flatten(input => days) d
), latest_weather as (
    select * from weather_days
    qualify row_number() over (
        partition by city_key, weather_date
        order by _loaded_at desc
    ) = 1
), flight_days as (
    select f.business_date, f.origin_airport,
           lower(trim(a.city)) as city_key,
           count(*) as flights,
           count(f.delay_min) as flights_with_known_delay,
           count_if(f.delay_min > 15) as delayed_over_15m,
           count_if(f.delay_min >= 180) as severely_delayed_flights,
           round(avg(f.delay_min), 2) as avg_delay_min
    from {{ ref('silver_flights') }} f
    join {{ ref('silver_airports') }} a
      on f.origin_airport = a.airport_code
    group by 1, 2, 3
)
select f.business_date, f.origin_airport, f.city_key as origin_city,
       f.flights, f.flights_with_known_delay, f.delayed_over_15m,
       f.severely_delayed_flights, f.avg_delay_min,
       w.precipitation_mm, w.max_wind_kmh, w.max_temperature_c,
       iff(w.weather_date is not null, true, false) as weather_available
from flight_days f
left join latest_weather w
  on f.city_key = w.city_key and f.business_date = w.weather_date
