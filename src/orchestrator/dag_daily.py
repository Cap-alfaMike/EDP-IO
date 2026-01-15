# ============================================================================
# EDP-IO - Pipeline Orchestrator (Airflow DAG)
# ============================================================================
"""
Apache Airflow DAG for orchestrating the EDP-IO data pipeline.

DESIGN DECISIONS:
-----------------
1. Why Airflow over Azure Data Factory?
   - Open source, portable to GCP/AWS
   - Python-native, same as ingestion code
   - Better observability and debugging
   - Can run locally for development

2. DAG Structure:
   - Parallel ingestion from Oracle and SQL Server
   - Sequential dbt layers: Bronze → Silver → Gold
   - LLM observability runs after dbt (for doc generation)
   - Notifications on failure

3. Idempotency:
   - Each task uses execution_date for partitioning
   - Safe to re-run any failed task
   - Backfill supported

PRODUCTION NOTES:
- In production, deploy on Azure Kubernetes Service (AKS)
- Use Airflow connections for secrets (backed by Key Vault)
- Enable PagerDuty/Slack alerts on failure
"""

from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
from airflow.models import Variable

# ============================================================================
# DAG Configuration
# ============================================================================

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email": ["data-platform@enterprise.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

# ============================================================================
# Task Functions
# ============================================================================

def ingest_oracle_customers(**context) -> dict[str, Any]:
    """Ingest customers from Oracle ERP."""
    from src.ingestion.oracle_ingest import OracleIngestion
    from src.utils.config import get_settings
    
    settings = get_settings()
    execution_date = context["execution_date"]
    
    # In production, this would use real Spark
    # For mock, use local generator
    if not settings.enable_real_database_connections:
        from src.ingestion.mock_data import RetailMockDataGenerator
        generator = RetailMockDataGenerator(seed=42)
        customers = generator.generate_customers(1000)
        return {"records": len(customers), "table": "customers"}
    
    ingestion = OracleIngestion()
    result = ingestion.ingest_customers(watermark=execution_date)
    return result


def ingest_oracle_products(**context) -> dict[str, Any]:
    """Ingest products from Oracle ERP."""
    from src.ingestion.oracle_ingest import OracleIngestion
    from src.utils.config import get_settings
    
    settings = get_settings()
    
    if not settings.enable_real_database_connections:
        from src.ingestion.mock_data import RetailMockDataGenerator
        generator = RetailMockDataGenerator(seed=42)
        products = generator.generate_products(500)
        return {"records": len(products), "table": "products"}
    
    ingestion = OracleIngestion()
    return ingestion.ingest_products()


def ingest_sqlserver_orders(**context) -> dict[str, Any]:
    """Ingest orders from SQL Server."""
    from src.ingestion.sqlserver_ingest import SQLServerIngestion
    from src.utils.config import get_settings
    
    settings = get_settings()
    execution_date = context["execution_date"]
    
    if not settings.enable_real_database_connections:
        from src.ingestion.mock_data import RetailMockDataGenerator
        generator = RetailMockDataGenerator(seed=42)
        customers = generator.generate_customers(100)
        products = generator.generate_products(50)
        orders, items = generator.generate_orders(
            500, 
            [c["customer_id"] for c in customers],
            [p["product_id"] for p in products]
        )
        return {"orders": len(orders), "order_items": len(items)}
    
    ingestion = SQLServerIngestion()
    return ingestion.ingest_all(watermark=execution_date)


def run_dbt_silver(**context) -> dict[str, Any]:
    """Run dbt Silver layer models."""
    import subprocess
    
    result = subprocess.run(
        ["dbt", "run", "--select", "tag:silver", "--profiles-dir", "."],
        cwd="dbt_project",
        capture_output=True,
        text=True,
        timeout=1800,  # 30 minutes
    )
    
    return {
        "return_code": result.returncode,
        "stdout": result.stdout[-1000:],  # Last 1000 chars
        "success": result.returncode == 0,
    }


def run_dbt_gold(**context) -> dict[str, Any]:
    """Run dbt Gold layer models."""
    import subprocess
    
    result = subprocess.run(
        ["dbt", "run", "--select", "tag:gold", "--profiles-dir", "."],
        cwd="dbt_project",
        capture_output=True,
        text=True,
        timeout=1800,
    )
    
    return {
        "return_code": result.returncode,
        "stdout": result.stdout[-1000:],
        "success": result.returncode == 0,
    }


