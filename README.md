# Retail Sales Medallion Pipeline

End-to-end retail sales and customer-service analytics on a bronze → silver → gold (medallion) lakehouse layout, with Airflow orchestration, Snowflake-flavored SQL marts, Tableau workbooks, and cloud mapping notes for Azure Data Factory / Databricks / ADLS / Microsoft Fabric.

**Repo:** [github.com/user-JB007/retail-sales-pipeline](https://github.com/user-JB007/retail-sales-pipeline)

---

## Tableau Reports

**Primary BI deliverable: packaged `.twbx` workbooks** (interactive — open in Tableau Desktop or Tableau Public). Screenshots below are secondary previews for GitHub browsing.

> **Use v3 — not v2.** `Retail_Ops_Dashboard_v2.twbx` opens as an empty **Sheet 31** (Tableau discarded the dashboards). Download **v3** instead.

| Workbook | Path | Notes |
|----------|------|-------|
| **Retail Ops Dashboard v3 (combined)** | [`tableau/workbooks/Retail_Ops_Dashboard_v3.twbx`](tableau/workbooks/Retail_Ops_Dashboard_v3.twbx) | **Sales** + **Service** dashboard tabs with KPI cards + charts |
| **Sales Dashboard v3** (reliable single) | [`tableau/workbooks/Retail_Sales_Dashboard_v3.twbx`](tableau/workbooks/Retail_Sales_Dashboard_v3.twbx) | Opens on **1. Overview** (KPI cards + charts filled) |
| **Service Dashboard v3** (reliable single) | [`tableau/workbooks/Retail_Service_Dashboard_v3.twbx`](tableau/workbooks/Retail_Service_Dashboard_v3.twbx) | Opens on **1. Overview** (SLA/CSAT KPIs + charts) |
| Sales Report (legacy multi-page) | [`tableau/workbooks/Retail_Sales_Report.twbx`](tableau/workbooks/Retail_Sales_Report.twbx) | Overview · Stores · Trends |
| Service Report (legacy multi-page) | [`tableau/workbooks/Retail_Service_Satisfaction_Report.twbx`](tableau/workbooks/Retail_Service_Satisfaction_Report.twbx) | Overview · SLA · Pending |

### How to open (Desktop / Public)

1. Download [`Retail_Ops_Dashboard_v3.twbx`](tableau/workbooks/Retail_Ops_Dashboard_v3.twbx) (or the Sales/Service Dashboard v3 files).
2. Double-click, or File → Open in Tableau Desktop / Tableau Public.
3. You should land on a **dashboard** tab (grid icon) — **Sales** (combined) or **1. Overview** (singles) — with KPI cards and charts filled. Switch tabs for the other page.
4. If anything still looks empty, open the two singles: `Retail_Sales_Dashboard_v3.twbx` and `Retail_Service_Dashboard_v3.twbx` and click the dashboard tabs at the bottom.
5. Do **not** open `Retail_Ops_Dashboard_v2.twbx` (known empty Sheet 31).

CSV marts and Hyper extracts are embedded; no separate data hunt. Worksheet tabs stay visible on purpose (hiding them contributed to v2 discarding UI).

**Rebuild after mart refresh:**

```bash
python scripts/run_local.py --engine pandas
python src/viz/generate_tableau_pages.py --export-marts
python scripts/build_hyper.py
python scripts/build_workbook.py
```

Details, calculated fields, and parameters: [`tableau/README.md`](tableau/README.md)

### Report 1 — Sales Report (preview)
Revenue, orders, stores/regions, categories/products, and trends. Parameter: **Top N Stores**.

| Page | Preview |
|------|---------|
| Overview | ![Sales Overview](tableau/screenshots/sales_01_overview.png) |
| Stores & Regions | ![Stores](tableau/screenshots/sales_02_stores.png) |
| Trends | ![Trends](tableau/screenshots/sales_03_trends.png) |

### Report 2 — Customer Satisfaction & Service Report (preview)
CSAT, within/beyond SLA, pending queue, aging, reason and channel. Parameter: **Aging Threshold Hours**.

| Page | Preview |
|------|---------|
| Overview | ![Service Overview](tableau/screenshots/service_01_overview.png) |
| SLA Performance | ![SLA](tableau/screenshots/service_02_sla.png) |
| Pending & Aging | ![Pending](tableau/screenshots/service_03_pending_aging.png) |

---

## Architecture

```mermaid
flowchart LR
  subgraph Sources
    RAW["data/raw<br/>CSV / Parquet"]
    API["Fake Store API<br/>products · carts · users"]
  end

  subgraph Medallion["Medallion Lakehouse"]
    B["Bronze<br/>land + ingest metadata"]
    S["Silver<br/>clean · conform · DQ · quarantine"]
    G["Gold<br/>business marts"]
  end

  subgraph Sinks
    LOCAL["Local FastAPI sink<br/>POST /ingest"]
    JP["JSONPlaceholder<br/>POST /posts"]
  end

  subgraph Orchestration
    AF["Apache Airflow DAG"]
  end

  subgraph Warehouse
    SF["Snowflake-style SQL<br/>dims · facts · marts"]
  end

  RAW --> B
  API --> B
  B --> S --> G
  G --> LOCAL
  G --> JP
  AF -.-> B
  AF -.-> S
  AF -.-> G
  G --> SF
```

| Layer | What it does |
|-------|----------------|
| **Raw** | Stores, products, customers, sales transactions, service tickets |
| **API source** | Fake Store HTTP pull → bronze `api_products` / `api_carts` / `api_users` |
| **Bronze** | Parquet landing with `_ingest_ts`, `_source_system`, run id |
| **Silver** | Typed dims/facts (sales + service), quarantine invalid rows, DQ report |
| **Gold** | Daily store/category sales, CLV, product performance, channel mix, service/SLA mart |
| **API sink** | POST gold summary to local landing API + JSONPlaceholder |
| **SQL** | Snowflake-flavored schemas, dims, facts, gold CTAS/views |

### Sources

| Source | Type | Notes |
|--------|------|-------|
| `data/raw/*.csv` | File | Default offline path (`--source file`) |
| [Fake Store API](https://fakestoreapi.com/) | HTTP GET | Primary API source — products, carts, users; no key required. Config: `api_source` in `config/pipeline.yaml` / `API_SOURCE_BASE_URL` |

### Sinks

| Sink | Type | Notes |
|------|------|-------|
| Local landing API | HTTP POST | `src/sinks/http_sink_server.py` — `POST /ingest` → `data/landing/`; default `SINK_API_URL=http://127.0.0.1:8089/ingest` |
| [JSONPlaceholder](https://jsonplaceholder.typicode.com/posts) | HTTP POST | Alternate external sink for delivery proof (`EXTERNAL_SINK_URL`) |
| File fallback | Local JSON | If the local sink is unreachable, payload is written under `data/landing/` |

---

## Tech stack

| Concern | Choice |
|---------|--------|
| Transforms | Python + **PySpark job structure** with **pandas fallback** (default for local/CI) |
| Architecture | Medallion (bronze / silver / gold) |
| Orchestration | Apache Airflow DAG (`dags/`) |
| Warehouse | Snowflake-flavored DDL + marts (`sql/`) |
| Quality | Custom DQ checks with fail-on-error gate |
| BI | Tableau workbooks + screenshots (`tableau/`) |
| Cloud design | ADF, Databricks, ADLS, Fabric — see `docs/cloud_mapping.md` |

---

## Quick start

```bash
# 1. Clone & install
git clone https://github.com/user-JB007/retail-sales-pipeline.git
cd retail-sales-pipeline
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt

# 2. Run the full pipeline (generate → bronze → silver → gold)
python scripts/run_local.py --engine pandas

# 3. Inspect outputs
ls data/gold/*/data.csv
cat data/gold/pipeline_outputs.json
```

Regenerate raw extracts only:

```bash
python -m src.generate_source_data --n-transactions 5000 --n-tickets 1800
```

Run layers individually:

```bash
python -m src.jobs.bronze_ingest --engine pandas
python -m src.jobs.silver_transform --engine pandas
python -m src.jobs.gold_aggregates --engine pandas
```

Tests:

```bash
pytest -q
```

### Optional PySpark

```bash
pip install "pyspark>=3.4,<4"   # requires Java 11+
unset FORCE_PANDAS
python scripts/run_local.py --engine spark
```

### Airflow

Point `RETAIL_PIPELINE_HOME` at this repo and drop `dags/retail_sales_pipeline_dag.py` into your Airflow `dags/` folder (or symlink). Task graph: `extract_api → generate_or_refresh_raw → bronze_ingest → silver_transform_and_dq → gold_build_marts → load_api_sink → warehouse_load_hint`.

### API source + sink

```bash
# Pull Fake Store products/carts/users into bronze (primary API source stage)
python -m src.integrations.api_source

# Full pipeline with API source, then POST gold summary to sinks
python scripts/run_local.py --engine pandas --source both --sink api

# Local sink receiver (separate terminal)
uvicorn src.sinks.http_sink_server:app --host 127.0.0.1 --port 8089

# Push gold summary only (local + JSONPlaceholder)
python -m src.integrations.api_sink
```

Offline: omit `--source api` / use `--source file` so the existing `data/raw` path continues to work when the network is unavailable. If a prior `data/bronze/api_products` landing exists, `api_source` reuses it on network failure.

---

## Project layout

```
retail-sales-pipeline/
├── README.md
├── requirements.txt / pyproject.toml
├── .env.example
├── config/pipeline.yaml
├── data/raw/                 # source CSVs + parquet (committed)
├── src/
│   ├── generate_source_data.py
│   ├── jobs/                 # bronze → silver → gold
│   ├── integrations/         # Fake Store source + HTTP sink client
│   ├── sinks/http_sink_server.py
│   ├── quality/checks.py
│   ├── viz/generate_tableau_pages.py
│   └── utils/
├── dags/retail_sales_pipeline_dag.py
├── sql/                      # Snowflake-flavored DDL + marts
├── docs/architecture.md
├── docs/cloud_mapping.md
├── tableau/                  # workbook briefs, calcs, screenshots, marts
├── scripts/run_local.py
└── tests/
```

Derived `data/bronze|silver|gold` are produced locally and gitignored.

---

## Gold marts

After `run_local.py`, gold marts include:

- `mart_daily_sales_by_store` — revenue, units, margin by store/day
- `mart_daily_sales_by_category` — category trends
- `mart_customer_lifetime_value` — order count, LTV, AOV by loyalty tier
- `mart_product_performance` — top products by net revenue
- `mart_channel_mix` — channel × payment method
- `mart_service_performance` — tickets with SLA clocks, CSAT, pending/aging

Silver also writes `quarantine_sales` for intentionally injected bad rows (orphan stores, negative qty, null amounts) so DQ behavior is auditable.

---

## Design notes

- **Fail-closed DQ** in silver — pipeline raises if critical checks fail.
- **Quarantine path** keeps bad rows auditable instead of silent drops.
- **Engine switch** (`--engine pandas|spark|auto`) keeps cluster-ready structure while allowing local runs.
- **SQL + cloud docs** bridge lakehouse code to warehouse and Azure/Fabric delivery.
- **No secrets** — `.env.example` lists environment variable names only.

More detail: [`docs/architecture.md`](docs/architecture.md) · [`docs/cloud_mapping.md`](docs/cloud_mapping.md)

---

## License

MIT
