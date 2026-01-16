# ============================================================================
# EDP-IO - Security Tests
# ============================================================================
"""
Tests for security utilities including PII masking and secret management.
"""

import pytest


class TestPIIMasker:
    """Tests for PII masking utilities."""

    def test_mask_email(self):
        """Test email address masking."""
        from src.utils.security import PIIMasker

        result = PIIMasker.mask("Contact: john.doe@company.com")

        assert "john.doe@company.com" not in result
        assert "@" in result  # Structure preserved
        assert "***" in result

    def test_mask_phone_brazilian(self):
        """Test Brazilian phone number masking."""
        from src.utils.security import PIIMasker

        result = PIIMasker.mask("Call me at +55 11 99999-8888")

        assert "99999-8888" not in result
        assert "***" in result

    def test_mask_cpf(self):
        """Test CPF (Brazilian tax ID) masking."""
        from src.utils.security import PIIMasker

        result = PIIMasker.mask("CPF: 123.456.789-00")

        assert "456.789" not in result
        assert "*" in result

    def test_mask_credit_card(self):
        """Test credit card masking."""
        from src.utils.security import PIIMasker

        result = PIIMasker.mask("Card: 4111-2222-3333-4444")

        assert "2222-3333" not in result
        assert "4444" in result  # Last 4 preserved
        assert "****" in result

    def test_mask_preserves_non_pii(self):
        """Test that non-PII text is preserved."""
        from src.utils.security import PIIMasker

        text = "This is a normal message without PII."
        result = PIIMasker.mask(text)

        assert result == text

    def test_mask_dict(self):
        """Test dictionary masking."""
        from src.utils.security import PIIMasker

        data = {
            "name": "John",
            "email": "john@email.com",
            "password": "secret123",
            "api_key": "abc123",
        }

        result = PIIMasker.mask_dict(data)

        assert result["name"] == "John"
        assert result["email"] != "john@email.com"
        assert result["password"] == "********"
        assert result["api_key"] == "********"

    def test_hash_pii_deterministic(self):
        """Test PII hashing is deterministic."""
        from src.utils.security import PIIMasker

        hash1 = PIIMasker.hash_pii("test@email.com")
        hash2 = PIIMasker.hash_pii("test@email.com")
        hash3 = PIIMasker.hash_pii("different@email.com")

        assert hash1 == hash2  # Same input = same hash
        assert hash1 != hash3  # Different input = different hash
        assert len(hash1) == 16  # Fixed length


class TestSecretProvider:
    """Tests for secret provider abstraction."""

    def test_mock_provider_returns_mock_secrets(self, mock_settings):
        """Test mock provider returns expected mock values."""
        from src.utils.security import MockSecretProvider

        provider = MockSecretProvider()

        secret = provider.get("AZURE_OPENAI_KEY")

        assert secret is not None
        assert "MOCK" in secret

    def test_mock_provider_exists_check(self, mock_settings):
        """Test exists method works correctly."""
        from src.utils.security import MockSecretProvider

        provider = MockSecretProvider()

        assert provider.exists("AZURE_OPENAI_KEY") is True
        assert provider.exists("NON_EXISTENT_SECRET") is False

    def test_secret_not_found_error(self, mock_settings):
        """Test error raised for missing secrets."""
        from src.utils.security import MockSecretProvider, SecretNotFoundError

        provider = MockSecretProvider()

        with pytest.raises(SecretNotFoundError):
            provider.get("THIS_SECRET_DOES_NOT_EXIST")


class TestConfig:
    """Tests for configuration management."""

    def test_settings_defaults(self):
        """Test settings have sensible defaults."""
        from src.utils.config import Settings

        # Create with no env file
        settings = Settings(_env_file=None)

        assert settings.environment == "development"
        assert settings.enable_llm_observability is False
        assert settings.enable_real_database_connections is False

    def test_is_development_property(self):
        """Test is_development computed property."""
        from src.utils.config import Settings

        settings = Settings(_env_file=None)
        settings.environment = "development"

        assert settings.is_development is True
        assert settings.is_production is False

    def test_bronze_path_local(self):
        """Test bronze path for local development."""
        from src.utils.config import Settings

        settings = Settings(_env_file=None)
        settings.enable_azure_integration = False

        assert settings.bronze_path == settings.local_bronze_path
