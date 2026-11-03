with typed as (
 select {{ parse_int('flight_id') }} as flight_id,
 {{ norm_text('flight_number') }} as flight_number,
 {{ norm_text('origin') }} as origin_airport,
 {{ norm_text('destination') }} as destination_airport,
 {{ parse_ts('scheduled_departure') }} as departure_utc,
 {{ parse_int('delay_min') }} as delay_raw,
 {{ parse_int('seats') }} as seats_raw,
 {{ batch_number('_source_file') }} as batch_id,_source_file,_loaded_at,
 scheduled_departure,delay_min,seats,origin,destination
 from {{ source('bronze','flights') }}
), cleaned as (
 select *,case when delay_raw between 0 and 1440 then delay_raw end as delay_min_clean,
 case when seats_raw between 50 and 400 then seats_raw end as seats_clean,
 case when departure_utc is not null and year(departure_utc) not in (1970,2099) then departure_utc end as departure_clean
 from typed
), scored as (
 select c.*,
 iff(flight_id is null,1,0)+iff(a.airport_code is null,1,0)+iff(z.airport_code is null,1,0)
 +iff(origin_airport is not null and origin_airport=destination_airport,1,0)
 +iff(departure_clean is null,1,0) as hard_count,
 iff(delay_min_clean is null,1,0)+iff(seats_clean is null,1,0) as soft_count,
 array_to_string(array_construct_compact(
 iff(flight_id is null,'missing flight_id',null),
 iff(a.airport_code is null,'unknown origin',null),
 iff(z.airport_code is null,'unknown destination',null),
 iff(origin_airport is not null and origin_airport=destination_airport,'origin equals destination',null),
 iff(departure_clean is null,'scheduled_departure not readable',null)), '; ') as quarantine_reason
 from cleaned c
 left join {{ ref('silver_airports') }} a on c.origin_airport=a.airport_code
 left join {{ ref('silver_airports') }} z on c.destination_airport=z.airport_code
), ranked as (
 select *,row_number() over(partition by flight_id order by batch_id desc,hard_count+soft_count asc,
 scheduled_departure asc nulls last,delay_min asc nulls last,seats asc nulls last,origin asc nulls last,destination asc nulls last,flight_number asc nulls last,_source_file asc,_loaded_at desc) as rn
 from scored
)
select * from ranked where rn=1 or flight_id is null
