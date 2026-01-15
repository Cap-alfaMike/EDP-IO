# ============================================================================
# EDP-IO - Security Module
# ============================================================================
"""
Security utilities for secret management and data protection.

ARCHITECTURAL DECISIONS:
-----------------------
1. SecretProvider abstraction enables transparent switching between:
   - Mock mode (development)
   - Azure Key Vault (production via Managed Identity)
   - Environment variables (CI/CD)

2. PIIMasker provides consistent PII protection across all layers

3. NO SECRETS IN CODE - All sensitive values retrieved via SecretProvider

PRODUCTION NOTES:
- In production, use Azure Managed Identity for authentication
- Key Vault access is role-based (RBAC)
- All access is audited via Azure Monitor

SECURITY MODEL:
- Development: Mock secrets for demo (clearly marked as MOCK)
- Staging: Real Key Vault, non-production data
- Production: Real Key Vault, production credentials, full RBAC
"""

import re
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from functools import lru_cache
import structlog

from src.utils.config import get_settings

logger = structlog.get_logger(__name__)


# ============================================================================
# Secret Provider - Abstract Interface
# ============================================================================

class BaseSecretProvider(ABC):
    """
    Abstract base class for secret providers.
    
    DESIGN PATTERN: Strategy Pattern
    WHY: Allows transparent switching between mock and real Key Vault
         based on configuration, without changing calling code.
    """
    
    @abstractmethod
    def get(self, secret_name: str) -> str:
        """
        Retrieve a secret by name.
        
        Args:
            secret_name: The name/identifier of the secret
            
        Returns:
            The secret value
            
        Raises:
            SecretNotFoundError: If secret doesn't exist
        """
        pass
    
    @abstractmethod
    def exists(self, secret_name: str) -> bool:
        """Check if a secret exists."""
        pass


class SecretNotFoundError(Exception):
    """Raised when a requested secret is not found."""
    pass


# ============================================================================
# Mock Secret Provider - For Development
# ============================================================================

class MockSecretProvider(BaseSecretProvider):
    """
    Mock secret provider for development and testing.
    
    IMPORTANT:
    - Returns clearly-marked mock values
    - Logs all access for debugging
    - Never use in production
    
    WHY MOCK?
    - Enables full development without cloud credentials
    - Allows CI/CD to run without secrets
    - Demonstrates the architecture pattern
    """
    
    # Mock secrets database - clearly marked as non-production
    _MOCK_SECRETS: Dict[str, str] = {
        # Azure OpenAI
        "AZURE_OPENAI_KEY": "MOCK-OPENAI-KEY-00000000",
        
        # Database credentials (would be real in production)
        "ORACLE_PASSWORD": "MOCK-ORACLE-PASSWORD",
        "SQLSERVER_PASSWORD": "MOCK-SQLSERVER-PASSWORD",
        
        # Connection strings
        "ADLS_CONNECTION_STRING": "MOCK-ADLS-CONNECTION-STRING",
        "DATABRICKS_TOKEN": "MOCK-DATABRICKS-TOKEN",
        
        # API keys
        "MONITORING_API_KEY": "MOCK-MONITORING-KEY",
    }
    
    def get(self, secret_name: str) -> str:
        """
        Get a mock secret value.
        
        BEHAVIOR:
        - Returns mock value if defined
        - Logs access for debugging
        - Raises error if secret not found (mimics production behavior)
        """
        secret_name_upper = secret_name.upper().replace("-", "_")
        
        if secret_name_upper in self._MOCK_SECRETS:
            logger.debug(
                "Mock secret accessed",
                secret_name=secret_name,
                provider="MockSecretProvider",
            )
            return self._MOCK_SECRETS[secret_name_upper]
        
        logger.warning(
            "Secret not found in mock provider",
            secret_name=secret_name,
        )
        raise SecretNotFoundError(f"Secret '{secret_name}' not found in mock provider")
    
    def exists(self, secret_name: str) -> bool:
        """Check if mock secret exists."""
        return secret_name.upper().replace("-", "_") in self._MOCK_SECRETS


# ============================================================================
# Azure Key Vault Secret Provider - For Production
# ============================================================================

