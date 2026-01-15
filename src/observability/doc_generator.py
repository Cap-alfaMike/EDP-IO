# ============================================================================
# EDP-IO - Documentation Generator
# ============================================================================
"""
Auto-generate documentation from dbt models using LLM.

PURPOSE:
-------
Documentation is often out of date. This module:
- Reads dbt manifest.json
- Extracts model SQL and metadata
- Uses LLM to generate business-friendly descriptions
- Creates markdown documentation

WHY LLM FOR DOCS?
----------------
1. Translates technical SQL to business language
2. Consistent formatting and style
3. Identifies business rules embedded in code
4. Scales to hundreds of models

SAFETY:
------
- Read-only operation (no data transformation)
- Generates documentation only
- Human review before publication
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from pydantic import BaseModel, Field

from src.utils.config import get_settings
from src.utils.security import SecretProvider
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ModelDocumentation(BaseModel):
    """Documentation for a single dbt model."""
    model_name: str = Field(description="Name of the model")
    schema: str = Field(description="Schema/layer (bronze, silver, gold)")
    
    summary: str = Field(
        description="One-line business summary"
    )
    
    description: str = Field(
        description="Detailed description of what the model does"
    )
    
    business_purpose: str = Field(
        description="Why this model exists from a business perspective"
    )
    
    key_transformations: List[str] = Field(
        default_factory=list,
        description="List of key transformations applied"
    )
    
    business_rules: List[str] = Field(
        default_factory=list,
        description="Business rules implemented in the model"
    )
    
    dependencies: List[str] = Field(
        default_factory=list,
        description="Upstream models/sources"
    )
    
    columns: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Column documentation"
    )
    
    usage_examples: List[str] = Field(
        default_factory=list,
        description="Example queries using this model"
    )
    
    sla: Optional[str] = Field(
        default=None,
        description="Service level agreement for freshness"
    )
    
    owner: Optional[str] = Field(
        default=None,
        description="Team or person responsible"
    )


class DocGenerator:
    """
    Generate documentation from dbt models using LLM.
    
    USAGE:
        generator = DocGenerator()
        
        # Generate docs for all models
        docs = generator.generate_all()
        
        # Or for a specific model
        doc = generator.generate_model_doc("fact_sales")
        
        # Export to markdown
        generator.export_markdown(docs, "docs/models.md")
    
    MOCK BEHAVIOR:
    When LLM is disabled, generates structured but generic documentation
    based on model naming conventions and SQL patterns.
    """
    
    SYSTEM_PROMPT = """You are a technical writer specializing in data documentation.

CONTEXT:
- You are documenting dbt models for a retail data platform (EDP-IO)
- Audience: Data analysts, business users, and engineers
- Goal: Make technical transformations understandable to business users

YOUR ROLE:
- Translate SQL logic into business language
- Identify and document business rules
- Explain column purposes clearly
- Suggest example queries

OUTPUT FORMAT (JSON):
{
    "summary": "One line summary",
    "description": "Detailed description",
    "business_purpose": "Why this exists for the business",
    "key_transformations": ["transform1", "transform2"],
    "business_rules": ["rule1", "rule2"],
    "usage_examples": ["SELECT query1", "SELECT query2"],
    "columns": [{"name": "col1", "description": "what it means"}]
}

