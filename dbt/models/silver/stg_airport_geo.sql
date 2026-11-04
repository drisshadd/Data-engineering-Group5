select
    payload:iata_code::varchar     as iata,
    payload:name::varchar          as airport_name,
    payload:latitude_deg::float    as latitude,
    payload:longitude_deg::float   as longitude,
    payload:iso_country::varchar   as country
from {{ source('bronze','api_raw') }}
where source = 'ourairports'
