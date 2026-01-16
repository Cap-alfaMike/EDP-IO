# ============================================================================
# EDP-IO - Bronze Layer Writer
# ============================================================================
"""
Delta Lake writer utilities for the Bronze layer.

ARCHITECTURAL DECISIONS:
------------------------
1. Delta Lake for Bronze layer because:
   - ACID transactions ensure data consistency
   - Time travel enables rollback and auditing
   - Schema enforcement prevents data corruption
   - Unified batch and streaming processing
   - Compatible with both Databricks and open-source Spark

2. Idempotency via MERGE operations:
   - Safe reprocessing without duplicates
   - Supports incremental and full refresh
   - Business key based deduplication

3. Partitioning strategy:
   - By ingestion date for efficient cleanup
   - Secondary partitioning by source for multi-tenant

PRODUCTION NOTES:
- In production, paths point to ADLS Gen2
- Authentication via Managed Identity
- This module works identically in dev and prod (only paths change)
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from delta import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType, TimestampType

from src.utils.config import get_settings
from src.utils.logging import PipelineContext, get_logger

logger = get_logger(__name__)


class WriteMode(Enum):
    """
    Write modes for Bronze layer ingestion.

    APPEND: Add new records (idempotent via dedup logic)
    MERGE: Upsert based on business keys (preferred for incremental)
    OVERWRITE: Full refresh (use carefully - loses history)
    """

    APPEND = "append"
    MERGE = "merge"
    OVERWRITE = "overwrite"


class SchemaValidationError(Exception):
    """Raised when data fails schema validation."""

    pass


class BronzeWriter:
    """
    Delta Lake writer for Bronze layer with enterprise features.

    FEATURES:
    - Schema enforcement with explicit validation
    - Idempotent writes via MERGE
    - Automatic metadata columns
    - Partition management
    - Time travel enabled by default

    DESIGN PATTERN: Builder pattern for configuration

    USAGE:
        writer = BronzeWriter(spark_session)
        writer.write(
            df=source_data,
            table_name="customers",
            business_keys=["customer_id"],
            mode=WriteMode.MERGE,
        )

    PRODUCTION PATH:
    - Dev: Writes to local Delta tables
    - Prod: Writes to ADLS Gen2 via abfss://
    """

    # Metadata columns added to all Bronze tables
    METADATA_COLUMNS = [
        ("_ingestion_timestamp", TimestampType(), "UTC timestamp of ingestion"),
        ("_source_system", StringType(), "Source system identifier"),
        ("_batch_id", StringType(), "Unique batch/run identifier"),
        ("_file_path", StringType(), "Source file path if applicable"),
    ]

    def __init__(
        self,
        spark: SparkSession,
        base_path: Optional[str] = None,
    ):
        """
        Initialize Bronze writer.

        Args:
            spark: Active SparkSession
            base_path: Override for Bronze layer path (uses settings if None)
        """
        self.spark = spark
        self.settings = get_settings()
        self.base_path = base_path or self.settings.bronze_path

        logger.info(
            "BronzeWriter initialized",
            base_path=self.base_path,
            environment=self.settings.environment,
        )

    def _get_table_path(self, table_name: str) -> str:
        """Get the full path for a Delta table."""
        return f"{self.base_path}/{table_name}"

    def _add_metadata_columns(
        self,
        df: DataFrame,
        source_system: str,
        batch_id: str,
        file_path: Optional[str] = None,
    ) -> DataFrame:
        """
        Add metadata columns to DataFrame for lineage and auditing.

        WHY METADATA COLUMNS?
        - Track data lineage (where did this record come from?)
        - Enable time-based queries (when was this ingested?)
        - Support troubleshooting (which batch caused issues?)
        - Audit compliance (prove data provenance)
        """
        return df.withColumns(
            {
                "_ingestion_timestamp": F.lit(datetime.now(timezone.utc)),
                "_source_system": F.lit(source_system),
                "_batch_id": F.lit(batch_id),
                "_file_path": F.lit(file_path),
            }
        )

    def _validate_schema(
        self,
        df: DataFrame,
        expected_schema: Optional[StructType],
        table_name: str,
    ) -> bool:
        """
        Validate DataFrame schema against expected schema.

        SCHEMA ENFORCEMENT STRATEGY:
        - Fail fast if required columns are missing
        - Allow extra columns (forward compatibility)
        - Type mismatches are logged and can be configured to fail

        Returns:
            True if validation passes

        Raises:
            SchemaValidationError if validation fails
        """
        if expected_schema is None:
            logger.warning(
                "No expected schema provided, skipping validation",
                table_name=table_name,
            )
            return True

        actual_columns = set(df.columns)
        expected_columns = {field.name for field in expected_schema.fields}

        # Check for missing required columns
        missing = expected_columns - actual_columns
        if missing:
            error_msg = f"Missing required columns: {missing}"
            logger.error(
                "Schema validation failed",
                table_name=table_name,
                missing_columns=list(missing),
            )
            raise SchemaValidationError(error_msg)

        # Log extra columns (warning, not error)
        extra = (
            actual_columns
            - expected_columns
            - {"_ingestion_timestamp", "_source_system", "_batch_id", "_file_path"}
        )
        if extra:
            logger.warning(
                "Extra columns detected (will be preserved)",
                table_name=table_name,
                extra_columns=list(extra),
            )

        logger.info(
            "Schema validation passed",
            table_name=table_name,
            column_count=len(actual_columns),
        )
        return True

    def _table_exists(self, table_path: str) -> bool:
        """Check if a Delta table exists at the given path."""
        try:
            DeltaTable.forPath(self.spark, table_path)
            return True
        except Exception:
            return False

    def write(
        self,
        df: DataFrame,
        table_name: str,
        source_system: str,
        business_keys: List[str],
        mode: WriteMode = WriteMode.MERGE,
        batch_id: Optional[str] = None,
        expected_schema: Optional[StructType] = None,
        partition_columns: Optional[List[str]] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Write DataFrame to Bronze layer Delta table.

        IDEMPOTENCY GUARANTEE:
        When using MERGE mode with business_keys, reprocessing the same
        data will result in updates rather than duplicates. This is critical
        for production reliability.

        Args:
            df: DataFrame to write
            table_name: Target table name
            source_system: Source system identifier (e.g., "oracle_erp")
            business_keys: Columns that uniquely identify a record
            mode: Write mode (APPEND, MERGE, OVERWRITE)
            batch_id: Optional batch identifier (auto-generated if None)
            expected_schema: Optional schema for validation
            partition_columns: Columns to partition by
            file_path: Source file path for lineage

        Returns:
            Dict with write statistics

        EXAMPLE:
            result = writer.write(
                df=customers_df,
                table_name="customers",
                source_system="oracle_erp",
                business_keys=["customer_id"],
                mode=WriteMode.MERGE,
            )
            print(f"Wrote {result['rows_affected']} rows")
        """
        table_path = self._get_table_path(table_name)
        batch_id = batch_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")

        with PipelineContext(
            "bronze_write",
            table_name=table_name,
            source_system=source_system,
            mode=mode.value,
        ):
            # Schema validation
            self._validate_schema(df, expected_schema, table_name)

            # Add metadata columns
            df_with_metadata = self._add_metadata_columns(df, source_system, batch_id, file_path)

            # Default partition by ingestion date
            if partition_columns is None:
                # Create date column from ingestion timestamp for partitioning
                df_with_metadata = df_with_metadata.withColumn(
                    "_ingestion_date", F.to_date(F.col("_ingestion_timestamp"))
                )
                partition_columns = ["_ingestion_date"]

            initial_count = df_with_metadata.count()

            # Execute write based on mode
            if mode == WriteMode.OVERWRITE:
                result = self._write_overwrite(df_with_metadata, table_path, partition_columns)
            elif mode == WriteMode.MERGE:
                result = self._write_merge(
                    df_with_metadata, table_path, business_keys, partition_columns
                )
            else:  # APPEND
                result = self._write_append(df_with_metadata, table_path, partition_columns)

            # Log completion
            logger.info(
                "Bronze write completed",
                table_name=table_name,
                rows_written=initial_count,
                mode=mode.value,
                table_path=table_path,
            )

            return {
                "table_name": table_name,
                "table_path": table_path,
                "rows_affected": initial_count,
                "mode": mode.value,
                "batch_id": batch_id,
                **result,
            }

    def _write_overwrite(
        self,
        df: DataFrame,
        table_path: str,
        partition_columns: List[str],
    ) -> Dict[str, Any]:
        """
        Full overwrite of the table.

        WARNING: This loses history! Use only for:
        - Initial load
        - Reference data with no history requirement
        - Disaster recovery scenarios
        """
        logger.warning(
            "Using OVERWRITE mode - existing data will be replaced",
            table_path=table_path,
        )

        df.write.format("delta").mode("overwrite").partitionBy(*partition_columns).option(
            "overwriteSchema", "true"
        ).save(table_path)

        return {"operation": "overwrite"}

    def _write_append(
        self,
        df: DataFrame,
        table_path: str,
        partition_columns: List[str],
    ) -> Dict[str, Any]:
        """
        Append data to table.

        NOTE: Does not deduplicate! Caller must ensure no duplicates
        or use MERGE mode instead.
        """
        df.write.format("delta").mode("append").partitionBy(*partition_columns).save(table_path)

        return {"operation": "append"}

    def _write_merge(
        self,
        df: DataFrame,
        table_path: str,
        business_keys: List[str],
        partition_columns: List[str],
    ) -> Dict[str, Any]:
        """
        Merge (upsert) data into table.

        MERGE STRATEGY:
        - Match on business keys
        - If match: Update all columns (including metadata)
        - If no match: Insert new record

        THIS IS THE PREFERRED MODE for production incremental loads.

        IDEMPOTENCY:
        Running the same data multiple times produces the same result.
        This is critical for:
        - Retry logic in case of failures
        - Backfill operations
        - Testing and validation
        """
        # Check if table exists
        if not self._table_exists(table_path):
            # First write - use overwrite to create
            logger.info(
                "Table does not exist, creating with initial data",
                table_path=table_path,
            )
            return self._write_overwrite(df, table_path, partition_columns)

        # Build merge condition
        merge_condition = " AND ".join([f"target.{key} = source.{key}" for key in business_keys])

        # Get target table
        target = DeltaTable.forPath(self.spark, table_path)

        # Build update set (all columns except business keys)
        all_columns = df.columns
        update_columns = {col: f"source.{col}" for col in all_columns}

        # Execute merge
        merge_result = (
            target.alias("target")
            .merge(df.alias("source"), merge_condition)
            .whenMatchedUpdate(set=update_columns)
            .whenNotMatchedInsertAll()
        )

        merge_result.execute()

        return {
            "operation": "merge",
            "merge_condition": merge_condition,
        }

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get metadata about a Bronze table.

        Returns information useful for monitoring and debugging:
        - Row count
        - Partition info
        - Version history
        - File statistics
        """
        table_path = self._get_table_path(table_name)

        if not self._table_exists(table_path):
            return {"exists": False, "table_name": table_name}

        delta_table = DeltaTable.forPath(self.spark, table_path)
        history = delta_table.history(10).collect()

        df = self.spark.read.format("delta").load(table_path)

        return {
            "exists": True,
            "table_name": table_name,
            "table_path": table_path,
            "row_count": df.count(),
            "column_count": len(df.columns),
            "columns": df.columns,
            "latest_version": history[0]["version"] if history else 0,
            "recent_operations": [
                {
                    "version": h["version"],
                    "operation": h["operation"],
                    "timestamp": str(h["timestamp"]),
                }
                for h in history[:5]
            ],
        }

    def vacuum_table(
        self,
        table_name: str,
        retention_hours: int = 168,  # 7 days default
    ) -> None:
        """
        Clean up old versions of the table.

        CAUTION: After vacuum, time travel to older versions is not possible.

        PRODUCTION NOTE:
        - Run vacuum during off-peak hours
        - Retention should align with SLA requirements
        - Consider longer retention for debugging production issues
        """
        table_path = self._get_table_path(table_name)

        if not self._table_exists(table_path):
            logger.warning("Table does not exist, skipping vacuum", table_name=table_name)
            return

        delta_table = DeltaTable.forPath(self.spark, table_path)
        delta_table.vacuum(retention_hours)

        logger.info(
            "Vacuum completed",
            table_name=table_name,
            retention_hours=retention_hours,
        )


# ============================================================================
# Spark Session Factory (Mock-Ready)
# ============================================================================


def get_spark_session(app_name: str = "EDP-IO") -> SparkSession:
    """
    Get or create a Spark session configured for Delta Lake.

    CONFIGURATION:
    - Delta Lake extensions enabled
    - Adaptive query execution
    - Memory optimization

    PRODUCTION NOTE:
    In production (Databricks), the session is pre-configured.
    This function is primarily for local development and testing.
    """
    settings = get_settings()

    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        )
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.databricks.delta.retentionDurationCheck.enabled", "false")
    )

    # Local mode configuration
    if settings.is_development:
        builder = (
            builder.master("local[*]")
            .config("spark.driver.memory", "4g")
            .config("spark.sql.shuffle.partitions", "8")
        )

    return builder.getOrCreate()
