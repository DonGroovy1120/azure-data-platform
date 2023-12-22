# Set spark configuration: https://docs.microsoft.com/en-us/azure/databricks/dev-tools/databricks-connect#aad-tokens
from json import loads
from os import environ
from pyspark.sql import SparkSession
from subprocess import run

def get_spark_context():
    # Command to run the Azure CLI
    command = "az account get-access-token --resource 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
    if "DATABRICKS_SUBSCRIPTION_ID" in environ:
        command += " --subscription " + environ["DATABRICKS_SUBSCRIPTION_ID"]

    # Run and decode the result
    result = run(command.split(" "), capture_output=True)
    result_json = loads(result.stdout.decode())

    # Get and set the spark object with the AAD token
    spark = SparkSession.builder.getOrCreate()
    spark.conf.set("spark.databricks.service.token", result_json["accessToken"])
    
    return spark