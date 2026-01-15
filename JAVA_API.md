# EDP-IO Java REST API

**Java/Spring Boot REST API for the EDP-IO platform**

This directory contains a production-ready REST API implementation that mirrors the Streamlit dashboard functionality, providing programmatic access to all platform features.

## 📋 Quick Links

- **Documentation**: [API_SPECIFICATION.md](./API_SPECIFICATION.md)
- **Readme**: [README.md](./README.md)
- **Quick Start**: [QUICKSTART.md](./QUICKSTART.md)

## 🚀 Quick Start

```bash
# Navigate to API directory
cd edp-io-api

# Build with Maven
mvn clean package

# Run the application
java -jar target/edp-io-api-1.0.0.jar

# Access API
# Swagger UI: http://localhost:8080/swagger-ui.html
# API Root: http://localhost:8080/api
```

## 📡 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/metrics` | GET | Platform KPIs (records, health, quality, freshness) |
| `/api/pipelines` | GET | All pipeline statuses |
| `/api/pipelines/{name}` | GET | Specific pipeline status |
| `/api/pipelines/{name}/trigger` | POST | Manually trigger pipeline execution |
| `/api/pipelines/{name}/history` | GET | Pipeline execution history |
| `/api/data-quality` | GET | Quality metrics for all tables |
| `/api/data-quality/{table}` | GET | Quality metrics for specific table |
| `/api/data-quality/{table}/test` | POST | Execute dbt quality tests |
| `/api/alerts` | GET | Active alerts and anomalies |
| `/api/schema-drift/{table}` | GET | Detect schema changes with LLM assessment |
| `/api/lineage/{table}` | GET | Data lineage (upstream/downstream) |
| `/api/chat` | POST | Ask the Architect (LLM chatbot) |

## 🏗️ Architecture

```
REST Controllers (5)
  ├─ MetricsController
  ├─ PipelineController
  ├─ DataQualityController
  ├─ ObservabilityController
  └─ ChatController
        ↓
Services (5)
  ├─ MetricsService
  ├─ PipelineService
  ├─ DataQualityService
  ├─ ObservabilityService
  └─ ChatService
        ↓
Providers (3)
  ├─ LLMProvider (Azure OpenAI, Vertex AI, Bedrock, Mock)
  ├─ DatabricksProvider (SQL queries)
  └─ KeyVaultProvider (Secret management)
        ↓
External Integrations
  ├─ Azure OpenAI (Chat/LLM)
  ├─ Databricks SQL (Data queries)
  ├─ Azure KeyVault (Secrets)
  ├─ Airflow REST API (Pipeline orchestration)
  ├─ Great Expectations (Data quality)
  └─ dbt (Data transformation)
```

## 🔧 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Spring Boot | 3.3.1 |
| Language | Java | 17+ |
| Build | Maven | 3.8+ |
| API Docs | Springdoc OpenAPI | 2.0.0 |
| Cloud SDKs | Azure SDK | Latest |
| Database Connector | Databricks SQL | 14.2.0 |
| LLM | Azure OpenAI | 1.0.0-beta.9 |
| Testing | JUnit 5, Mockito | Latest |

## 📚 Features

✅ **Complete API Coverage**
- Metrics and KPIs
- Pipeline orchestration and monitoring
- Data quality validation
- Observability and alerts
- Schema drift detection
- Data lineage analysis
- LLM-powered chatbot

✅ **Enterprise Features**
- CORS support for frontend integration
- OpenAPI/Swagger documentation
- Comprehensive error handling
- Mock data fallback
- Structured logging
- Spring Boot best practices

✅ **Integration Support**
- Azure OpenAI for "Ask the Architect"
- Databricks for data queries
- Azure KeyVault for secrets
- Airflow for pipeline orchestration

## 🔐 Configuration

Set environment variables before running:

