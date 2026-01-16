# ============================================================================
# EDP-IO - Ask the Data Architect
# ============================================================================
"""
LLM-powered chatbot for data platform Q&A.

Uses the observability LLM to answer questions about:
- Pipeline errors and troubleshooting
- Data model documentation
- Best practices and architecture
- Schema and lineage questions

SAFETY:
- LLM is advisory only
- No execution of commands
- References documentation and logs
"""

import json
from datetime import datetime

import streamlit as st

# Try to import observability modules
try:
    from src.observability.doc_generator import DocGenerator
    from src.observability.log_analyzer import LogAnalyzer
    from src.utils.config import get_settings

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


st.set_page_config(
    page_title="Ask the Architect | EDP-IO",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Ask the Data Architect")
st.caption("Your AI assistant for data platform questions")


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": """👋 Hello! I'm your Data Architect assistant.

I can help you with:
- 🔧 **Troubleshooting** pipeline errors
- 📖 **Documentation** about data models
- 🏗️ **Architecture** questions
- 📊 **Data quality** insights

What would you like to know?""",
        }
    ]


# Sidebar with context options
st.sidebar.subheader("Context")
context_mode = st.sidebar.radio(
    "Mode",
    ["General Q&A", "Error Analysis", "Documentation"],
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
**Sample Questions:**
- Why did the Oracle ingestion fail?
- Explain the SCD Type 2 implementation
- What tables are affected if customers fails?
- How is customer segment calculated?
- What's the grain of fact_sales?
"""
)

st.sidebar.markdown("---")
st.sidebar.caption(
    """
⚠️ **Advisory Only Mode**

This assistant provides suggestions and documentation. 
It does not execute commands or modify data.
All recommendations require human approval.
"""
)


def get_mock_response(question: str) -> str:
    """Generate contextual mock responses."""
    q_lower = question.lower()

    # Error/troubleshooting questions
    if any(word in q_lower for word in ["error", "fail", "issue", "problem", "why"]):
        return """Based on the recent logs, here's my analysis:

**Issue Identified:** Schema drift detected in Oracle CRM source

**Root Cause:**
A new column `loyalty_points` was added to the CRM.CUSTOMERS table in the source system without prior notification.

**Impact:**
- 🟡 Medium severity
- Affects: `bronze.customers` → `silver.stg_customers` → `gold.dim_customer`
- Pipeline is still running but new column is not being captured

**Recommended Actions:**
1. Review the new column with CRM team
2. Update data contract in `contracts.yaml`
3. Add column to Bronze schema
4. Schedule reprocessing of affected data

⚠️ *These are suggestions only. Please review and approve before taking action.*

Would you like me to generate the updated data contract?"""

    # Documentation questions
    elif any(
        word in q_lower for word in ["explain", "what is", "how does", "documentation", "describe"]
    ):
        if "scd" in q_lower or "type 2" in q_lower:
            return """**SCD Type 2 Implementation in EDP-IO**

SCD Type 2 (Slowly Changing Dimension Type 2) tracks historical changes by creating new records.

**How it works in our Silver layer:**

1. **Change Detection:**
   - We hash tracked columns (name, email, segment, etc.)
   - Compare incoming data hash with current record hash
   - If different → change detected

2. **Record Management:**
   - Old record: `valid_to` = current timestamp, `is_current` = false
   - New record: `valid_from` = current timestamp, `is_current` = true

3. **Key Fields:**
   | Field | Purpose |
   |-------|---------|
   | `surrogate_key` | Unique ID for each version |
   | `valid_from` | When this version became active |
   | `valid_to` | When superseded (9999-12-31 if current) |
   | `is_current` | Fast filter for current state |

**Example Query - Point in Time:**
```sql
SELECT * FROM silver.stg_customers
WHERE customer_id = 'CUST-001'
  AND '2024-06-15' BETWEEN valid_from AND valid_to
```

**Trade-offs:**
- ✅ Full history preserved
- ✅ Point-in-time queries possible
- ⚠️ Increased storage
- ⚠️ More complex joins (use `is_current` for simplicity)"""

        elif "fact_sales" in q_lower or "grain" in q_lower:
            return """**fact_sales Documentation**

**Grain:** One row per order line item (product sold in an order)

**Dimensions:**
- `dim_customer_key` → dim_customer
- `dim_product_key` → dim_product  
- `dim_date_key` → dim_date

**Measures (Additive):**
| Measure | Description | Aggregation |
|---------|-------------|-------------|
| `units_sold` | Quantity ordered | SUM |
| `gross_revenue` | Before discounts | SUM |
| `discount_amount` | Total discount | SUM |
| `net_revenue` | After discounts | SUM |
| `cost_of_goods_sold` | Product cost | SUM |
| `gross_profit` | Revenue - COGS | SUM |

**Business Purpose:**
Central source of truth for retail analytics including:
- Revenue analysis
- Profitability by product/customer
- Discount effectiveness
- Category performance

**Example - Revenue by Segment:**
```sql
SELECT 
    c.customer_segment,
    SUM(f.net_revenue) as revenue
FROM gold.fact_sales f
JOIN gold.dim_customer c 
    ON f.dim_customer_key = c.dim_customer_key
WHERE d.is_current_year = true
GROUP BY 1
ORDER BY 2 DESC
```"""

        else:
            return f"""I'll help you understand that! Here's what I know:

**{question}**

The EDP-IO platform uses a Lakehouse architecture with three layers:

1. **Bronze Layer:** Raw data from source systems
   - Minimal transformation
   - Schema enforcement
   - Idempotent ingestion

2. **Silver Layer:** Cleaned and historized
   - SCD Type 2 for dimensions
   - Data quality validation
   - Business key standardization

3. **Gold Layer:** Analytics-ready
   - Star schema design
   - Conformed dimensions
   - Fact tables with measures

Would you like more details on any specific component?"""

    # Lineage/impact questions
    elif any(word in q_lower for word in ["affect", "impact", "depend", "lineage", "downstream"]):
        return """**Impact Analysis**

If `bronze.customers` fails, here's the cascade:

```
bronze.customers ❌
    └── silver.stg_customers ⚠️ (blocked)
        └── gold.dim_customer ⚠️ (stale)
            └── gold.fact_sales ⚠️ (customer dim stale)
                └── Power BI Dashboards 📊 (affected)
```

**Affected Reports:**
- Customer Analytics Dashboard
- Sales by Segment Report
- Customer Lifetime Value

**Mitigation:**
- Gold layer will continue with stale dimension data
- Reports will show last known customer attributes
- SLA: 24 hours before business impact

Would you like me to analyze a specific failure scenario?"""

    # Default response
    else:
        return f"""Thanks for your question!

**"{question}"**

I'm here to help with:
- Pipeline troubleshooting
- Data model documentation  
- Architecture questions
- Quality insights

Could you provide more context or rephrase your question? 

For example:
- "Why did the Oracle ingestion fail yesterday?"
- "Explain how dim_customer is built"
- "What's the impact if orders table is delayed?"

I'll do my best to provide relevant information!"""


# Chat interface
st.markdown("---")

# Display existing messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input for new message
if prompt := st.chat_input("Ask me anything about the data platform..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = get_mock_response(prompt)
        st.markdown(response)

    # Add assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})


# Clear chat button
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()


st.markdown("---")
st.caption(
    """
🔒 **Privacy Note:** This assistant uses Azure OpenAI in advisory mode. 
No sensitive data is sent to external services. All analysis is based on 
metadata and logs only.
"""
)
