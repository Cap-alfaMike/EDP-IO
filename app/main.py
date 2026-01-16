# ============================================================================
# EDP-IO - Streamlit Dashboard Main Application
# ============================================================================
"""
Executive-friendly dashboard for the EDP-IO platform.

DESIGN PHILOSOPHY:
-----------------
1. Executive Language: Avoid technical jargon, focus on business value
2. At-a-Glance: Key metrics immediately visible
3. Drill-Down: Details available on demand
4. Mobile-Friendly: Responsive layout

PAGES:
- Home: Executive summary with KPIs
- Pipeline Status: Health of data pipelines
- Data Quality: Quality metrics and trends
- Data Lineage: Visual data flow
- Ask the Architect: LLM-powered Q&A

MOCK DATA:
When real data is unavailable, displays realistic mock values.
"""

import random
from datetime import datetime, timedelta

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="EDP-IO | Data Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize dark mode state
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Custom CSS for executive styling
st.markdown(
    """
<style>
    /* Executive color palette */
    :root {
        --primary: #1e3a5f;
        --secondary: #3498db;
        --success: #27ae60;
        --warning: #f39c12;
        --danger: #e74c3c;
        --background: #f8f9fa;
    }
    
    /* Clean, professional look */
    .main {
        background-color: var(--background);
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .metric-value {
        font-size: 2.5em;
        font-weight: bold;
        color: var(--primary);
    }
    
    .metric-label {
        font-size: 0.9em;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Status indicators */
    .status-healthy {
        color: var(--success);
    }
    
    .status-warning {
        color: var(--warning);
    }
    
    .status-error {
        color: var(--danger);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: var(--primary);
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)


def get_mock_metrics():
    """Generate realistic mock metrics for demo."""
    random.seed(42)  # Consistent values

    return {
        "total_records": 2_847_293,
        "tables_monitored": 12,
        "pipelines_healthy": 11,
        "pipelines_total": 12,
        "data_freshness_hours": 1.5,
        "quality_score": 98.7,
        "alerts_open": 2,
        "last_run": datetime.now() - timedelta(minutes=15),
    }


def render_header():
    """Render the main header."""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("📊 EDP-IO Data Platform")
        st.caption("Enterprise Data Platform with Intelligent Observability")

    with col2:
        st.markdown(
            f"""
        <div style="text-align: right; padding: 10px;">
            <small style="color: #666;">Last updated</small><br>
            <strong>{datetime.now().strftime('%Y-%m-%d %H:%M')}</strong>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_kpi_cards(metrics):
    """Render executive KPI cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📦 Total Records",
            value=f"{metrics['total_records']:,}",
            delta="+12,453 today",
        )

    with col2:
        health_pct = (metrics["pipelines_healthy"] / metrics["pipelines_total"]) * 100
        st.metric(
            label="🟢 Pipeline Health",
            value=f"{health_pct:.0f}%",
            delta=f"{metrics['pipelines_healthy']}/{metrics['pipelines_total']} healthy",
        )

    with col3:
        st.metric(
            label="✅ Data Quality Score",
            value=f"{metrics['quality_score']}%",
            delta="+0.2% vs last week",
        )

    with col4:
        freshness_status = "🟢" if metrics["data_freshness_hours"] < 2 else "🟡"
        st.metric(
            label=f"{freshness_status} Data Freshness",
            value=f"{metrics['data_freshness_hours']:.1f}h",
            delta="Within SLA",
        )


def render_pipeline_summary():
    """Render pipeline status summary."""
    st.subheader("📈 Pipeline Status")

    pipelines = [
        {
            "name": "Oracle Customers",
            "status": "✅ Healthy",
            "last_run": "15 min ago",
            "records": "1,247",
            "color": "green",
        },
        {
            "name": "Oracle Products",
            "status": "✅ Healthy",
            "last_run": "22 min ago",
            "records": "583",
            "color": "green",
        },
        {
            "name": "SQL Server Orders",
            "status": "⚠️ Warning",
            "last_run": "1h 30min ago",
            "records": "5,892",
            "color": "orange",
        },
        {
            "name": "SQL Server Order Items",
            "status": "✅ Healthy",
            "last_run": "1h 30min ago",
            "records": "18,234",
            "color": "green",
        },
        {
            "name": "dbt Silver Layer",
            "status": "✅ Healthy",
            "last_run": "45 min ago",
            "records": "-",
            "color": "green",
        },
        {
            "name": "dbt Gold Layer",
            "status": "✅ Healthy",
            "last_run": "45 min ago",
            "records": "-",
            "color": "green",
        },
    ]

    col1, col2 = st.columns(2)

    for i, pipeline in enumerate(pipelines):
        with col1 if i % 2 == 0 else col2:
            status_color = {"green": "🟢", "orange": "🟡", "red": "🔴"}.get(pipeline["color"], "⚪")
            st.markdown(
                f"""
            <div style="background: white; padding: 15px; border-radius: 8px; margin: 5px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{pipeline['name']}</strong><br>
                        <small style="color: #666;">Last run: {pipeline['last_run']}</small>
                    </div>
                    <div style="text-align: right;">
                        {status_color} {pipeline['status']}<br>
                        <small style="color: #666;">{pipeline['records']} records</small>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )


def render_alerts():
    """Render active alerts section."""
    st.subheader("🔔 Active Alerts")

    alerts = [
        {
            "severity": "⚠️",
            "title": "Schema Drift Detected",
            "description": "New column 'loyalty_points' in Oracle CRM customers table",
            "time": "2 hours ago",
            "action": "Update data contract",
        },
        {
            "severity": "ℹ️",
            "title": "Slow Pipeline",
            "description": "SQL Server Orders ingestion took 45 min (SLA: 30 min)",
            "time": "1.5 hours ago",
            "action": "Review query performance",
        },
    ]

    for alert in alerts:
        with st.expander(f"{alert['severity']} {alert['title']} — {alert['time']}"):
            st.write(alert["description"])
            st.button(f"🔧 {alert['action']}", key=f"btn_{alert['title']}")


def render_business_impact():
    """Render business impact summary."""
    st.subheader("💼 Business Impact")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
        **Revenue Tracked**
        <h2 style="color: #27ae60;">R$ 2.4M</h2>
        <small>Today's orders processed</small>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        **Customers Updated**
        <h2 style="color: #3498db;">1,247</h2>
        <small>Profile updates synced</small>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        **Reports Generated**
        <h2 style="color: #9b59b6;">42</h2>
        <small>BI reports refreshed</small>
        """,
            unsafe_allow_html=True,
        )


def main():
    """Main application entry point."""
    # Sidebar navigation
    st.sidebar.title("Navigation")
    st.sidebar.markdown("---")

    # Dark mode toggle in sidebar
    st.sidebar.markdown("**⚙️ Settings:**")
    if st.sidebar.button("🌙 Toggle Dark Mode", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 Pages:**")
    st.sidebar.page_link("pages/1_pipeline_status.py", label="Pipeline Status")
    st.sidebar.page_link("pages/2_data_quality.py", label="Data Quality")
    st.sidebar.page_link("pages/3_lineage.py", label="Data Lineage")
    st.sidebar.page_link("pages/4_ask_architect.py", label="Ask the Architect")

    st.sidebar.markdown("---")
    st.sidebar.caption("EDP-IO v1.0.0 | Mock Production")

    # Main content
    render_header()

    st.markdown("---")

    # Get metrics
    metrics = get_mock_metrics()

    # KPI Cards
    render_kpi_cards(metrics)

    st.markdown("---")

    # Two-column layout for main content
    col1, col2 = st.columns([2, 1])

    with col1:
        render_pipeline_summary()

    with col2:
        render_alerts()
        render_business_impact()

    # Footer
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; color: #666; font-size: 0.9em;">
        <strong>EDP-IO</strong> — Enterprise Data Platform with Intelligent Observability<br>
        <small>This is a mock production demo. No real data is being processed.</small>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
