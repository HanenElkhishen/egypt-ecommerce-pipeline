with orders as (
    select * from {{ ref('stg_orders') }}
),

items as (
    select
        order_id,
        sum(quantity) as items_count,
        sum(line_total_egp) as order_total_egp
    from {{ ref('stg_order_items') }}
    group by order_id
)

select
    o.order_id,
    o.customer_id,
    o.order_ts,
    o.order_date,
    o.order_status,
    coalesce(i.items_count, 0) as items_count,
    coalesce(i.order_total_egp, 0) as order_total_egp
from orders o
left join items i on o.order_id = i.order_id