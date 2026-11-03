select 1 as error
where abs(coalesce((select sum(total_revenue_gbp) from {{ ref('daily_otp') }}),0)
 - coalesce((select sum(revenue_gbp) from {{ ref('flight_performance') }}),0)) > 0.01
