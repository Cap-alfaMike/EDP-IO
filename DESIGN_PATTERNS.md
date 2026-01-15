# 🏗️ Design Patterns in EDP-IO Java API

> **For Interview Preparation**: This document maps every design pattern used in the EDP-IO Java REST API, with code examples and strategic talking points.

---

## Table of Contents

1. [Strategy Pattern](#1-strategy-pattern)
2. [Data Transfer Object (DTO)](#2-data-transfer-object-dto)
3. [Layered Architecture (N-Tier)](#3-layered-architecture-n-tier)
4. [Dependency Injection (IoC)](#4-dependency-injection-ioc)
5. [Facade Pattern](#5-facade-pattern)
6. [Singleton Pattern](#6-singleton-pattern)
7. [Interview Prep Script](#interview-prep-script)

---

## 1. Strategy Pattern

### Definition
Define a **family of algorithms**, encapsulate them, and make them **interchangeable**. Strategy lets the algorithm vary independently from clients that use it.

### Location in EDP-IO
**File**: `edp-io-api/src/main/java/com/edpio/api/provider/LLMProvider.java`

### The Problem It Solves
- You need to support **multiple LLM vendors** (Azure OpenAI, GCP Vertex AI, AWS Bedrock)
- Each has different APIs, authentication, response formats
- Without a pattern: massive if-else chains, vendor lock-in, hard to test
- With Strategy: **swap vendors by changing one config variable**

### Code Example

```java
// Strategy interface (could be abstract class)
public class LLMProvider {
    
    public String generateInsight(String businessQuestion) {
        String provider = System.getenv().getOrDefault("LLM_PROVIDER", "mock");
        
        // Strategy selection based on configuration
        return switch(provider) {
            case "azure" -> {
                // Strategy 1: Azure OpenAI
                AzureOpenAIClient client = new AzureOpenAIClient(
                    System.getenv("AZURE_OPENAI_ENDPOINT"),
                    System.getenv("AZURE_OPENAI_KEY")
                );
                yield client.complete(businessQuestion);
            }
            case "vertex" -> {
                // Strategy 2: GCP Vertex AI
                VertexAIClient client = new VertexAIClient(
                    System.getenv("GCP_PROJECT_ID")
                );
                yield client.predict(businessQuestion);
            }
            case "bedrock" -> {
                // Strategy 3: AWS Bedrock
                BedrockClient client = new BedrockClient(
                    System.getenv("AWS_REGION")
                );
                yield client.invoke(businessQuestion);
            }
            default -> generateMockInsight(businessQuestion);
        };
    }
    
    private String generateMockInsight(String question) {
        // Strategy 4: Mock (for testing, development)
        return "Mock insight for: " + question;
    }
}
```

### In application.properties
```properties
# Change provider without code modification
LLM_PROVIDER=azure    # or: vertex, bedrock, mock
```

### Interview Talking Point
> *"Using the Strategy Pattern in our LLMProvider class, we achieve multi-cloud agnosticismwithout code duplication. The same API code runs on Azure, GCP, or AWS. If we need to migrate from Azure to AWS Bedrock, we simply change `LLM_PROVIDER=bedrock` in the configuration—no code refactoring, no regression testing of the core logic."*

---

## 2. Data Transfer Object (DTO)

### Definition
An object that carries data between **processes** (e.g., from backend to frontend), **decoupling** the internal representation from the public API contract.

### Location in EDP-IO
**Directory**: `edp-io-api/src/main/java/com/edpio/api/model/`

**Files**: `MetricsResponse.java`, `PipelineStatus.java`, `Alert.java`, `ChatMessage.java`, `DataQualityMetrics.java`, `SchemaDrift.java`

### The Problem It Solves
- **Internal database schema** might have 50+ columns, nested relationships, technical debt
- **Public API clients** (Streamlit, mobile apps, data portals) don't care about internal complexity
- Without DTOs: clients see internal schema → breaking changes propagate
- With DTOs: clients see stable, curated interface → schema evolution is internal

### Code Example

```java
// INTERNAL ENTITY (may change)
@Entity
@Table(name = "pipeline_runs")
public class PipelineRunEntity {
    @Id
    private Long id;
    
    @Column(name = "pipeline_name")
    private String name;
    
    @Column(name = "start_time")
    private LocalDateTime startTime;
    
    @Column(name = "end_time")
    private LocalDateTime endTime;
    
    @Column(name = "status")
    private String status;
    
    // Internal fields (not for public API)
    private String internalTrackingId;
    private String debugLogs;
    private Integer retryAttempts;
    private String technicalErrorMessage;
    // ... 40 more internal fields
}

// PUBLIC DTO (stable contract)
@Data
@Schema(description = "Pipeline execution status for public API consumers")
public class PipelineStatus {
    
    @Schema(example = "customer_etl", description = "Pipeline identifier")
    private String pipelineName;
    
    @Schema(example = "2026-01-15T10:30:00Z", description = "Execution start time")
    private LocalDateTime startTime;
    
    @Schema(example = "2026-01-15T10:45:00Z", description = "Execution end time")
    private LocalDateTime endTime;
    
    @Schema(example = "SUCCEEDED", description = "Status: PENDING, RUNNING, SUCCEEDED, FAILED")
    private String status;
    
    @Schema(example = "5", description = "Duration in minutes")
    private Long durationMinutes;
}

// SERVICE LAYER: Maps Entity → DTO
@Service
public class PipelineService {
    
    public PipelineStatus getPipelineStatus(String pipelineName) {
        PipelineRunEntity entity = repository.findLatest(pipelineName);
        
        // Map entity to DTO (hide internal complexity)
        return PipelineStatus.builder()
            .pipelineName(entity.getName())
            .startTime(entity.getStartTime())
            .endTime(entity.getEndTime())
            .status(entity.getStatus())
            .durationMinutes(
                ChronoUnit.MINUTES.between(entity.getStartTime(), entity.getEndTime())
            )
            .build();
    }
}

// CLIENT (e.g., Streamlit)
// Receives only:
// {
//   "pipelineName": "customer_etl",
//   "startTime": "2026-01-15T10:30:00Z",
//   "endTime": "2026-01-15T10:45:00Z",
//   "status": "SUCCEEDED",
//   "durationMinutes": 15
// }
//
// Never sees: internalTrackingId, debugLogs, technicalErrorMessage, etc.
```

### Interview Talking Point
> *"We use Data Transfer Objects to create a stable public API contract. When the database schema evolves—and it will—we update only the Entity-to-DTO mapper in the service layer. Clients don't break. A mobile app that was built against our API 6 months ago continues working without changes, even if we've internally refactored the database schema 5 times."*

---

## 3. Layered Architecture (N-Tier)

### Definition
Organize code into horizontal layers, each with a **single responsibility**: HTTP handling (Controller), business logic (Service), infrastructure (Provider).

### Location in EDP-IO

```
edp-io-api/src/main/java/com/edpio/api/
├── controller/     ← HTTP/REST Layer
├── service/        ← Business Logic Layer
├── provider/       ← Infrastructure/Data Access Layer
└── model/          ← Data Transfer Objects
```

### The Problem It Solves
- Monolithic code (everything in one class) is **unmaintainable** and **untestable**
- Changes to HTTP handling shouldn't affect business logic
- Different teams can work on different layers in parallel
- Easy to swap implementations (real Databricks in prod, mock in tests)

### Code Example

```java
// ====================================================================
// LAYER 1: Controller (HTTP Handling & Routing)
// ====================================================================
@RestController
@RequestMapping("/api/metrics")
@Tag(name = "Metrics", description = "Platform KPI endpoints")
public class MetricsController {
    
    @Autowired
    private MetricsService metricsService;
    
    @GetMapping
    @Operation(summary = "Get platform KPIs")
    public MetricsResponse getMetrics() {
        // Controller: 
        // - Parse HTTP request
        // - Validate input
        // - Delegate to service
        // - Convert service result to HTTP response
        // - Handle HTTP status codes
        
        return metricsService.calculateKPIs();
    }
}

// ====================================================================
// LAYER 2: Service (Business Logic & Orchestration)
// ====================================================================
@Service
public class MetricsService {
    
    @Autowired
    private DatabricksProvider databricksProvider;
    
    @Autowired
    private ObservabilityService observabilityService;
    
    public MetricsResponse calculateKPIs() {
        // Service: 
        // - Implement business rules (how to calculate quality score)
        // - Orchestrate multiple providers
        // - No knowledge of HTTP, JSON, or REST
        
        long totalRuns = databricksProvider.countPipelineRuns();
        double avgTime = databricksProvider.getAvgProcessingTime();
        double qualityScore = calculateQualityScore();
        long alertCount = observabilityService.getAlertCount();
        
        return MetricsResponse.builder()
            .dataQualityScore(qualityScore)
            .pipelineRunsLast24h(totalRuns)
            .avgProcessingTimeMinutes(avgTime)
            .activeAlerts(alertCount)
            .build();
    }
    
    private double calculateQualityScore() {
        // Pure business logic
        // No database, HTTP, or external API calls here
        // Just math, rules, decisions
        return 92.5;
    }
}

// ====================================================================
// LAYER 3: Provider (Infrastructure & External APIs)
// ====================================================================
@Component
public class DatabricksProvider {
    
    @Autowired
    private DatabricksConnector connector;
    
    public long countPipelineRuns() {
        // Provider:
        // - Execute infrastructure calls (database queries, API calls)
        // - Handle network errors, retries, connection pooling
        // - Transform raw data to domain objects
        
        try {
            String sql = "SELECT COUNT(*) as count FROM runs WHERE created_at > CURRENT_DATE - 1";
            QueryResult result = connector.executeSQL(sql);
            return result.getAsLong("count");
        } catch (DatabricksException e) {
            // Retry logic, fallback, circuit breaker
            throw new RuntimeException("Failed to count runs", e);
        }
    }
    
    public double getAvgProcessingTime() {
        String sql = "SELECT AVG(CAST(duration_minutes AS DOUBLE)) as avg_time FROM runs";
        QueryResult result = connector.executeSQL(sql);
        return result.getAsDouble("avg_time");
    }
}
```

### Testing Benefits

```java
// UNIT TEST: Test service logic in ISOLATION
@Test
public void testQualityScoreCalculation() {
    // Arrange: Create mock providers
    DatabricksProvider mockDatabricks = mock(DatabricksProvider.class);
    ObservabilityService mockObservability = mock(ObservabilityService.class);
    
    when(mockDatabricks.countPipelineRuns()).thenReturn(100L);
    when(mockDatabricks.getAvgProcessingTime()).thenReturn(5.2);
    when(mockObservability.getAlertCount()).thenReturn(3L);
    
    // Inject mocks
    MetricsService service = new MetricsService();
    service.databricksProvider = mockDatabricks;
    service.observabilityService = mockObservability;
    
    // Act
    MetricsResponse response = service.calculateKPIs();
    
    // Assert: No real Databricks connection needed
    assertEquals(100L, response.getPipelineRunsLast24h());
    assertEquals(5.2, response.getAvgProcessingTimeMinutes());
    assertEquals(3L, response.getActiveAlerts());
    
    // Test runs in milliseconds, not seconds
}
```

### Interview Talking Point
> *"We organize code into three layers: Controllers handle HTTP, Services contain business logic, and Providers abstract external systems. This separation allows us to test business logic without spinning up real databases. A unit test that would normally take 10 seconds (database connection overhead) now takes 50 milliseconds. We can run 10,000 tests in parallel."*

---

## 4. Dependency Injection (IoC)

### Definition
**Don't create dependencies manually**. Let a container (Spring) **inject** them. Enables loose coupling and testability.

### Location in EDP-IO
**Mechanism**: Spring's `@Autowired` annotations throughout the codebase

### The Problem It Solves
- **Hard-coded dependencies** = impossible to test in isolation
- **Tight coupling** = changing one class breaks many others
- Without DI: inject real objects in prod, real objects in test (slow, flaky)
- With DI: inject real objects in prod, inject mocks in test (fast, reliable)

### Code Example - WITHOUT DI (Anti-pattern)

```java
// ❌ WRONG: Hard-coded dependency
@Service
public class MetricsService {
    
    private DatabricksProvider provider = new DatabricksProvider(); // Hard-coded!
    
    public MetricsResponse calculateKPIs() {
        long runs = provider.countPipelineRuns(); // Always calls REAL Databricks
        return new MetricsResponse(runs);
    }
}

// Unit test: ❌ Will fail if Databricks is down
@Test
public void testMetrics() {
    MetricsService service = new MetricsService();
    service.calculateKPIs(); // ❌ Calls REAL Databricks, might timeout
}
```

### Code Example - WITH DI (Correct)

```java
// ✅ CORRECT: Constructor Injection
@Service
public class MetricsService {
    
    private final DatabricksProvider provider;
    
    public MetricsService(DatabricksProvider provider) { // Injected
        this.provider = provider;
    }
    
    public MetricsResponse calculateKPIs() {
        long runs = provider.countPipelineRuns();
        return new MetricsResponse(runs);
    }
}

// Unit test: ✅ Inject a Mock
@Test
public void testMetrics() {
    // Arrange: Create a mock provider
    DatabricksProvider mockProvider = mock(DatabricksProvider.class);
    when(mockProvider.countPipelineRuns()).thenReturn(100L);
    
    // Act: Inject the mock
    MetricsService service = new MetricsService(mockProvider);
    MetricsResponse response = service.calculateKPIs();
    
    // Assert: No real Databricks call
    assertEquals(100L, response.getPipelineRunsLast24h());
    
    // Verify: Mock was called exactly once
    verify(mockProvider, times(1)).countPipelineRuns();
}
```

### Spring Configuration

```java
// Spring automatically injects beans
@RestController
@RequestMapping("/api/metrics")
public class MetricsController {
    
    @Autowired
    private MetricsService metricsService; // Spring injects the real service
    
    @GetMapping
    public MetricsResponse getMetrics() {
        return metricsService.calculateKPIs();
    }
}

// Test configuration: Override beans with mocks
@SpringBootTest
public class MetricsControllerTest {
    
    @MockBean
    private MetricsService mockService;
    
    @Autowired
    private WebTestClient client;
    
    @Test
    public void testMetricsEndpoint() {
        when(mockService.calculateKPIs()).thenReturn(
            MetricsResponse.builder()
                .dataQualityScore(95.0)
                .pipelineRunsLast24h(50L)
                .build()
        );
        
        client.get()
            .uri("/api/metrics")
            .exchange()
            .expectStatus().isOk()
            .expectBody(MetricsResponse.class);
    }
}
```

### Interview Talking Point
> *"We use Spring's Dependency Injection to inject real services in production and mock services in unit tests. This enables us to test complex business logic in isolation without external network calls. Our test suite runs in 30 seconds instead of 30 minutes because we're not waiting for database connections."*

---

## 5. Facade Pattern

### Definition
Provide a **unified, simplified interface** to a complex subsystem. Hide internal complexity behind a simple API.

### Location in EDP-IO
**File**: `edp-io-api/src/main/java/com/edpio/api/controller/PipelineController.java`

### The Problem It Solves
- Clients need a simple, cohesive interface
- Behind the scenes: many steps, integrations, error handling
- Without Facade: clients orchestrate complex workflows themselves
- With Facade: clients call one endpoint, backend handles complexity

### Code Example

```java
@RestController
@RequestMapping("/api/pipelines")
@Tag(name = "Pipelines", description = "Pipeline orchestration endpoints")
public class PipelineController {
    
    @Autowired
    private PipelineService pipelineService;
    
    // ============================================================
    // SIMPLE FACADE: Client calls one endpoint
    // ============================================================
    @PostMapping("/{pipelineId}/trigger")
    @Operation(summary = "Trigger pipeline execution")
    public PipelineStatus triggerPipeline(
        @PathVariable String pipelineId,
        @RequestBody TriggerRequest request
    ) {
        // Behind the scenes, PipelineService orchestrates:
        // 1. Validate input
        // 2. Check if user has permission (RBAC)
        // 3. Retrieve secrets from KeyVault
        // 4. Trigger Airflow DAG
        // 5. Log audit trail
        // 6. Monitor execution
        // 7. Return status
        
        return pipelineService.triggerPipeline(pipelineId, request);
    }
}

// ============================================================
// BEHIND THE FACADE: Complex orchestration
// ============================================================
@Service
public class PipelineService {
    
    @Autowired
    private KeyVaultProvider keyVault;
    
    @Autowired
    private AirflowProvider airflow;
    
    @Autowired
    private AuditLogger auditLogger;
    
    @Autowired
    private RBACValidator rbac;
    
    public PipelineStatus triggerPipeline(String pipelineId, TriggerRequest request) {
        
        // Step 1: Validate permissions
        if (!rbac.hasPermission(getCurrentUser(), "execute_pipeline")) {
            throw new UnauthorizedException("User not authorized");
        }
        
        // Step 2: Retrieve secrets
        String airflowUrl = keyVault.getSecret("AIRFLOW_URL");
        String airflowToken = keyVault.getSecret("AIRFLOW_TOKEN");
        
        // Step 3: Trigger Airflow
        String runId = airflow.triggerDag(
            airflowUrl,
            airflowToken,
            pipelineId,
            request.getParameters()
        );
        
        // Step 4: Log audit trail
        auditLogger.log(
            AuditEvent.builder()
                .action("PIPELINE_TRIGGERED")
                .resource(pipelineId)
                .userId(getCurrentUser())
                .timestamp(LocalDateTime.now())
                .build()
        );
        
        // Step 5: Return simple status
        return PipelineStatus.builder()
            .pipelineId(pipelineId)
            .runId(runId)
            .status("RUNNING")
            .triggeredAt(LocalDateTime.now())
            .build();
    }
}
```

### Client Perspective

```
Client sees:
  POST /api/pipelines/{pipelineId}/trigger
  
  Response:
  {
    "pipelineId": "customer_etl",
    "runId": "run-12345",
    "status": "RUNNING",
    "triggeredAt": "2026-01-15T10:30:00Z"
  }

Client doesn't care about:
  - KeyVault secret retrieval
  - RBAC validation logic
  - Airflow DAG configuration
  - Audit logging
  - Error handling
```

### Interview Talking Point
> *"We use the Facade Pattern in our controllers. A client calls a single endpoint like `POST /trigger`. Behind that facade, we orchestrate dozens of steps: validation, secret retrieval, RBAC checks, Airflow triggers, audit logging. The client sees simplicity; the backend handles rigor. This is the definition of good API design."*

---

## 6. Singleton Pattern

### Definition
Ensure a class has **only one instance** and provide a **global point of access** to it.

### Location in EDP-IO
**Mechanism**: Spring's default bean scope is `Singleton`

### The Problem It Solves
- Creating multiple instances of expensive objects = **memory waste**
- Database connections, HTTP clients, thread pools should be shared
- Without Singleton: 1000 concurrent users → 1000 service instances
- With Singleton: 1000 concurrent users → 1 service instance (+ connection pooling)

### Code Example

```java
// ============================================================
// SPRING BEANS ARE SINGLETONS BY DEFAULT
// ============================================================

@Service
public class MetricsService {
    @Autowired
    private DatabricksProvider provider;
    
    public MetricsResponse calculateKPIs() {
        return provider.getMetrics();
    }
}

// Spring application context:
// - Creates ONE instance of MetricsService
// - Injects it to ALL requests
// - Reuses the same instance for 1000+ concurrent users

// In application.properties:
// spring.datasource.hikari.maximum-pool-size=10

// This means:
// - One MetricsService instance handles all requests
// - Connection pool of 10 Databricks connections
// - 1000 concurrent users share 10 connections via queuing
```

### Memory Comparison

```
WITHOUT SINGLETON (Anti-pattern):
- 1000 concurrent users
- 1000 MetricsService instances
- 1000 DatabricksProvider instances
- Memory: 1000 × 100 KB = 100 MB just for service instances
- Plus: 1000 database connections = server exhaustion ❌

WITH SINGLETON (Correct):
- 1000 concurrent users
- 1 MetricsService instance
- 1 DatabricksProvider instance
- Memory: 100 KB (shared)
- Plus: Connection pool (default 10) = efficient ✅
```

### Code Example - Connection Pooling

```java
@Component
public class DatabricksProvider {
    
    // HikariCP connection pool (Singleton)
    private static final DataSource dataSource = createDataSource();
    
    private static DataSource createDataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:databricks://...");
        config.setUsername("username");
        config.setPassword("password");
        config.setMaximumPoolSize(10); // Only 10 connections
        return new HikariDataSource(config);
    }
    
    public QueryResult executeSQL(String sql) {
        // Request: 1000 concurrent users
        // Connection: Pull from pool (queued if all 10 are busy)
        // Execute: Run SQL
        // Return: Put connection back in pool
        // Result: All 1000 users served by 10 connections
        
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            
            return new QueryResult(rs);
        }
    }
}

// Spring Configuration
@Configuration
public class DatabaseConfig {
    
    @Bean
    @Scope("singleton")  // ← Only one instance in entire application
    public DatabricksProvider databricksProvider() {
        return new DatabricksProvider();
    }
}
```

### Interview Talking Point
> *"Spring manages beans as Singletons by default. This means we have one MetricsService instance serving thousands of concurrent requests. Combined with connection pooling, a pool of 10 Databricks connections efficiently serves 1000 concurrent users. Without Singleton, we'd need 1000 connection instances—the server would be exhausted before reaching 100 users."*

---

## Interview Prep Script

### Scenario: "Tell us about your architecture."

> *"The EDP-IO Java API is built on six design patterns that work together to create a scalable, testable, enterprise-grade backend.*
>
> *First, we use the **Strategy Pattern** for cloud agnosticism. Our LLMProvider abstracts Azure OpenAI, GCP Vertex AI, and AWS Bedrock. Change one config variable, and we're running on a different cloud. No code refactoring.*
>
> *Second, we strictly separate concerns with **Layered Architecture**: Controllers handle HTTP, Services implement business logic, and Providers abstract external systems. This allows us to test business logic in isolation without database connections.*
>
> *Third, we use **Dependency Injection** throughout. The Spring container injects real services in production and mocks in tests. Our test suite runs in 30 seconds instead of 30 minutes.*
>
> *Fourth, we expose a simple interface via the **Facade Pattern**. When a client calls `POST /trigger`, they don't know we're orchestrating KeyVault secret retrieval, RBAC validation, Airflow triggers, and audit logging. The client sees simplicity; the backend ensures rigor.*
>
> *Fifth, we use **Data Transfer Objects** to decouple our API contract from our internal schema. When the database evolves, clients don't break.*
>
> *Sixth, Spring manages all services as **Singletons**. One MetricsService instance serves thousands of requests. With connection pooling, 10 database connections handle the entire load.*
>
> *Together, these patterns create a platform that scales horizontally, is easy to test, and supports multiple clients (Streamlit UI today, mobile/portal apps tomorrow) without code duplication."*

### Scenario: "How would you add a new LLM vendor?"

> *"With the Strategy Pattern, adding a new LLM vendor takes 20 minutes. I'd:*
>
> 1. *Create a new case in LLMProvider's switch statement*
> 2. *Implement the vendor's API call (e.g., Anthropic Claude)*
> 3. *Add the new configuration option: `LLM_PROVIDER=anthropic`*
> 4. *No changes to Controllers, Services, or the rest of the system*
>
> *This is the power of Strategy—the abstraction is already there. The system is designed for extensibility, not modification."*

### Scenario: "Your tests are slow. Why?"

> *"Tests should be fast. If they're slow, it's because they're hitting real infrastructure. In our architecture:*
>
> - *Unit tests inject mocks → run in milliseconds*
> - *Integration tests use real services → run in seconds*
> - *End-to-end tests hit real databases → run in minutes*
>
> *We organize the test pyramid accordingly. 1000 unit tests (fast), 100 integration tests (moderate), 10 end-to-end tests (slow). The slow tests run only in CI/CD, not on every commit."*

---

## Checklists for Interviews

### When Asked About Architecture:

- [ ] Mention **Strategy Pattern** for multi-cloud
- [ ] Explain **N-Tier Layering** for testability
- [ ] Describe **Dependency Injection** for loose coupling
- [ ] Discuss **Facade Pattern** for simplicity
- [ ] Highlight **DTOs** for API stability
- [ ] Mention **Singleton** for resource efficiency

### When Asked to Solve a Problem:

- [ ] "First, I'd identify which layer needs the change"
- [ ] "Can I make this change without affecting other layers?"
- [ ] "How would I test this in isolation?"
- [ ] "Is there a pattern that naturally fits this problem?"

### Red Flags to Avoid:

- ❌ "We don't really have a pattern, it just evolved"
- ❌ "Everything is in one big class"
- ❌ "We hard-code the database URL in the service"
- ❌ "Tests are slow because they hit the real database"
- ❌ "We can't add a new cloud provider without refactoring"

---

## References

- [Refactoring.Guru - Design Patterns](https://refactoring.guru/design-patterns)
- [Spring Framework Documentation](https://spring.io/projects/spring-framework)
- [Martin Fowler - Enterprise Application Architecture](https://martinfowler.com/)

---

**Last Updated**: January 15, 2026  
**Author**: EDP-IO Development Team  
**Status**: Ready for Interview Prep ✅
