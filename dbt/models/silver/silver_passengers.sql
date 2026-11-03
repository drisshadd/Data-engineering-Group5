with typed as (
 select {{ parse_int('passenger_id') }} as passenger_id,
 case when lower(replace(trim(email),' ','')) = 'test@test.com' or contains(email,'..') then null
 when regexp_like(lower(replace(trim(email),' ','')), '^[^@]+@[^@]+\\.[a-z]{2,}$') then lower(replace(trim(email),' ','')) end as email,
 case when lower(trim(frequent_flyer_tier)) like 'none%' then 'none'
 when lower(trim(frequent_flyer_tier)) like 'silver%' then 'silver'
 when lower(trim(frequent_flyer_tier)) like 'gold%' then 'gold'
 when lower(trim(frequent_flyer_tier)) like 'plat%' then 'platinum' end as tier,
 full_name, email as email_raw, frequent_flyer_tier as tier_raw,
 {{ batch_number('_source_file') }} as batch_id,_source_file,_loaded_at
 from {{ source('bronze','passengers') }}
), ranked as (
 select *,iff(email is null,1,0)+iff(tier is null,1,0) as problem_count from typed
)
select passenger_id, email, tier, full_name, batch_id, _source_file, _loaded_at
from ranked where passenger_id is not null
qualify row_number() over(partition by passenger_id order by batch_id desc,problem_count asc,email_raw asc nulls last,tier_raw asc nulls last,full_name asc nulls last,_source_file asc,_loaded_at desc)=1
