import os
import random

import psycopg2
from dotenv import load_dotenv
from faker import Faker
from psycopg2.extras import execute_values

load_dotenv()

SEED = 42
N_CUSTOMERS = 500
N_PRODUCTS = 50
N_ORDERS = 2000

fake = Faker()
Faker.seed(SEED)
random.seed(SEED)

CITIES = [
    "Cairo",
    "Giza",
    "Alexandria",
    "Mansoura",
    "Shibin El Kom",
    "Tanta",
    "Aswan",
    "Luxor",
    "Port Said",
    "Suez",
]
STATUSES = ["completed", "completed", "completed", "shipped", "cancelled", "returned"]

CATALOG = {
    "Electronics": (["Phone", "Headphones", "Laptop", "Smart Watch", "Charger"], 300, 25000),
    "Fashion": (["T-Shirt", "Jeans", "Sneakers", "Jacket", "Backpack"], 100, 3000),
    "Home": (["Lamp", "Blender", "Pillow", "Kettle", "Vacuum"], 80, 6000),
    "Books": (["Novel", "Cookbook", "Biography", "Notebook", "Atlas"], 30, 500),
}

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id INT, first_name TEXT, last_name TEXT, email TEXT,
    city TEXT, signup_date DATE, loaded_at TIMESTAMP DEFAULT now()
);
CREATE TABLE IF NOT EXISTS raw.products (
    product_id INT, product_name TEXT, category TEXT,
    price_egp NUMERIC(10,2), loaded_at TIMESTAMP DEFAULT now()
);
CREATE TABLE IF NOT EXISTS raw.orders (
    order_id INT, customer_id INT, order_date TIMESTAMP,
    status TEXT, loaded_at TIMESTAMP DEFAULT now()
);
CREATE TABLE IF NOT EXISTS raw.order_items (
    order_item_id INT, order_id INT, product_id INT, quantity INT,
    unit_price_egp NUMERIC(10,2), loaded_at TIMESTAMP DEFAULT now()
);
"""


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def generate_customers():
    rows = []
    for customer_id in range(1, N_CUSTOMERS + 1):
        email = fake.email() if random.random() > 0.03 else None  # ~3% missing emails
        rows.append(
            (
                customer_id,
                fake.first_name(),
                fake.last_name(),
                email,
                random.choice(CITIES),
                fake.date_between(start_date="-2y", end_date="-30d"),
            )
        )
    rows.extend(random.sample(rows, 5))  # intentional duplicates
    return rows


def generate_products():
    rows = []
    for product_id in range(1, N_PRODUCTS + 1):
        category = random.choice(list(CATALOG))
        names, low, high = CATALOG[category]
        name = f"{random.choice(names)} {fake.word().title()}"
        rows.append((product_id, name, category, round(random.uniform(low, high), 2)))
    return rows


def generate_orders_and_items(products):
    price_by_id = {p[0]: p[3] for p in products}
    orders, items = [], []
    item_id = 1
    for order_id in range(1, N_ORDERS + 1):
        status = random.choice(STATUSES)
        if random.random() < 0.01:
            status = status.upper()  # intentional inconsistent casing
        orders.append(
            (
                order_id,
                random.randint(1, N_CUSTOMERS),
                fake.date_time_between(start_date="-1y", end_date="now"),
                status,
            )
        )
        for _ in range(random.randint(1, 4)):
            product_id = random.randint(1, N_PRODUCTS)
            items.append(
                (item_id, order_id, product_id, random.randint(1, 3), price_by_id[product_id])
            )
            item_id += 1
    return orders, items


def load_table(cur, table, columns, rows):
    cur.execute(f"TRUNCATE TABLE raw.{table}")  # makes the script re-runnable
    execute_values(
        cur,
        f"INSERT INTO raw.{table} ({', '.join(columns)}) VALUES %s",
        rows,
    )
    print(f"Loaded {len(rows):>5} rows into raw.{table}")


def main():
    customers = generate_customers()
    products = generate_products()
    orders, items = generate_orders_and_items(products)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
            load_table(
                cur,
                "customers",
                ["customer_id", "first_name", "last_name", "email", "city", "signup_date"],
                customers,
            )
            load_table(
                cur, "products", ["product_id", "product_name", "category", "price_egp"], products
            )
            load_table(cur, "orders", ["order_id", "customer_id", "order_date", "status"], orders)
            load_table(
                cur,
                "order_items",
                ["order_item_id", "order_id", "product_id", "quantity", "unit_price_egp"],
                items,
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
