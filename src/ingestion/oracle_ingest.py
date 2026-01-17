# ============================================================================
# EDP-IO - Oracle Database Ingestion
# ============================================================================
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           DATA CONTRACT                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Source System    : Oracle ERP (Legacy CRM & Inventory)                       ║
║ Tables           : CRM.CUSTOMERS, INV.PRODUCTS, POS.STORES                   ║
║ Owner            : data-engineering@enterprise.com                           ║
║ SLA              : Daily refresh by 06:00 UTC                                ║
║ Data Contract    : src/ingestion/data_contracts/contracts.yaml               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ARCHITECTURAL DECISIONS:                                                      ║
║ 1. JDBC for reliable, transaction-safe reads                                 ║
║ 2. Partitioned reads for parallel extraction                                 ║
║ 3. Watermark-based incremental extraction                                    ║
║ 4. Schema validation before write                                            ║
║ 5. Idempotent writes via MERGE on business keys                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ PRODUCTION PATH:                                                              ║
║ - Development: Uses RetailMockDataGenerator                                   ║
║ - Production: Connects to Oracle via JDBC with Key Vault credentials         ║
║ - Feature Flag: ENABLE_REAL_DATABASE_CONNECTIONS                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DecimalType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from src.ingestion.bronze_writer import BronzeWriter, get_spark_session, WriteMode
from src.ingestion.mock_data import RetailMockDataGenerator
from src.utils.config import get_settings
from src.utils.logging import get_logger, PipelineContext
from src.utils.security import SecretProvider

logger = get_logger(__name__)


# ============================================================================
# Schema Definitions
# ============================================================================
# These schemas match the data contracts defined in contracts.yaml
# They are used for:
# 1. Schema enforcement on incoming data
# 2. Type casting for consistency
# 3. Documentation of expected structure

CUSTOMERS_SCHEMA = StructType(
    [
        StructField("customer_id", StringType(), False),
        StructField("first_name", StringType(), False),
        StructField("last_name", StringType(), False),
        StructField("email", StringType(), True),
        StructField("phone", StringType(), True),
        StructField("address_line1", StringType(), True),
        StructField("city", StringType(), True),
        StructField("state", StringType(), True),
        StructField("postal_code", StringType(), True),
        StructField("country_code", StringType(), False),
        StructField("customer_segment", StringType(), True),
        StructField("registration_date", DateType(), False),
        StructField("is_active", BooleanType(), False),
        StructField("created_at", TimestampType(), False),
        StructField("updated_at", TimestampType(), False),
    ]
)

PRODUCTS_SCHEMA = StructType(
    [
        StructField("product_id", StringType(), False),
        StructField("product_name", StringType(), False),
        StructField("category_id", StringType(), False),
        StructField("category_name", StringType(), True),
        StructField("subcategory_name", StringType(), True),
        StructField("brand", StringType(), True),
        StructField("unit_price", DecimalType(10, 2), False),
        StructField("unit_cost", DecimalType(10, 2), False),
        StructField("stock_quantity", IntegerType(), False),
        StructField("is_active", BooleanType(), False),
        StructField("created_at", TimestampType(), False),
        StructField("updated_at", TimestampType(), False),
    ]
)

STORES_SCHEMA = StructType(
    [
        StructField("store_id", StringType(), False),
        StructField("store_name", StringType(), False),
        StructField("store_type", StringType(), False),
        StructField("region", StringType(), False),
        StructField("city", StringType(), False),
        StructField("state", StringType(), False),
        StructField("manager_name", StringType(), True),
        StructField("open_date", DateType(), False),
        StructField("is_active", BooleanType(), False),
        StructField("created_at", TimestampType(), False),
        StructField("updated_at", TimestampType(), False),
    ]
)


@dataclass
class OracleConnectionConfig:
    """
    Oracle connection configuration.

    SECURITY NOTE:
    - Host/port can be in config
    - Password MUST come from SecretProvider
    - Never log connection strings
    """

    host: str
    port: int = 1521
    service_name: str = "ORCL"
    user: str = "readonly_user"

    @property
    def jdbc_url(self) -> str:
        """Generate JDBC URL (without password)."""
        return f"jdbc:oracle:thin:@//{self.host}:{self.port}/{self.service_name}"


