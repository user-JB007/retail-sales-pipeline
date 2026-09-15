-- =============================================================================
-- Snowflake-flavored DDL: schemas for medallion + warehouse presentation
-- Target: Snowflake (also compatible with DuckDB / BigQuery dialect with tweaks)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS RETAIL_ANALYTICS;
USE DATABASE RETAIL_ANALYTICS;

CREATE SCHEMA IF NOT EXISTS BRONZE COMMENT = 'Raw landing zone — append-only extracts';
CREATE SCHEMA IF NOT EXISTS SILVER COMMENT = 'Cleaned, conformed, DQ-gated entities';
CREATE SCHEMA IF NOT EXISTS GOLD   COMMENT = 'Business marts for BI and self-serve';
CREATE SCHEMA IF NOT EXISTS RAW    COMMENT = 'External stage / file landing metadata';

-- File format for CSV ingest demos
CREATE OR REPLACE FILE FORMAT RETAIL_ANALYTICS.RAW.CSV_FF
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  NULL_IF = ('', 'NULL', 'null');

-- Example external stage (replace URL / credentials in real deployments)
-- CREATE OR REPLACE STAGE RETAIL_ANALYTICS.RAW.LANDING
--   URL = 's3://your-bucket/retail/raw/'
--   FILE_FORMAT = RETAIL_ANALYTICS.RAW.CSV_FF;
