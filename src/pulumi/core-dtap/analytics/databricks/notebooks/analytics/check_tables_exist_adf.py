# Databricks notebook source

# MAGIC %md
# MAGIC ### To be used by Azure Data Factory only.
# MAGIC If you want to sync the tables, use the `mount_tables` notebook in this folder

# COMMAND ----------

from json import loads

# E.g. "/mnt/source/schema1|{\"name\":\"table1\",\"type\":\"Folder\"}"
schema_path, tables = dbutils.widgets.get("table_details").split("|")

schema = schema_path.split("/")[-1]
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")

# Tables that the Analytics workspace already knows about
known_tables = [table.tableName for table in spark.sql(f"SHOW TABLES FROM {schema}").collect()]

# Tables that ADF has told us about
folder_tables = [loads(table_json_raw)["name"] for table_json_raw in tables.split(";")]

# Any new tables
new_tables = [table for table in folder_tables if table not in known_tables]
if new_tables:
    raise Exception(" ".join([
            f"New tables not in the Analytics workspace!",
            f"Schema: {schema}, tables: {str(sorted(new_tables))}.",
            "Run the notebook at /Shared/Ingenii Engineering/mount_tables to make these available in the Analytics workspace"
        ])
    )
