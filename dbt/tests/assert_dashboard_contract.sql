-- Fail when dashboard-facing fields are missing after a dbt build.
with required as (
 select 'FLIGHT_PERFORMANCE' as table_name,'REVENUE_GBP' as column_name union all
 select 'FLIGHT_PERFORMANCE','BOOKING_COUNT' union all
 select 'FLIGHT_PERFORMANCE','IS_ON_TIME' union all
 select 'FLIGHT_PERFORMANCE','SCHEDULED_DEPARTURE_UTC' union all
 select 'DAILY_OTP','TOTAL_FLIGHTS' union all
 select 'DAILY_OTP','TOTAL_REVENUE_GBP' union all
 select 'DAILY_OTP','OTP_PCT'
)
select r.table_name,r.column_name from required r
left join SKYHOP.INFORMATION_SCHEMA.COLUMNS c
 on c.table_schema='GOLD' and c.table_name=r.table_name and c.column_name=r.column_name
where c.column_name is null
