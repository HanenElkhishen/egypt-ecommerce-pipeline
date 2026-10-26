select
    order_date,
    count(*) as orders_count,
    sum(order_total_egp) as revenue_egp,
    round(avg(order_total_egp), 2) as avg_order_value_egp
from {{ ref('fct_orders') }}
where order_status = 'completed'
group by order_date