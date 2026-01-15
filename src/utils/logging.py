# ============================================================================
# EDP-IO - Structured Logging Module
# ============================================================================
"""
Enterprise-grade structured logging with correlation and context.

ARCHITECTURAL DECISIONS:
-----------------------
1. Structured logging (JSON) for production - enables log aggregation
2. Human-readable format for development
3. Correlation IDs for request tracing
4. Automatic PII masking in logs

PRODUCTION INTEGRATION:
- Azure Monitor / Log Analytics
- Application Insights
- OpenTelemetry compatible

WHY STRUCTLOG?
- Consistent structured output
- Context binding (add fields that persist across log calls)
- Processor pipeline for transformation
- Excellent performance
"""

import sys
import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from contextvars import ContextVar
import structlog

from src.utils.config import get_settings


# Context variable for correlation ID (thread-safe)
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """
    Get the current correlation ID or generate a new one.
    
    USAGE:
    - Track requests across the system
    - Link logs from the same pipeline run
    - Enable distributed tracing
    """
    cid = _correlation_id.get()
    if cid is None:
        cid = str(uuid.uuid4())[:8]  # Short ID for readability
        _correlation_id.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set a specific correlation ID (e.g., from an incoming request)."""
    _correlation_id.set(correlation_id)


def add_correlation_id(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Processor to add correlation ID to all log entries."""
    event_dict["correlation_id"] = get_correlation_id()
    return event_dict


def add_timestamp(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Processor to add ISO timestamp to all log entries."""
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_service_info(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Processor to add service metadata."""
    settings = get_settings()
    event_dict["service"] = "edp-io"
    event_dict["environment"] = settings.environment
    return event_dict


def mask_sensitive_data(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Processor to mask sensitive data in logs.
    
    SECURITY: Prevents accidental PII/secrets in logs.
    """
    from src.utils.security import PIIMasker
    
    sensitive_keys = {"password", "secret", "token", "key", "credential", "api_key"}
    
    for key, value in list(event_dict.items()):
        key_lower = key.lower()
        
        # Fully mask known sensitive keys
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            event_dict[key] = "********"
        elif isinstance(value, str) and len(value) > 0:
            # Apply PII masking to string values
            event_dict[key] = PIIMasker.mask(value)
    
    return event_dict


def configure_logging() -> None:
    """
    Configure structured logging for the application.
    
    Call this once at application startup.
    
    BEHAVIOR:
    - Development: Human-readable colored output
    - Production: JSON output for log aggregation
    """
    settings = get_settings()
    
    # Common processors for all environments
    shared_processors = [
        structlog.stdlib.add_log_level,
        add_timestamp,
        add_correlation_id,
        add_service_info,
        mask_sensitive_data,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.log_format == "json" or settings.is_production:
        # Production: JSON format for log aggregation
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Human-readable format
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a logger instance with optional name binding.
    
    USAGE:
        logger = get_logger(__name__)
        logger.info("Processing started", records=1000)
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(module=name)
    return logger


# Pipeline execution context manager
class PipelineContext:
    """
    Context manager for pipeline execution logging.
    
    Provides:
    - Automatic correlation ID management
    - Start/end logging
    - Duration tracking
    - Error context
    
    USAGE:
        with PipelineContext("bronze_ingestion", source="oracle"):
            # Pipeline code here
            pass
    """
    
    def __init__(self, pipeline_name: str, **context):
        self.pipeline_name = pipeline_name
        self.context = context
        self.logger = get_logger("pipeline")
        self.start_time = None
    
    def __enter__(self):
        # Generate new correlation ID for this pipeline run
        self.correlation_id = str(uuid.uuid4())[:8]
        set_correlation_id(self.correlation_id)
        
        self.start_time = datetime.now(timezone.utc)
        self.logger.info(
            "Pipeline started",
            pipeline=self.pipeline_name,
            **self.context,
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        if exc_type is not None:
            self.logger.error(
                "Pipeline failed",
                pipeline=self.pipeline_name,
                duration_seconds=duration,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context,
            )
        else:
            self.logger.info(
                "Pipeline completed",
                pipeline=self.pipeline_name,
                duration_seconds=duration,
                **self.context,
            )
        
        return False  # Don't suppress exceptions


# ============================================================================
# Initialize logging on module import
# ============================================================================
# Note: This is called automatically, but can be called again to reconfigure
configure_logging()
