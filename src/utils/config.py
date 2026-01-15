# ============================================================================
# EDP-IO - Configuration Management
# ============================================================================
"""
Centralized configuration management with environment-aware settings.

ARCHITECTURAL DECISIONS:
-----------------------
1. Pydantic Settings for type-safe configuration validation
2. Feature flags for controlling mock vs. real service integration
3. Environment-based configuration (dev/staging/prod)
4. No secrets in code - all secrets resolved via SecretProvider

PRODUCTION NOTES:
- In production, ENABLE_AZURE_INTEGRATION would be True
- Secrets would be retrieved from Azure Key Vault via Managed Identity
- This module would not change - only environment configuration
"""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings with validation and environment variable support.
    
    DESIGN PATTERN: Singleton-like access via get_settings()
    WHY: Ensures consistent configuration across all modules and allows
         for easy testing via dependency injection.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars for flexibility
    )
    
    # -------------------------------------------------------------------------
    # Environment Configuration
    # -------------------------------------------------------------------------
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment. Controls logging, error handling, and integrations.",
    )
    
    # -------------------------------------------------------------------------
    # Feature Flags - CRITICAL for mock vs. production behavior
    # -------------------------------------------------------------------------
    enable_llm_observability: bool = Field(
        default=False,
        description="Enable Azure OpenAI integration. When False, uses mock responses.",
    )
    
    enable_real_database_connections: bool = Field(
        default=False,
        description="Enable real database connections. When False, uses generated mock data.",
    )
    
    enable_azure_integration: bool = Field(
        default=False,
        description="Enable Azure service integration. When False, uses local mocks.",
    )
    
    # -------------------------------------------------------------------------
    # Azure Configuration
    # -------------------------------------------------------------------------
    azure_tenant_id: str = Field(
        default="00000000-0000-0000-0000-000000000000",
        description="Azure Active Directory tenant ID.",
    )
    
    azure_subscription_id: str = Field(
        default="00000000-0000-0000-0000-000000000000",
        description="Azure subscription ID.",
    )
    
    azure_resource_group: str = Field(
        default="rg-edp-io-dev",
        description="Azure resource group name.",
    )
    
    azure_key_vault_url: str = Field(
        default="https://kv-edp-io-dev.vault.azure.net/",
        description="Azure Key Vault URL for secrets management.",
    )
    
    # -------------------------------------------------------------------------
    # Azure OpenAI (LLM Observability)
    # -------------------------------------------------------------------------
    azure_openai_endpoint: str = Field(
        default="https://edp-io-openai.openai.azure.com/",
        description="Azure OpenAI endpoint URL.",
    )
    
    azure_openai_api_version: str = Field(
        default="2024-02-01",
        description="Azure OpenAI API version.",
    )
    
    azure_openai_deployment_name: str = Field(
        default="gpt-4o",
        description="Azure OpenAI deployment/model name.",
    )
    
    # -------------------------------------------------------------------------
    # Data Lake Configuration
    # -------------------------------------------------------------------------
    adls_account_name: str = Field(
        default="adlsedpiodev",
        description="Azure Data Lake Storage Gen2 account name.",
    )
    
    adls_container_bronze: str = Field(
        default="bronze",
        description="Container for Bronze layer (raw data).",
    )
    
    adls_container_silver: str = Field(
        default="silver",
        description="Container for Silver layer (cleaned data).",
    )
    
    adls_container_gold: str = Field(
        default="gold",
        description="Container for Gold layer (analytical models).",
    )
    
    # -------------------------------------------------------------------------
    # Databricks Configuration
    # -------------------------------------------------------------------------
    databricks_host: str = Field(
        default="https://adb-1234567890123456.7.azuredatabricks.net",
        description="Databricks workspace URL.",
    )
    
    databricks_http_path: str = Field(
        default="/sql/1.0/warehouses/abcdef1234567890",
        description="Databricks SQL warehouse HTTP path.",
    )
    
    # -------------------------------------------------------------------------
    # Local Development Paths
    # -------------------------------------------------------------------------
    local_data_path: str = Field(
        default="./data",
        description="Local path for data storage during development.",
    )
    
    local_bronze_path: str = Field(
        default="./data/bronze",
        description="Local path for Bronze layer.",
    )
    
    local_silver_path: str = Field(
        default="./data/silver",
        description="Local path for Silver layer.",
    )
    
    local_gold_path: str = Field(
        default="./data/gold",
        description="Local path for Gold layer.",
    )
    
    # -------------------------------------------------------------------------
    # Logging Configuration
    # -------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application log level.",
    )
    
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format. JSON recommended for production.",
    )
    
    # -------------------------------------------------------------------------
    # Streamlit Configuration
    # -------------------------------------------------------------------------
    streamlit_server_port: int = Field(
        default=8501,
        description="Streamlit server port.",
    )
    
    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    @property
    def bronze_path(self) -> str:
        """
        Get the Bronze layer path based on environment.
        
        PRODUCTION: Returns ADLS path
        DEVELOPMENT: Returns local path
        """
        if self.enable_azure_integration:
            return f"abfss://{self.adls_container_bronze}@{self.adls_account_name}.dfs.core.windows.net/"
        return self.local_bronze_path
    
    @property
    def silver_path(self) -> str:
        """Get the Silver layer path based on environment."""
        if self.enable_azure_integration:
            return f"abfss://{self.adls_container_silver}@{self.adls_account_name}.dfs.core.windows.net/"
        return self.local_silver_path
    
    @property
    def gold_path(self) -> str:
        """Get the Gold layer path based on environment."""
        if self.enable_azure_integration:
            return f"abfss://{self.adls_container_gold}@{self.adls_account_name}.dfs.core.windows.net/"
        return self.local_gold_path


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    DESIGN PATTERN: Singleton via lru_cache
    WHY: Avoids re-parsing environment on every access while still allowing
         fresh settings if cache is cleared (useful for testing).
    
    USAGE:
        settings = get_settings()
        if settings.enable_llm_observability:
            # Use real LLM
        else:
            # Use mock
    """
    return Settings()


# ============================================================================
# Module-level convenience exports
# ============================================================================
settings = get_settings()
