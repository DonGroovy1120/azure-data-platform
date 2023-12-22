# Instructions: https://docs.microsoft.com/en-gb/azure/databricks/dev-tools/databricks-connect

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

USER root
RUN apt-get update
RUN apt-get install default-jre -y

USER jovyan
ARG CLUSTER_VERSION
RUN pip uninstall pyspark && pip install -U "databricks-connect==${CLUSTER_VERSION}.*"

COPY ingenii_databricks_connect-1.0.0-py3-none-any.whl /tmp/
RUN pip install /tmp/ingenii_databricks_connect-1.0.0-py3-none-any.whl
