"""Build a reproducible DuckDB analytics model from the UCI Online Retail workbook."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

DATA_URL = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def snake_case(value: str) -> str:
    """Convert source headers into stable SQL-friendly names."""
    first_pass = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower().replace(" ", "_")


def download_source(root: Path, force: bool = False) -> Path:
    """Download and extract the official UCI workbook."""
    raw_dir = root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = raw_dir / "Online Retail.xlsx"
    if workbook_path.exists() and not force:
        return workbook_path

    zip_path = raw_dir / "online-retail.zip"
    urllib.request.urlretrieve(DATA_URL, zip_path)  # noqa: S310 - fixed trusted URL
    with zipfile.ZipFile(zip_path) as archive:
        archive.extract("Online Retail.xlsx", raw_dir)
    return workbook_path


def clean_source(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize types and derive row-level commercial fields."""
    df = frame.copy()
    df.columns = [snake_case(str(column)) for column in df.columns]
    df = df.rename(columns={"invoice_no": "invoice_id", "stock_code": "product_id"})

    df["invoice_id"] = df["invoice_id"].astype("string")
    df["product_id"] = df["product_id"].astype("string")
    df["description"] = df["description"].astype("string").str.strip()
    df["country"] = df["country"].astype("string").str.strip()
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    df["is_cancelled"] = df["invoice_id"].str.startswith("C", na=False)
    df["is_sale"] = (df["quantity"] > 0) & (df["unit_price"] > 0) & ~df["is_cancelled"]
    df["is_return"] = (df["quantity"] < 0) | df["is_cancelled"]
    df["line_value"] = df["quantity"] * df["unit_price"]
    df["sales_revenue"] = df["line_value"].where(df["is_sale"], 0.0)
    df["return_value"] = (-df["line_value"]).where(df["is_return"], 0.0).clip(lower=0)
    return df


def read_queries(root: Path) -> str:
    """Load the dimensional model and analytical marts in execution order."""
    return "\n".join(
        (root / "sql" / name).read_text(encoding="utf-8")
        for name in ("01_star_schema.sql", "02_business_marts.sql")
    )


def export_table(connection: duckdb.DuckDBPyConnection, table: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    safe_path = str(destination.resolve()).replace("'", "''")
    connection.execute(f"COPY {table} TO '{safe_path}' (HEADER, DELIMITER ',')")


def build(root: Path = DEFAULT_ROOT, force_download: bool = False) -> dict[str, object]:
    """Run ingestion, modeling, checks, and aggregate exports."""
    workbook_path = download_source(root, force=force_download)
    processed_dir = root / "data" / "processed"
    exports_dir = root / "exports"
    processed_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    source = pd.read_excel(workbook_path, engine="openpyxl")
    transactions = clean_source(source)

    database_path = processed_dir / "online_retail.duckdb"
    if database_path.exists():
        database_path.unlink()

    with duckdb.connect(database_path) as connection:
        connection.register("transactions_df", transactions)
        connection.execute("CREATE TABLE raw_transactions AS SELECT * FROM transactions_df")
        connection.execute(read_queries(root))

        tables = [
            "kpi_summary",
            "monthly_performance",
            "country_performance",
            "product_performance",
            "rfm_segments",
            "cohort_retention",
            "data_quality",
        ]
        for table in tables:
            export_table(connection, table, exports_dir / f"{table}.csv")

        kpis = connection.execute("SELECT * FROM kpi_summary").fetchdf().iloc[0].to_dict()
        quality = connection.execute("SELECT check_name, check_value FROM data_quality").fetchall()
        kpis["data_quality"] = {name: value for name, value in quality}

    serializable = {
        key: (value.item() if hasattr(value, "item") else value) for key, value in kpis.items()
    }
    (exports_dir / "metrics.json").write_text(
        json.dumps(serializable, indent=2, default=str), encoding="utf-8"
    )
    return serializable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    result = build(arguments.root.resolve(), arguments.force_download)
    print(json.dumps(result, indent=2, default=str))
