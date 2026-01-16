# ============================================================================
# EDP-IO - Cloud Providers Package
# ============================================================================
"""
Multi-cloud provider abstractions for platform portability.

DESIGN PHILOSOPHY:
-----------------
1. INTERFACE SEGREGATION: Each cloud concern has its own abstract interface
2. DEPENDENCY INJECTION: Providers are injected via configuration
3. FEATURE FLAGS: Control which provider is active via environment
4. MOCK FIRST: All providers have mock implementations for development

PROVIDER CATEGORIES:
- StorageProvider: Object/blob storage (ADLS, GCS, S3)
- ComputeProvider: Spark clusters (Databricks, Dataproc, EMR)
- LLMProvider: Language models (Azure OpenAI, Vertex AI, Bedrock)
- ServerlessProvider: Functions/containers (Azure Functions, Cloud Run, Lambda)

USAGE:
    from src.providers import get_storage_provider, get_llm_provider

    storage = get_storage_provider()  # Returns configured provider
    storage.upload("path/to/file", "container/key")

    llm = get_llm_provider()
    response = llm.chat([{"role": "user", "content": "Hello"}])

CONFIGURATION:
    Set via environment variables:
    - CLOUD_PROVIDER: azure | gcp | aws
    - SERVERLESS_MODE: true | false
"""

from src.providers.compute import ComputeProvider, get_compute_provider
from src.providers.llm import LLMProvider, get_llm_provider
from src.providers.serverless import (ServerlessProvider,
                                      get_serverless_provider)
from src.providers.storage import StorageProvider, get_storage_provider

__all__ = [
    # Storage
    "StorageProvider",
    "get_storage_provider",
    # Compute
    "ComputeProvider",
    "get_compute_provider",
    # LLM
    "LLMProvider",
    "get_llm_provider",
    # Serverless
    "ServerlessProvider",
    "get_serverless_provider",
]
