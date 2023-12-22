from pulumi import ResourceOptions
from pulumi_azure_native import operationalinsights

from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from management import resource_groups
from project_config import platform_config, platform_outputs

outputs = platform_outputs["logs"] = {}

workspace_name = generate_resource_name(
    resource_type="log_analytics_workspace",
    resource_name="logs",
    platform_config=platform_config,
)
log_analytics_workspace = operationalinsights.Workspace(
    resource_name=workspace_name,
    location=platform_config.region.long_name,
    resource_group_name=resource_groups["security"].name,
    retention_in_days=platform_config["logs"]["retention"],
    sku=operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
    workspace_name=workspace_name,
    tags=platform_config.tags,
    opts=ResourceOptions(protect=platform_config.resource_protection),
)
if platform_config.resource_protection:
    lock_resource(workspace_name, log_analytics_workspace.id)

outputs["name"] = log_analytics_workspace.name
outputs["id"] = log_analytics_workspace.id
