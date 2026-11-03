select 1 as error
where abs(coalesce((select sum(net_revenue_gbp) from {{ ref('flight_performance') }}),0)
 - coalesce((select sum(iff(not is_refund,fare_gbp,0)) from {{ ref('silver_bookings') }}),0)) > 0.01
