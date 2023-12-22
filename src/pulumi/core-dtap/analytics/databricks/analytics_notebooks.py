from os import listdir
from pulumi import ResourceOptions
import pulumi_databricks as databricks

from ingenii_azure_data_platform.utils import generate_resource_name

from analytics.databricks.analytics_workspace import databricks_provider
from project_config import platform_config

folder_path = "/Shared/Ingenii Engineering"

ingenii_engineering_directory = databricks.Directory(
    resource_name=generate_resource_name(
        resource_type="databricks_directory",
        resource_name="analytics_ingenii_engineering",
        platform_config=platform_config,
    ),
    path=folder_path,
    opts=ResourceOptions(
        delete_before_replace=True,
        provider=databricks_provider,
    ),
)

notebooks_root = "analytics/databricks/notebooks/analytics"
for file_name in listdir(notebooks_root):
    if not file_name.endswith(".py"):
        continue
    databricks.Notebook(
        resource_name=generate_resource_name(
            resource_type="databricks_notebook",
            resource_name=f"ingenii_engineering_{file_name.strip('.py')}",
            platform_config=platform_config,
        ),
        language="PYTHON",
        path=f"{folder_path}/{file_name.strip('.py')}",
        source=f"{notebooks_root}/{file_name}",
        opts=ResourceOptions(
            depends_on=[ingenii_engineering_directory],
            provider=databricks_provider,
        ),
    )
