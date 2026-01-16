# ============================================================================
# EDP-IO - RAG Context Provider for LLM Observability
# ============================================================================
"""
Retrieval-Augmented Generation (RAG) context provider.

PURPOSE:
-------
Provides relevant context to LLM observability modules by retrieving:
- Data contracts (schema definitions)
- dbt documentation (manifest.json, catalog.json)
- Historical error logs and resolutions
- Lineage information

ARCHITECTURE:
------------
This implements a CHAINED RAG pattern:

1. Query Understanding → LLM classifies the query type
2. Context Retrieval → Fetch relevant documents from vector store
3. Context Ranking → Re-rank by relevance to specific query
4. Response Generation → LLM generates response with context

WHY RAG FOR OBSERVABILITY?
-------------------------
- LLMs hallucinate less with grounded context
- Platform-specific knowledge (data contracts, lineage)
- Historical context (what worked before for similar errors)
- Reduces token usage (only relevant context)

VECTOR STORE:
------------
Uses ChromaDB for simplicity (local, no infra needed).
In production, migrate to Azure AI Search or Pinecone.

MOCK MODE:
---------
When ENABLE_LLM_OBSERVABILITY=false, returns mock context.
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.utils.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class QueryType(str, Enum):
    """Types of queries for routing to appropriate context."""

    ERROR_ANALYSIS = "error_analysis"
    SCHEMA_QUESTION = "schema_question"
    LINEAGE_QUESTION = "lineage_question"
    DOCUMENTATION = "documentation"
    GENERAL = "general"


class ContextChunk(BaseModel):
    """A chunk of context retrieved for RAG."""

    content: str = Field(description="The text content")
    source: str = Field(description="Source of the content (file path, table name)")
    chunk_type: str = Field(description="Type: contract, manifest, log, doc")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGContext(BaseModel):
    """Full context for LLM with retrieved chunks."""

    query: str = Field(description="Original query")
    query_type: QueryType = Field(description="Classified query type")
    chunks: List[ContextChunk] = Field(default_factory=list)
    total_tokens: int = Field(default=0, description="Estimated token count")

    def to_prompt_context(self) -> str:
        """Format context for LLM prompt."""
        if not self.chunks:
            return "No relevant context found."

        context_parts = []
        for i, chunk in enumerate(self.chunks[:5], 1):  # Max 5 chunks
            context_parts.append(
                f"[{i}] Source: {chunk.source}\n"
                f"Type: {chunk.chunk_type}\n"
                f"Content:\n{chunk.content}\n"
            )

        return "\n---\n".join(context_parts)


class RAGContextProvider:
    """
    Provides RAG context for LLM observability.

    USAGE:
        provider = RAGContextProvider()

        # Get context for error analysis
        context = provider.get_context(
            query="Column 'loyalty_points' not found",
            query_type=QueryType.ERROR_ANALYSIS,
        )

        # Use in LLM prompt
        prompt = f"Context:\n{context.to_prompt_context()}\n\nQuery: {query}"

    CHAINED RAG PATTERN:
    1. Classify query → Route to appropriate retriever
    2. Retrieve relevant chunks
    3. Re-rank by relevance
    4. Return formatted context
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the RAG context provider.

        Args:
            project_root: Root path of the project (for finding contracts, dbt)
        """
        self.settings = get_settings()
        self.project_root = Path(project_root or ".")
        self._vector_store = None
        self._documents_loaded = False

        logger.info(
            "RAGContextProvider initialized",
            llm_enabled=self.settings.enable_llm_observability,
        )

    @property
    def is_enabled(self) -> bool:
        """Check if RAG is enabled (depends on LLM setting)."""
        return self.settings.enable_llm_observability

    # =========================================================================
    # DOCUMENT LOADING
    # =========================================================================

    def _load_data_contracts(self) -> List[ContextChunk]:
        """Load data contracts from YAML."""
        import yaml

        contracts_path = self.project_root / "src/ingestion/data_contracts/contracts.yaml"
        chunks = []

        if contracts_path.exists():
            with open(contracts_path) as f:
                contracts = yaml.safe_load(f)

            for table_name, contract in contracts.items():
                chunks.append(
                    ContextChunk(
                        content=yaml.dump({table_name: contract}, default_flow_style=False),
                        source=f"contracts.yaml#{table_name}",
                        chunk_type="contract",
                        metadata={
                            "table": table_name,
                            "source_system": contract.get("source_system"),
                            "owner": contract.get("owner"),
                        },
                    )
                )

        logger.info(f"Loaded {len(chunks)} data contract chunks")
        return chunks

    def _load_dbt_manifest(self) -> List[ContextChunk]:
        """Load dbt manifest for model documentation."""
        manifest_path = self.project_root / "dbt_project/target/manifest.json"
        chunks = []

        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)

            for node_key, node in manifest.get("nodes", {}).items():
                if not node_key.startswith("model."):
                    continue

                model_info = {
                    "name": node.get("name"),
                    "description": node.get("description", ""),
                    "schema": node.get("schema"),
                    "columns": list(node.get("columns", {}).keys()),
                    "depends_on": node.get("depends_on", {}).get("nodes", []),
                }

                chunks.append(
                    ContextChunk(
                        content=json.dumps(model_info, indent=2),
                        source=f"manifest.json#{node.get('name')}",
                        chunk_type="manifest",
                        metadata=model_info,
                    )
                )
        else:
            # Mock manifest for development
            mock_models = [
                {
                    "name": "stg_customers",
                    "schema": "silver",
                    "description": "Staged customers with SCD2",
                },
                {
                    "name": "stg_products",
                    "schema": "silver",
                    "description": "Staged products with pricing history",
                },
                {"name": "dim_customer", "schema": "gold", "description": "Customer dimension"},
                {
                    "name": "fact_sales",
                    "schema": "gold",
                    "description": "Sales fact at order line grain",
                },
            ]
            for model in mock_models:
                chunks.append(
                    ContextChunk(
                        content=json.dumps(model, indent=2),
                        source=f"manifest.json#{model['name']}",
                        chunk_type="manifest",
                        metadata=model,
                    )
                )

        logger.info(f"Loaded {len(chunks)} dbt manifest chunks")
        return chunks

    def _load_error_history(self) -> List[ContextChunk]:
        """Load historical error resolutions for similar error matching."""
        # In production: Load from database or log aggregator
        # For mock: Return sample error patterns

        error_patterns = [
            {
                "error": "Column 'X' not found in schema",
                "root_cause": "Schema drift - new column added in source",
                "resolution": "1. Update data contract\n2. Add column to Bronze schema\n3. Reprocess",
                "category": "schema_drift",
            },
            {
                "error": "Connection refused by Oracle",
                "root_cause": "Database maintenance window or network issue",
                "resolution": "1. Check Oracle status\n2. Verify network\n3. Retry with backoff",
                "category": "connection",
            },
            {
                "error": "Null values in required column",
                "root_cause": "Data quality issue in source",
                "resolution": "1. Quarantine records\n2. Notify source owner\n3. Review validation rules",
                "category": "data_quality",
            },
            {
                "error": "MERGE failed - duplicate keys",
                "root_cause": "Business key collision in source data",
                "resolution": "1. Check source deduplication\n2. Review business key definition\n3. Add tie-breaker column",
                "category": "idempotency",
            },
        ]

        chunks = []
        for pattern in error_patterns:
            chunks.append(
                ContextChunk(
                    content=json.dumps(pattern, indent=2),
                    source="error_history",
                    chunk_type="error_pattern",
                    metadata={"category": pattern["category"]},
                )
            )

        logger.info(f"Loaded {len(chunks)} error history chunks")
        return chunks

    # =========================================================================
    # QUERY CLASSIFICATION
    # =========================================================================

    def classify_query(self, query: str) -> QueryType:
        """
        Classify query to route to appropriate context.

        In production with LLM enabled, this uses an LLM call.
        In mock mode, uses keyword matching.
        """
        query_lower = query.lower()

        # Keyword-based classification (fast, no LLM needed)
        if any(word in query_lower for word in ["error", "fail", "exception", "traceback"]):
            return QueryType.ERROR_ANALYSIS
        elif any(word in query_lower for word in ["schema", "column", "field", "type"]):
            return QueryType.SCHEMA_QUESTION
        elif any(word in query_lower for word in ["lineage", "upstream", "downstream", "depends"]):
            return QueryType.LINEAGE_QUESTION
        elif any(word in query_lower for word in ["what is", "explain", "document", "how does"]):
            return QueryType.DOCUMENTATION
        else:
            return QueryType.GENERAL

    # =========================================================================
    # CONTEXT RETRIEVAL
    # =========================================================================

    def get_context(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        max_chunks: int = 5,
    ) -> RAGContext:
        """
        Get relevant context for a query.

        Args:
            query: The user query or error message
            query_type: Optional pre-classified type
            max_chunks: Maximum chunks to return

        Returns:
            RAGContext with relevant chunks for LLM prompt
        """
        # Classify if not provided
        if query_type is None:
            query_type = self.classify_query(query)

        logger.info(
            "Getting RAG context",
            query_type=query_type.value,
            query_length=len(query),
        )

        # Route to appropriate retriever
        if query_type == QueryType.ERROR_ANALYSIS:
            chunks = self._retrieve_for_error(query)
        elif query_type == QueryType.SCHEMA_QUESTION:
            chunks = self._retrieve_for_schema(query)
        elif query_type == QueryType.LINEAGE_QUESTION:
            chunks = self._retrieve_for_lineage(query)
        else:
            chunks = self._retrieve_general(query)

        # Score and rank
        ranked_chunks = self._rank_chunks(chunks, query)[:max_chunks]

        # Estimate tokens (rough: 4 chars per token)
        total_content = sum(len(c.content) for c in ranked_chunks)
        estimated_tokens = total_content // 4

        return RAGContext(
            query=query,
            query_type=query_type,
            chunks=ranked_chunks,
            total_tokens=estimated_tokens,
        )

    def _retrieve_for_error(self, query: str) -> List[ContextChunk]:
        """Retrieve context for error analysis."""
        chunks = []
        chunks.extend(self._load_error_history())
        chunks.extend(self._load_data_contracts())  # Schema context helps
        return chunks

    def _retrieve_for_schema(self, query: str) -> List[ContextChunk]:
        """Retrieve context for schema questions."""
        chunks = []
        chunks.extend(self._load_data_contracts())
        chunks.extend(self._load_dbt_manifest())
        return chunks

    def _retrieve_for_lineage(self, query: str) -> List[ContextChunk]:
        """Retrieve context for lineage questions."""
        return self._load_dbt_manifest()

    def _retrieve_general(self, query: str) -> List[ContextChunk]:
        """Retrieve general context."""
        chunks = []
        chunks.extend(self._load_data_contracts())
        chunks.extend(self._load_dbt_manifest())
        return chunks

    def _rank_chunks(
        self,
        chunks: List[ContextChunk],
        query: str,
    ) -> List[ContextChunk]:
        """
        Rank chunks by relevance to query.

        In production with LLM: Use embedding similarity.
        In mock mode: Simple keyword matching.
        """
        query_words = set(query.lower().split())

        for chunk in chunks:
            content_words = set(chunk.content.lower().split())
            overlap = len(query_words & content_words)
            chunk.relevance_score = min(overlap / max(len(query_words), 1), 1.0)

        # Sort by relevance
        return sorted(chunks, key=lambda c: c.relevance_score, reverse=True)


# ============================================================================
# Integration with LogAnalyzer
# ============================================================================


class RAGEnhancedLogAnalyzer:
    """
    Log analyzer enhanced with RAG context.

    CHAINED LLM PATTERN:
    1. RAG retrieves relevant context (contracts, past errors)
    2. Context is injected into prompt
    3. LLM generates analysis with grounded information
    """

    def __init__(self):
        from src.observability.log_analyzer import LogAnalyzer

        self.log_analyzer = LogAnalyzer()
        self.rag_provider = RAGContextProvider()

    def analyze_with_context(self, error_log: str) -> dict:
        """
        Analyze error with RAG-enhanced context.

        Returns both the analysis and the context used.
        """
        # Get relevant context
        context = self.rag_provider.get_context(
            query=error_log,
            query_type=QueryType.ERROR_ANALYSIS,
        )

        # Analyze with context
        analysis = self.log_analyzer.analyze(
            error_log,
            context={"rag_context": context.to_prompt_context()},
        )

        return {
            "analysis": analysis,
            "context_used": context,
            "chunks_count": len(context.chunks),
        }
