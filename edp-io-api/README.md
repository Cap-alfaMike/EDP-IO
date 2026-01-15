# README for EDP-IO REST API

## Overview

This is a Java/Spring Boot REST API implementation of the EDP-IO (Enterprise Data Platform with Intelligent Observability) dashboard.

The API mirrors the Streamlit dashboard functionality, providing programmatic access to:
- **Platform Metrics**: KPIs, pipeline health, data quality scores
- **Pipeline Management**: Status monitoring, execution history, manual triggers
- **Data Quality**: Quality metrics per table, dbt test results
- **Observability**: Active alerts, schema drift detection, data lineage
- **Ask the Architect**: LLM-powered chatbot for Q&A about data architecture

## Architecture

```
┌─────────────────┐
│  REST API       │  (Spring Boot 3.3.1, Java 17)
│  Controllers    │
├─────────────────┤
│  Services       │  (Business Logic)
├─────────────────┤
│  Providers      │  (External Integrations)
│  - LLM (Azure OpenAI)
│  - Databricks SQL
│  - Azure KeyVault
└─────────────────┘
```

## API Endpoints

### Metrics
- `GET /api/metrics` - Platform KPIs (records, pipeline health, quality score, freshness)

### Pipelines
- `GET /api/pipelines` - All pipeline statuses
- `GET /api/pipelines/{name}` - Specific pipeline status
- `POST /api/pipelines/{name}/trigger` - Manually trigger pipeline execution
- `GET /api/pipelines/{name}/history` - Pipeline execution history

### Data Quality
- `GET /api/data-quality` - Quality metrics for all tables
- `GET /api/data-quality/{table}` - Quality metrics for specific table
- `POST /api/data-quality/{table}/test` - Execute dbt quality tests

### Observability
- `GET /api/alerts` - Active alerts from monitoring
- `GET /api/schema-drift/{table}` - Detect schema changes
- `GET /api/lineage/{table}` - Data lineage (upstream/downstream dependencies)

### Chat (Ask the Architect)
- `POST /api/chat` - LLM-powered Q&A about data platform

## Configuration

Environment variables (or `application.properties`):

```properties
# Azure
AZURE_KEYVAULT_ENDPOINT=https://your-vault.vault.azure.net/
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Databricks
DATABRICKS_HOST=your-workspace.azuredatabricks.net
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=your-pat-token

# LLM Provider
LLM_PROVIDER=azure  # Options: azure, vertex, bedrock, mock
```

## Building and Running

### Prerequisites
- Java 17+
- Maven 3.8+

### Build
```bash
mvn clean package
```

### Run
```bash
java -jar target/edp-io-api-1.0.0.jar
```

Or with Maven:
```bash
mvn spring-boot:run
```

### Development
```bash
mvn spring-boot:run -Dspring-boot.run.arguments="--spring.profiles.active=dev"
```

## API Documentation

Once running, access the interactive API docs at:
- Swagger UI: http://localhost:8080/swagger-ui.html
- OpenAPI JSON: http://localhost:8080/v3/api-docs

## Testing

Run unit tests:
```bash
mvn test
```

Run integration tests:
```bash
mvn verify
```

## Key Components

### Controllers
- `MetricsController`: Platform metrics endpoints
- `PipelineController`: Pipeline status and orchestration
- `DataQualityController`: Data quality metrics and testing
- `ObservabilityController`: Alerts, schema drift, lineage
- `ChatController`: LLM-powered chatbot

### Services
- `MetricsService`: Queries Databricks for KPIs
- `PipelineService`: Manages pipeline status and Airflow integration
- `DataQualityService`: Data quality metrics and dbt test integration
- `ObservabilityService`: Alerts, schema drift detection, lineage analysis
- `ChatService`: LLM chat interactions

### Providers
- `LLMProvider`: Azure OpenAI, Vertex AI, Bedrock, Mock
- `DatabricksProvider`: SQL queries against Databricks
- `KeyVaultProvider`: Secure secret management

## Integration Points

### Azure OpenAI
- Used by ChatService for "Ask the Architect" Q&A
- Configurable deployment (default: gpt-4)
- Supports schema drift impact assessment via LLM

### Databricks SQL
- Executes queries against Unity Catalog
- Powers metrics, data quality, pipeline status
- Uses credentials from KeyVault in production

### Azure KeyVault
- Stores API keys, tokens, and sensitive configuration
- Fallback to environment variables if KeyVault unavailable

### Airflow (via REST API)
- Trigger pipeline execution
- Query execution history
- Monitor DAG status (in production implementation)

## Development Notes

### Mock Data
When external services are unavailable, the API returns mock data matching production response format.

### Error Handling
- All endpoints include try-catch with appropriate HTTP status codes
- Detailed error messages in responses
- Logging at DEBUG level for troubleshooting

### Thread Safety
All services are stateless and thread-safe. Providers handle connection pooling.

## Future Enhancements

1. **Authentication**: Add JWT/OAuth2 security
2. **Caching**: Implement Redis caching for frequently accessed metrics
3. **Database**: Add PostgreSQL for storing chat history
4. **Async**: Use @Async for long-running operations (trigger, tests)
5. **Monitoring**: Add Micrometer metrics for performance tracking
6. **Deployment**: Docker containerization and Kubernetes manifests

## License

MIT License - See LICENSE file

## Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Create Pull Request

## Contact

Data Engineering Team - https://github.com/Cap-alfaMike/EDP-IO
