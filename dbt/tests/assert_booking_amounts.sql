select * from {{ ref('silver_bookings') }} where fare_gbp is null or fare_gbp<0
