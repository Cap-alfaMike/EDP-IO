# ============================================================================
# EDP-IO - Ingestion Package
# ============================================================================
"""
Module A: Ingestion & Bronze Layer

This package handles data ingestion from legacy source systems into the 
Bronze layer of the Lakehouse architecture.

ARCHITECTURAL OVERVIEW:
----------------------
1. Data flows from source systems (Oracle, SQL Server) to Bronze layer
2. Bronze layer stores data in Delta Lake format with minimal transformation
3. Schema enforcement ensures data contract compliance
4. Idempotent processing enables safe reprocessing

KEY COMPONENTS:
- oracle_ingest.py: Oracle database ingestion
- sqlserver_ingest.py: SQL Server database ingestion
- bronze_writer.py: Delta Lake write utilities
- data_contracts/: Schema and contract definitions
- mock_data.py: Retail mock data generators

PRODUCTION PATH:
- Development: Uses mock data generators
- Production: Connects to real databases via JDBC
- Switching: Controlled by ENABLE_REAL_DATABASE_CONNECTIONS feature flag
"""

from src.ingestion.bronze_writer import BronzeWriter, WriteMode
from src.ingestion.mock_data import RetailMockDataGenerator

__all__ = [
    "BronzeWriter",
    "WriteMode",
    "RetailMockDataGenerator",
]
