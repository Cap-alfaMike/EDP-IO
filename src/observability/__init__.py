# ============================================================================
# EDP-IO - Observability Package
# ============================================================================
"""
Module C: Intelligent Observability with LLM

This package provides LLM-powered observability features for the data platform.
The LLM acts as an ADVISOR ONLY - it never executes actions or transforms data.

CORE PRINCIPLES:
---------------
1. ADVISOR-ONLY: LLM suggests, humans approve
2. DETERMINISTIC PIPELINES: No LLM in data transformation
3. STRUCTURED OUTPUT: All LLM responses follow defined schemas
4. FEATURE FLAG: Disable LLM entirely via ENABLE_LLM_OBSERVABILITY
5. RAG-ENHANCED: Context retrieval for grounded responses
6. METRICS-TRACKED: All LLM calls are monitored for cost/quality

COMPONENTS:
- log_analyzer.py: Analyzes pipeline errors and suggests fixes
- schema_drift.py: Detects and assesses schema changes
- doc_generator.py: Auto-generates documentation from dbt models
- rag_context.py: RAG context provider for chained LLM architecture
- llm_metrics.py: Metrics tracking for LLM usage and costs
"""

from src.observability.log_analyzer import LogAnalyzer, ErrorAnalysis
from src.observability.schema_drift import SchemaDriftDetector, DriftReport
from src.observability.doc_generator import DocGenerator
from src.observability.rag_context import (
    RAGContextProvider,
    RAGContext,
    QueryType,
    RAGEnhancedLogAnalyzer,
)
from src.observability.llm_metrics import (
    LLMMetricsTracker,
    LLMAnalytics,
    LLMRole,
    LLMModel,
    get_metrics_store,
)

__all__ = [
    # Log Analysis
    "LogAnalyzer",
    "ErrorAnalysis",
    # Schema Drift
    "SchemaDriftDetector",
    "DriftReport",
    # Documentation
    "DocGenerator",
    # RAG Context
    "RAGContextProvider",
    "RAGContext",
    "QueryType",
    "RAGEnhancedLogAnalyzer",
    # LLM Metrics
    "LLMMetricsTracker",
    "LLMAnalytics",
    "LLMRole",
    "LLMModel",
    "get_metrics_store",
]
