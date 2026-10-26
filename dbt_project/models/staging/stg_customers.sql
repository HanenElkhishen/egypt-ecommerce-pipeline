with source as (
    select * from {{ source('raw', 'customers') }}
),

deduplicated as (
    select
        *,
        row_number() over (partition by customer_id order by loaded_at) as rn
    from source
)

select
    customer_id,
    initcap(trim(first_name)) as first_name,
    initcap(trim(last_name)) as last_name,
    lower(trim(email)) as email,
    city,
    signup_date
from deduplicated
where rn = 1