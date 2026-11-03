-- Fails if bronze source has no ingestion records; adjustable recency SLA after first run
select 'flights' as source_name where (select count(*) from {{ source('bronze','flights') }})=0
union all select 'bookings' where (select count(*) from {{ source('bronze','bookings') }})=0
