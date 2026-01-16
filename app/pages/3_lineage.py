# ============================================================================
# EDP-IO - Data Lineage Page
# ============================================================================
"""
Visual data lineage showing how data flows through the platform.

Shows:
- Source to Bronze to Silver to Gold flow
- Table dependencies
- Impact analysis (what breaks if X fails)
"""

import streamlit as st
from streamlit_mermaid import st_mermaid

st.set_page_config(
    page_title="Data Lineage | EDP-IO",
    page_icon="🔗",
    layout="wide",
)

st.title("🔗 Data Lineage")
st.caption("Understand how data flows through the platform")


# Summary
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Source Systems", "2", "Oracle, SQL Server")

with col2:
    st.metric("Data Layers", "3", "Bronze → Silver → Gold")

with col3:
    st.metric("Total Models", "12", "dbt managed")


st.markdown("---")


# Main lineage diagram
st.subheader("End-to-End Data Flow")

lineage_mermaid = """
flowchart LR
    subgraph Sources["📦 Source Systems"]
        ORACLE[(Oracle ERP)]
        SQLSERVER[(SQL Server)]
    end
    
    subgraph Bronze["🥉 Bronze Layer"]
        B_CUST[customers]
        B_PROD[products]
        B_STORE[stores]
        B_ORD[orders]
        B_ITEMS[order_items]
    end
    
    subgraph Silver["🥈 Silver Layer"]
        S_CUST[stg_customers]
        S_PROD[stg_products]
        S_ORD[stg_orders]
    end
    
    subgraph Gold["🥇 Gold Layer"]
        D_CUST[dim_customer]
        D_PROD[dim_product]
        D_DATE[dim_date]
        F_SALES[fact_sales]
    end
    
    subgraph Analytics["📊 Analytics"]
        BI[Power BI]
        DASH[Dashboards]
    end
    
    ORACLE --> B_CUST
    ORACLE --> B_PROD
    ORACLE --> B_STORE
    SQLSERVER --> B_ORD
    SQLSERVER --> B_ITEMS
    
    B_CUST --> S_CUST
    B_PROD --> S_PROD
    B_ORD --> S_ORD
    
    S_CUST --> D_CUST
    S_PROD --> D_PROD
    
    D_CUST --> F_SALES
    D_PROD --> F_SALES
    D_DATE --> F_SALES
    S_ORD --> F_SALES
    B_ITEMS --> F_SALES
    
    F_SALES --> BI
    D_CUST --> BI
    D_PROD --> BI
    F_SALES --> DASH
"""

st_mermaid(lineage_mermaid, height=500)


st.markdown("---")


# Layer-specific views
st.subheader("Layer Details")

tab1, tab2, tab3 = st.tabs(["🥉 Bronze", "🥈 Silver", "🥇 Gold"])

with tab1:
    st.markdown(
        """
    ### Bronze Layer
    **Purpose:** Raw data storage with minimal transformation
    
    | Table | Source | Update Frequency | Records |
    |-------|--------|------------------|---------|
    | customers | Oracle ERP | Daily | ~1M |
    | products | Oracle ERP | Every 6h | ~50K |
    | stores | Oracle ERP | Daily | ~500 |
    | orders | SQL Server | Hourly | ~5M |
    | order_items | SQL Server | Hourly | ~20M |
    
    **Key Features:**
    - Schema enforcement
    - Idempotent ingestion (MERGE)
    - Ingestion metadata columns
    - Delta Lake with time travel
    """
    )

with tab2:
    st.markdown(
        """
    ### Silver Layer
    **Purpose:** Cleaned, validated, historized data
    
    | Model | Source | Transformation | SCD Type |
    |-------|--------|----------------|----------|
    | stg_customers | bronze.customers | Cleansing, standardization | Type 2 |
    | stg_products | bronze.products | Pricing history | Type 2 |
    | stg_orders | bronze.orders | Validation, dedup | Type 1 |
    
    **Key Features:**
    - SCD Type 2 for historical tracking
    - Data quality validation
    - Business key standardization
    - Audit columns (valid_from, valid_to)
    """
    )

with tab3:
    st.markdown(
        """
    ### Gold Layer
    **Purpose:** Star schema for analytics
    
    | Model | Type | Grain | Key Metrics |
    |-------|------|-------|-------------|
    | dim_customer | Dimension | 1 per customer | Segment, tenure, region |
    | dim_product | Dimension | 1 per product | Category, price tier, margin |
    | dim_date | Dimension | 1 per day | Calendar attributes |
    | fact_sales | Fact | 1 per order line | Revenue, cost, profit |
    
    **Key Features:**
    - Conformed dimensions
    - Additive measures
    - Optimized for BI tools
    - Fast query performance
    """
    )


st.markdown("---")


# Impact analysis
st.subheader("Impact Analysis")

selected_table = st.selectbox(
    "Select a table to see impact if it fails:",
    ["bronze.customers", "bronze.orders", "silver.stg_customers", "gold.fact_sales"],
)

impact_map = {
    "bronze.customers": {
        "direct": ["silver.stg_customers"],
        "indirect": ["gold.dim_customer", "gold.fact_sales"],
        "affected_reports": ["Customer Analytics", "Sales Dashboard", "Segmentation Report"],
        "severity": "HIGH",
    },
    "bronze.orders": {
        "direct": ["silver.stg_orders"],
        "indirect": ["gold.fact_sales"],
        "affected_reports": ["Sales Dashboard", "Revenue Report", "Order Analytics"],
        "severity": "CRITICAL",
    },
    "silver.stg_customers": {
        "direct": ["gold.dim_customer"],
        "indirect": ["gold.fact_sales"],
        "affected_reports": ["Customer Analytics", "Segmentation Report"],
        "severity": "HIGH",
    },
    "gold.fact_sales": {
        "direct": [],
        "indirect": [],
        "affected_reports": ["Sales Dashboard", "Revenue Report", "Executive KPIs"],
        "severity": "CRITICAL",
    },
}

impact = impact_map.get(selected_table, {})

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"**Directly Dependent:** {', '.join(impact.get('direct', [])) or 'None'}")
    st.markdown(f"**Indirectly Dependent:** {', '.join(impact.get('indirect', [])) or 'None'}")

with col2:
    severity = impact.get("severity", "UNKNOWN")
    color = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")
    st.markdown(f"**Severity:** {color} {severity}")
    st.markdown(f"**Affected Reports:** {', '.join(impact.get('affected_reports', []))}")


st.markdown("---")
st.caption("Lineage derived from dbt manifest and data contracts")
