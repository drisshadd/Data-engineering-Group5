select coalesce(p.tier,'unknown') as loyalty_tier,count(*) as bookings_sold,
 sum(b.fare_gbp) as gross_sales_gbp,count(distinct b.passenger_id) as distinct_passengers
from {{ ref('silver_bookings') }} b left join {{ ref('silver_passengers') }} p on b.passenger_id=p.passenger_id
where not b.is_refund group by 1
