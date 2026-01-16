# ============================================================================
# EDP-IO - LLM Observability Dashboard
# ============================================================================
"""
Streamlit page for monitoring LLM usage across the platform.

VISUALIZATIONS:
--------------
1. Summary KPIs: Total calls, tokens, cost, latency
2. Usage by Role: Which components use LLM most
3. Cost Trend: Daily cost over time
4. Confidence Distribution: Quality of LLM responses
5. RAG Context Usage: How much context is being retrieved
"""

import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="LLM Observability | EDP-IO",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 LLM Observability")
st.caption("Monitor AI usage, costs, and quality across the data platform")


# ============================================================================
# Mock Data Generation (for demo)
# ============================================================================


def generate_mock_llm_metrics():
    """Generate realistic mock LLM metrics for demo."""
    random.seed(42)

    roles = ["log_analyzer", "schema_drift", "doc_generator", "chatbot"]
    role_weights = [0.3, 0.15, 0.1, 0.45]  # Chatbot used most

    metrics = []
    now = datetime.now()

    for i in range(500):  # 500 calls over 30 days
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)

        role = random.choices(roles, role_weights)[0]

        # Role-specific patterns
        if role == "log_analyzer":
            input_tokens = random.randint(500, 1500)
            output_tokens = random.randint(200, 600)
            confidence = random.uniform(0.7, 0.95)
            latency = random.randint(800, 2000)
        elif role == "schema_drift":
            input_tokens = random.randint(300, 800)
            output_tokens = random.randint(150, 400)
            confidence = random.uniform(0.75, 0.98)
            latency = random.randint(600, 1500)
        elif role == "doc_generator":
            input_tokens = random.randint(1000, 3000)
            output_tokens = random.randint(500, 1500)
            confidence = random.uniform(0.8, 0.95)
            latency = random.randint(1500, 4000)
        else:  # chatbot
            input_tokens = random.randint(200, 1000)
            output_tokens = random.randint(100, 500)
            confidence = random.uniform(0.6, 0.9)
            latency = random.randint(500, 1800)

        total_tokens = input_tokens + output_tokens
        cost = (input_tokens / 1000) * 0.01 + (output_tokens / 1000) * 0.03

        metrics.append(
            {
                "timestamp": now - timedelta(days=days_ago, hours=hours_ago),
                "role": role,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "latency_ms": latency,
                "cost_usd": cost,
                "confidence": confidence,
                "success": random.random() > 0.02,  # 98% success rate
                "rag_chunks": random.randint(0, 5),
                "human_approved": random.random() > 0.1 if random.random() > 0.3 else None,
            }
        )

    return pd.DataFrame(metrics)


@st.cache_data(ttl=300)
def load_llm_metrics():
    """Load LLM metrics (mock for demo)."""
    return generate_mock_llm_metrics()


# Load data
df = load_llm_metrics()

# Time filter
st.sidebar.subheader("Time Range")
days_options = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}
selected_days = st.sidebar.selectbox("Period", list(days_options.keys()))
days = days_options[selected_days]

# Filter data
cutoff = datetime.now() - timedelta(days=days)
df_filtered = df[df["timestamp"] >= cutoff]


# ============================================================================
# SUMMARY KPIs
# ============================================================================

st.markdown("---")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_calls = len(df_filtered)
    st.metric(
        "Total LLM Calls",
        f"{total_calls:,}",
        f"+{len(df_filtered[df_filtered['timestamp'] >= datetime.now() - timedelta(days=1)])} today",
    )

with col2:
    total_tokens = df_filtered["total_tokens"].sum()
    st.metric(
        "Total Tokens",
        f"{total_tokens:,.0f}",
        f"~{total_tokens / total_calls:.0f}/call" if total_calls > 0 else "N/A",
    )

with col3:
    total_cost = df_filtered["cost_usd"].sum()
    daily_avg = total_cost / days if days > 0 else 0
    st.metric(
        "Total Cost",
        f"${total_cost:.2f}",
        f"${daily_avg:.2f}/day avg",
    )

with col4:
    avg_latency = df_filtered["latency_ms"].mean()
    st.metric(
        "Avg Latency",
        f"{avg_latency:.0f}ms",
        "⚡ Good" if avg_latency < 1500 else "🔄 Slow",
    )

with col5:
    success_rate = df_filtered["success"].mean() * 100
    st.metric(
        "Success Rate",
        f"{success_rate:.1f}%",
        "✅ Healthy" if success_rate > 95 else "⚠️ Review",
    )


st.markdown("---")


# ============================================================================
# USAGE BY ROLE
# ============================================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Usage by Role")

    role_stats = (
        df_filtered.groupby("role")
        .agg(
            {
                "total_tokens": ["count", "sum"],
                "cost_usd": "sum",
                "latency_ms": "mean",
                "confidence": "mean",
            }
        )
        .round(2)
    )

    role_stats.columns = ["Calls", "Tokens", "Cost ($)", "Avg Latency (ms)", "Avg Confidence"]
    role_stats = role_stats.reset_index()
    role_stats.columns = [
        "Role",
        "Calls",
        "Tokens",
        "Cost ($)",
        "Avg Latency (ms)",
        "Avg Confidence",
    ]

    # Role icons
    role_icons = {
        "log_analyzer": "🔍",
        "schema_drift": "📐",
        "doc_generator": "📝",
        "chatbot": "💬",
    }
    role_stats["Role"] = role_stats["Role"].apply(lambda x: f"{role_icons.get(x, '')} {x}")

    st.dataframe(role_stats, use_container_width=True, hide_index=True)

