-- Column-level guard on dashboard models
select column_name from SKYHOP.INFORMATION_SCHEMA.COLUMNS where table_schema='GOLD' and table_name in ('FLIGHT_PERFORMANCE','DAILY_OTP') and column_name in ('EMAIL','FULL_NAME')
