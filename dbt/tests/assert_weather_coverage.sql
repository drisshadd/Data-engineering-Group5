-- WARN-only coverage check. Weather is optional for the core flight pipeline.
-- Configure severity: warn via config; do not block builds for incomplete external data.
{{ config(severity='warn') }}
select 'no_weather_matches' as issue
where (select count_if(weather_available) from {{ ref('weather_impact') }}) = 0
