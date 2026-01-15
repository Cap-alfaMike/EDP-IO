# ============================================================================
# EDP-IO - Orchestrator Package
# ============================================================================
"""
Pipeline orchestration for EDP-IO.

ORCHESTRATION OPTIONS:
---------------------
1. Apache Airflow (this implementation) - Open source, portable
2. Azure Data Factory - Native Azure, simpler for basic workflows
3. Prefect/Dagster - Modern Python-first alternatives

DESIGN PHILOSOPHY:
-----------------
- Declarative DAGs for transparency
- Idempotent tasks for safe retries
- Parallel where possible, sequential where required
- Integrated observability (LLM analysis on failure)

PRODUCTION DEPLOYMENT:
---------------------
- Run on Azure Kubernetes Service (AKS)
- Or use managed Airflow (Cloud Composer, MWAA equivalent)
- Secrets via Airflow Connections backed by Key Vault
"""

# DAG is imported by Airflow directly from dag_daily.py
# This init exposes helper utilities

__all__ = [
    "get_dag_run_status",
    "trigger_dag_run",
]


def get_dag_run_status(dag_id: str, run_id: str) -> dict:
    """Get status of a DAG run (mock for demo)."""
    return {
        "dag_id": dag_id,
        "run_id": run_id,
        "state": "success",
        "execution_date": "2024-01-15T06:00:00Z",
    }


def trigger_dag_run(dag_id: str, conf: dict = None) -> dict:
    """Trigger a DAG run (mock for demo)."""
    return {
        "dag_id": dag_id,
        "run_id": f"manual__{dag_id}",
        "state": "queued",
    }
