# Databricks notebook source

# MAGIC %md
# MAGIC ### Create tables for any new data
# MAGIC To be run whenever new tables are created in the engineering workspace and are needed here
# MAGIC This is always safe to run

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE DATABASE IF NOT EXISTS orchestration ;
# MAGIC CREATE TABLE IF NOT EXISTS orchestration.import_file USING DELTA LOCATION '/mnt/orchestration/import_file' ;

# COMMAND ----------

from pyspark.sql.functions import col

# Add all known source tables. Avoid any individual tables
known_databases = [db.databaseName for db in spark.sql(f"SHOW DATABASES").collect()]
known_sources = spark.table("orchestration.import_file").select("source").distinct().collect()

for source in known_sources:
    if source.source.lower() not in known_databases:
        spark.sql(f"CREATE DATABASE {source.source}")

    known_tables = spark.table("orchestration.import_file").where(col("source") == source.source).select("table").distinct().collect()
    mounted_tables = [table.tableName for table in spark.sql(f"SHOW TABLES FROM {source.source}").collect()]
    for known_table in known_tables:
        if known_table.table.lower() not in mounted_tables:
            print(f"Adding table {source.source}.{known_table.table}")
            spark.sql(f"CREATE TABLE {source.source}.{known_table.table} USING DELTA LOCATION '/mnt/source/{source.source}/{known_table.table}'")

# COMMAND ----------

# Add any model tables
known_databases = [db.databaseName for db in spark.sql(f"SHOW DATABASES").collect()]

for schema in dbutils.fs.ls("/mnt/models"):
  schema = schema.name.strip("/").lower()
  if schema not in known_databases:
    spark.sql(f"CREATE DATABASE {schema}")

  known_tables = [table.tableName for table in spark.sql(f"SHOW TABLES FROM {schema}").collect()]
  for table in dbutils.fs.ls(f"/mnt/models/{schema}"):
    table = table.name.strip("/").lower()
    if table not in known_tables:
      print(f"Adding model {schema}.{table}")
      spark.sql(f"CREATE TABLE {schema}.{table} USING DELTA LOCATION '/mnt/models/{schema}/{table}'")

# COMMAND ----------

# Add any snapshot tables
known_databases = [db.databaseName for db in spark.sql(f"SHOW DATABASES").collect()]

for schema in dbutils.fs.ls("/mnt/snapshots"):
  schema = schema.name.strip("/").lower()
  if schema not in known_databases:
    spark.sql(f"CREATE DATABASE {schema}")

  known_tables = [table.tableName for table in spark.sql(f"SHOW TABLES FROM {schema}").collect()]
  for table in dbutils.fs.ls(f"/mnt/snapshots/{schema}"):
    table = table.name.strip("/").lower()
    if table not in known_tables:
      print(f"Adding snapshot {schema}.{table}")
      spark.sql(f"CREATE TABLE {schema}.{table} USING DELTA LOCATION '/mnt/snapshots/{schema}/{table}'")

# COMMAND ----------
