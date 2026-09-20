"""Interactive executive dashboard for the Online Retail case study."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
EXPORTS = ROOT / "exports"

st.set_page_config(page_title="E-commerce Business Analytics", page_icon="📊", layout="wide")


@st.cache_data
def load_csv(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    path = EXPORTS / f"{name}.csv"
    if not path.exists():
        st.error("No encuentro los datos procesados. Ejecuta `python -m src.pipeline`.")
        st.stop()
    return pd.read_csv(path, parse_dates=parse_dates)


kpis = load_csv("kpi_summary", ["start_date", "end_date"]).iloc[0]
monthly = load_csv("monthly_performance", ["month"])
countries = load_csv("country_performance")
products = load_csv("product_performance")
rfm = load_csv("rfm_segments")
cohorts = load_csv("cohort_retention", ["cohort_month", "order_month"])

st.title("E-commerce Business Analytics")
st.caption(
    f"UCI Online Retail · {kpis.start_date:%d %b %Y}–{kpis.end_date:%d %b %Y} · "
    "Ventas positivas separadas de cancelaciones y devoluciones"
)

cards = st.columns(5)
cards[0].metric("Revenue", f"£{kpis.revenue / 1_000_000:.2f}M")
cards[1].metric("Orders", f"{kpis.orders:,.0f}")
cards[2].metric("Customers", f"{kpis.customers:,.0f}")
cards[3].metric("Average order value", f"£{kpis.average_order_value:,.0f}")
cards[4].metric("Return value rate", f"{kpis.return_value_rate:.1%}")

overview, customers_tab, cohorts_tab = st.tabs(["Performance", "Customers", "Cohorts"])

with overview:
    left, right = st.columns((1.7, 1))
    with left:
        fig = px.line(monthly, x="month", y="revenue", markers=True, title="Monthly revenue")
        fig.update_traces(line_color="#14B8A6", line_width=3)
        fig.update_layout(yaxis_tickprefix="£", yaxis_tickformat=",.0f", xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        top_countries = (
            countries.query("market_type == 'International'").head(10).sort_values("revenue")
        )
        fig = px.bar(
            top_countries,
            x="revenue",
            y="country",
            orientation="h",
            title="Top international markets",
            color_discrete_sequence=["#3B82F6"],
        )
        fig.update_layout(xaxis_tickprefix="£", xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top products by revenue")
    st.dataframe(
        products.head(15)[["product_id", "product_description", "revenue", "units_sold", "orders"]],
        use_container_width=True,
        hide_index=True,
        column_config={"revenue": st.column_config.NumberColumn(format="£%.2f")},
    )

with customers_tab:
    segment_summary = (
        rfm.groupby("segment", as_index=False)
        .agg(customers=("customer_id", "nunique"), revenue=("monetary_value", "sum"))
        .sort_values("revenue", ascending=False)
    )
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            segment_summary,
            x="segment",
            y="revenue",
            color="segment",
            title="Customer value by RFM segment",
        )
        fig.update_layout(showlegend=False, xaxis_title=None, yaxis_tickprefix="£")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.scatter(
            rfm,
            x="frequency",
            y="monetary_value",
            color="segment",
            hover_data=["customer_id", "recency_days"],
            log_x=True,
            log_y=True,
            title="Frequency vs customer value",
        )
        fig.update_layout(xaxis_title="Orders (log)", yaxis_title="Revenue (log)")
        st.plotly_chart(fig, use_container_width=True)

with cohorts_tab:
    max_horizon = int(min(12, cohorts.cohort_index.max()))
    horizon = st.slider("Months since first purchase", 1, max_horizon, min(6, max_horizon))
    matrix = (
        cohorts.query("cohort_index <= @horizon")
        .pivot(index="cohort_month", columns="cohort_index", values="retention_rate")
        .sort_index()
    )
    matrix.index = matrix.index.strftime("%Y-%m")
    fig = px.imshow(
        matrix,
        text_auto=".0%",
        aspect="auto",
        color_continuous_scale=["#EFF6FF", "#3B82F6", "#0F172A"],
        zmin=0,
        zmax=1,
        labels={"x": "Months since acquisition", "y": "Cohort", "color": "Retention"},
        title="Monthly cohort retention",
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Source: UCI Machine Learning Repository · Online Retail (Chen, 2015).")
