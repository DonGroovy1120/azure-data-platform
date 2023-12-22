# Databricks notebook source

from os import environ
from py4j.protocol import Py4JJavaError
from typing import Union

from ingenii_data_engineering.dbt_schema import get_project_config, get_source

from ingenii_databricks.enums import Stage
from ingenii_databricks.pipeline import add_to_source_table, archive_file, \
    create_file_table, move_rows_to_review, prepare_individual_table_yml, \
    pre_process_file, propagate_source_data, remove_file_table, \
    revert_individual_table_yml, test_file_table
from ingenii_databricks.orchestration import ImportFileEntry
from ingenii_databricks.validation import check_parameters, \
    check_source_schema, compare_schema_and_table

# COMMAND ----------


def get_parameter(parameter_name: str) -> Union[str, None]:
    """
    Obtain a parameter of the pipeline. If it hasn't been passed, return None

    Parameters
    ----------
    parameter_name : str
        The name of the parameter to get

    Returns
    -------
    Union[str, None]
        Either the parameter value, or None
    """

    try:
        return dbutils.widgets.get(parameter_name)
    except Py4JJavaError:
        return


# COMMAND ----------

# Obtain parameters
dbt_root_folder = environ["DBT_ROOT_FOLDER"]
log_target_folder = environ["DBT_LOGS_FOLDER"]
file_name = get_parameter("file_name")
increment = get_parameter("increment")
source = get_parameter("source")
table_name = get_parameter("table")
file_path = get_parameter("file_path")

if (source is None or table_name is None) and file_path is not None:
    source, table_name = \
        file_path.replace("raw/", "").strip("/").split("/")

check_parameters(source, table_name, file_path, file_name, increment)

# Passed from widget as a string
increment = int(increment)

# Will get populated later in the pipeline
databricks_dbt_token = None

# COMMAND ----------

source_details = get_source(dbt_root_folder, source)

# Check that the schema for this particular source is acceptable
check_source_schema(source_details)

if table_name not in source_details["tables"]:
    raise Exception(
        f"Table schema '{table_name}' not found for source '{source}'"
    )
table_schema = source_details["tables"][table_name]

# COMMAND ----------

# Find or create the orchestration entry
import_entry = ImportFileEntry(spark, source_name=source,
                               table_name=table_name, file_name=file_name,
                               increment=increment)

# Check that the current table schema will accept this new data
compare_schema_and_table(spark, import_entry, table_schema)

# COMMAND ----------

if import_entry.is_stage(Stage.NEW):
    archive_file(import_entry)
    import_entry.update_status(Stage.ARCHIVED)

# COMMAND ----------

# Pre-process and stage the file
if import_entry.is_stage(Stage.ARCHIVED):
    pre_process_file(import_entry)

    # Create individual table in the source database
    n_rows = create_file_table(spark, import_entry, table_schema)
    import_entry.update_rows_read(n_rows)
    import_entry.update_status(Stage.STAGED)

# COMMAND ----------

# Create temporary .yml to identify this as a source, including tests
# Run the tests
# Move any failed rows: https://docs.getdbt.com/faqs/failed-tests
# Run cleaning checks, moving offending entries to a review table
if import_entry.is_stage(Stage.STAGED):
    prepare_individual_table_yml(table_schema["file_name"], import_entry)

    # Run tests and analyse the results
    databricks_dbt_token = \
        dbutils.secrets.get(scope=environ["DBT_TOKEN_SCOPE"],
                            key=environ["DBT_TOKEN_NAME"])
    testing_result = \
        test_file_table(import_entry, databricks_dbt_token,
                        dbt_root_folder, log_target_folder)

    revert_individual_table_yml(table_schema["file_name"])

    # If bad data, entries in the column will be NULL
    if not testing_result["success"]:
        print("Errors found while testing:")
        for error_message in testing_result["error_messages"]:
            print(f"    - {error_message}")

        if testing_result["error_sql_files"]:
            move_rows_to_review(
                spark, import_entry, table_schema,
                dbt_root_folder, testing_result["error_sql_files"])

            print(f"Rows with problems have been moved to review table "
                  f"{import_entry.get_full_review_table_name()}")
        else:
            raise Exception("\n".join([
                "stdout:", testing_result["stdout"],
                "stderr:", testing_result["stderr"]
                ]))
    else:
        import_entry.update_status(Stage.CLEANED)

# COMMAND ----------

# Append / Merge into main table
if import_entry.is_stage(Stage.CLEANED):
    add_to_source_table(spark, import_entry, table_schema)
    import_entry.update_status(Stage.INSERTED)

# COMMAND ----------

# Tidying
if import_entry.is_stage(Stage.INSERTED):
    remove_file_table(spark, dbutils, import_entry)
    import_entry.update_status(Stage.COMPLETED)

    # Optimize table to keep it performant
    spark.sql("OPTIMIZE orchestration.import_file ZORDER BY (source, table)")

# COMMAND ----------

# Check pipeline did complete as expected
final_stage = import_entry.get_current_stage()
if final_stage != Stage.COMPLETED:
    raise Exception(
        f"Pipeline didn't make it to completion! "
        f"Only made it to the '{final_stage}' stage!"
    )

# COMMAND ----------

# Propagate this source data to downstream models and snapshots
if databricks_dbt_token is None:
    databricks_dbt_token = \
        dbutils.secrets.get(scope=environ["DBT_TOKEN_SCOPE"],
                            key=environ["DBT_TOKEN_NAME"])

project_name = get_project_config(dbt_root_folder)["name"]
propagate_source_data(
    databricks_dbt_token, project_name,
    import_entry.source, import_entry.table)
