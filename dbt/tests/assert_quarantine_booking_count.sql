-- Counts are baseline-specific: use warn to avoid blocking future incremental ingestion.
{{ config(severity='warn') }}
select 1 as error where (select count(*) from {{ ref('bookings') }}) != 977
