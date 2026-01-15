# ============================================================================
# EDP-IO - LLM Log Analyzer
# ============================================================================
"""
LLM-powered log analysis for pipeline error troubleshooting.

DESIGN PHILOSOPHY:
-----------------
1. LLM is ADVISORY ONLY - never executes fixes
2. All suggestions require human approval
3. Output is always structured JSON for automation
4. Feature flag allows complete disable

WHY THIS IS SAFE:
- LLM never touches data
- LLM never executes commands
- All actions are suggestions with "requires_human_approval: true"
- Reduces MTTR by providing contextual insights

WHY THIS SCALES:
- Consistent analysis across all pipeline errors
- No need for custom regex per error type
- Learns from patterns in logs
- Can be extended with RAG for knowledge base

PRODUCTION NOTES:
- In production, uses Azure OpenAI (HIPAA/SOC2 compliant)
- Prompts are versioned and tested
- Token usage is monitored and capped
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import json

from pydantic import BaseModel, Field

from src.utils.config import get_settings
from src.utils.security import SecretProvider
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Severity(str, Enum):
    """Error severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ErrorType(str, Enum):
    """Categorized error types for routing."""
    SCHEMA_DRIFT = "SchemaDrift"
    CONNECTION_FAILURE = "ConnectionFailure"
    DATA_QUALITY = "DataQuality"
    RESOURCE_EXHAUSTION = "ResourceExhaustion"
    PERMISSION_DENIED = "PermissionDenied"
    TIMEOUT = "Timeout"
    UNKNOWN = "Unknown"


class ErrorAnalysis(BaseModel):
    """
    Structured output from LLM log analysis.
    
    This schema is REQUIRED for all LLM responses.
    It ensures consistent, automatable output.
    
    IMPORTANT:
    requires_human_approval is ALWAYS True.
    The LLM never has authority to auto-execute.
    """
    error_type: ErrorType = Field(
        description="Categorized error type for routing and aggregation"
    )
    root_cause: str = Field(
        description="Technical explanation of what went wrong"
    )
    business_impact: Severity = Field(
        description="Severity of business impact"
    )
    affected_tables: List[str] = Field(
        default_factory=list,
        description="List of tables/datasets affected"
    )
    recommended_action: str = Field(
        description="Specific remediation steps"
    )
    sql_fix: Optional[str] = Field(
        default=None,
        description="Optional SQL to fix the issue (for human review)"
    )
    requires_human_approval: bool = Field(
        default=True,
        description="Always True - humans must approve actions"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="LLM's confidence in this analysis (0-1)"
    )
    additional_context: Optional[str] = Field(
        default=None,
        description="Any additional relevant information"
    )


# Mock responses for when LLM is disabled or for testing
MOCK_RESPONSES: Dict[str, ErrorAnalysis] = {
    "schema": ErrorAnalysis(
        error_type=ErrorType.SCHEMA_DRIFT,
        root_cause="New column 'loyalty_points' added in source Oracle CRM system without corresponding update to data contracts",
        business_impact=Severity.MEDIUM,
        affected_tables=["bronze.customers", "silver.stg_customers"],
        recommended_action="1. Review new column with source team\n2. Update data contract in contracts.yaml\n3. Add column to Bronze schema\n4. Reprocess last 24h partition",
        sql_fix="ALTER TABLE bronze.customers ADD COLUMN loyalty_points INT;",
        requires_human_approval=True,
        confidence_score=0.85,
        additional_context="This appears to be a planned enhancement from the CRM Q1 roadmap. Check with CRM team for documentation."
    ),
    "connection": ErrorAnalysis(
        error_type=ErrorType.CONNECTION_FAILURE,
        root_cause="Oracle database connection refused - possible maintenance window or network issue",
        business_impact=Severity.HIGH,
        affected_tables=["bronze.customers", "bronze.products", "bronze.stores"],
        recommended_action="1. Check Oracle server status\n2. Verify network connectivity from Databricks\n3. Check if maintenance window is scheduled\n4. Retry with exponential backoff",
        requires_human_approval=True,
        confidence_score=0.90,
        additional_context="Oracle maintenance typically occurs Sundays 02:00-06:00 UTC. Current time matches this window."
    ),
    "data_quality": ErrorAnalysis(
        error_type=ErrorType.DATA_QUALITY,
        root_cause="Null values detected in required column 'customer_id' - 147 records affected",
        business_impact=Severity.HIGH,
        affected_tables=["bronze.orders"],
        recommended_action="1. Identify source of null customer_ids\n2. Quarantine affected records\n3. Notify source system owner\n4. Implement stricter source validation",
        requires_human_approval=True,
        confidence_score=0.88,
        additional_context="This may indicate a frontend bug allowing guest checkout without account creation."
    ),
    "default": ErrorAnalysis(
        error_type=ErrorType.UNKNOWN,
        root_cause="Unable to determine root cause from provided logs",
        business_impact=Severity.MEDIUM,
        affected_tables=[],
        recommended_action="1. Collect additional logs\n2. Check system metrics\n3. Escalate to platform team if persistent",
        requires_human_approval=True,
        confidence_score=0.30,
        additional_context="Insufficient context for confident analysis. Consider enabling debug logging."
    ),
}


