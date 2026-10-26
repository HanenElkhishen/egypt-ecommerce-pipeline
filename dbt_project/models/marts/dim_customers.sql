with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
),

customer_orders as (
    select
        customer_id,
        count(*) as total_orders,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        sum(case when order_status = 'completed' then order_total_egp else 0 end) as lifetime_value_egp
    from orders
    group by customer_id
)

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.city,
    c.signup_date,
    coalesce(co.total_orders, 0) as total_orders,
    co.first_order_date,
    co.last_order_date,
    coalesce(co.lifetime_value_egp, 0) as lifetime_value_egp
from customers c
left join customer_orders co on c.customer_id = co.customer_id