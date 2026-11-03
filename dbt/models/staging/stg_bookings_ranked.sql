with typed as (
 select {{ parse_int('booking_id') }} as booking_id,
 {{ parse_int('flight_id') }} as flight_id,
 {{ parse_int('passenger_id') }} as passenger_id,
 {{ money_amount('fare_gbp') }} as amount_raw,
 iff(contains(coalesce(fare_gbp,''),'€'),true,false) as is_eur,
 case when lower(trim(cabin)) like 'econ%' then 'economy'
 when lower(trim(cabin)) like 'prem%' then 'premium'
 when lower(trim(cabin)) like 'bus%' then 'business' end as cabin,
 {{ parse_ts('coalesce(booked_at,booked_at_v2)') }} as booked_utc_raw,
 {{ batch_number('_source_file') }} as batch_id,_source_file,_loaded_at,
 fare_gbp,flight_id as flight_id_raw,passenger_id as passenger_id_raw,cabin as cabin_raw,
 coalesce(booked_at,booked_at_v2) as booked_raw
 from {{ source('bronze','bookings') }}
), checked as (
 select t.*,iff(f.flight_id is null,1,0) as unknown_flight,
 iff(p.passenger_id is null,1,0) as unknown_passenger,
 iff(booked_utc_raw is null or year(booked_utc_raw) in (1970,2099),1,0) as bad_booking_time,
 iff(booking_id is null,1,0)+iff(f.flight_id is null,1,0)+iff(is_eur,1,0)+iff(amount_raw is null,1,0) as hard_count,
 iff(p.passenger_id is null,1,0)+iff(cabin is null,1,0)
 +iff(booked_utc_raw is null or year(booked_utc_raw) in (1970,2099),1,0) as soft_count,
 array_to_string(array_construct_compact(
 iff(booking_id is null,'missing booking_id',null),
 iff(f.flight_id is null,'unknown or quarantined flight_id',null),
 iff(is_eur,'fare in EUR on a GBP feed',null),
 iff(not is_eur and amount_raw is null,'fare not readable',null)), '; ') as quarantine_reason
 from typed t
 left join {{ ref('silver_flights') }} f on t.flight_id=f.flight_id
 left join {{ ref('silver_passengers') }} p on t.passenger_id=p.passenger_id
), ranked as (
 select *,row_number() over(partition by booking_id order by batch_id desc,hard_count+soft_count asc,
 fare_gbp asc nulls last,flight_id_raw asc nulls last,passenger_id_raw asc nulls last,cabin_raw asc nulls last,booked_raw asc nulls last,_source_file asc,_loaded_at desc) as rn
 from checked
)
select * from ranked where rn=1 or booking_id is null
