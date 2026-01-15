-- ============================================================================
-- EDP-IO - Gold Layer: Product Dimension
-- ============================================================================
-- PURPOSE:
-- Conformed product dimension with category hierarchy and pricing tiers.
-- Optimized for retail analytics and category performance reporting.
--
-- DESIGN DECISIONS:
-- -----------------
-- 1. Current Pricing Only:
--    - This dimension shows current price
--    - Historical pricing is in Silver (SCD2)
--    - Fact table captures price at transaction time
--
-- 2. Category Hierarchy:
--    - Flattened for drill-down analysis
--    - Level 1: Category → Level 2: Subcategory
--
-- 3. Derived Attributes:
--    - Price tier for segmentation
--    - Margin band for profitability analysis
--
-- RETAIL ANALYTICS CONTEXT:
-- ------------------------
-- This dimension enables:
-- - Category performance analysis
-- - Brand performance comparison
-- - Margin analysis by product line
-- - Inventory optimization (via stock status)
-- ============================================================================

{{
    config(
        materialized='table',
        tags=['gold', 'dimension', 'product']
    )
}}

WITH current_products AS (
    SELECT
        surrogate_key AS silver_key,
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
        source_created_at,
        source_updated_at,
        _loaded_at
    FROM {{ ref('stg_products') }}
    WHERE is_current = TRUE
),

enriched AS (
    SELECT
        *,
        -- Category hierarchy path for drill-down
        CONCAT(category_name, ' > ', COALESCE(subcategory_name, 'General')) AS category_path,
        
        -- Margin band for profitability analysis
        CASE
            WHEN margin_percentage < 10 THEN 'LOW_MARGIN'
            WHEN margin_percentage < 25 THEN 'STANDARD_MARGIN'
            WHEN margin_percentage < 40 THEN 'GOOD_MARGIN'
            ELSE 'HIGH_MARGIN'
        END AS margin_band,
        
        -- Inventory value
        stock_quantity * unit_cost AS inventory_value,
        stock_quantity * unit_price AS inventory_retail_value,
        
        -- Product age
        DATEDIFF(CURRENT_DATE(), DATE(source_created_at)) AS days_in_catalog,
        CASE
            WHEN DATEDIFF(CURRENT_DATE(), DATE(source_created_at)) < 30 THEN 'NEW_ARRIVAL'
            WHEN DATEDIFF(CURRENT_DATE(), DATE(source_created_at)) < 180 THEN 'CURRENT'
            WHEN DATEDIFF(CURRENT_DATE(), DATE(source_created_at)) < 365 THEN 'ESTABLISHED'
            ELSE 'LEGACY'
        END AS product_lifecycle_stage
    FROM current_products
)

SELECT
    -- Surrogate key for fact joins
    {{ dbt_utils.generate_surrogate_key(['product_id']) }} AS dim_product_key,
    
    -- Natural key
    product_id,
    
    -- Product attributes
    product_name,
    brand,
    
    -- Category hierarchy
    category_id,
    category_name,
    subcategory_name,
    category_path,
    
    -- Pricing
    unit_price,
    unit_cost,
    unit_margin,
    margin_percentage,
    price_tier,
    margin_band,
    
    -- Inventory
    stock_quantity,
    stock_status,
    inventory_value,
    inventory_retail_value,
    
    -- Lifecycle
    days_in_catalog,
    product_lifecycle_stage,
    
    -- Status
    is_active,
    CASE WHEN is_active THEN 'Active' ELSE 'Discontinued' END AS product_status,
    
    -- Audit
    source_created_at,
    source_updated_at,
    _loaded_at,
    CURRENT_TIMESTAMP() AS _dim_loaded_at,
    '{{ invocation_id }}' AS _dbt_run_id

FROM enriched
