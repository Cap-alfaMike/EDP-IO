-- ============================================================================
-- EDP-IO - Silver Layer: Staged Orders
-- ============================================================================
-- PURPOSE:
-- Transform Bronze order data into clean Silver layer with validation
-- and standardization. Orders are transactional (no SCD2 needed).
--
-- DESIGN DECISIONS:
-- -----------------
-- 1. No SCD2: Orders are immutable transactions (status changes tracked via events)
-- 2. Validation: Business rules enforced (total calculation, enum values)
-- 3. Deduplication: Handle potential duplicate ingestion gracefully
--
-- BUSINESS IMPACT:
-- ---------------
-- - Accurate revenue reporting
-- - Order status tracking for operations
-- - Customer purchase behavior analysis
-- ============================================================================

{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
        tags=['silver', 'transactional', 'orders']
    )
}}

WITH source AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        -- Standardize status enum
        UPPER(TRIM(order_status)) AS order_status,
        -- PII handling: Keep address but flag for masking in Gold if needed
        shipping_address,
        UPPER(TRIM(payment_method)) AS payment_method,
        -- Financial fields
        CAST(subtotal AS DECIMAL(12, 2)) AS subtotal,
        CAST(discount_amount AS DECIMAL(10, 2)) AS discount_amount,
        CAST(shipping_cost AS DECIMAL(10, 2)) AS shipping_cost,
        CAST(total_amount AS DECIMAL(12, 2)) AS total_amount,
        -- Calculated total for validation
        CAST(subtotal - discount_amount + shipping_cost AS DECIMAL(12, 2)) AS calculated_total,
        -- Timestamps
        created_at AS source_created_at,
        updated_at AS source_updated_at,
        -- Metadata
        _ingestion_timestamp,
        _source_system,
        _batch_id
    FROM {{ source('bronze', 'orders') }}
    
    {% if is_incremental() %}
    WHERE _ingestion_timestamp > (
        SELECT COALESCE(MAX(_loaded_at), '1900-01-01'::TIMESTAMP)
        FROM {{ this }}
    )
    {% endif %}
),

-- ============================================================================
-- VALIDATION: Apply business rules
-- ============================================================================

validated AS (
    SELECT
        *,
        -- Total validation (allow small rounding differences)
        ABS(total_amount - calculated_total) < 0.01 AS is_total_valid,
        -- Status validation
        order_status IN ('PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED') AS is_status_valid,
        -- Payment validation
        payment_method IN ('CREDIT_CARD', 'DEBIT_CARD', 'PIX', 'BOLETO', 'WALLET') AS is_payment_valid
    FROM source
),

-- Flag records but don't filter (allow investigation)
flagged AS (
    SELECT
        *,
        CASE
            WHEN NOT is_total_valid THEN 'INVALID_TOTAL'
            WHEN NOT is_status_valid THEN 'INVALID_STATUS'
            WHEN NOT is_payment_valid THEN 'INVALID_PAYMENT'
            ELSE 'VALID'
        END AS validation_status
    FROM validated
),

-- ============================================================================
-- DEDUPLICATION: Take latest version per order_id
-- ============================================================================

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_id 
            ORDER BY _ingestion_timestamp DESC
        ) AS row_num
    FROM flagged
),

-- ============================================================================
-- FINAL OUTPUT
-- ============================================================================

final AS (
    SELECT
        -- Primary key
        order_id,
        
        -- Foreign key
        customer_id,
        
        -- Order details
        order_date,
        order_status,
        payment_method,
        
        -- Shipping (PII-sensitive)
        shipping_address,
        
        -- Financials (use calculated_total if original is invalid)
        subtotal,
        discount_amount,
        shipping_cost,
        CASE 
            WHEN is_total_valid THEN total_amount
            ELSE calculated_total
        END AS total_amount,
        
        -- Derived metrics
        discount_amount / NULLIF(subtotal, 0) * 100 AS discount_percentage,
        
        -- Validation flag
        validation_status,
        
        -- Timestamps
        order_date AS order_datetime,
        DATE(order_date) AS order_date_key,
        EXTRACT(YEAR FROM order_date) AS order_year,
        EXTRACT(MONTH FROM order_date) AS order_month,
        EXTRACT(DAY FROM order_date) AS order_day,
        EXTRACT(DAYOFWEEK FROM order_date) AS order_day_of_week,
        
        source_created_at,
        source_updated_at,
        
        -- Audit fields
        CURRENT_TIMESTAMP() AS _loaded_at,
        '{{ invocation_id }}' AS _dbt_run_id,
        _source_system,
        _batch_id
        
    FROM deduplicated
    WHERE row_num = 1  -- Latest version only
)

SELECT * FROM final
