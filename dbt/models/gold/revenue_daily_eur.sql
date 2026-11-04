with daily as (
    select business_date,
           count(*)            as flights,
           sum(net_revenue_gbp) as net_revenue_gbp
    from {{ ref('flight_performance') }}
    group by 1
),
fx as (
    select d.business_date, x.gbp_per_eur
    from daily d
    join {{ ref('stg_fx_eur_gbp') }} x
      on x.rate_date <= d.business_date
     and x.rate_date >= dateadd(day, -7, d.business_date)
    qualify row_number() over (partition by d.business_date order by x.rate_date desc) = 1
)
select d.business_date,
       d.flights,
       d.net_revenue_gbp,
       f.gbp_per_eur,
       round(d.net_revenue_gbp / f.gbp_per_eur, 2) as net_revenue_eur
from daily d
left join fx f on f.business_date = d.business_date
