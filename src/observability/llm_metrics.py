# ============================================================================
# EDP-IO - LLM Metrics Tracker
# ============================================================================
"""
Tracks and stores metrics for all LLM calls in the platform.

METRICS TRACKED:
---------------
- Token usage (input, output, total)
- Latency (response time)
- Cost (based on model pricing)
- Role/component (log_analyzer, schema_drift, doc_gen, chatbot)
- Confidence scores
- Human approval outcomes

WHY TRACK LLM METRICS?
---------------------
1. Cost Management: Monitor and optimize token usage
2. Performance: Identify slow calls, optimize prompts
3. Quality: Track confidence scores over time
4. Compliance: Audit trail for LLM decisions
5. Capacity Planning: Predict API usage patterns

STORAGE:
-------
In production: Azure Cosmos DB or dedicated time-series DB
For mock: In-memory with persistence to JSON
"""

import json
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class LLMRole(str, Enum):
    """Roles/components that use LLM."""

    LOG_ANALYZER = "log_analyzer"
    SCHEMA_DRIFT = "schema_drift"
    DOC_GENERATOR = "doc_generator"
    RAG_CLASSIFIER = "rag_classifier"
    CHATBOT = "chatbot"
    GENERAL = "general"


class LLMModel(str, Enum):
    """LLM models used."""

    GPT4 = "gpt-4"
    GPT4_TURBO = "gpt-4-turbo"
    GPT35_TURBO = "gpt-3.5-turbo"
    MOCK = "mock"


# Pricing per 1K tokens (as of 2024)
MODEL_PRICING = {
    LLMModel.GPT4: {"input": 0.03, "output": 0.06},
    LLMModel.GPT4_TURBO: {"input": 0.01, "output": 0.03},
    LLMModel.GPT35_TURBO: {"input": 0.0005, "output": 0.0015},
    LLMModel.MOCK: {"input": 0.0, "output": 0.0},
}


@dataclass
class LLMCallMetrics:
    """Metrics for a single LLM call."""

    call_id: str
    timestamp: datetime
    role: LLMRole
    model: LLMModel

    # Token usage
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Performance
    latency_ms: float

    # Cost
    cost_usd: float

    # Quality
    confidence_score: Optional[float] = None
    human_approved: Optional[bool] = None

    # Context
    query_type: Optional[str] = None
    rag_chunks_used: int = 0

    # Metadata
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat(),
            "role": self.role.value,
            "model": self.model.value,
        }