```bash
# Azure
export AZURE_KEYVAULT_ENDPOINT=https://your-vault.vault.azure.net/
export AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
export AZURE_OPENAI_KEY=your-api-key
export AZURE_OPENAI_DEPLOYMENT=gpt-4

# Databricks
export DATABRICKS_HOST=your-workspace.azuredatabricks.net
export DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
export DATABRICKS_TOKEN=your-pat-token

# Provider selection
export LLM_PROVIDER=azure  # Options: azure, vertex, bedrock, mock
```

Or use `src/main/resources/application.properties`

## 📖 Documentation

### API Specification
Complete endpoint documentation with examples and business logic:
```
edp-io-api/API_SPECIFICATION.md
```

### Project README
Detailed architecture and deployment guide:
```
edp-io-api/README.md
```

### Quick Start
Get up and running in 5 minutes:
```
edp-io-api/QUICKSTART.md
```

## 🧪 Testing

Run unit tests:
```bash
mvn test
```

Run specific test class:
```bash
mvn test -Dtest=MetricsServiceTest
```

Run with coverage:
```bash
mvn test jacoco:report
```

## 📦 Building for Production

```bash
# Build JAR
mvn clean package

# Create Docker image (if Dockerfile exists)
docker build -t edp-io-api:1.0.0 .

# Push to registry
docker push your-registry/edp-io-api:1.0.0
```

## 🚢 Deployment Options

### Local Development
```bash
mvn spring-boot:run
```

### Azure Container Instances
```bash
az container create \
  --resource-group your-rg \
  --name edp-io-api \
  --image your-registry/edp-io-api:1.0.0 \
  --environment-variables AZURE_OPENAI_KEY=xxx DATABRICKS_TOKEN=yyy
```

### Azure Kubernetes Service (AKS)
```bash
kubectl apply -f edp-io-api-deployment.yaml
```

### Docker Compose (with Python dashboard)
```bash
docker-compose -f docker-compose.yml up
```

## 🔄 Integration with Python Dashboard

The Java API can be called from the Python dashboard:

```python
import requests

BASE_URL = "http://localhost:8080/api"

# Get metrics
response = requests.get(f"{BASE_URL}/metrics")
metrics = response.json()

# Get pipelines
response = requests.get(f"{BASE_URL}/pipelines")
pipelines = response.json()

# Ask the architect
response = requests.post(
    f"{BASE_URL}/chat",
    json={"message": "Why did Oracle ingestion fail?"}
)
answer = response.json()["response"]
```

## 📊 Mock Data

When external services are unavailable, the API returns realistic mock data:

- **Metrics**: 2.8M records, 12 tables, 11/12 pipelines healthy
- **Pipelines**: 6 pipelines with mixed health statuses
- **Alerts**: Active schema drift and slow pipeline warnings
- **Data Quality**: 3 tables with detailed violation metrics
- **Chat**: Context-aware responses for common questions

This allows development and testing without production credentials.

## 🛠️ Development Workflow

1. **Clone and setup**:
   ```bash
   git clone https://github.com/Cap-alfaMike/EDP-IO.git
   cd edp-io-api
   ```

2. **Run locally**:
   ```bash
   mvn spring-boot:run
   ```

3. **Access Swagger UI**:
   Open http://localhost:8080/swagger-ui.html

4. **Make changes** and test with Swagger or curl:
   ```bash
   curl http://localhost:8080/api/metrics
   ```

5. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: add endpoint for X"
   git push origin feature/your-feature
   ```

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and write tests
3. Run tests: `mvn test`
4. Commit: `git commit -am 'Add feature'`
5. Push: `git push origin feature/your-feature`
6. Create Pull Request

## 📝 License

MIT License - See LICENSE file in project root

## 📞 Support

For issues or questions:
- GitHub Issues: https://github.com/Cap-alfaMike/EDP-IO/issues
- Email: data-engineering@example.com
- Slack: #edp-io channel

---

**Version**: 1.0.0  
**Java**: 17+  
**Spring Boot**: 3.3.1  
**Status**: Production-Ready  
**Last Updated**: January 15, 2026
