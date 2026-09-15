# Cloud Mapping — ADF, Databricks, ADLS, Microsoft Fabric

This document maps the local medallion pipeline to common Microsoft / Azure patterns. **No live cloud credentials** are required; treat this as a design handoff for client workshops.

## Component mapping

| Local (this repo) | Azure / Fabric equivalent |
|-------------------|---------------------------|
| `data/raw/` | **ADLS Gen2** container `raw/retail/` (landing zone) |
| Bronze Parquet | ADLS `bronze/retail/` or Databricks bronze Delta tables |
| Silver transforms | **Databricks** notebooks / Jobs (PySpark) or Fabric Lakehouse notebooks |
| Gold marts | Databricks SQL / Fabric Warehouse / Synapse dedicated pool |
| Airflow DAG | **Azure Data Factory** pipeline (or Fabric Data Pipeline / Airflow on AKS) |
| `sql/*.sql` | Synapse / Fabric Warehouse / Snowflake (if hybrid) |
| DQ checks | ADF data flow asserts, Databricks Expectations, or Great Expectations job |

## Azure Data Factory (ADF)

Suggested pipeline activities:

1. **Get Metadata / ForEach** — discover new files under ADLS `raw/`.  
2. **Copy Activity** — raw → bronze (preserve format; add ingest columns via mapping).  
3. **Databricks Notebook Activity** — invoke silver notebook (clean + DQ).  
4. **If Condition** — fail pipeline when DQ summary has failures.  
5. **Databricks / Script Activity** — gold mart builds.  
6. **Stored Procedure / Script** — refresh warehouse views.

Trigger: tumbling window or event-based (BlobCreated on landing).

## Databricks + ADLS

```
ADLS raw  --(Autoloader)-->  bronze Delta
                |
         DLT / Jobs (silver)
                |
           gold Delta / SQL warehouse
```

- Use **Unity Catalog** schemas: `retail.bronze`, `retail.silver`, `retail.gold`.  
- Replace `src/jobs/*.py` with notebooks that read/write Delta; keep the same DQ module.  
- Schedule with Databricks Workflows *or* call from ADF.

## Microsoft Fabric

| Layer | Fabric artifact |
|-------|-----------------|
| Lakehouse | Files (raw) + Tables (bronze/silver/gold Delta) |
| Notebooks | PySpark / pandas equivalents of `src/jobs` |
| Data Pipeline | Orchestration mirroring the Airflow DAG |
| Warehouse | Gold marts via T-SQL (adapt Snowflake DDL) |
| Power BI | Semantic model on gold tables / Direct Lake |

## Example ADF pipeline JSON

```json
{
  "name": "pl_retail_medallion",
  "properties": {
    "activities": [
      {"name": "Copy_Raw_To_Bronze", "type": "Copy"},
      {"name": "Notebook_Silver_DQ", "type": "DatabricksNotebook",
       "dependsOn": [{"activity": "Copy_Raw_To_Bronze", "dependencyConditions": ["Succeeded"]}]},
      {"name": "Notebook_Gold_Marts", "type": "DatabricksNotebook",
       "dependsOn": [{"activity": "Notebook_Silver_DQ", "dependencyConditions": ["Succeeded"]}]}
    ]
  }
}
```

## Security & ops notes (client checklist)

- Prefer **managed identities** over keys for ADLS / Databricks.  
- Separate storage accounts or containers per environment (dev/test/prod).  
- Quarantine path stays in silver for data steward review.  
- Cost control: Autoloader + incremental gold; cluster policies for Spark jobs.  
