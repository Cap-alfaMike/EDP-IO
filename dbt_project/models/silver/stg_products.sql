-- ============================================================================
-- EDP-IO - Silver Layer: Staged Products
-- ============================================================================
-- PURPOSE:
-- Clean and standardize product catalog data from Bronze layer.
-- Products use SCD2 for tracking price and attribute changes.
--
-- DESIGN DECISIONS:
-- -----------------
-- 1. SCD2 for Prices: Track price changes over time for margin analysis
-- 2. Category Hierarchy: Flattened for query simplicity
-- 3. Stock as Snapshot: Current stock only (history tracked in separate table)
--
-- ANALYTICS IMPACT:
-- ---------------
-- - Historical price analysis
-- - Category performance trends
-- - Margin analysis over time
-- ============================================================================

{{
    config(
        materialized='incremental',
        unique_key='surrogate_key',
        incremental_strategy='merge',
        tags=['silver', 'scd2', 'products']
    )
}}

WITH source AS (
    SELECT
        product_id,
        TRIM(product_name) AS product_name,
        category_id,
        INITCAP(TRIM(category_name)) AS category_name,
        INITCAP(TRIM(subcategory_name)) AS subcategory_name,
        INITCAP(TRIM(brand)) AS brand,
        CAST(unit_price AS DECIMAL(10, 2)) AS unit_price,
        CAST(unit_cost AS DECIMAL(10, 2)) AS unit_cost,
        stock_quantity,
        COALESCE(is_active, TRUE) AS is_active,
        created_at AS source_created_at,
        updated_at AS source_updated_at,
        _ingestion_timestamp,
        _source_system,
        _batch_id
    FROM {{ source('bronze', 'products') }}
    
    {% if is_incremental() %}
    WHERE _ingestion_timestamp > (
        SELECT COALESCE(MAX(_loaded_at), '1900-01-01'::TIMESTAMP)
        FROM {{ this }}
    )
    {% endif %}
),

-- Calculate derived fields
enriched AS (
    SELECT
        *,
        -- Margin calculation
        unit_price - unit_cost AS unit_margin,
        (unit_price - unit_cost) / NULLIF(unit_price, 0) * 100 AS margin_percentage,
        -- Price tier for segmentation
        CASE
            WHEN unit_price < 50 THEN 'BUDGET'
            WHEN unit_price < 200 THEN 'MID_RANGE'
            WHEN unit_price < 1000 THEN 'PREMIUM'
            ELSE 'LUXURY'
        END AS price_tier,
        -- Stock status
        CASE
            WHEN stock_quantity = 0 THEN 'OUT_OF_STOCK'
            WHEN stock_quantity < 10 THEN 'LOW_STOCK'
            WHEN stock_quantity < 100 THEN 'NORMAL_STOCK'
            ELSE 'HIGH_STOCK'
        END AS stock_status,
        -- Hash for change detection (price and key attributes)
        {{ dbt_utils.generate_surrogate_key([
            'product_name', 'category_id', 'brand', 
            'unit_price', 'unit_cost', 'is_active'
        ]) }} AS row_hash
    FROM source
),

-- Change detection for SCD2
{% if is_incremental() %}
current_records AS (
    SELECT product_id, _row_hash AS current_hash
    FROM {{ this }}
    WHERE is_current = TRUE
),

changes AS (
    SELECT
        e.*,
        CASE
            WHEN c.product_id IS NULL THEN 'INSERT'
            WHEN e.row_hash != c.current_hash THEN 'UPDATE'
            ELSE 'NO_CHANGE'
        END AS change_type
    FROM enriched e
    LEFT JOIN current_records c ON e.product_id = c.product_id
)
{% else %}
changes AS (
    SELECT *, 'INSERT' AS change_type FROM enriched
)
{% endif %}

-- Final output
SELECT
    {{ dbt_utils.generate_surrogate_key(['product_id', 'source_updated_at']) }} AS surrogate_key,
    product_id,
    product_name,
    category_id,
    category_name,
    subcategory_name,
    brand,
    unit_price,
    unit_cost,
    unit_margin,
    margin_percentage,
    price_tier,
    stock_quantity,
    stock_status,
    is_active,
    -- SCD2 fields
    source_updated_at AS valid_from,
    CAST('9999-12-31 23:59:59' AS TIMESTAMP) AS valid_to,
    TRUE AS is_current,
    row_hash AS _row_hash,
    -- Audit
    source_created_at,
    source_updated_at,
    CURRENT_TIMESTAMP() AS _loaded_at,
    '{{ invocation_id }}' AS _dbt_run_id,
    _source_system,
    _batch_id
FROM changes
WHERE change_type != 'NO_CHANGE'
