import generate_and_load as g


def test_customers_include_intentional_duplicates():
    rows = g.generate_customers()
    assert len(rows) == g.N_CUSTOMERS + 5


def test_products_have_positive_prices():
    products = g.generate_products()
    assert len(products) == g.N_PRODUCTS
    assert all(p[3] > 0 for p in products)


def test_every_item_belongs_to_an_existing_order():
    products = g.generate_products()
    orders, items = g.generate_orders_and_items(products)
    order_ids = {o[0] for o in orders}
    assert len(orders) == g.N_ORDERS
    assert all(item[1] in order_ids for item in items)