def run_dbt_tests(**context) -> dict[str, Any]:
    """Run dbt tests for data quality."""
    import subprocess
    
    result = subprocess.run(
        ["dbt", "test", "--profiles-dir", "."],
        cwd="dbt_project",
        capture_output=True,
        text=True,
        timeout=900,
    )
    
    return {
        "return_code": result.returncode,
        "tests_passed": "PASS" in result.stdout,
        "success": result.returncode == 0,
    }


def generate_documentation(**context) -> dict[str, Any]:
    """Generate dbt documentation using LLM."""
    from src.observability.doc_generator import DocGenerator
    
    generator = DocGenerator()
    docs = generator.generate_all()
    
    # Export to markdown
    output_path = generator.export_markdown(docs, "docs/models.md")
    
    return {
        "models_documented": len(docs),
        "output_path": output_path,
    }


def notify_success(**context) -> None:
    """Send success notification."""
    # In production: Slack/Teams webhook
    print(f"Pipeline completed successfully at {datetime.now()}")


def notify_failure(context) -> None:
    """Send failure notification with LLM analysis."""
    from src.observability.log_analyzer import LogAnalyzer
    
    # Get error from context
    exception = context.get("exception", "Unknown error")
    task_id = context.get("task_instance").task_id
    
    # Analyze with LLM
    analyzer = LogAnalyzer()
    analysis = analyzer.analyze(str(exception), context={"task": task_id})
    
    # In production: Send to Slack/PagerDuty
    print(f"Pipeline failed: {task_id}")
    print(f"LLM Analysis: {analysis.recommended_action}")


# ============================================================================
# DAG Definition
# ============================================================================

with DAG(
    dag_id="edp_io_daily_pipeline",
    default_args=default_args,
    description="EDP-IO Daily Data Pipeline",
    schedule_interval="0 6 * * *",  # 06:00 UTC daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["edp-io", "data-platform", "retail"],
    on_failure_callback=notify_failure,
) as dag:
    
    # Start
    start = EmptyOperator(task_id="start")
    
    # -------------------------------------------------------------------------
    # INGESTION LAYER (Parallel)
    # -------------------------------------------------------------------------
    with TaskGroup("ingestion") as ingestion_group:
        
        # Oracle sources (parallel)
        with TaskGroup("oracle") as oracle_group:
            oracle_customers = PythonOperator(
                task_id="customers",
                python_callable=ingest_oracle_customers,
            )
            
            oracle_products = PythonOperator(
                task_id="products",
                python_callable=ingest_oracle_products,
            )
            
            oracle_stores = PythonOperator(
                task_id="stores",
                python_callable=lambda: {"records": 50, "table": "stores"},
            )
        
        # SQL Server sources (parallel)
        with TaskGroup("sqlserver") as sqlserver_group:
            sqlserver_orders = PythonOperator(
                task_id="orders",
                python_callable=ingest_sqlserver_orders,
            )
    
    # -------------------------------------------------------------------------
    # DBT TRANSFORMATION (Sequential)
    # -------------------------------------------------------------------------
    with TaskGroup("dbt") as dbt_group:
        
        dbt_silver = PythonOperator(
            task_id="silver",
            python_callable=run_dbt_silver,
        )
        
        dbt_gold = PythonOperator(
            task_id="gold",
            python_callable=run_dbt_gold,
        )
        
        dbt_test = PythonOperator(
            task_id="test",
            python_callable=run_dbt_tests,
        )
        
        # Sequential: Silver → Gold → Test
        dbt_silver >> dbt_gold >> dbt_test
    
    # -------------------------------------------------------------------------
    # OBSERVABILITY (After dbt)
    # -------------------------------------------------------------------------
    with TaskGroup("observability") as observability_group:
        
        generate_docs = PythonOperator(
            task_id="generate_docs",
            python_callable=generate_documentation,
        )
    
    # End
    end = PythonOperator(
        task_id="notify_success",
        python_callable=notify_success,
    )
    
    # -------------------------------------------------------------------------
    # DAG Dependencies
    # -------------------------------------------------------------------------
    # 
    # start → [ingestion] → [dbt] → [observability] → end
    #
    start >> ingestion_group >> dbt_group >> observability_group >> end
