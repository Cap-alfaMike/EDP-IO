# EDP-IO REST API Specification

## Overview

The EDP-IO REST API is a Spring Boot 3.3.1 (Java 17) microservice that provides programmatic access to all dashboard functionality. It mirrors the Python Streamlit dashboard endpoints with professional error handling, CORS support, and OpenAPI/Swagger documentation.

**Base URL**: `http://localhost:8080/api`  
**API Docs**: `http://localhost:8080/swagger-ui.html`  
**OpenAPI JSON**: `http://localhost:8080/v3/api-docs`

---

## API Endpoints Reference

### 1. METRICS ENDPOINT

#### Get Platform Metrics
```http
GET /api/metrics
```

**Response** (200 OK):
```json
{
  "totalRecords": 2847293,
  "tablesMonitored": 12,
  "pipelinesHealthy": 11,
  "pipelinesTotal": 12,
  "qualityScore": 98.7,
  "dataFreshnessHours": 1.5,
  "alertsOpen": 2,
  "lastUpdated": "2024-01-15T14:30:00Z"
}
```

**Business Logic**:
- Queries Databricks `gold.fact_sales` for total records
- Counts tables from `information_schema.columns`
- Aggregates pipeline health from Airflow metadata
- Calculates quality score from Great Expectations results
- Measures freshness as time since last successful ingestion

---

### 2. PIPELINE ENDPOINTS

#### List All Pipelines
```http
GET /api/pipelines
```

**Response** (200 OK):
```json
[
  {
    "pipelineName": "oracle_customers",
    "status": "HEALTHY",
    "lastRun": "15 min ago",
    "recordsProcessed": 1247,
    "errorCount": 0,
    "durationSeconds": 42.5
  },
  {
    "pipelineName": "sqlserver_orders",
    "status": "WARNING",
    "lastRun": "1h 30min ago",
    "recordsProcessed": 5892,
    "errorCount": 1,
    "durationSeconds": 95.7
  }
]
```

**Business Logic**:
- Queries Airflow metadata database for DAG runs
- Determines status from task states and error codes
- Calculates duration from start/end timestamps
- Tracks record counts from ingestion logs

#### Get Single Pipeline Status
```http
GET /api/pipelines/{name}
```

Example: `GET /api/pipelines/oracle_customers`

#### Trigger Pipeline Execution
```http
POST /api/pipelines/{name}/trigger
```

**Response** (200 OK):
```json
{
  "pipeline": "oracle_customers",
  "status": "TRIGGERED",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1705337400000
}
```

**Business Logic**:
- Calls Airflow REST API: `POST /api/v1/dags/{dag_id}/dagRuns`
- Returns unique run ID for tracking
- Initiates pipeline execution with current execution date

#### Get Pipeline Execution History
```http
GET /api/pipelines/{name}/history?limit=10
```

**Response** (200 OK):
```json
[
  {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "RUNNING",
    "start_time": 1705337400000,
    "end_time": 1705337540000,
    "duration_seconds": 140.5
  }
]
```

---

### 3. DATA QUALITY ENDPOINTS

#### Get Quality Metrics for All Tables
```http
GET /api/data-quality
```

**Response** (200 OK):
```json
{
  "tables": [
    {
      "tableName": "dim_customer",
      "qualityScore": 99.2,
      "rowCount": 45000,
      "columnCount": 12,
      "nullViolations": 0,
      "uniqueViolations": 0,
      "typeViolations": 0
    }
  ],
  "overall_score": 98.6,
  "last_validated": 1705337400000
}
```

**Business Logic**:
- Queries dbt test results from `observability.dbt_test_results`
- Runs Great Expectations validations for constraints
- Counts violations per column from quality check tables
- Computes overall score as weighted average

#### Get Quality Metrics for Specific Table
```http
GET /api/data-quality/{table}
```

Example: `GET /api/data-quality/dim_customer`

#### Run Quality Tests
```http
POST /api/data-quality/{table}/test
```

**Response** (200 OK):
```json
{
  "table": "dim_customer",
  "status": "PASSED",
  "tests_run": 12,
  "tests_passed": 12,
  "tests_failed": 0,
  "execution_time_ms": 2450
}
```

**Business Logic**:
- Executes `dbt test --select <table_name>`
- Parses dbt output for test results
- Returns pass/fail summary with execution time
- Updates quality metrics tables

---

### 4. OBSERVABILITY ENDPOINTS

#### Get Active Alerts
```http
GET /api/alerts
```

**Response** (200 OK):
```json
{
  "alerts": [
    {
      "severity": "WARNING",
      "title": "Schema Drift Detected",
      "description": "New column 'loyalty_points' in Oracle CRM customers table",
      "timestamp": "2 hours ago",
      "recommendedAction": "Update data contract"
    }
  ],
  "critical_count": 0,
  "warning_count": 1
}
```

**Business Logic**:
- Queries monitoring tables for recent failures/anomalies
- Analyzes logs with LLM for root cause and impact
- Generates recommended actions based on failure type
- Filters by severity level (INFO, WARNING, ERROR, CRITICAL)

#### Detect Schema Drift
```http
GET /api/schema-drift/{table}
```

Example: `GET /api/schema-drift/customers`

**Response** (200 OK):
```json
{
  "table": "customers",
  "status": "DRIFT_DETECTED",
  "changes": [
    "Column 'email' added",
    "Column 'phone' removed"
  ],
  "llm_assessment": "Impact: Medium. Affects: bronze.customers → silver.stg_customers → gold.dim_customer. Action: Update data contract and reload data."
}
```

**Business Logic**:
- Compares current schema with previous version
- Detects column additions, removals, type changes, nullable changes
- Uses LLM to assess business impact
- Recommends action (update contract, reload, notify stakeholders)

