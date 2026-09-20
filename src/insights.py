"""Print the decision-relevant findings used in the project narrative."""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def show(connection: duckdb.DuckDBPyConnection, title: str, query: str) -> None:
    print(f"\n{title}")
    print(connection.sql(query).df().to_string(index=False))


if __name__ == "__main__":
    database_path = ROOT / "data" / "processed" / "online_retail.duckdb"
    with duckdb.connect(database_path, read_only=True) as con:
        show(con, "MONTHS", "SELECT * FROM monthly_performance ORDER BY revenue DESC LIMIT 4")
        show(
            con,
            "COUNTRIES",
            """SELECT * FROM country_performance
               WHERE market_type = 'International' LIMIT 5""",
        )
        show(
            con,
            "RFM",
            """SELECT segment, COUNT(*) AS customers,
                      ROUND(SUM(monetary_value), 2) AS revenue
               FROM rfm_segments GROUP BY 1 ORDER BY revenue DESC""",
        )
        show(
            con,
            "RETENTION",
            """SELECT cohort_index,
                      ROUND(SUM(active_customers)::DOUBLE / SUM(cohort_size), 4)
                          AS weighted_retention
               FROM cohort_retention WHERE cohort_index BETWEEN 0 AND 6
               GROUP BY 1 ORDER BY 1""",
        )
        show(
            con,
            "PRODUCTS",
            """SELECT product_description, revenue, units_sold
               FROM product_performance LIMIT 5""",
        )
