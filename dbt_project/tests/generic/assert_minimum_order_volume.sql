select 1 as problem
where (select count(*) from {{ ref('fct_orders') }}) < 100