class OracleIngestion:
    """
    Oracle database ingestion handler.

    DESIGN DECISIONS:
    -----------------
    1. Lazy Connection: Only connects when needed
    2. Partitioned Reads: Uses Oracle partition columns for parallel reads
    3. Watermark Tracking: Supports incremental updates based on updated_at
    4. Mock Fallback: Uses generated data when database unavailable

    IDEMPOTENCY:
    Running this ingestion multiple times for the same date/batch is safe.
    The Bronze writer uses MERGE to update existing records rather than duplicate.

    USAGE:
        ingestion = OracleIngestion(spark)

        # Ingest all Oracle tables
        results = ingestion.ingest_all()

        # Or ingest specific table
        result = ingestion.ingest_customers()
    """

    SOURCE_SYSTEM = "oracle_erp"

    def __init__(
        self,
        spark: Optional[SparkSession] = None,
        connection_config: Optional[OracleConnectionConfig] = None,
    ):
        """
        Initialize Oracle ingestion.

        Args:
            spark: SparkSession (creates one if None)
            connection_config: Oracle connection settings (uses settings if None)
        """
        self.spark = spark or get_spark_session()
        self.settings = get_settings()

        # Connection config from settings or override
        if connection_config:
            self.connection_config = connection_config
        else:
            self.connection_config = OracleConnectionConfig(
                host=(
                    self.settings.oracle_host
                    if hasattr(self.settings, "oracle_host")
                    else "localhost"
                ),
                port=1521,
                service_name="ERPDB",
            )

        # Initialize Bronze writer
        self.bronze_writer = BronzeWriter(self.spark)

        # Mock data generator (only used in dev mode)
        self._mock_generator = None

        logger.info(
            "OracleIngestion initialized",
            source_system=self.SOURCE_SYSTEM,
            use_mock=not self.settings.enable_real_database_connections,
        )

    @property
    def mock_generator(self) -> RetailMockDataGenerator:
        """Lazy-initialize mock generator."""
        if self._mock_generator is None:
            self._mock_generator = RetailMockDataGenerator(seed=42)
        return self._mock_generator

    def _get_password(self) -> str:
        """
        Get Oracle password from secure storage.

        SECURITY:
        - Never hardcode passwords
        - Use SecretProvider abstraction
        - In prod: Key Vault with Managed Identity
        - In dev: Mock secret provider
        """
        return SecretProvider.get("ORACLE_PASSWORD")

    def _read_from_oracle(
        self,
        table: str,
        schema: StructType,
        partition_column: Optional[str] = None,
        num_partitions: int = 4,
        watermark_column: Optional[str] = None,
        watermark_value: Optional[datetime] = None,
    ) -> DataFrame:
        """
        Read data from Oracle table via JDBC.

        PERFORMANCE OPTIMIZATION:
        - Partitioned reads for parallelism
        - Predicate pushdown to Oracle
        - Column pruning

        Args:
            table: Fully qualified table name (schema.table)
            schema: Expected schema for type casting
            partition_column: Column for parallel reads (numeric preferred)
            num_partitions: Number of Spark partitions
            watermark_column: Column for incremental reads
            watermark_value: Only read records updated after this time
        """
        jdbc_url = self.connection_config.jdbc_url
        password = self._get_password()

        # Build query with optional watermark filter
        if watermark_column and watermark_value:
            query = f"""
                (SELECT * FROM {table} 
                 WHERE {watermark_column} > TO_TIMESTAMP('{watermark_value.isoformat()}', 'YYYY-MM-DD"T"HH24:MI:SS')
                ) watermarked_query
            """
        else:
            query = f"({table}) full_table_query"

        logger.info(
            "Reading from Oracle",
            table=table,
            partitions=num_partitions,
            has_watermark=watermark_value is not None,
        )

        # Configure JDBC read
        reader = (
            self.spark.read.format("jdbc")
            .option("url", jdbc_url)
            .option("dbtable", query)
            .option("user", self.connection_config.user)
            .option("password", password)
            .option("driver", "oracle.jdbc.driver.OracleDriver")
            .option("fetchsize", "10000")
        )

        # Add partitioning if specified
        if partition_column:
            reader = reader.option("partitionColumn", partition_column).option(
                "numPartitions", str(num_partitions)
            )

        return reader.load()

    def _read_mock_data(self, entity: str) -> DataFrame:
        """
        Read mock data instead of Oracle (development mode).

        This method is used when ENABLE_REAL_DATABASE_CONNECTIONS is False.
        It generates realistic data using Faker.
        """
        logger.info(
            "Using mock data (development mode)",
            entity=entity,
        )

        # Generate data
        all_data = self.mock_generator.generate_all()

        if entity == "customers":
            data = all_data["customers"]
            schema = CUSTOMERS_SCHEMA
        elif entity == "products":
            data = all_data["products"]
            schema = PRODUCTS_SCHEMA
        elif entity == "stores":
            data = all_data["stores"]
            schema = STORES_SCHEMA
        else:
            raise ValueError(f"Unknown entity: {entity}")

        # Convert to DataFrame
        df = self.spark.createDataFrame(data, schema=schema)
        return df

    def ingest_customers(
        self,
        watermark: Optional[datetime] = None,
        mode: WriteMode = WriteMode.MERGE,
    ) -> Dict[str, Any]:
        """
        Ingest customer data from Oracle CRM.

        DATA CONTRACT:
        - Source: CRM.CUSTOMERS
        - Business Key: customer_id
        - Update Strategy: SCD Type 2 (handled in Silver layer)
        - PII Fields: first_name, last_name, email, phone, address

        IDEMPOTENCY:
        Re-running this for the same date updates existing records.
        No duplicates will be created due to MERGE on customer_id.

        Args:
            watermark: Only ingest records updated after this time
            mode: Write mode (default: MERGE for idempotency)

        Returns:
            Dict with ingestion statistics
        """
        with PipelineContext("oracle_customers_ingestion", source_table="CRM.CUSTOMERS"):

            # Get data based on configuration
            if self.settings.enable_real_database_connections:
                df = self._read_from_oracle(
                    table="CRM.CUSTOMERS",
                    schema=CUSTOMERS_SCHEMA,
                    watermark_column="updated_at",
                    watermark_value=watermark,
                )
            else:
                df = self._read_mock_data("customers")

            # Write to Bronze
            result = self.bronze_writer.write(
                df=df,
                table_name="customers",
                source_system=self.SOURCE_SYSTEM,
                business_keys=["customer_id"],
                mode=mode,
                expected_schema=CUSTOMERS_SCHEMA,
            )

            return result

    def ingest_products(
        self,
        watermark: Optional[datetime] = None,
        mode: WriteMode = WriteMode.MERGE,
    ) -> Dict[str, Any]:
        """
        Ingest product catalog from Oracle Inventory.

        DATA CONTRACT:
        - Source: INV.PRODUCTS
        - Business Key: product_id
        - Refresh: Every 6 hours
        - Criticality: High (affects pricing)
        """
        with PipelineContext("oracle_products_ingestion", source_table="INV.PRODUCTS"):

            if self.settings.enable_real_database_connections:
                df = self._read_from_oracle(
                    table="INV.PRODUCTS",
                    schema=PRODUCTS_SCHEMA,
                    watermark_column="updated_at",
                    watermark_value=watermark,
                )
            else:
                df = self._read_mock_data("products")

            result = self.bronze_writer.write(
                df=df,
                table_name="products",
                source_system=self.SOURCE_SYSTEM,
                business_keys=["product_id"],
                mode=mode,
                expected_schema=PRODUCTS_SCHEMA,
            )

            return result

    def ingest_stores(
        self,
        mode: WriteMode = WriteMode.MERGE,
    ) -> Dict[str, Any]:
        """
        Ingest store locations from Oracle POS.

        DATA CONTRACT:
        - Source: POS.STORES
        - Business Key: store_id
        - Refresh: Daily (stores rarely change)
        """
        with PipelineContext("oracle_stores_ingestion", source_table="POS.STORES"):

            if self.settings.enable_real_database_connections:
                df = self._read_from_oracle(
                    table="POS.STORES",
                    schema=STORES_SCHEMA,
                )
            else:
                df = self._read_mock_data("stores")

            result = self.bronze_writer.write(
                df=df,
                table_name="stores",
                source_system=self.SOURCE_SYSTEM,
                business_keys=["store_id"],
                mode=mode,
                expected_schema=STORES_SCHEMA,
            )

            return result

    def ingest_all(
        self,
        watermark: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Run full Oracle ingestion pipeline.

        ORCHESTRATION:
        In production, this would be called by Databricks Workflows
        or Azure Data Factory. The order respects dependencies.

        Args:
            watermark: Cutoff for incremental ingestion

        Returns:
            Dict with results for each table
        """
        logger.info("Starting full Oracle ingestion", source_system=self.SOURCE_SYSTEM)

        results = {}

        # Ingest in dependency order (none here, but important pattern)
        results["stores"] = self.ingest_stores()
        results["products"] = self.ingest_products(watermark=watermark)
        results["customers"] = self.ingest_customers(watermark=watermark)

        logger.info(
            "Oracle ingestion completed",
            tables_processed=len(results),
            total_rows=sum(r["rows_affected"] for r in results.values()),
        )

        return results


# ============================================================================
# CLI Entry Point
# ============================================================================


def main():
    """
    Command-line entry point for Oracle ingestion.

    USAGE:
        python -m src.ingestion.oracle_ingest

    In production, this would be called via Databricks job or ADF pipeline.
    """
    import argparse

    parser = argparse.ArgumentParser(description="EDP-IO Oracle Ingestion")
    parser.add_argument(
        "--table", choices=["customers", "products", "stores", "all"], default="all"
    )
    parser.add_argument("--watermark", type=str, help="ISO format datetime for incremental")
    args = parser.parse_args()

    # Parse watermark if provided
    watermark = None
    if args.watermark:
        watermark = datetime.fromisoformat(args.watermark)

    # Run ingestion
    ingestion = OracleIngestion()

    if args.table == "all":
        results = ingestion.ingest_all(watermark=watermark)
        for table, result in results.items():
            print(f"{table}: {result['rows_affected']} rows")
    else:
        method = getattr(ingestion, f"ingest_{args.table}")
        result = method(watermark=watermark) if args.table != "stores" else method()
        print(f"{args.table}: {result['rows_affected']} rows")


if __name__ == "__main__":
    main()
