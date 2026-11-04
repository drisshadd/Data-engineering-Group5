select
    'govuk'                       as holiday_source,
    d.key::varchar                as holiday_calendar,
    to_date(e.value:date::varchar) as holiday_date,
    e.value:title::varchar        as holiday_name
from {{ source('bronze','api_raw') }} a,
     lateral flatten(input => a.payload) d,
     lateral flatten(input => d.value:events) e
where a.source = 'govuk_bank_holidays'
union all
select
    'nager',
    'FR',
    to_date(h.value:date::varchar),
    h.value:name::varchar
from {{ source('bronze','api_raw') }} a,
     lateral flatten(input => a.payload) h
where a.source = 'nager_date'
