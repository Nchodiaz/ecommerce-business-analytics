"""Prepare compact, typed data for the portfolio Excel workbook generator."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "exports"


def records(frame: pd.DataFrame) -> list[list[object]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return [clean.columns.tolist(), *clean.values.tolist()]


def main() -> None:
    kpis = pd.read_csv(EXPORTS / "kpi_summary.csv")
    monthly = pd.read_csv(EXPORTS / "monthly_performance.csv")
    countries = pd.read_csv(EXPORTS / "country_performance.csv")
    products = pd.read_csv(EXPORTS / "product_performance.csv").head(20)
    rfm = pd.read_csv(EXPORTS / "rfm_segments.csv")
    cohorts = pd.read_csv(EXPORTS / "cohort_retention.csv")
    quality = pd.read_csv(EXPORTS / "data_quality.csv")

    segment_summary = (
        rfm.groupby("segment", as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            revenue=("monetary_value", "sum"),
            median_recency_days=("recency_days", "median"),
            median_orders=("frequency", "median"),
        )
        .sort_values("revenue", ascending=False)
    )
    segment_summary["revenue"] = segment_summary["revenue"].round(2)
    segment_summary["median_recency_days"] = segment_summary["median_recency_days"].round(1)
    cohort_matrix = (
        cohorts.query("cohort_index <= 12")
        .pivot(index="cohort_month", columns="cohort_index", values="retention_rate")
        .reset_index()
    )
    cohort_matrix.columns = [
        "cohort_month" if value == "cohort_month" else f"month_{int(value)}"
        for value in cohort_matrix.columns
    ]

    payload = {
        "kpis": records(kpis),
        "monthly": records(monthly),
        "markets": records(countries.head(16)),
        "products": records(products),
        "segments": records(segment_summary),
        "cohorts": records(cohort_matrix),
        "quality": records(quality),
    }
    destination = EXPORTS / "workbook_payload.json"
    destination.write_text(json.dumps(payload, default=str), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