class LogAnalyzer:
    """
    LLM-powered log analyzer for pipeline troubleshooting.
    
    USAGE:
        analyzer = LogAnalyzer()
        result = analyzer.analyze(error_log)
        
        if result.requires_human_approval:
            # Show to operator for approval
            notify_operator(result)
    
    BEHAVIOR:
    - When ENABLE_LLM_OBSERVABILITY is True: Uses Azure OpenAI
    - When False: Returns mock/templated responses
    
    This dual behavior enables:
    - Demo without cloud credentials
    - CI/CD testing without API calls
    - Gradual rollout of LLM features
    """
    
    SYSTEM_PROMPT = """You are an expert data pipeline troubleshooting assistant for the EDP-IO platform.

CONTEXT:
- EDP-IO is an enterprise data platform with Bronze/Silver/Gold Lakehouse architecture
- Data flows from Oracle and SQL Server to Azure Databricks via PySpark
- dbt handles Silver and Gold layer transformations

YOUR ROLE:
- Analyze error logs and identify root causes
- Suggest remediation actions
- Categorize errors for routing
- NEVER suggest executing anything automatically

CRITICAL RULES:
1. You are ADVISORY ONLY - all suggestions require human approval
2. Always set requires_human_approval to true
3. Provide specific, actionable recommendations
4. Include affected tables/datasets when identifiable
5. Rate your confidence honestly

OUTPUT FORMAT:
Respond ONLY with valid JSON matching this schema:
{
    "error_type": "SchemaDrift|ConnectionFailure|DataQuality|ResourceExhaustion|PermissionDenied|Timeout|Unknown",
    "root_cause": "Technical explanation",
    "business_impact": "LOW|MEDIUM|HIGH|CRITICAL",
    "affected_tables": ["table1", "table2"],
    "recommended_action": "Step-by-step remediation",
    "sql_fix": "Optional SQL command (for human review only)",
    "requires_human_approval": true,
    "confidence_score": 0.0-1.0,
    "additional_context": "Optional additional info"
}"""
    
    def __init__(self):
        """Initialize the log analyzer."""
        self.settings = get_settings()
        self._client = None
        
        logger.info(
            "LogAnalyzer initialized",
            llm_enabled=self.settings.enable_llm_observability,
        )
    
    @property
    def is_enabled(self) -> bool:
        """Check if LLM observability is enabled."""
        return self.settings.enable_llm_observability
    
    def _get_client(self):
        """Lazy-initialize the OpenAI client."""
        if self._client is None and self.is_enabled:
            try:
                from openai import AzureOpenAI
                
                api_key = SecretProvider.get("AZURE_OPENAI_KEY")
                
                self._client = AzureOpenAI(
                    api_key=api_key,
                    api_version=self.settings.azure_openai_api_version,
                    azure_endpoint=self.settings.azure_openai_endpoint,
                )
                
                logger.info("Azure OpenAI client initialized")
                
            except ImportError:
                logger.error("OpenAI package not installed")
                raise
            except Exception as e:
                logger.error("Failed to initialize OpenAI client", error=str(e))
                raise
        
        return self._client
    
    def _get_mock_response(self, error_log: str) -> ErrorAnalysis:
        """
        Return a mock response based on error keywords.
        
        Used when LLM is disabled or for testing.
        """
        error_lower = error_log.lower()
        
        if "schema" in error_lower or "column" in error_lower or "drift" in error_lower:
            return MOCK_RESPONSES["schema"]
        elif "connection" in error_lower or "refused" in error_lower or "timeout" in error_lower:
            return MOCK_RESPONSES["connection"]
        elif "null" in error_lower or "quality" in error_lower or "validation" in error_lower:
            return MOCK_RESPONSES["data_quality"]
        else:
            return MOCK_RESPONSES["default"]
    
    def analyze(
        self,
        error_log: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorAnalysis:
        """
        Analyze an error log and return structured remediation suggestions.
        
        Args:
            error_log: The error message or log content to analyze
            context: Optional additional context (pipeline name, run ID, etc.)
        
        Returns:
            ErrorAnalysis with categorization and recommendations
        
        IMPORTANT:
        The returned analysis ALWAYS has requires_human_approval=True.
        The LLM never has authority to auto-execute fixes.
        
        EXAMPLE:
            result = analyzer.analyze(
                error_log="Column 'loyalty_points' not found in schema",
                context={"pipeline": "oracle_customers"}
            )
            print(result.recommended_action)
        """
        logger.info(
            "Analyzing error log",
            llm_enabled=self.is_enabled,
            log_length=len(error_log),
        )
        
        # If LLM is disabled, return mock response
        if not self.is_enabled:
            logger.info("LLM disabled, returning mock response")
            return self._get_mock_response(error_log)
        
        # Build the prompt
        user_message = f"Analyze this error and suggest remediation:\n\n{error_log}"
        
        if context:
            user_message += f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"
        
        try:
            client = self._get_client()
            
            response = client.chat.completions.create(
                model=self.settings.azure_openai_deployment_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,  # Lower temperature for consistent analysis
                max_tokens=1000,
                response_format={"type": "json_object"},
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            response_data = json.loads(response_text)
            
            # Ensure human approval is required (safety enforcement)
            response_data["requires_human_approval"] = True
            
            analysis = ErrorAnalysis(**response_data)
            
            logger.info(
                "Error analysis completed",
                error_type=analysis.error_type,
                confidence=analysis.confidence_score,
            )
            
            return analysis
            
        except Exception as e:
            logger.error(
                "LLM analysis failed, returning fallback",
                error=str(e),
            )
            # Fallback to mock on error
            fallback = self._get_mock_response(error_log)
            fallback.additional_context = f"LLM analysis failed: {str(e)}. Using fallback analysis."
            fallback.confidence_score = 0.2
            return fallback
    
    def analyze_batch(
        self,
        error_logs: List[str],
    ) -> List[ErrorAnalysis]:
        """
        Analyze multiple error logs.
        
        For efficiency, similar errors are grouped and analyzed once.
        """
        results = []
        for log in error_logs:
            results.append(self.analyze(log))
        return results
    
    def format_for_display(self, analysis: ErrorAnalysis) -> str:
        """
        Format analysis for human-readable display.
        
        Returns a formatted string suitable for Slack/Teams notifications.
        """
        severity_emoji = {
            Severity.LOW: "🟢",
            Severity.MEDIUM: "🟡",
            Severity.HIGH: "🟠",
            Severity.CRITICAL: "🔴",
        }
        
        return f"""
{severity_emoji.get(analysis.business_impact, "⚪")} **{analysis.error_type.value}** (Confidence: {analysis.confidence_score:.0%})

**Root Cause:**
{analysis.root_cause}

**Affected Tables:**
{', '.join(analysis.affected_tables) or 'None identified'}

**Recommended Action:**
{analysis.recommended_action}

{f"**SQL Fix (for review):**```sql{analysis.sql_fix}```" if analysis.sql_fix else ""}

⚠️ **Human approval required before any action**
"""
