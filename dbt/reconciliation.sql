-- Run in Snowsight after dbt build; targets refer to 2-batch seed-42 reference only.
select 'silver_flights' metric,count(*)::varchar value from SKYHOP.SILVER.SILVER_FLIGHTS
union all select 'silver_bookings',count(*)::varchar from SKYHOP.SILVER.SILVER_BOOKINGS
union all select 'quarantine_bookings',count(*)::varchar from SKYHOP.QUARANTINE.BOOKINGS_QUARANTINE
union all select 'gold_net_revenue_gbp',sum(net_revenue_gbp)::varchar from SKYHOP.GOLD.FLIGHT_PERFORMANCE
union all select 'gold_uk261_exposure_gbp',sum(uk261_exposure_gbp)::varchar from SKYHOP.GOLD.FLIGHT_PERFORMANCE;
