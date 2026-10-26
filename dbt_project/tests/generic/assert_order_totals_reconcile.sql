-- Fails if total revenue in the mart differs from the sum of staging line totals
with mart as (
    select sum(order_total_egp) as total from {{ ref('fct_orders') }}
),

staging as (
    select sum(line_total_egp) as total from {{ ref('stg_order_items') }}
)

select
    mart.total as mart_total,
    staging.total as staging_total
from mart
cross join staging
where mart.total <> staging.total