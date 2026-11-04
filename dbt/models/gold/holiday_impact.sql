with otp as (
    select business_date, origin_city, flights_with_delay, on_time_flights, flights_delayed_3h_plus
    from {{ ref('daily_otp') }}
),
cal as (
    select city, holiday_calendar from SKYHOP.BRONZE.CITY_REFERENCE
),
hol as (
    select distinct holiday_calendar, holiday_date from {{ ref('stg_holidays') }}
)
select
    iff(hol.holiday_date is not null, 'public holiday', 'normal day') as day_type,
    count(*)                                  as city_days,
    sum(otp.flights_with_delay)               as flights_with_delay,
    sum(otp.on_time_flights)                  as on_time_flights,
    round(100 * sum(otp.on_time_flights) / nullif(sum(otp.flights_with_delay), 0), 2) as otp15_pct,
    sum(otp.flights_delayed_3h_plus)          as flights_delayed_3h_plus
from otp
join cal on cal.city = otp.origin_city
left join hol on hol.holiday_calendar = cal.holiday_calendar
             and hol.holiday_date = otp.business_date
group by 1
