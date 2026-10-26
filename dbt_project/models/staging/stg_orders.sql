select
    order_id,
    customer_id,
    order_date as order_ts,
    order_date::date as order_date,
    lower(trim(status)) as order_status
from {{ source('raw', 'orders') }}