#### Get Data Lineage
```http
GET /api/lineage/{table}
```

Example: `GET /api/lineage/dim_customer`

**Response** (200 OK):
```json
{
  "table": "dim_customer",
  "upstream": [
    "oracle.customers",
    "sql_server.orders"
  ],
  "downstream": [
    "gold.fact_sales",
    "power_bi.customer_dashboard"
  ]
}
```

**Business Logic**:
- Queries dbt manifest for model dependencies
- Traces upstream sources and downstream consumers
- Used for impact analysis when tables change
- Supports "what if this table fails?" scenarios

---

### 5. CHAT ENDPOINT (Ask the Architect)

#### Ask the Architect
```http
POST /api/chat
Content-Type: application/json

{
  "message": "Why did the Oracle ingestion fail?"
}
```

**Response** (200 OK):
```json
{
  "response": "Based on the recent logs, the root cause is schema drift detected in Oracle CRM. New column 'loyalty_points' was added without prior notification. Recommended action: Update data contract in contracts.yaml and trigger reprocessing.",
  "model": "azure/gpt-4",
  "input_tokens": 100,
  "output_tokens": 50,
  "latency_ms": 250.5
}
```

**Business Logic**:
- Builds message context with system prompt
- Calls Azure OpenAI (or configured LLM provider)
- Processes questions about:
  - Pipeline troubleshooting (error analysis)
  - Data model documentation (SCD Type 2, grain, lineage)
  - Architecture questions (Bronze/Silver/Gold layers)
  - Data quality insights
- Advisory mode only - never executes commands
- Returns token usage for cost tracking

**Supported Question Types**:
- "Why did [pipeline] fail?" → Error analysis with root cause
- "Explain SCD Type 2" → Documentation with examples
- "What's the grain of fact_sales?" → Data model documentation
- "What's affected if [table] fails?" → Impact analysis with lineage

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (missing parameters, invalid JSON) |
| 404 | Resource not found (pipeline, table, etc.) |
| 500 | Server error (external service failure) |

**Error Response Format**:
```json
{
  "error": "Failed to process request: Connection to Databricks timed out"
}
```

---

## Integration Points

### Azure OpenAI
Used by ChatService for "Ask the Architect" functionality.

**Configuration**:
```properties
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### Databricks SQL
Executes queries against Unity Catalog for metrics, quality, pipeline status.

**Configuration**:
```properties
DATABRICKS_HOST=your-workspace.azuredatabricks.net
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=your-pat-token
```

### Airflow
Orchestrates pipelines and provides execution metadata.

**Configuration**:
```properties
AIRFLOW_WEBSERVER_HOST=airflow.example.com
AIRFLOW_WEBSERVER_PORT=8080
AIRFLOW_AUTH_TOKEN=your-token
```

### Azure KeyVault
Stores and retrieves sensitive secrets (API keys, tokens, connection strings).

**Configuration**:
```properties
AZURE_KEYVAULT_ENDPOINT=https://your-vault.vault.azure.net/
```

---

## Mock Data Fallback

When external services are unavailable, the API returns realistic mock data:

- **Metrics**: 2.8M records, 12 tables, 11/12 pipelines healthy, 98.7% quality
- **Pipelines**: 6 pipelines with various statuses (HEALTHY, WARNING)
- **Alerts**: 2 active alerts (schema drift, slow pipeline)
- **Data Quality**: 3 tables with detailed metrics
- **Schema Drift**: Detected changes and LLM assessment
- **Lineage**: Upstream and downstream dependencies
- **Chat**: Context-aware LLM responses (error analysis, documentation, SCD Type 2, etc.)

This allows development and testing without requiring access to production systems.

---

## Building and Running

### Requirements
- Java 17+
- Maven 3.8+

### Build
```bash
cd edp-io-api
mvn clean package
```

### Run
```bash
java -jar target/edp-io-api-1.0.0.jar
```

The API will start on `http://localhost:8080`

### Development
```bash
mvn spring-boot:run -Dspring-boot.run.arguments="--server.port=8080 --logging.level.com.edpio=DEBUG"
```

---

## Architecture Diagram

```
┌──────────────────────────────────────┐
│       REST Controllers (5)           │
│ - MetricsController                  │
│ - PipelineController                 │
│ - DataQualityController              │
│ - ObservabilityController            │
│ - ChatController                     │
└──────────┬───────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│       Services (5)                   │
│ - MetricsService                     │
│ - PipelineService                    │
│ - DataQualityService                 │
│ - ObservabilityService               │
│ - ChatService                        │
└──────────┬───────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│       Providers (3)                  │
│ - LLMProvider                        │
│ - DatabricksProvider                 │
│ - KeyVaultProvider                   │
└──────────┬───────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│   External Integrations              │
│ - Azure OpenAI (LLM)                 │
│ - Databricks SQL (Data Lake)         │
│ - Azure KeyVault (Secrets)           │
│ - Airflow REST API (Orchestration)   │
│ - Great Expectations (Quality)       │
│ - dbt (Transformation)               │
└──────────────────────────────────────┘
```

---

## Next Steps

1. **Configure Azure/Databricks credentials** in `application.properties`
2. **Build and run** with `mvn spring-boot:run`
3. **Test endpoints** via Swagger UI at `http://localhost:8080/swagger-ui.html`
4. **Integrate** with frontend applications (React, Angular, Vue)
5. **Deploy** to production (Azure Container Instances, AKS, etc.)

---

**Version**: 1.0.0  
**Last Updated**: January 15, 2026  
**Repository**: https://github.com/Cap-alfaMike/EDP-IO
