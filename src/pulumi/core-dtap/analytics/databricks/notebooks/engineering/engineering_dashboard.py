# Databricks notebook source
from ingenii_databricks.dashboard_utils import create_widgets
create_widgets(spark, dbutils)

# COMMAND ----------

from ingenii_databricks.dashboard_utils import filtered_import_table
display(filtered_import_table(spark, dbutils))

# COMMAND ----------

# Run an ingestion on an exiting entry. This cell should be updated and run manually
# dbutils.notebook.run("/Shared/Ingenii Engineering/data_pipeline", 600, {
#     "source": "random_example",
#     "table": "alpha",
#     "file_name": "20210512_RandomExample.csv",
#     "increment": 0
# })

# COMMAND ----------

# Run an ingestion on a new file. This cell should be updated and run manually
# dbutils.notebook.run("/Shared/Ingenii Engineering/data_pipeline", 600, {
#     "file_path": "/random_example/alpha",
#     "file_name": "20210514_RandomExample.csv",
#     "increment": 0
# })

# COMMAND ----------

# Script to ingest incomplete files
# from pyspark.sql.functions import col
# incomplete = spark.table("orchestration.import_file").where(col("date_completed").isNull())

# for row in incomplete.collect():
#   dbutils.notebook.run("/Shared/Ingenii Engineering/data_pipeline", 600, {
#       "source": row.source,
#       "table": row.table,
#       "file_name": row.file_name,
#       "increment": row.increment
#   })

# COMMAND ----------

# Script to abandon incomplete file
# from ingenii_databricks.pipeline_utils import abandon_file
# abandon_file(spark=spark, dbutils=dbutils, row_hash=123456789, increment=0)