with col2:
    st.subheader("💰 Cost Distribution")

    cost_by_role = df_filtered.groupby("role")["cost_usd"].sum().reset_index()

    fig = px.pie(
        cost_by_role,
        values="cost_usd",
        names="role",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)


st.markdown("---")


# ============================================================================
# TRENDS
# ============================================================================

st.subheader("📈 Usage Trends")

tab1, tab2, tab3 = st.tabs(["Calls & Tokens", "Cost", "Latency"])

with tab1:
    daily = (
        df_filtered.groupby(df_filtered["timestamp"].dt.date)
        .agg(
            {
                "total_tokens": ["count", "sum"],
            }
        )
        .reset_index()
    )
    daily.columns = ["date", "calls", "tokens"]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily["date"], y=daily["calls"], name="Calls", marker_color="#3498db"))
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["tokens"] / 1000,
            name="Tokens (K)",
            yaxis="y2",
            marker_color="#e74c3c",
            mode="lines+markers",
        )
    )

    fig.update_layout(
        yaxis=dict(title="Calls"),
        yaxis2=dict(title="Tokens (K)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    daily_cost = (
        df_filtered.groupby(df_filtered["timestamp"].dt.date)["cost_usd"].sum().reset_index()
    )
    daily_cost.columns = ["date", "cost"]
    daily_cost["cumulative"] = daily_cost["cost"].cumsum()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily_cost["date"], y=daily_cost["cost"], name="Daily Cost", marker_color="#27ae60"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_cost["date"],
            y=daily_cost["cumulative"],
            name="Cumulative",
            yaxis="y2",
            marker_color="#9b59b6",
            mode="lines",
        )
    )

    fig.update_layout(
        yaxis=dict(title="Daily Cost ($)"),
        yaxis2=dict(title="Cumulative ($)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    hourly = df_filtered.copy()
    hourly["hour"] = hourly["timestamp"].dt.hour
    latency_by_hour = hourly.groupby("hour")["latency_ms"].mean().reset_index()

    fig = px.line(
        latency_by_hour,
        x="hour",
        y="latency_ms",
        markers=True,
        labels={"hour": "Hour of Day", "latency_ms": "Avg Latency (ms)"},
    )
    fig.add_hline(y=1500, line_dash="dash", line_color="red", annotation_text="SLA: 1500ms")
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)


st.markdown("---")


# ============================================================================
# QUALITY METRICS
# ============================================================================

st.subheader("✅ Quality & Confidence")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Confidence Score Distribution**")

    fig = px.histogram(
        df_filtered,
        x="confidence",
        nbins=20,
        color="role",
        labels={"confidence": "Confidence Score", "count": "Frequency"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("**Confidence by Role**")

    conf_by_role = (
        df_filtered.groupby("role")["confidence"].agg(["mean", "min", "max"]).reset_index()
    )
    conf_by_role.columns = ["Role", "Avg", "Min", "Max"]

    fig = go.Figure()
    for _, row in conf_by_role.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row["Role"], row["Role"], row["Role"]],
                y=[row["Min"], row["Avg"], row["Max"]],
                mode="lines+markers",
                name=row["Role"],
                marker=dict(size=[8, 14, 8]),
            )
        )

    fig.update_layout(
        yaxis=dict(title="Confidence Score", range=[0.5, 1.0]),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


st.markdown("---")


# ============================================================================
# RAG CONTEXT USAGE
# ============================================================================

st.subheader("📚 RAG Context Usage")

col1, col2, col3 = st.columns(3)

with col1:
    avg_chunks = df_filtered["rag_chunks"].mean()
    st.metric("Avg RAG Chunks Retrieved", f"{avg_chunks:.1f}")

with col2:
    calls_with_rag = (df_filtered["rag_chunks"] > 0).sum()
    pct_with_rag = calls_with_rag / len(df_filtered) * 100
    st.metric("Calls Using RAG", f"{pct_with_rag:.0f}%")

with col3:
    # Correlation between RAG usage and confidence
    with_rag = df_filtered[df_filtered["rag_chunks"] > 0]["confidence"].mean()
    without_rag = df_filtered[df_filtered["rag_chunks"] == 0]["confidence"].mean()
    improvement = ((with_rag - without_rag) / without_rag * 100) if without_rag else 0
    st.metric("Confidence with RAG", f"{with_rag:.0%}", f"+{improvement:.1f}% vs without")


# ============================================================================
# HUMAN APPROVAL TRACKING
# ============================================================================

st.markdown("---")
st.subheader("👤 Human Approval Tracking")

approval_df = df_filtered[df_filtered["human_approved"].notna()]

if len(approval_df) > 0:
    col1, col2 = st.columns(2)

    with col1:
        approved = approval_df["human_approved"].sum()
        total = len(approval_df)
        rate = approved / total * 100

        st.metric(
            "Approval Rate",
            f"{rate:.1f}%",
            f"{approved}/{total} approved",
        )

    with col2:
        by_role = approval_df.groupby("role")["human_approved"].mean().reset_index()
        by_role["approval_rate"] = by_role["human_approved"] * 100

        fig = px.bar(
            by_role,
            x="role",
            y="approval_rate",
            labels={"approval_rate": "Approval Rate (%)", "role": "Role"},
            color="approval_rate",
            color_continuous_scale="RdYlGn",
        )
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No human approval data recorded yet.")


st.markdown("---")
st.caption(f"Data period: {days} days | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
