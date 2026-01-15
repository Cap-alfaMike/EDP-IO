-- ============================================================================
-- EDP-IO - Silver Layer: Staged Customers (SCD Type 2)
-- ============================================================================
-- PURPOSE:
-- Transform Bronze customer data into a clean, historized Silver layer
-- with full SCD Type 2 implementation for tracking customer changes.
--
-- DESIGN TRADE-OFFS:
-- -----------------
-- 1. Full History vs. Storage:
--    - We keep every version of customer data
--    - Increases storage but enables time-travel analytics
--    - "What segment was this customer in last quarter?"
--
-- 2. Incremental vs. Full Refresh:
--    - Incremental for efficiency (only process new/changed records)
--    - MERGE strategy ensures idempotency
--    - Full refresh option available for disaster recovery
--
-- 3. Denormalization:
--    - Address fields kept flat (no separate address table)
--    - Simplifies queries at cost of some normalization
--    - Acceptable for analytics workload
--
-- BUSINESS IMPACT:
-- ---------------
-- - Customer analytics can now answer historical questions
-- - Segment migration tracking for retention analysis
-- - Audit compliance for data lineage
-- ============================================================================

{{
    config(
        materialized='incremental',
        unique_key='surrogate_key',
        incremental_strategy='merge',
        merge_update_columns=['valid_to', 'is_current', '_loaded_at'],
        tags=['silver', 'scd2', 'customer']
    )
}}

-- ============================================================================
-- SOURCE: Bronze layer customer data
-- ============================================================================

WITH source AS (
    SELECT
        customer_id,
        -- Clean and standardize name fields
        INITCAP(TRIM(first_name)) AS first_name,
        INITCAP(TRIM(last_name)) AS last_name,
        -- Lowercase email for consistency
        LOWER(TRIM(email)) AS email,
        -- Standardize phone (remove non-digits for comparison)
        REGEXP_REPLACE(phone, '[^0-9+]', '') AS phone,
        -- Address fields
        TRIM(address_line1) AS address_line1,
        INITCAP(TRIM(city)) AS city,
        UPPER(TRIM(state)) AS state,
        TRIM(postal_code) AS postal_code,
        UPPER(TRIM(COALESCE(country_code, 'BR'))) AS country_code,
        -- Business fields
        UPPER(TRIM(customer_segment)) AS customer_segment,
        registration_date,
        COALESCE(is_active, TRUE) AS is_active,
        -- Source timestamps
        created_at AS source_created_at,
        updated_at AS source_updated_at,
        -- Ingestion metadata from Bronze
        _ingestion_timestamp,
        _source_system,
        _batch_id
    FROM {{ source('bronze', 'customers') }}
    
    {% if is_incremental() %}
    -- Only process new or updated records
    WHERE _ingestion_timestamp > (
        SELECT COALESCE(MAX(_loaded_at), '1900-01-01'::TIMESTAMP)
        FROM {{ this }}
    )
    {% endif %}
),

-- ============================================================================
-- CHANGE DETECTION: Compare with current records
-- ============================================================================
-- We hash the tracked columns to detect changes efficiently
-- This avoids expensive column-by-column comparisons

current_records AS (
    {% if is_incremental() %}
    SELECT
        customer_id,
        {{ dbt_utils.generate_surrogate_key([
            'first_name', 'last_name', 'email', 'phone',
            'address_line1', 'city', 'state', 'postal_code',
            'customer_segment', 'is_active'
        ]) }} AS current_hash,
        surrogate_key,
        valid_from
    FROM {{ this }}
    WHERE is_current = TRUE
    {% else %}
    -- Empty for initial load
    SELECT
        NULL AS customer_id,
        NULL AS current_hash,
        NULL AS surrogate_key,
        NULL AS valid_from
    WHERE 1 = 0
    {% endif %}
),

-- Identify inserts and updates
changes AS (
    SELECT
        s.*,
        {{ dbt_utils.generate_surrogate_key([
            's.first_name', 's.last_name', 's.email', 's.phone',
            's.address_line1', 's.city', 's.state', 's.postal_code',
            's.customer_segment', 's.is_active'
        ]) }} AS row_hash,
        c.current_hash,
        c.surrogate_key AS existing_surrogate_key,
        CASE
            WHEN c.customer_id IS NULL THEN 'INSERT'
            WHEN {{ dbt_utils.generate_surrogate_key([
                's.first_name', 's.last_name', 's.email', 's.phone',
                's.address_line1', 's.city', 's.state', 's.postal_code',
                's.customer_segment', 's.is_active'
            ]) }} != c.current_hash THEN 'UPDATE'
            ELSE 'NO_CHANGE'
        END AS change_type
    FROM source s
    LEFT JOIN current_records c
        ON s.customer_id = c.customer_id
),

-- ============================================================================
-- FINAL OUTPUT: SCD Type 2 records
-- ============================================================================

final AS (
    SELECT
        -- Surrogate key for joining (hash of business key + valid_from)
        {{ dbt_utils.generate_surrogate_key(['customer_id', 'source_updated_at']) }} AS surrogate_key,
        
        -- Business key
        customer_id,
        
        -- Attributes (tracked for changes)
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
        is_active,
        
        -- Source timestamps
        registration_date,
        source_created_at,
        source_updated_at,
        
        -- SCD Type 2 fields
        source_updated_at AS valid_from,
        CAST('9999-12-31 23:59:59' AS TIMESTAMP) AS valid_to,
        TRUE AS is_current,
        
        -- Row hash for future change detection
        row_hash AS _row_hash,
        
        -- Audit fields
        CURRENT_TIMESTAMP() AS _loaded_at,
        '{{ invocation_id }}' AS _dbt_run_id,
        _source_system,
        _batch_id
        
    FROM changes
    WHERE change_type != 'NO_CHANGE'
)

SELECT * FROM final

-- ============================================================================
-- POST-PROCESSING NOTES:
-- ============================================================================
-- After this model runs, a post-hook should close expired records:
-- UPDATE silver.stg_customers
-- SET valid_to = <new_valid_from>, is_current = FALSE
-- WHERE customer_id IN (SELECT customer_id FROM changes WHERE change_type = 'UPDATE')
--   AND is_current = TRUE
--   AND valid_from < <new_valid_from>
-- ============================================================================
