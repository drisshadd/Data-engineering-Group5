{% macro clean_text(col) %}nullif(nullif(nullif(nullif(trim({{ col }}), ''), 'N/A'), 'NULL'), '-'){% endmacro %}
{% macro norm_text(col) %}upper({{ clean_text(col) }}){% endmacro %}
{% macro parse_int(col) %}try_to_number(regexp_substr({{ clean_text(col) }}, '-?[0-9]+'))::integer{% endmacro %}
{% macro batch_number(col) %}coalesce(try_to_number(regexp_substr({{ col }}, 'batch_([0-9]+)', 1, 1, 'e', 1)), 0){% endmacro %}
{% macro parse_ts(col) %}
coalesce(
  try_to_timestamp_tz({{ clean_text(col) }}),
  try_to_timestamp_tz({{ clean_text(col) }} || ' +0000', 'YYYY-MM-DD HH24:MI:SS TZHTZM'),
  try_to_timestamp_tz({{ clean_text(col) }} || ' +0000', 'DD/MM/YYYY HH24:MI TZHTZM'),
  case when regexp_like({{ clean_text(col) }}, '^[0-9]{9,10}$') then to_timestamp_tz(try_to_number({{ clean_text(col) }})) end
)
{% endmacro %}
{% macro money_amount(col) %}
try_to_decimal(
  case when regexp_like(replace(replace(replace({{ clean_text(col) }}, '£',''), 'GBP',''),' ',''), '^-?[0-9]+,[0-9]{1,2}$')
    then replace(replace(replace(replace({{ clean_text(col) }}, '£',''), 'GBP',''),' ',''), ',', '.')
    else replace(replace(replace(replace({{ clean_text(col) }}, '£',''), 'GBP',''),' ',''), ',', '') end, 18, 2)
{% endmacro %}
{% macro source_rank(cols) %}
  {{ batch_number('_source_file') }} desc,
  problem_count asc,
  {% for col in cols %}{{ col }} asc nulls last{% if not loop.last %},{% endif %}{% endfor %},
  _source_file asc, _loaded_at desc
{% endmacro %}
