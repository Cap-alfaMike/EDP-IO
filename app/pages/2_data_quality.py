# ============================================================================
# EDP-IO - Data Quality Page
# ============================================================================
"""
Data quality metrics and trends for data governance.

Shows:
- Quality scores by table
- Test results from dbt
- Trend analysis
- Quality rules and violations
"""

import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Data Quality | EDP-IO",
    page_icon="✅",
    layout="wide",
)

st.title("✅ Data Quality")
st.caption("Monitor data quality metrics and trends across the platform")


def generate_quality_data():
    """Generate mock quality metrics."""
    random.seed(42)

    tables = [
        {"table": "bronze.customers", "layer": "Bronze", "owner": "CRM Team"},
        {"table": "bronze.products", "layer": "Bronze", "owner": "Inventory Team"},
        {"table": "bronze.orders", "layer": "Bronze", "owner": "E-commerce Team"},
        {"table": "silver.stg_customers", "layer": "Silver", "owner": "Data Engineering"},
        {"table": "silver.stg_products", "layer": "Silver", "owner": "Data Engineering"},
        {"table": "silver.stg_orders", "layer": "Silver", "owner": "Data Engineering"},
        {"table": "gold.dim_customer", "layer": "Gold", "owner": "Analytics"},
        {"table": "gold.dim_product", "layer": "Gold", "owner": "Analytics"},
        {"table": "gold.fact_sales", "layer": "Gold", "owner": "Analytics"},
    ]

    data = []
    for t in tables:
        data.append(
            {
                **t,
                "Completeness": round(random.uniform(95, 100), 1),
                "Uniqueness": round(random.uniform(99, 100), 1),
                "Validity": round(random.uniform(97, 100), 1),
                "Freshness": round(random.uniform(96, 100), 1),
                "Overall": round(random.uniform(97, 99.5), 1),
                "Tests Passed": random.randint(5, 12),
                "Tests Failed": random.choice([0, 0, 0, 0, 1]),
            }
        )

    return pd.DataFrame(data)


def generate_trend_data():
    """Generate quality trend data."""
    dates = pd.date_range(end=datetime.now(), periods=30, freq="D")

    trend = pd.DataFrame(
        {
            "date": dates,
            "Bronze": [random.uniform(96, 99) for _ in range(30)],
            "Silver": [random.uniform(97, 99.5) for _ in range(30)],
            "Gold": [random.uniform(98, 99.8) for _ in range(30)],
        }
    )

    return trend


# Summary metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Overall Quality Score", "98.7%", "+0.2%")

with col2:
    st.metric("Tables Monitored", "9", "All passing")

with col3:
    st.metric("Tests Passed", "72/73", "98.6%")

with col4:
    st.metric("SLA Compliance", "100%", "On target")


st.markdown("---")


# Quality by layer
st.subheader("Quality by Data Layer")

quality_df = generate_quality_data()

# Layer summary
layer_summary = (
    quality_df.groupby("layer")
    .agg(
        {
            "Overall": "mean",
            "Tests Passed": "sum",
            "Tests Failed": "sum",
        }
    )
    .round(1)
)

col1, col2, col3 = st.columns(3)

for i, layer in enumerate(["Bronze", "Silver", "Gold"]):
    with [col1, col2, col3][i]:
        score = layer_summary.loc[layer, "Overall"]
        passed = int(layer_summary.loc[layer, "Tests Passed"])
        failed = int(layer_summary.loc[layer, "Tests Failed"])

        color = "#27ae60" if score >= 98 else "#f39c12" if score >= 95 else "#e74c3c"

        st.markdown(
            f"""
        <div style="background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color: #666; margin: 0;">{layer} Layer</h3>
            <h1 style="color: {color}; margin: 10px 0;">{score}%</h1>
            <small style="color: #666;">✅ {passed} passed | ❌ {failed} failed</small>
        </div>
        """,
            unsafe_allow_html=True,
        )


st.markdown("---")


# Trend chart
st.subheader("Quality Trend (30 Days)")

trend_df = generate_trend_data()

fig = px.line(
    trend_df,
    x="date",
    y=["Bronze", "Silver", "Gold"],
    title="",
    labels={"value": "Quality Score (%)", "date": "Date", "variable": "Layer"},
)
fig.update_layout(
    yaxis_range=[94, 100],
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig, use_container_width=True)


st.markdown("---")


# Detailed table quality
st.subheader("Quality by Table")

# Display options
view_mode = st.radio("View", ["Summary", "Detailed"], horizontal=True)

if view_mode == "Summary":
    display_cols = ["table", "layer", "Overall", "Tests Passed", "Tests Failed"]
else:
    display_cols = [
        "table",
        "layer",
        "Completeness",
        "Uniqueness",
        "Validity",
        "Freshness",
        "Overall",
    ]

st.dataframe(
    quality_df[display_cols].style.background_gradient(
        cmap="RdYlGn",
        subset=[
            c
            for c in display_cols
            if c in ["Completeness", "Uniqueness", "Validity", "Freshness", "Overall"]
        ],
        vmin=95,
        vmax=100,
    ),
    use_container_width=True,
    height=350,
)


st.markdown("---")


# Quality rules
st.subheader("Quality Rules")

rules = [
    {
        "rule": "customer_id_unique",
        "table": "bronze.customers",
        "type": "Uniqueness",
        "status": "✅ Pass",
    },
    {
        "rule": "order_total_valid",
        "table": "bronze.orders",
        "type": "Validity",
        "status": "✅ Pass",
    },
    {
        "rule": "product_price_positive",
        "table": "bronze.products",
        "type": "Validity",
        "status": "✅ Pass",
    },
    {
        "rule": "email_format_valid",
        "table": "silver.stg_customers",
        "type": "Format",
        "status": "⚠️ Warning (2 violations)",
    },
    {
        "rule": "foreign_key_customer",
        "table": "gold.fact_sales",
        "type": "Referential",
        "status": "✅ Pass",
    },
]

for rule in rules:
    col1, col2, col3, col4 = st.columns([2, 2, 1, 2])
    with col1:
        st.text(rule["rule"])
    with col2:
        st.text(rule["table"])
    with col3:
        st.text(rule["type"])
    with col4:
        st.text(rule["status"])


st.markdown("---")
st.caption(
    "Quality metrics updated every 15 minutes | Last update: "
    + datetime.now().strftime("%Y-%m-%d %H:%M")
)
