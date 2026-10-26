select
    product_id,
    trim(product_name) as product_name,
    category,
    price_egp
from {{ source('raw', 'products') }}