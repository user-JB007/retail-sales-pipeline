-- =============================================================================
-- Fact tables (Silver → Warehouse)
-- =============================================================================

USE DATABASE RETAIL_ANALYTICS;
USE SCHEMA SILVER;

CREATE OR REPLACE TABLE FACT_SALES (
    TRANSACTION_ID      VARCHAR(32)   NOT NULL,
    TRANSACTION_TS      TIMESTAMP_NTZ NOT NULL,
    TRANSACTION_DATE    DATE          NOT NULL,
    DATE_KEY            NUMBER(8,0),
    STORE_ID            VARCHAR(16)   NOT NULL,
    PRODUCT_ID          VARCHAR(16)   NOT NULL,
    CUSTOMER_ID         VARCHAR(16),
    QUANTITY            NUMBER(10,0)  NOT NULL,
    UNIT_PRICE          NUMBER(12,2),
    DISCOUNT_PCT        NUMBER(5,4),
    DISCOUNT_AMOUNT     NUMBER(12,2),
    GROSS_AMOUNT        NUMBER(14,2),
    NET_AMOUNT          NUMBER(14,2)  NOT NULL,
    UNIT_COST           NUMBER(12,2),
    COGS                NUMBER(14,2),
    GROSS_PROFIT        NUMBER(14,2),
    GROSS_MARGIN_PCT    NUMBER(8,2),
    PAYMENT_METHOD      VARCHAR(32),
    CHANNEL             VARCHAR(32),
    CURRENCY            VARCHAR(8) DEFAULT 'USD',
    CATEGORY            VARCHAR(64),
    SUBCATEGORY         VARCHAR(64),
    BRAND               VARCHAR(64),
    DW_LOADED_AT        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_FACT_SALES PRIMARY KEY (TRANSACTION_ID)
);

-- Clustering for analytical scans (Snowflake)
ALTER TABLE FACT_SALES CLUSTER BY (TRANSACTION_DATE, STORE_ID);

CREATE OR REPLACE TABLE QUARANTINE_SALES (
    TRANSACTION_ID      VARCHAR(32),
    TRANSACTION_TS      TIMESTAMP_NTZ,
    STORE_ID            VARCHAR(16),
    PRODUCT_ID          VARCHAR(16),
    CUSTOMER_ID         VARCHAR(16),
    QUANTITY            NUMBER(10,0),
    NET_AMOUNT          NUMBER(14,2),
    CHANNEL             VARCHAR(32),
    PAYMENT_METHOD      VARCHAR(32),
    QUARANTINE_REASON   VARCHAR(200),
    DW_LOADED_AT        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Example MERGE pattern from staged Parquet / Snowpipe landing
-- MERGE INTO FACT_SALES tgt
-- USING STG_FACT_SALES src
--   ON tgt.TRANSACTION_ID = src.TRANSACTION_ID
-- WHEN MATCHED THEN UPDATE SET ...
-- WHEN NOT MATCHED THEN INSERT (...);