class AzureKeyVaultSecretProvider(BaseSecretProvider):
    """
    Azure Key Vault secret provider for production use.
    
    AUTHENTICATION:
    - Uses Azure Managed Identity (DefaultAzureCredential)
    - No credentials in code - authentication is infrastructure-managed
    
    PRODUCTION FEATURES:
    - Automatic credential rotation support
    - Audit logging via Azure Monitor
    - RBAC-controlled access
    
    IMPLEMENTATION NOTE:
    This class is fully implemented but requires:
    1. Azure subscription with Key Vault
    2. Managed Identity configured on compute
    3. Proper RBAC assignments
    """
    
    def __init__(self, vault_url: str):
        """
        Initialize the Key Vault provider.
        
        Args:
            vault_url: The Key Vault URL (e.g., https://my-vault.vault.azure.net/)
        """
        self._vault_url = vault_url
        self._client = None
        
        # Lazy initialization - only import/create client when needed
        # This allows the code to load without Azure SDK in mock mode
    
    def _get_client(self):
        """Lazy-initialize the Key Vault client."""
        if self._client is None:
            try:
                from azure.identity import DefaultAzureCredential
                from azure.keyvault.secrets import SecretClient
                
                credential = DefaultAzureCredential()
                self._client = SecretClient(
                    vault_url=self._vault_url,
                    credential=credential,
                )
                logger.info(
                    "Azure Key Vault client initialized",
                    vault_url=self._vault_url,
                )
            except ImportError:
                raise RuntimeError(
                    "Azure SDK not installed. Install with: pip install azure-identity azure-keyvault-secrets"
                )
            except Exception as e:
                logger.error(
                    "Failed to initialize Key Vault client",
                    error=str(e),
                    vault_url=self._vault_url,
                )
                raise
        return self._client
    
    def get(self, secret_name: str) -> str:
        """
        Retrieve a secret from Azure Key Vault.
        
        SECURITY:
        - Uses Managed Identity (no credentials in code)
        - All access is audited
        """
        try:
            client = self._get_client()
            secret = client.get_secret(secret_name)
            
            logger.info(
                "Secret retrieved from Key Vault",
                secret_name=secret_name,
                vault_url=self._vault_url,
            )
            
            return secret.value
            
        except Exception as e:
            logger.error(
                "Failed to retrieve secret from Key Vault",
                secret_name=secret_name,
                error=str(e),
            )
            raise SecretNotFoundError(f"Failed to retrieve secret '{secret_name}': {e}")
    
    def exists(self, secret_name: str) -> bool:
        """Check if secret exists in Key Vault."""
        try:
            self.get(secret_name)
            return True
        except SecretNotFoundError:
            return False


# ============================================================================
# Secret Provider Factory
# ============================================================================

class SecretProvider:
    """
    Factory class providing a unified interface for secret retrieval.
    
    USAGE:
        # Get a secret (automatically uses correct provider based on config)
        api_key = SecretProvider.get("AZURE_OPENAI_KEY")
        
        # Check if secret exists
        if SecretProvider.exists("OPTIONAL_SECRET"):
            ...
    
    BEHAVIOR:
    - Development: Uses MockSecretProvider
    - Production (ENABLE_AZURE_INTEGRATION=true): Uses AzureKeyVaultSecretProvider
    
    THIS IS THE PUBLIC API - All modules should use this class.
    """
    
    _provider: Optional[BaseSecretProvider] = None
    
    @classmethod
    def _get_provider(cls) -> BaseSecretProvider:
        """Get or create the appropriate secret provider."""
        if cls._provider is None:
            settings = get_settings()
            
            if settings.enable_azure_integration:
                cls._provider = AzureKeyVaultSecretProvider(
                    vault_url=settings.azure_key_vault_url
                )
                logger.info(
                    "Using Azure Key Vault for secrets",
                    vault_url=settings.azure_key_vault_url,
                )
            else:
                cls._provider = MockSecretProvider()
                logger.info(
                    "Using mock secret provider (development mode)",
                    warning="Do not use mock secrets in production!",
                )
        
        return cls._provider
    
    @classmethod
    def get(cls, secret_name: str) -> str:
        """
        Get a secret value.
        
        This is the primary API for secret retrieval across the platform.
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            The secret value
            
        Example:
            >>> api_key = SecretProvider.get("AZURE_OPENAI_KEY")
        """
        return cls._get_provider().get(secret_name)
    
    @classmethod
    def exists(cls, secret_name: str) -> bool:
        """Check if a secret exists."""
        return cls._get_provider().exists(secret_name)
    
    @classmethod
    def reset(cls) -> None:
        """
        Reset the provider (useful for testing).
        
        WARNING: Only use in tests to reset state between test cases.
        """
        cls._provider = None


# ============================================================================
# PII Masking Utilities
# ============================================================================

