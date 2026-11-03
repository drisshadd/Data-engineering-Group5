with typed as (
 select {{ norm_text('airport_code') }} as airport_code,
 initcap({{ clean_text('city') }}) as city,
 {{ parse_int('runways') }} as runways,
 {{ batch_number('_source_file') }} as batch_id, _source_file, _loaded_at,
 city as city_raw, runways as runways_raw
 from {{ source('bronze','airports') }}
), scored as (
 select *, iff(city is null,1,0)+iff(runways is null,1,0) as problem_count from typed
)
select airport_code,city,runways,batch_id,_source_file,_loaded_at
from scored where airport_code is not null
qualify row_number() over(partition by airport_code order by batch_id desc, problem_count asc,city_raw asc nulls last,runways_raw asc nulls last,_source_file asc,_loaded_at desc)=1
