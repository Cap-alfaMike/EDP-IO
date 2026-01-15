# ============================================================================
# EDP-IO - Ingestion Tests
# ============================================================================
"""
Tests for ingestion module including mock data generation and bronze writer.
"""

import pytest
from decimal import Decimal
from datetime import datetime, date


class TestRetailMockDataGenerator:
    """Tests for the mock data generator."""
    
    def test_generator_initialization(self):
        """Test generator can be instantiated."""
        from src.ingestion.mock_data import RetailMockDataGenerator
        
        generator = RetailMockDataGenerator(seed=42)
        assert generator is not None
        assert generator.seed == 42
    
    def test_generate_customers(self):
        """Test customer generation produces valid data."""
        from src.ingestion.mock_data import RetailMockDataGenerator
        
        generator = RetailMockDataGenerator(seed=42)
        customers = generator.generate_customers(100)
        
        assert len(customers) == 100
        
        # Verify structure
        first = customers[0]
        assert "customer_id" in first
        assert "first_name" in first
        assert "email" in first
        assert "customer_segment" in first
        assert "is_active" in first
        
        # Verify business rules
        assert first["customer_id"].startswith("CUST-")
        assert first["customer_segment"] in ["BRONZE", "SILVER", "GOLD", "PLATINUM"]
        assert first["country_code"] == "BR"
        assert isinstance(first["registration_date"], date)
    
    def test_generate_products(self):
        """Test product generation produces valid data."""
        from src.ingestion.mock_data import RetailMockDataGenerator
        
        generator = RetailMockDataGenerator(seed=42)
        products = generator.generate_products(50)
        
        assert len(products) == 50
        
        first = products[0]
        assert first["product_id"].startswith("SKU-")
        assert isinstance(first["unit_price"], Decimal)
        assert isinstance(first["unit_cost"], Decimal)
        assert first["unit_cost"] <= first["unit_price"]  # Cost < Price
        assert first["stock_quantity"] >= 0
    
    def test_generate_orders_with_referential_integrity(self):
        """Test order generation maintains referential integrity."""
        from src.ingestion.mock_data import RetailMockDataGenerator
        
        generator = RetailMockDataGenerator(seed=42)
        
        # Must generate customers and products first
        customers = generator.generate_customers(100)
        products = generator.generate_products(50)
        
        customer_ids = [c["customer_id"] for c in customers]
        product_ids = [p["product_id"] for p in products]
        
        orders, order_items = generator.generate_orders(200, customer_ids, product_ids)
        
        assert len(orders) == 200
        assert len(order_items) > 0
        
        # Verify referential integrity
        for order in orders:
            assert order["customer_id"] in customer_ids
        
        for item in order_items:
            assert item["product_id"] in product_ids
            assert any(o["order_id"] == item["order_id"] for o in orders)
    
    def test_deterministic_with_seed(self):
        """Test generator produces same data with same seed."""
        from src.ingestion.mock_data import RetailMockDataGenerator
        
        gen1 = RetailMockDataGenerator(seed=123)
        gen2 = RetailMockDataGenerator(seed=123)
        
        customers1 = gen1.generate_customers(10)
        customers2 = gen2.generate_customers(10)
        
        for c1, c2 in zip(customers1, customers2):
            assert c1["customer_id"] == c2["customer_id"]
            assert c1["first_name"] == c2["first_name"]


class TestBronzeWriter:
    """Tests for the Bronze layer writer."""
    
    def test_metadata_columns_added(self, mock_settings):
        """Test that metadata columns are properly defined."""
        from src.ingestion.bronze_writer import BronzeWriter
        
        # Verify metadata column definitions
        assert len(BronzeWriter.METADATA_COLUMNS) == 4
        
        column_names = [c[0] for c in BronzeWriter.METADATA_COLUMNS]
        assert "_ingestion_timestamp" in column_names
        assert "_source_system" in column_names
        assert "_batch_id" in column_names
        assert "_file_path" in column_names
    
    def test_write_mode_enum(self):
        """Test write modes are properly defined."""
        from src.ingestion.bronze_writer import WriteMode
        
        assert WriteMode.APPEND.value == "append"
        assert WriteMode.MERGE.value == "merge"
        assert WriteMode.OVERWRITE.value == "overwrite"


class TestDataContracts:
    """Tests for data contract validation."""
    
    def test_contracts_file_parseable(self):
        """Test contracts.yaml can be parsed."""
        import yaml
        from pathlib import Path
        
        contracts_path = Path("src/ingestion/data_contracts/contracts.yaml")
        
        if contracts_path.exists():
            with open(contracts_path) as f:
                contracts = yaml.safe_load(f)
            
            # Verify expected tables
            assert "customers" in contracts
            assert "products" in contracts
            assert "orders" in contracts
            
            # Verify structure
            customer_contract = contracts["customers"]
            assert "source_system" in customer_contract
            assert "schema" in customer_contract
            assert "quality_rules" in customer_contract
    
    def test_customer_contract_has_required_fields(self):
        """Test customer contract defines all required fields."""
        import yaml
        from pathlib import Path
        
        contracts_path = Path("src/ingestion/data_contracts/contracts.yaml")
        
        if contracts_path.exists():
            with open(contracts_path) as f:
                contracts = yaml.safe_load(f)
            
            customer_fields = [
                f["name"] for f in contracts["customers"]["schema"]["fields"]
            ]
            
            required = ["customer_id", "first_name", "last_name", "email"]
            for field in required:
                assert field in customer_fields, f"Missing required field: {field}"
