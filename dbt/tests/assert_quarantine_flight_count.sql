{{ config(severity='warn') }}
select 1 as error where (select count(*) from {{ ref('flights') }}) != 79
