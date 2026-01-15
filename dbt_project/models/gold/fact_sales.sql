-- ============================================================================
-- EDP-IO - Gold Layer: Sales Fact Table
-- ============================================================================
-- PURPOSE:
-- Central fact table for retail sales analysis at the order line level.
-- Grain: One row per order item (product sold in an order).
--
-- DESIGN TRADE-OFFS:
-- -----------------
-- 1. Grain Selection:
--    - Line item grain (not order level) for product-level analysis
--    - Trade-off: More rows, but maximum analytical flexibility
--    - Aggregations handled by BI layer or summary tables
--
-- 2. Additive Measures:
--    - Revenue, cost, profit are fully additive
--    - Can be summed across any dimension
--
-- 3. Semi-Additive Measures:
--    - Prices (unit_price, unit_cost) are semi-additive
--    - Don't sum across products, average or latest
--
-- BUSINESS METRICS ENABLED:
-- ------------------------
-- - Revenue (GMV) by any dimension combination
-- - Gross margin and profitability
-- - Units sold and average basket size
-- - Discount effectiveness
-- - Regional/channel performance
--
-- STAR SCHEMA RELATIONSHIPS:
-- -------------------------
-- fact_sales → dim_customer (customer analysis)
-- fact_sales → dim_product (product performance)
-- fact_sales → dim_date (time-based trends)
-- (dim_store intentionally omitted for MVP - would be added if store data available)
-- ============================================================================

{{
    config(
        materialized='incremental',
        unique_key='fact_sales_key',
        incremental_strategy='merge',
        tags=['gold', 'fact', 'sales']
    )
}}

WITH orders AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        order_status,
        payment_method,
        subtotal AS order_subtotal,
        discount_amount AS order_discount,
        shipping_cost,
        total_amount AS order_total,
        order_date_key,
        validation_status,
        _loaded_at AS order_loaded_at
    FROM {{ ref('stg_orders') }}
    
    {% if is_incremental() %}
    WHERE _loaded_at > (
        SELECT COALESCE(MAX(_fact_loaded_at), '1900-01-01'::TIMESTAMP)
        FROM {{ this }}
    )
    {% endif %}
),

order_items AS (
    SELECT
        order_item_id,
        order_id,
        product_id,
        quantity,
        unit_price AS line_unit_price,
        discount_percent AS line_discount_percent,
        line_total
    FROM {{ source('bronze', 'order_items') }}
),

-- Join orders with items
order_lines AS (
    SELECT
        oi.order_item_id,
        oi.order_id,
        o.customer_id,
        oi.product_id,
        o.order_date,
        o.order_date_key,
        o.order_status,
        o.payment_method,
        oi.quantity,
        oi.line_unit_price,
        oi.line_discount_percent,
        oi.line_total,
        o.shipping_cost,
        o.order_total,
        o.validation_status,
        o.order_loaded_at
    FROM order_items oi
    INNER JOIN orders o ON oi.order_id = o.order_id
),

-- Enrich with dimension keys and derived metrics
enriched AS (
    SELECT
        ol.*,
        
        -- Dimension keys for joining
        {{ dbt_utils.generate_surrogate_key(['ol.customer_id']) }} AS dim_customer_key,
        {{ dbt_utils.generate_surrogate_key(['ol.product_id']) }} AS dim_product_key,
        ol.order_date_key AS dim_date_key,
        
        -- Get product cost for margin calculation
        p.unit_cost AS product_unit_cost,
        p.category_name,
        p.subcategory_name,
        p.brand,
        
        -- Calculate line-level metrics
        ol.quantity * p.unit_cost AS line_cost,
        ol.line_total - (ol.quantity * p.unit_cost) AS line_profit,
        
        -- Margin percentage
        CASE 
            WHEN ol.line_total > 0 
            THEN (ol.line_total - (ol.quantity * p.unit_cost)) / ol.line_total * 100
            ELSE 0
        END AS line_margin_percentage,
        
        -- Discount amount
        ol.quantity * ol.line_unit_price * (ol.line_discount_percent / 100) AS line_discount_amount,
        
        -- Original price before discount
        ol.quantity * ol.line_unit_price AS line_gross_amount
        
    FROM order_lines ol
    LEFT JOIN {{ ref('stg_products') }} p 
        ON ol.product_id = p.product_id 
        AND p.is_current = TRUE
)

SELECT
    -- Fact key (grain: order_item_id)
    {{ dbt_utils.generate_surrogate_key(['order_item_id']) }} AS fact_sales_key,
    
    -- Degenerate dimension (order info stored in fact)
    order_id,
    order_item_id,
    
    -- Dimension foreign keys
    dim_customer_key,
    dim_product_key,
    dim_date_key,
    
    -- Order attributes (degenerate dimensions)
    order_status,
    payment_method,
    
    -- =========================================================================
    -- MEASURES - Additive (can sum across all dimensions)
    -- =========================================================================
    
    -- Quantity
    quantity AS units_sold,
    
    -- Revenue
    line_gross_amount AS gross_revenue,
    line_discount_amount AS discount_amount,
    line_total AS net_revenue,
    
    -- Cost & Profit
    line_cost AS cost_of_goods_sold,
    line_profit AS gross_profit,
    
    -- =========================================================================
    -- MEASURES - Semi-Additive (context-dependent aggregation)
    -- =========================================================================
    
    -- Prices (use AVG or weighted average when aggregating)
    line_unit_price AS unit_selling_price,
    product_unit_cost AS unit_cost,
    
    -- Percentages (use weighted average when aggregating)
    line_discount_percent AS discount_percentage,
    line_margin_percentage AS margin_percentage,
    
    -- =========================================================================
    -- DERIVED ATTRIBUTES (for convenience)
    -- =========================================================================
    
    -- Time (allows direct filtering without join)
    order_date,
    DATE(order_date) AS order_date_only,
    HOUR(order_date) AS order_hour,
    
    -- Product attributes (denormalized for common filters)
    product_id,
    category_name,
    subcategory_name,
    brand,
    
    -- Customer (for direct filtering)
    customer_id,
    
    -- =========================================================================
    -- AUDIT & QUALITY
    -- =========================================================================
    
    validation_status,
    order_loaded_at AS source_loaded_at,
    CURRENT_TIMESTAMP() AS _fact_loaded_at,
    '{{ invocation_id }}' AS _dbt_run_id

FROM enriched
