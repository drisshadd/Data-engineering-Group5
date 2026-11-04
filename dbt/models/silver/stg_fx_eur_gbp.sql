select
    to_date(r.key)     as rate_date,
    r.value:GBP::float as gbp_per_eur
from {{ source('bronze','api_raw') }} a,
     lateral flatten(input => a.payload:rates) r
where a.source = 'frankfurter'
