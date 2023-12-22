import pulumi
import pulumi_azure_native as azure_native

from ingenii_azure_data_platform.logs import log_diagnostic_settings
from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from logs import log_analytics_workspace
from logging import log
from project_config import platform_config, platform_outputs
from management import resource_groups

outputs = platform_outputs["network"]["network_security_groups"] = {}

# TODO: Remove duplication. Use a for loop or another method to create the NSGs.

# ----------------------------------------------------------------------------------------------------------------------
# DATABRICKS NSG for ENGINEERING SUBNETS
# ----------------------------------------------------------------------------------------------------------------------
databricks_engineering_resource_name = generate_resource_name(
    resource_type="network_security_group",
    resource_name="databricks-eng",
    platform_config=platform_config,
)
databricks_engineering = azure_native.network.NetworkSecurityGroup(
    resource_name=databricks_engineering_resource_name,
    network_security_group_name=databricks_engineering_resource_name,
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
    # Tags are added in the ignore_changes list because of:
    # https://github.com/ingenii-solutions/azure-data-platform/issues/71
    opts=pulumi.ResourceOptions(ignore_changes=["security_rules", "tags"]),
)
if platform_config.resource_protection:
    lock_resource(databricks_engineering_resource_name, databricks_engineering.id)

# Export NSG metadata
outputs["databricks_engineering"] = {
    "name": databricks_engineering.name,
    "id": databricks_engineering.id,
}

# ----------------------------------------------------------------------------------------------------------------------
# DATABRICKS NSG for ANALYTICS SUBNETS
# ----------------------------------------------------------------------------------------------------------------------
databricks_analytics_resource_name = generate_resource_name(
    resource_type="network_security_group",
    resource_name="databricks-atc",
    platform_config=platform_config,
)
databricks_analytics = azure_native.network.NetworkSecurityGroup(
    resource_name=databricks_analytics_resource_name,
    network_security_group_name=databricks_analytics_resource_name,
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
    # Tags are added in the ignore_changes list because of:
    # https://github.com/ingenii-solutions/azure-data-platform/issues/71
    opts=pulumi.ResourceOptions(ignore_changes=["security_rules", "tags"]),
)
if platform_config.resource_protection:
    lock_resource(databricks_analytics_resource_name, databricks_analytics.id)

# Export NSG metadata
outputs["databricks_analytics"] = {
    "name": databricks_analytics.name,
    "id": databricks_analytics.id,
}

# ----------------------------------------------------------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------------------------------------------------------

engineering_workspace_config = platform_config["analytics_services"]["databricks"][
    "workspaces"
]["engineering"]
engineering_nsg_details = engineering_workspace_config.get(
    "network_security_groups", {}
)
log_diagnostic_settings(
    platform_config,
    log_analytics_workspace.id,
    databricks_engineering.type,
    databricks_engineering.id,
    databricks_engineering_resource_name,
    logs_config=engineering_nsg_details.get("logs", {}),
    metrics_config=engineering_nsg_details.get("metrics", {}),
)

analytics_workspace_config = platform_config["analytics_services"]["databricks"][
    "workspaces"
]["analytics"]
analytics_nsg_details = analytics_workspace_config.get("network_security_groups", {})
log_diagnostic_settings(
    platform_config,
    log_analytics_workspace.id,
    databricks_analytics.type,
    databricks_analytics.id,
    databricks_analytics_resource_name,
    logs_config=analytics_nsg_details.get("logs", {}),
    metrics_config=analytics_nsg_details.get("metrics", {}),
)
