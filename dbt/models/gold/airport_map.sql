with o as (
    select origin_city,
           sum(flights_operated)        as flights,
           sum(on_time_flights)         as on_time_flights,
           sum(flights_with_delay)      as flights_with_delay,
           sum(flights_delayed_3h_plus) as flights_delayed_3h_plus
    from {{ ref('daily_otp') }}
    group by 1
)
select o.origin_city,
       c.iata,
       g.airport_name,
       g.latitude,
       g.longitude,
       g.country,
       o.flights,
       round(100 * o.on_time_flights / nullif(o.flights_with_delay, 0), 2) as otp15_pct,
       o.flights_delayed_3h_plus
from o
join SKYHOP.BRONZE.CITY_REFERENCE c on c.city = o.origin_city
left join {{ ref('stg_airport_geo') }} g on g.iata = c.iata
