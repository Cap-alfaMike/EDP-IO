-- ============================================================================
-- EDP-IO - Gold Layer: Date Dimension
-- ============================================================================
-- PURPOSE:
-- Standard date dimension for time-based analysis.
-- Pre-generated calendar table for consistent date handling.
--
-- DESIGN PHILOSOPHY:
-- -----------------
-- Date dimensions are fundamental to star schemas. This table:
-- - Provides consistent date attributes across all facts
-- - Enables fiscal year analysis (configurable)
-- - Supports Brazilian holidays (for retail patterns)
-- - Allows easy time-based filtering and grouping
--
-- PERFORMANCE:
-- -----------
-- Small table (~10K rows for 30 years) - cached in memory by BI tools
-- ============================================================================

{{
    config(
        materialized='table',
        tags=['gold', 'dimension', 'date']
    )
}}

-- Generate date spine (2020-01-01 to 2030-12-31)
WITH date_spine AS (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2020-01-01' as date)",
        end_date="cast('2030-12-31' as date)"
    ) }}
),

dates AS (
    SELECT
        CAST(date_day AS DATE) AS calendar_date
    FROM date_spine
),

enriched AS (
    SELECT
        calendar_date,
        
        -- Date key (YYYYMMDD format for efficient joining)
        CAST(DATE_FORMAT(calendar_date, 'yyyyMMdd') AS INT) AS date_key,
        
        -- Year components
        YEAR(calendar_date) AS year,
        QUARTER(calendar_date) AS quarter,
        MONTH(calendar_date) AS month,
        WEEKOFYEAR(calendar_date) AS week_of_year,
        DAYOFMONTH(calendar_date) AS day_of_month,
        DAYOFWEEK(calendar_date) AS day_of_week,
        DAYOFYEAR(calendar_date) AS day_of_year,
        
        -- Period names
        DATE_FORMAT(calendar_date, 'MMMM') AS month_name,
        DATE_FORMAT(calendar_date, 'MMM') AS month_name_short,
        DATE_FORMAT(calendar_date, 'EEEE') AS day_name,
        DATE_FORMAT(calendar_date, 'E') AS day_name_short,
        
        -- Formatted dates
        DATE_FORMAT(calendar_date, 'yyyy-MM') AS year_month,
        DATE_FORMAT(calendar_date, 'yyyy-Qq') AS year_quarter,
        
        -- Week boundaries
        DATE_TRUNC('week', calendar_date) AS week_start_date,
        DATE_ADD(DATE_TRUNC('week', calendar_date), 6) AS week_end_date,
        
        -- Month boundaries
        DATE_TRUNC('month', calendar_date) AS month_start_date,
        LAST_DAY(calendar_date) AS month_end_date,
        
        -- Flags
        CASE WHEN DAYOFWEEK(calendar_date) IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekend,
        CASE WHEN DAYOFWEEK(calendar_date) NOT IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekday,
        CASE WHEN calendar_date = LAST_DAY(calendar_date) THEN TRUE ELSE FALSE END AS is_month_end,
        
        -- Fiscal year (assuming Jan fiscal year start - configurable)
        YEAR(calendar_date) AS fiscal_year,
        QUARTER(calendar_date) AS fiscal_quarter,
        
        -- Relative flags (for dashboards)
        CASE WHEN calendar_date = CURRENT_DATE() THEN TRUE ELSE FALSE END AS is_today,
        CASE WHEN YEAR(calendar_date) = YEAR(CURRENT_DATE()) THEN TRUE ELSE FALSE END AS is_current_year,
        CASE WHEN YEAR(calendar_date) = YEAR(CURRENT_DATE()) 
             AND MONTH(calendar_date) = MONTH(CURRENT_DATE()) THEN TRUE ELSE FALSE END AS is_current_month,
        
        -- Days from today (for trending)
        DATEDIFF(calendar_date, CURRENT_DATE()) AS days_from_today
        
    FROM dates
)

SELECT
    -- Primary key
    date_key,
    calendar_date,
    
    -- Year hierarchy
    year,
    quarter,
    month,
    week_of_year,
    day_of_month,
    day_of_week,
    day_of_year,
    
    -- Names
    month_name,
    month_name_short,
    day_name,
    day_name_short,
    
    -- Formatted strings
    year_month,
    year_quarter,
    
    -- Week info
    week_start_date,
    week_end_date,
    
    -- Month info
    month_start_date,
    month_end_date,
    
    -- Fiscal calendar
    fiscal_year,
    fiscal_quarter,
    
    -- Flags
    is_weekend,
    is_weekday,
    is_month_end,
    is_today,
    is_current_year,
    is_current_month,
    
    -- Relative
    days_from_today,
    
    -- Audit
    CURRENT_TIMESTAMP() AS _dim_loaded_at,
    '{{ invocation_id }}' AS _dbt_run_id

FROM enriched
