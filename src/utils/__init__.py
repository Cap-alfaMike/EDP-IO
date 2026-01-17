# ============================================================================
# EDP-IO - Utilities Package
# ============================================================================
"""
EDP-IO Utility modules for security, configuration, and shared functionality.

ARCHITECTURAL NOTE:
This package contains cross-cutting concerns that are used throughout the platform.
All modules are designed with a "production-ready mock" pattern - they implement
real interfaces but can operate without cloud credentials using feature flags.
"""

from src.utils.config import Settings, get_settings
from src.utils.logging import configure_logging, get_logger
from src.utils.security import PIIMasker, SecretProvider

__all__ = [
    "Settings",
    "get_settings",
    "SecretProvider",
    "PIIMasker",
    "get_logger",
    "configure_logging",
]
