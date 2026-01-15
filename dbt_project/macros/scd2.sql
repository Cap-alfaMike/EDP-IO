-- ============================================================================
-- EDP-IO - SCD Type 2 Macro
-- ============================================================================
-- Implements Slowly Changing Dimension Type 2 for historization.
--
-- DESIGN DECISIONS:
-- -----------------
-- 1. Surrogate Key: Generated hash for consistent joining
-- 2. Business Key: Natural key from source system
-- 3. Valid From/To: Date range for record validity
-- 4. Is Current: Boolean flag for current record (optimization)
--
-- WHY SCD TYPE 2?
-- - Preserves full history of changes
-- - Enables point-in-time analysis
-- - Required for compliance (GDPR "right to explanation")
-- - Supports business questions like "what was the customer segment last year?"
--
-- TRADE-OFFS:
-- - Increased storage (every change creates new record)
-- - More complex queries (must filter for current or point-in-time)
-- - Mitigated by: is_current flag and proper indexing
--
-- USAGE:
--   {{ scd2_merge(
--       source_table='bronze.customers',
--       target_table='silver.dim_customers',
--       business_key='customer_id',
--       tracked_columns=['first_name', 'last_name', 'email', 'customer_segment'],
--       updated_at_column='updated_at'
--   ) }}
-- ============================================================================

{% macro scd2_merge(source_table, target_table, business_key, tracked_columns, updated_at_column='updated_at') %}
{#
    SCD Type 2 merge operation for dimension tables.
    
    Args:
        source_table: Source table reference (Bronze layer)
        target_table: Target table reference (Silver layer)
        business_key: Column(s) that uniquely identify an entity
        tracked_columns: Columns to track for changes
        updated_at_column: Timestamp column indicating last update
    
    Returns:
        SQL for MERGE operation with SCD Type 2 logic
#}

-- Generate surrogate key from business key + valid_from
{% set surrogate_key_expr %}
    {{ dbt_utils.generate_surrogate_key([business_key, 'valid_from']) }}
{% endset %}

-- Generate hash of tracked columns for change detection
{% set change_hash_expr %}
    {{ dbt_utils.generate_surrogate_key(tracked_columns) }}
{% endset %}

WITH source_data AS (
    SELECT
        {{ business_key }},
        {% for col in tracked_columns %}
        {{ col }},
        {% endfor %}
        {{ updated_at_column }},
        {{ change_hash_expr }} AS _row_hash,
        CURRENT_TIMESTAMP() AS _loaded_at
    FROM {{ source_table }}
),

-- Get current records from target
current_records AS (
    SELECT
        {{ business_key }},
        _row_hash,
        valid_from,
        valid_to,
        is_current
    FROM {{ target_table }}
    WHERE is_current = TRUE
),

-- Identify changes by comparing hashes
changes AS (
    SELECT
        s.*,
        c._row_hash AS current_hash,
        c.valid_from AS current_valid_from,
        CASE 
            WHEN c.{{ business_key }} IS NULL THEN 'INSERT'
            WHEN s._row_hash != c._row_hash THEN 'UPDATE'
            ELSE 'NO_CHANGE'
        END AS _change_type
    FROM source_data s
    LEFT JOIN current_records c
        ON s.{{ business_key }} = c.{{ business_key }}
)

-- Final output with SCD Type 2 fields
SELECT
    {{ surrogate_key_expr }} AS surrogate_key,
    {{ business_key }},
    {% for col in tracked_columns %}
    {{ col }},
    {% endfor %}
    _row_hash,
    CASE 
        WHEN _change_type = 'INSERT' THEN {{ updated_at_column }}
        WHEN _change_type = 'UPDATE' THEN {{ updated_at_column }}
        ELSE current_valid_from
    END AS valid_from,
    CAST('{{ var("scd2_valid_to_default") }}' AS TIMESTAMP) AS valid_to,
    TRUE AS is_current,
    _loaded_at,
    '{{ invocation_id }}' AS _dbt_run_id
FROM changes
WHERE _change_type != 'NO_CHANGE'

{% endmacro %}


-- ============================================================================
-- Helper Macro: Close expired records
-- ============================================================================
-- Called after SCD2 merge to update valid_to on superseded records

{% macro scd2_close_expired(target_table, business_key) %}
{#
    Close expired SCD Type 2 records by setting valid_to and is_current.
    
    This should be called in a post-hook after the SCD2 merge.
#}

UPDATE {{ target_table }} AS target
SET 
    valid_to = source.valid_from,
    is_current = FALSE
FROM (
    SELECT 
        {{ business_key }},
        valid_from,
        ROW_NUMBER() OVER (
            PARTITION BY {{ business_key }} 
            ORDER BY valid_from DESC
        ) AS rn
    FROM {{ target_table }}
) AS source
WHERE target.{{ business_key }} = source.{{ business_key }}
  AND target.is_current = TRUE
  AND source.rn = 1
  AND target.valid_from < source.valid_from

{% endmacro %}


-- ============================================================================
-- Helper Macro: Generate audit columns
-- ============================================================================
-- Standard audit columns for all Silver/Gold tables

{% macro audit_columns() %}
    CURRENT_TIMESTAMP() AS _loaded_at,
    '{{ invocation_id }}' AS _dbt_run_id,
    '{{ this.schema }}.{{ this.name }}' AS _dbt_model
{% endmacro %}


-- ============================================================================
-- Helper Macro: Optimize Delta table
-- ============================================================================
-- Called in post-hook to optimize Delta Lake tables

{% macro optimize_delta(table_ref) %}
    {% if target.type == 'databricks' %}
        OPTIMIZE {{ table_ref }}
    {% endif %}
{% endmacro %}
