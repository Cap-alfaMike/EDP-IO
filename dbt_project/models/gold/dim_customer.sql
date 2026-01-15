-- ============================================================================
-- EDP-IO - Gold Layer: Customer Dimension
-- ============================================================================
-- PURPOSE:
-- Conformed customer dimension for the star schema, flattening SCD2 history
-- for the current view while preserving access to historical data.
--
-- DESIGN TRADE-OFFS:
-- -----------------
-- 1. Denormalized: Single table vs. normalized address
--    - Trade-off: Storage vs. query simplicity
--    - Decision: Denormalized for BI tool compatibility
--
-- 2. Current-Only View:
--    - This dimension shows current state only
--    - For historical analysis, use silver.stg_customers with valid_from/valid_to
--
-- 3. Surrogate Key:
--    - dim_customer_key is stable across updates
--    - Use for fact table joins
--
-- PERFORMANCE:
-- -----------
-- - Materialized as table for fast BI queries
-- - Optimized for common filters: segment, city, state
--
-- BUSINESS CONTEXT:
-- ----------------
-- Customer segmentation drives marketing campaigns, personalization,
-- and lifetime value analysis. This dimension enables slicing by:
-- - Geographic region
-- - Customer segment (Bronze → Platinum)
-- - Tenure (registration_date derived)
-- - Activity status
-- ============================================================================

{{
    config(
        materialized='table',
        tags=['gold', 'dimension', 'customer']
    )
}}

WITH current_customers AS (
    -- Get current version only from SCD2 Silver table
    SELECT
        surrogate_key AS silver_key,
        customer_id,
        first_name,
        last_name,
        email,
        phone,
        address_line1,
        city,
        state,
        postal_code,
        country_code,
        customer_segment,
        registration_date,
        is_active,
        source_created_at,
        source_updated_at,
        _loaded_at
    FROM {{ ref('stg_customers') }}
    WHERE is_current = TRUE
),

enriched AS (
    SELECT
        *,
        -- Full name for display
        CONCAT(first_name, ' ', last_name) AS full_name,
        
        -- Customer tenure calculation
        DATEDIFF(CURRENT_DATE(), registration_date) AS tenure_days,
        FLOOR(DATEDIFF(CURRENT_DATE(), registration_date) / 365.25) AS tenure_years,
        
        -- Tenure segment for analysis
        CASE
            WHEN DATEDIFF(CURRENT_DATE(), registration_date) < 90 THEN 'NEW'
            WHEN DATEDIFF(CURRENT_DATE(), registration_date) < 365 THEN 'DEVELOPING'
            WHEN DATEDIFF(CURRENT_DATE(), registration_date) < 730 THEN 'ESTABLISHED'
            ELSE 'LOYAL'
        END AS tenure_segment,
        
        -- Geographic region (Brazil-specific)
        CASE
            WHEN state IN ('AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO') THEN 'Norte'
            WHEN state IN ('AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE') THEN 'Nordeste'
            WHEN state IN ('DF', 'GO', 'MT', 'MS') THEN 'Centro-Oeste'
            WHEN state IN ('ES', 'MG', 'RJ', 'SP') THEN 'Sudeste'
            WHEN state IN ('PR', 'RS', 'SC') THEN 'Sul'
            ELSE 'Unknown'
        END AS region,
        
        -- Segment numeric for sorting/comparison
        CASE customer_segment
            WHEN 'BRONZE' THEN 1
            WHEN 'SILVER' THEN 2
            WHEN 'GOLD' THEN 3
            WHEN 'PLATINUM' THEN 4
            ELSE 0
        END AS segment_rank
    FROM current_customers
)

SELECT
    -- Surrogate key for joins (use this in fact tables)
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} AS dim_customer_key,
    
    -- Natural key (for reference/debugging)
    customer_id,
    
    -- Name attributes
    first_name,
    last_name,
    full_name,
    
    -- Contact (PII - consider masking in production views)
    email,
    phone,
    
    -- Address
    address_line1,
    city,
    state,
    postal_code,
    country_code,
    region,
    
    -- Segments
    customer_segment,
    segment_rank,
    tenure_segment,
    
    -- Metrics
    registration_date,
    tenure_days,
    tenure_years,
    
    -- Status
    is_active,
    CASE WHEN is_active THEN 'Active' ELSE 'Inactive' END AS status_description,
    
    -- Audit
    source_created_at,
    source_updated_at,
    _loaded_at,
    CURRENT_TIMESTAMP() AS _dim_loaded_at,
    '{{ invocation_id }}' AS _dbt_run_id

FROM enriched