class LLMMetricsStore:
    """
    In-memory store for LLM metrics with persistence.

    Thread-safe for concurrent access.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._metrics: List[LLMCallMetrics] = []
        self._lock = threading.Lock()
        self._persist_path = Path(persist_path or "data/llm_metrics.json")

        # Load existing metrics
        self._load()

    def add(self, metric: LLMCallMetrics) -> None:
        """Add a metric to the store."""
        with self._lock:
            self._metrics.append(metric)

            # Persist periodically (every 10 calls)
            if len(self._metrics) % 10 == 0:
                self._persist()

    def get_all(self) -> List[LLMCallMetrics]:
        """Get all metrics."""
        with self._lock:
            return list(self._metrics)

    def get_by_role(self, role: LLMRole) -> List[LLMCallMetrics]:
        """Get metrics filtered by role."""
        with self._lock:
            return [m for m in self._metrics if m.role == role]

    def get_by_timerange(
        self, start: datetime, end: Optional[datetime] = None
    ) -> List[LLMCallMetrics]:
        """Get metrics within a time range."""
        end = end or datetime.now(timezone.utc)
        with self._lock:
            return [m for m in self._metrics if start <= m.timestamp <= end]

    def _persist(self) -> None:
        """Persist metrics to disk."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "w") as f:
                json.dump([m.to_dict() for m in self._metrics], f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist metrics: {e}")

    def _load(self) -> None:
        """Load metrics from disk."""
        if not self._persist_path.exists():
            return

        try:
            with open(self._persist_path) as f:
                data = json.load(f)

            for item in data:
                item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                item["role"] = LLMRole(item["role"])
                item["model"] = LLMModel(item["model"])
                self._metrics.append(LLMCallMetrics(**item))

            logger.info(f"Loaded {len(self._metrics)} historical metrics")
        except Exception as e:
            logger.warning(f"Failed to load metrics: {e}")


# Singleton store
_metrics_store: Optional[LLMMetricsStore] = None


def get_metrics_store() -> LLMMetricsStore:
    """Get the singleton metrics store."""
    global _metrics_store
    if _metrics_store is None:
        _metrics_store = LLMMetricsStore()
    return _metrics_store


class LLMMetricsTracker:
    """
    Context manager for tracking LLM call metrics.

    USAGE:
        with LLMMetricsTracker(role=LLMRole.LOG_ANALYZER) as tracker:
            response = llm.chat(messages)
            tracker.set_tokens(response.usage.input, response.usage.output)
            tracker.set_confidence(0.85)

    Automatically records latency and persists to store.
    """

    def __init__(
        self,
        role: LLMRole,
        model: LLMModel = LLMModel.GPT4,
        call_id: Optional[str] = None,
    ):
        self.role = role
        self.model = model
        self.call_id = call_id or f"{role.value}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._input_tokens = 0
        self._output_tokens = 0
        self._confidence: Optional[float] = None
        self._human_approved: Optional[bool] = None
        self._query_type: Optional[str] = None
        self._rag_chunks = 0
        self._success = True
        self._error: Optional[str] = None

    def __enter__(self) -> "LLMMetricsTracker":
        self._start_time = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._end_time = datetime.now(timezone.utc)

        if exc_type is not None:
            self._success = False
            self._error = str(exc_val)

        # Calculate metrics
        latency_ms = (self._end_time - self._start_time).total_seconds() * 1000

        pricing = MODEL_PRICING.get(self.model, {"input": 0, "output": 0})
        cost = (self._input_tokens / 1000) * pricing["input"] + (
            self._output_tokens / 1000
        ) * pricing["output"]

        # Create and store metric
        metric = LLMCallMetrics(
            call_id=self.call_id,
            timestamp=self._start_time,
            role=self.role,
            model=self.model,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            total_tokens=self._input_tokens + self._output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            confidence_score=self._confidence,
            human_approved=self._human_approved,
            query_type=self._query_type,
            rag_chunks_used=self._rag_chunks,
            success=self._success,
            error_message=self._error,
        )

        get_metrics_store().add(metric)

        logger.debug(
            "LLM call tracked",
            call_id=self.call_id,
            role=self.role.value,
            tokens=metric.total_tokens,
            latency_ms=latency_ms,
            cost=cost,
        )

    def set_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Set token counts from LLM response."""
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens

    def set_confidence(self, score: float) -> None:
        """Set confidence score from LLM response."""
        self._confidence = score

    def set_human_approved(self, approved: bool) -> None:
        """Record human approval decision."""
        self._human_approved = approved

    def set_query_type(self, query_type: str) -> None:
        """Set the query type."""
        self._query_type = query_type

    def set_rag_chunks(self, count: int) -> None:
        """Set number of RAG chunks used."""
        self._rag_chunks = count


class LLMAnalytics:
    """
    Compute analytics over LLM metrics.

    Provides aggregations for dashboard visualization.
    """

    def __init__(self, store: Optional[LLMMetricsStore] = None):
        self.store = store or get_metrics_store()

    def get_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary statistics for the last N days."""
        start = datetime.now(timezone.utc) - timedelta(days=days)
        metrics = self.store.get_by_timerange(start)

        if not metrics:
            return self._empty_summary()

        return {
            "total_calls": len(metrics),
            "total_tokens": sum(m.total_tokens for m in metrics),
            "total_cost_usd": sum(m.cost_usd for m in metrics),
            "avg_latency_ms": sum(m.latency_ms for m in metrics) / len(metrics),
            "success_rate": sum(1 for m in metrics if m.success) / len(metrics) * 100,
            "avg_confidence": self._avg_confidence(metrics),
            "human_approval_rate": self._approval_rate(metrics),
            "period_days": days,
        }

    def get_by_role(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """Get statistics grouped by role."""
        start = datetime.now(timezone.utc) - timedelta(days=days)
        metrics = self.store.get_by_timerange(start)

        by_role = defaultdict(list)
        for m in metrics:
            by_role[m.role.value].append(m)

        result = {}
        for role, role_metrics in by_role.items():
            result[role] = {
                "calls": len(role_metrics),
                "tokens": sum(m.total_tokens for m in role_metrics),
                "cost_usd": sum(m.cost_usd for m in role_metrics),
                "avg_latency_ms": sum(m.latency_ms for m in role_metrics) / len(role_metrics),
                "avg_confidence": self._avg_confidence(role_metrics),
            }

        return result

    def get_daily_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily aggregated metrics."""
        start = datetime.now(timezone.utc) - timedelta(days=days)
        metrics = self.store.get_by_timerange(start)

        by_day = defaultdict(list)
        for m in metrics:
            day_key = m.timestamp.strftime("%Y-%m-%d")
            by_day[day_key].append(m)

        trend = []
        for day, day_metrics in sorted(by_day.items()):
            trend.append(
                {
                    "date": day,
                    "calls": len(day_metrics),
                    "tokens": sum(m.total_tokens for m in day_metrics),
                    "cost_usd": sum(m.cost_usd for m in day_metrics),
                    "avg_latency_ms": sum(m.latency_ms for m in day_metrics) / len(day_metrics),
                }
            )

        return trend

    def get_cost_breakdown(self, days: int = 7) -> Dict[str, float]:
        """Get cost breakdown by model."""
        start = datetime.now(timezone.utc) - timedelta(days=days)
        metrics = self.store.get_by_timerange(start)

        by_model = defaultdict(float)
        for m in metrics:
            by_model[m.model.value] += m.cost_usd

        return dict(by_model)

    def _avg_confidence(self, metrics: List[LLMCallMetrics]) -> Optional[float]:
        """Calculate average confidence score."""
        scores = [m.confidence_score for m in metrics if m.confidence_score is not None]
        return sum(scores) / len(scores) if scores else None

    def _approval_rate(self, metrics: List[LLMCallMetrics]) -> Optional[float]:
        """Calculate human approval rate."""
        approvals = [m.human_approved for m in metrics if m.human_approved is not None]
        return sum(1 for a in approvals if a) / len(approvals) * 100 if approvals else None

    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary when no data."""
        return {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "success_rate": 0.0,
            "avg_confidence": None,
            "human_approval_rate": None,
            "period_days": 0,
        }
