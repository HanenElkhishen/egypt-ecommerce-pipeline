select
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price_egp,
    quantity * unit_price_egp as line_total_egp
from {{ source('raw', 'order_items') }}