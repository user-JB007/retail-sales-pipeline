# Architecture — Retail Sales Medallion Pipeline

## Overview

This project implements a classic **medallion (bronze / silver / gold)** retail sales pipeline suitable for design review and as a template for freelance client work.

| Layer | Purpose | Contents |
|-------|---------|----------|
| **Raw** | Source extracts | CSV / Parquet POS-style files |
| **Bronze** | Land as-is + metadata | Parquet tables with `_ingest_ts`, `_source_system` |
| **Silver** | Clean & conform | Dims + fact + quarantine; DQ gates |
| **Gold** | Business marts | Daily store/category, CLV, product, channel mix |
| **Warehouse** | SQL presentation | Snowflake-flavored DDL + marts (`sql/`) |

## Local runtime flow

```
generate_source_data → bronze_ingest → silver_transform (+ DQ) → gold_aggregates
                     ↑                    ↑
              data/raw/*           quarantine + manifests
```

Orchestration is expressed as an **Apache Airflow DAG** (`dags/retail_sales_pipeline_dag.py`) with the same task graph. For a local run, execute `python scripts/run_local.py`.

## Engine strategy

- **Preferred:** PySpark job structure (session helper, bronze write as parquet directories).
- **Default local/CI path:** pandas fallback via `FORCE_PANDAS=1` or `--engine pandas`.
- Same layer boundaries and DQ checks regardless of engine — the job graph stays production-shaped without requiring a Spark cluster.

## Data quality

Silver enforces:

- Non-empty fact
- Unique `transaction_id`
- Required non-nulls
- Positive quantity / net amount
- Referential integrity to store & product
- Allowed channel / payment enums

Invalid rows are written to `data/silver/quarantine_sales` instead of silently dropping without audit.

## Warehouse layer

`sql/` contains Snowflake-style:

1. Database / schema creation  
2. Dimension DDL (+ `DIM_DATE` seed)  
3. Fact + quarantine DDL with clustering hint  
4. Gold mart CTAS / views  

These scripts are documentation-as-code for warehouse design reviews; they document warehouse design; local runs use the Python jobs.

## Cloud platform mapping

See [cloud_mapping.md](./cloud_mapping.md) for how the same pipeline maps to **Azure Data Factory, Databricks, ADLS, and Microsoft Fabric** without live credentials.

## Extension ideas (client conversations)

- CDC from transactional DB via Debezium / Fivetran  
- dbt models on top of silver for versioned SQL transforms  
- Great Expectations or Soda as dedicated DQ runners  
- Incremental loads partitioned by `transaction_date`  
- Row-level security on gold views for multi-tenant retail brands  


## Service data

Raw `service_tickets` land in bronze, clean as `fact_service_tickets` in silver, and publish as gold `mart_service_performance` for the Customer Satisfaction & Service Tableau workbook.


## API source and sink

**Source (primary for API stage):** [Fake Store API](https://fakestoreapi.com/) — `GET /products`, `/carts`, `/users` into bronze tables `api_products`, `api_carts`, `api_users`. URLs and timeouts are config-driven (`config/pipeline.yaml` `api_source`, env `API_SOURCE_BASE_URL`).

**Sink:** POST gold mart summary JSON to:

1. Local FastAPI landing service (`src/sinks/http_sink_server.py`, `SINK_API_URL`, default `http://127.0.0.1:8089/ingest`) writing under `data/landing/`
2. Optional [JSONPlaceholder](https://jsonplaceholder.typicode.com/posts) (`EXTERNAL_SINK_URL`)

Airflow tasks: `extract_api`, `load_api_sink`. CLI: `python scripts/run_local.py --source api|both --sink api`.

When the network is unavailable, keep `--source file` so file-based raw → bronze continues; API extract reuses an existing bronze landing if present.
