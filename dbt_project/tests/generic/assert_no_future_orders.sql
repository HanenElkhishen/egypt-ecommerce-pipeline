-- Allows one day of slack for timezone differences
select order_id, order_date
from {{ ref('stg_orders') }}
where order_date > current_date + 1