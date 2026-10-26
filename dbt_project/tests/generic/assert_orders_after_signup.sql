{{ config(severity='warn') }}

select
    o.order_id,
    o.order_date,
    c.signup_date
from {{ ref('stg_orders') }} o
inner join {{ ref('stg_customers') }} c on o.customer_id = c.customer_id
where o.order_date < c.signup_date