GUIDELINES:
- Use business terms, not just technical ones
- Explain "why" not just "what"
- Be concise but complete
- Highlight important business rules"""
    
    def __init__(self, dbt_project_path: Optional[str] = None):
        """
        Initialize the doc generator.
        
        Args:
            dbt_project_path: Path to dbt project (default: dbt_project/)
        """
        self.settings = get_settings()
        self.dbt_path = Path(dbt_project_path or "dbt_project")
        self._manifest = None
        
        logger.info(
            "DocGenerator initialized",
            dbt_path=str(self.dbt_path),
            llm_enabled=self.settings.enable_llm_observability,
        )
    
    @property
    def is_enabled(self) -> bool:
        """Check if LLM is enabled."""
        return self.settings.enable_llm_observability
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load dbt manifest.json."""
        if self._manifest is not None:
            return self._manifest
        
        manifest_path = self.dbt_path / "target" / "manifest.json"
        
        if not manifest_path.exists():
            logger.warning("manifest.json not found, using mock data")
            return self._get_mock_manifest()
        
        with open(manifest_path) as f:
            self._manifest = json.load(f)
        
        return self._manifest
    
    def _get_mock_manifest(self) -> Dict[str, Any]:
        """Return mock manifest for demo purposes."""
        return {
            "nodes": {
                "model.edp_io.stg_customers": {
                    "name": "stg_customers",
                    "schema": "silver",
                    "raw_code": "SELECT * FROM source WITH SCD2...",
                    "depends_on": {"nodes": ["source.bronze.customers"]},
                    "columns": {
                        "customer_id": {"description": ""},
                        "first_name": {"description": ""},
                        "customer_segment": {"description": ""},
                    }
                },
                "model.edp_io.fact_sales": {
                    "name": "fact_sales",
                    "schema": "gold",
                    "raw_code": "SELECT orders JOIN items...",
                    "depends_on": {"nodes": ["model.edp_io.stg_orders"]},
                    "columns": {
                        "fact_sales_key": {"description": ""},
                        "net_revenue": {"description": ""},
                        "gross_profit": {"description": ""},
                    }
                },
            }
        }
    
    def _get_mock_doc(self, model_name: str, model_info: Dict) -> ModelDocumentation:
        """Generate mock documentation based on model patterns."""
        schema = model_info.get("schema", "unknown")
        
        # Pattern-based documentation
        if model_name.startswith("stg_"):
            return ModelDocumentation(
                model_name=model_name,
                schema=schema,
                summary=f"Staged {model_name[4:]} data with cleansing and SCD2",
                description=f"This Silver layer model cleanses and standardizes {model_name[4:]} data from the Bronze layer. It implements SCD Type 2 for historical tracking.",
                business_purpose=f"Provides clean, historized {model_name[4:]} data for downstream analytics and reporting.",
                key_transformations=[
                    "Data type standardization",
                    "Null handling and default values",
                    "SCD Type 2 historization",
                    "Row-level deduplication",
                ],
                business_rules=[
                    "Business key uniqueness enforced",
                    "Historical versions tracked with valid_from/valid_to",
                    "Current record identified by is_current=true",
                ],
                dependencies=list(model_info.get("depends_on", {}).get("nodes", [])),
                columns=[
                    {"name": col, "description": f"Cleaned {col} from source"}
                    for col in model_info.get("columns", {}).keys()
                ],
                usage_examples=[
                    f"-- Get current {model_name[4:]}\nSELECT * FROM {schema}.{model_name} WHERE is_current = true",
                ],
            )
        
        elif model_name.startswith("dim_"):
            return ModelDocumentation(
                model_name=model_name,
                schema=schema,
                summary=f"{model_name[4:].title()} dimension for star schema analytics",
                description=f"Gold layer dimension table containing current-state {model_name[4:]} attributes for analytical queries.",
                business_purpose=f"Enables slicing and filtering of fact data by {model_name[4:]} attributes.",
                key_transformations=[
                    "Surrogate key generation",
                    "Current-state flattening from SCD2",
                    "Derived attribute calculation",
                ],
                business_rules=[
                    "One row per entity (current state only)",
                    "Surrogate key used for fact table joins",
                ],
                dependencies=list(model_info.get("depends_on", {}).get("nodes", [])),
                columns=[
                    {"name": col, "description": f"Dimension attribute: {col}"}
                    for col in model_info.get("columns", {}).keys()
                ],
                usage_examples=[
                    f"-- Join with fact table\nSELECT d.*, SUM(f.revenue)\nFROM {model_name} d\nJOIN fact_sales f ON d.dim_{model_name[4:]}_key = f.dim_{model_name[4:]}_key\nGROUP BY 1",
                ],
            )
        
        elif model_name.startswith("fact_"):
            return ModelDocumentation(
                model_name=model_name,
                schema=schema,
                summary=f"{model_name[5:].title()} fact table for business metrics",
                description=f"Gold layer fact table containing {model_name[5:]} transactions at grain level with all measures and dimension keys.",
                business_purpose=f"Central source of truth for {model_name[5:]} analytics, enabling revenue, volume, and profitability analysis.",
                key_transformations=[
                    "Dimension key lookup",
                    "Measure calculation (revenue, cost, profit)",
                    "Date dimension integration",
                ],
                business_rules=[
                    "Grain: one row per transaction line item",
                    "Additive measures can be aggregated across all dimensions",
                    "Dimension keys enable star schema joins",
                ],
                dependencies=list(model_info.get("depends_on", {}).get("nodes", [])),
                columns=[
                    {"name": col, "description": f"Fact measure or key: {col}"}
                    for col in model_info.get("columns", {}).keys()
                ],
                usage_examples=[
                    f"-- Total revenue by segment\nSELECT c.customer_segment, SUM(f.net_revenue) as revenue\nFROM {model_name} f\nJOIN dim_customer c ON f.dim_customer_key = c.dim_customer_key\nGROUP BY 1",
                ],
            )
        
        else:
            return ModelDocumentation(
                model_name=model_name,
                schema=schema,
                summary=f"Data model: {model_name}",
                description="Auto-generated documentation. Please add detailed description.",
                business_purpose="Document the business purpose of this model.",
                key_transformations=[],
                business_rules=[],
                dependencies=list(model_info.get("depends_on", {}).get("nodes", [])),
                columns=[],
            )
    
    def generate_model_doc(
        self,
        model_name: str,
        model_sql: Optional[str] = None,
    ) -> ModelDocumentation:
        """
        Generate documentation for a single model.
        
        Args:
            model_name: Name of the dbt model
            model_sql: Optional SQL code (loaded from manifest if not provided)
        
        Returns:
            ModelDocumentation with generated content
        """
        manifest = self._load_manifest()
        
        # Find model in manifest
        model_key = f"model.edp_io.{model_name}"
        model_info = manifest.get("nodes", {}).get(model_key, {})
        
        if not model_info:
            logger.warning(f"Model {model_name} not found in manifest")
            model_info = {"name": model_name, "schema": "unknown"}
        
        model_sql = model_sql or model_info.get("raw_code", "")
        
        logger.info(
            "Generating documentation",
            model=model_name,
            llm_enabled=self.is_enabled,
        )
        
        if not self.is_enabled:
            return self._get_mock_doc(model_name, model_info)
        
        # LLM-powered documentation
        return self._llm_generate(model_name, model_info, model_sql)
    
    def _llm_generate(
        self,
        model_name: str,
        model_info: Dict,
        model_sql: str,
    ) -> ModelDocumentation:
        """Use LLM to generate rich documentation."""
        try:
            from openai import AzureOpenAI
            
            api_key = SecretProvider.get("AZURE_OPENAI_KEY")
            
            client = AzureOpenAI(
                api_key=api_key,
                api_version=self.settings.azure_openai_api_version,
                azure_endpoint=self.settings.azure_openai_endpoint,
            )
            
            user_message = f"""Document this dbt model:

Model Name: {model_name}
Schema: {model_info.get('schema', 'unknown')}

SQL Code:
```sql
{model_sql[:2000]}  # Truncate for token limit
```

Dependencies: {model_info.get('depends_on', {}).get('nodes', [])}

Columns: {list(model_info.get('columns', {}).keys())}
"""
            
            response = client.chat.completions.create(
                model=self.settings.azure_openai_deployment_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.5,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return ModelDocumentation(
                model_name=model_name,
                schema=model_info.get("schema", "unknown"),
                dependencies=model_info.get("depends_on", {}).get("nodes", []),
                **result,
            )
            
        except Exception as e:
            logger.error("LLM doc generation failed", error=str(e))
            return self._get_mock_doc(model_name, model_info)
    
    def generate_all(self) -> List[ModelDocumentation]:
        """Generate documentation for all models in manifest."""
        manifest = self._load_manifest()
        docs = []
        
        for node_key, node_info in manifest.get("nodes", {}).items():
            if not node_key.startswith("model."):
                continue
            
            model_name = node_info.get("name", "unknown")
            doc = self.generate_model_doc(model_name)
            docs.append(doc)
        
        logger.info(f"Generated docs for {len(docs)} models")
        return docs
    
    def export_markdown(
        self,
        docs: List[ModelDocumentation],
        output_path: str,
    ) -> str:
        """Export documentation to markdown file."""
        lines = ["# EDP-IO Data Model Documentation\n"]
        lines.append("*Auto-generated documentation for dbt models*\n")
        lines.append("---\n")
        
        # Group by schema
        by_schema: Dict[str, List[ModelDocumentation]] = {}
        for doc in docs:
            by_schema.setdefault(doc.schema, []).append(doc)
        
        for schema in ["bronze", "silver", "gold"]:
            if schema not in by_schema:
                continue
            
            lines.append(f"\n## {schema.title()} Layer\n")
            
            for doc in by_schema[schema]:
                lines.append(f"\n### {doc.model_name}\n")
                lines.append(f"**{doc.summary}**\n")
                lines.append(f"\n{doc.description}\n")
                lines.append(f"\n**Business Purpose:** {doc.business_purpose}\n")
                
                if doc.key_transformations:
                    lines.append("\n**Key Transformations:**")
                    for t in doc.key_transformations:
                        lines.append(f"- {t}")
                    lines.append("")
                
                if doc.business_rules:
                    lines.append("\n**Business Rules:**")
                    for r in doc.business_rules:
                        lines.append(f"- {r}")
                    lines.append("")
                
                if doc.usage_examples:
                    lines.append("\n**Example Usage:**")
                    lines.append("```sql")
                    lines.append(doc.usage_examples[0])
                    lines.append("```\n")
        
        content = "\n".join(lines)
        
        with open(output_path, "w") as f:
            f.write(content)
        
        logger.info(f"Documentation exported to {output_path}")
        return output_path
