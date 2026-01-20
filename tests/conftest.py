# ============================================================================
# EDP-IO - pytest Configuration
# ============================================================================
"""
Shared fixtures and configuration for tests.
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_settings():
    """Mock settings for testing without .env file."""
    with patch("src.utils.config.get_settings") as mock:
        settings = MagicMock()
        settings.environment = "development"
        settings.enable_llm_observability = False
        settings.enable_real_database_connections = False
        settings.enable_azure_integration = False
        settings.log_level = "DEBUG"
        settings.bronze_path = "./test_data/bronze"
        settings.silver_path = "./test_data/silver"
        settings.gold_path = "./test_data/gold"
        settings.is_development = True
        settings.is_production = False
        mock.return_value = settings
        yield settings


@pytest.fixture
def mock_secret_provider():
    """Mock secret provider for testing."""
    with patch("src.utils.security.SecretProvider") as mock:
        mock.get.return_value = "MOCK-SECRET-VALUE"
        mock.exists.return_value = True
        yield mock


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return [
        {
            "customer_id": "CUST-00000001",
            "first_name": "João",
            "last_name": "Silva",
            "email": "joao.silva@email.com",
            "phone": "+5511999999999",
            "city": "São Paulo",
            "state": "SP",
            "country_code": "BR",
            "customer_segment": "GOLD",
            "registration_date": datetime(2023, 1, 15).date(),
            "is_active": True,
            "created_at": datetime(2023, 1, 15, 10, 30, 0),
            "updated_at": datetime(2024, 1, 10, 15, 45, 0),
        },
        {
            "customer_id": "CUST-00000002",
            "first_name": "Maria",
            "last_name": "Santos",
            "email": "maria.santos@email.com",
            "phone": "+5521988888888",
            "city": "Rio de Janeiro",
            "state": "RJ",
            "country_code": "BR",
            "customer_segment": "SILVER",
            "registration_date": datetime(2022, 6, 20).date(),
            "is_active": True,
            "created_at": datetime(2022, 6, 20, 14, 0, 0),
            "updated_at": datetime(2024, 1, 5, 9, 15, 0),
        },
    ]


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return [
        {
            "product_id": "SKU-000001",
            "product_name": "Smartphone XYZ",
            "category_name": "Electronics",
            "subcategory_name": "Smartphones",
            "brand": "TechMax",
            "unit_price": 1999.99,
            "unit_cost": 1200.00,
            "stock_quantity": 150,
            "is_active": True,
        },
        {
            "product_id": "SKU-000002",
            "product_name": "Running Shoes",
            "category_name": "Fashion",
            "subcategory_name": "Shoes",
            "brand": "SportPro",
            "unit_price": 299.99,
            "unit_cost": 120.00,
            "stock_quantity": 500,
            "is_active": True,
        },
    ]


@pytest.fixture
def sample_error_log():
    """Sample error log for observability testing."""
    return """
    2024-01-10 15:30:45 ERROR [pipeline.oracle_ingest] Failed to process customers
    Traceback:
      File "oracle_ingest.py", line 245, in ingest_customers
        df = self._read_from_oracle(table="CRM.CUSTOMERS", ...)
      File "oracle_ingest.py", line 180, in _read_from_oracle
        return reader.load()
    pyspark.sql.utils.AnalysisException: Cannot resolve column 'loyalty_points' given input columns

    Schema mismatch detected. Expected columns do not match actual columns from source.
    """


@pytest.fixture
def sample_schema_expected():
    """Expected schema for drift detection testing."""
    from src.observability.schema_drift import SchemaColumn

    return [
        SchemaColumn(name="customer_id", data_type="string", nullable=False),
        SchemaColumn(name="first_name", data_type="string", nullable=False),
        SchemaColumn(name="email", data_type="string", nullable=True),
        SchemaColumn(name="is_active", data_type="boolean", nullable=False),
    ]


@pytest.fixture
def sample_schema_actual():
    """Actual schema with drift for testing."""
    from src.observability.schema_drift import SchemaColumn

    return [
        SchemaColumn(name="customer_id", data_type="string", nullable=False),
        SchemaColumn(name="first_name", data_type="string", nullable=False),
        SchemaColumn(name="email", data_type="string", nullable=True),
        SchemaColumn(name="is_active", data_type="boolean", nullable=False),
        SchemaColumn(name="loyalty_points", data_type="integer", nullable=True),  # NEW
    ]
