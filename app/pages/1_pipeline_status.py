# ============================================================================
# EDP-IO - Pipeline Status Page
# ============================================================================
"""
Detailed pipeline monitoring for operations teams.

Shows:
- All pipeline runs with status
- Execution timeline
- Error details
- Retry controls (simulated)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random


st.set_page_config(
    page_title="Pipeline Status | EDP-IO",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Pipeline Status")
st.caption("Real-time monitoring of all data pipelines")


def get_pipeline_history():
    """Generate mock pipeline history."""
    random.seed(42)
    
    pipelines = [
        {"name": "oracle_customers", "source": "Oracle ERP", "target": "bronze.customers"},
        {"name": "oracle_products", "source": "Oracle ERP", "target": "bronze.products"},
        {"name": "oracle_stores", "source": "Oracle ERP", "target": "bronze.stores"},
        {"name": "sqlserver_orders", "source": "SQL Server", "target": "bronze.orders"},
        {"name": "sqlserver_order_items", "source": "SQL Server", "target": "bronze.order_items"},
        {"name": "dbt_silver", "source": "Bronze Layer", "target": "Silver Layer"},
        {"name": "dbt_gold", "source": "Silver Layer", "target": "Gold Layer"},
    ]
    
    history = []
    now = datetime.now()
    
    for i in range(24):  # Last 24 runs
        for p in pipelines:
            run_time = now - timedelta(hours=i)
            status = random.choices(
                ["Success", "Success", "Success", "Warning", "Failed"],
                weights=[0.85, 0.05, 0.05, 0.03, 0.02]
            )[0]
            
            duration = random.randint(1, 15) if "dbt" not in p["name"] else random.randint(5, 25)
            records = random.randint(100, 5000) if status == "Success" else 0
            
            history.append({
                "Pipeline": p["name"],
                "Source": p["source"],
                "Target": p["target"],
                "Status": status,
                "Start Time": run_time.strftime("%Y-%m-%d %H:%M"),
                "Duration (min)": duration,
                "Records": records,
            })
    
    return pd.DataFrame(history)


# Summary metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Pipelines Running", "7", "All active")

with col2:
    st.metric("Success Rate (24h)", "97.3%", "+1.2%")

with col3:
    st.metric("Avg Duration", "8.4 min", "-0.5 min")

with col4:
    st.metric("Records Processed", "47.2K", "+5.3K today")


st.markdown("---")


# Quick status by pipeline
st.subheader("Current Pipeline Health")

statuses = [
    ("Oracle Customers", "🟢 Healthy", "15 min ago", "1,247"),
    ("Oracle Products", "🟢 Healthy", "22 min ago", "583"),
    ("Oracle Stores", "🟢 Healthy", "45 min ago", "52"),
    ("SQL Server Orders", "🟡 Warning", "1h 30min ago", "5,892"),
    ("SQL Server Order Items", "🟢 Healthy", "1h 30min ago", "18,234"),
    ("dbt Silver", "🟢 Healthy", "45 min ago", "-"),
    ("dbt Gold", "🟢 Healthy", "45 min ago", "-"),
]

cols = st.columns(len(statuses))
for i, (name, status, last_run, records) in enumerate(statuses):
    with cols[i]:
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <strong style="font-size: 0.8em;">{name}</strong><br>
            <span style="font-size: 1.2em;">{status}</span><br>
            <small style="color: #666;">{last_run}</small>
        </div>
        """, unsafe_allow_html=True)


st.markdown("---")


# Detailed history table
st.subheader("Execution History")

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    status_filter = st.selectbox("Status", ["All", "Success", "Warning", "Failed"])
with col2:
    pipeline_filter = st.selectbox("Pipeline", ["All", "oracle_customers", "oracle_products", "sqlserver_orders", "dbt_silver", "dbt_gold"])
with col3:
    hours_filter = st.slider("Last N hours", 1, 24, 6)

# Load and filter data
df = get_pipeline_history()

if status_filter != "All":
    df = df[df["Status"] == status_filter]
if pipeline_filter != "All":
    df = df[df["Pipeline"] == pipeline_filter]

df = df.head(hours_filter * 7)  # Approximate records

# Color code status
def color_status(val):
    colors = {"Success": "green", "Warning": "orange", "Failed": "red"}
    return f'color: {colors.get(val, "black")}'

styled_df = df.style.applymap(color_status, subset=["Status"])
st.dataframe(styled_df, use_container_width=True, height=400)


st.markdown("---")


# Error details (if any failed)
st.subheader("Recent Errors")

errors = [
    {
        "pipeline": "sqlserver_orders",
        "time": "Today 14:23",
        "error": "Connection timeout after 30s",
        "suggestion": "Check SQL Server availability and network connectivity",
    }
]

for error in errors:
    with st.expander(f"❌ {error['pipeline']} — {error['time']}"):
        st.error(error['error'])
        st.info(f"💡 **Suggestion:** {error['suggestion']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.button("🔄 Retry", key=f"retry_{error['pipeline']}")
        with col2:
            st.button("🔍 View Logs", key=f"logs_{error['pipeline']}")


st.markdown("---")
st.caption("Last refreshed: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
