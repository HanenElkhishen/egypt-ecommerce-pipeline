import sys

from generate_and_load import get_connection

CHECKS = {
    "customers table is not empty": "SELECT COUNT(*) > 0 FROM raw.customers",
    "orders table is not empty": "SELECT COUNT(*) > 0 FROM raw.orders",
    "every order item points to an existing order": """
        SELECT COUNT(*) = 0
        FROM raw.order_items i
        LEFT JOIN raw.orders o ON i.order_id = o.order_id
        WHERE o.order_id IS NULL
    """,
    "no zero or negative quantities": "SELECT COUNT(*) = 0 FROM raw.order_items WHERE quantity <= 0",
}


def main():
    conn = get_connection()
    failed = []
    try:
        with conn.cursor() as cur:
            for name, query in CHECKS.items():
                cur.execute(query)
                passed = cur.fetchone()[0]
                print(f"{'PASS' if passed else 'FAIL'}  {name}")
                if not passed:
                    failed.append(name)
    finally:
        conn.close()

    if failed:
        sys.exit(f"{len(failed)} raw data check(s) failed")


if __name__ == "__main__":
    main()