class PIIMasker:
    """
    Utility class for masking Personally Identifiable Information (PII).
    
    COMPLIANCE:
    - GDPR, LGPD, CCPA compatible
    - Masks PII in logs, error messages, and data displays
    - Preserves data utility while protecting privacy
    
    PATTERNS DETECTED:
    - Email addresses
    - Phone numbers (Brazilian and international)
    - CPF (Brazilian tax ID)
    - Credit card numbers
    - IP addresses
    
    USAGE:
        masked_text = PIIMasker.mask("Contact: john@email.com")
        # Returns: "Contact: j***@e***.com"
    """
    
    # PII detection patterns
    _PATTERNS = {
        "email": (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            lambda m: PIIMasker._mask_email(m.group())
        ),
        "phone_br": (
            r'\b(?:\+55\s?)?\(?\d{2}\)?\s?\d{4,5}[-.\s]?\d{4}\b',
            lambda m: PIIMasker._mask_generic(m.group(), visible_start=3, visible_end=2)
        ),
        "cpf": (
            r'\b\d{3}\.?\d{3}\.?\d{3}[-.]?\d{2}\b',
            lambda m: PIIMasker._mask_generic(m.group(), visible_start=3, visible_end=2)
        ),
        "credit_card": (
            r'\b(?:\d{4}[-.\s]?){3}\d{4}\b',
            lambda m: PIIMasker._mask_credit_card(m.group())
        ),
        "ip_address": (
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            lambda m: PIIMasker._mask_generic(m.group(), visible_start=3, visible_end=0)
        ),
    }
    
    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask an email address preserving partial visibility."""
        try:
            local, domain = email.split("@")
            domain_parts = domain.split(".")
            
            masked_local = local[0] + "***" if len(local) > 1 else "***"
            masked_domain = domain_parts[0][0] + "***" if len(domain_parts[0]) > 1 else "***"
            
            return f"{masked_local}@{masked_domain}.{''.join(domain_parts[1:])}"
        except Exception:
            return "***@***.***"
    
    @staticmethod
    def _mask_generic(value: str, visible_start: int = 3, visible_end: int = 2) -> str:
        """Generic masking preserving start and end characters."""
        # Remove non-alphanumeric for consistent masking
        clean = re.sub(r'[^A-Za-z0-9]', '', value)
        
        if len(clean) <= visible_start + visible_end:
            return "*" * len(value)
        
        masked = clean[:visible_start] + "*" * (len(clean) - visible_start - visible_end)
        if visible_end > 0:
            masked += clean[-visible_end:]
        
        return masked
    
    @staticmethod
    def _mask_credit_card(card: str) -> str:
        """Mask credit card showing only last 4 digits."""
        clean = re.sub(r'[^0-9]', '', card)
        return "**** **** **** " + clean[-4:] if len(clean) >= 4 else "****"
    
    @classmethod
    def mask(cls, text: str) -> str:
        """
        Mask all detected PII in the given text.
        
        Args:
            text: The text potentially containing PII
            
        Returns:
            Text with PII masked
            
        Example:
            >>> PIIMasker.mask("Email: john.doe@company.com, CPF: 123.456.789-00")
            "Email: j***@c***.com, CPF: 123*******00"
        """
        if not text:
            return text
        
        result = text
        for pattern_name, (pattern, mask_fn) in cls._PATTERNS.items():
            result = re.sub(pattern, mask_fn, result, flags=re.IGNORECASE)
        
        return result
    
    @classmethod
    def mask_dict(cls, data: Dict[str, Any], sensitive_keys: Optional[set] = None) -> Dict[str, Any]:
        """
        Mask PII in dictionary values.
        
        Args:
            data: Dictionary to mask
            sensitive_keys: Set of keys that should always be fully masked
            
        Returns:
            Dictionary with masked values
        """
        sensitive_keys = sensitive_keys or {"password", "secret", "token", "key", "credential"}
        
        result = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Fully mask known sensitive keys
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                result[key] = "********"
            elif isinstance(value, str):
                result[key] = cls.mask(value)
            elif isinstance(value, dict):
                result[key] = cls.mask_dict(value, sensitive_keys)
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def hash_pii(cls, value: str, salt: str = "edp-io-salt") -> str:
        """
        Create a deterministic hash of PII for analytics without exposing the value.
        
        USAGE:
        - Create customer IDs for analytics
        - Link records without exposing PII
        
        Args:
            value: The PII value to hash
            salt: Salt for the hash (should be consistent within environment)
            
        Returns:
            SHA-256 hash of the value
        """
        return hashlib.sha256(f"{salt}{value}".encode()).hexdigest()[:16]
