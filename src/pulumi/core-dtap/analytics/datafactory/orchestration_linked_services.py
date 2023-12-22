from pulumi_azure_native import datafactory as adf

from ingenii_azure_data_platform.iam import ServicePrincipalRoleAssignment

from analytics.databricks import analytics_workspace as databricks_analytics, \
    engineering_workspace as databricks_engineering
from analytics.datafactory.orchestration import datafactory, datafactory_name
from management import resource_groups
from security import credentials_store
from storage.datalake import datalake

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> DATALAKE ACCESS
# ----------------------------------------------------------------------------------------------------------------------

ServicePrincipalRoleAssignment(
    principal_id=datafactory.identity.principal_id,
    principal_name="orchestration-datafactory-identity",
    role_name="Storage Blob Data Contributor",
    scope=datalake.id,
    scope_description="datalake",
)

datalake_linked_service = adf.LinkedService(
    resource_name=f"{datafactory_name}-link-to-datalake",
    factory_name=datafactory.name,
    linked_service_name="DataLake",
    properties=adf.AzureBlobFSLinkedServiceArgs(
        url=datalake.primary_endpoints.dfs,
        description="Managed by Ingenii Data Platform",
        type="AzureBlobFS",
    ),
    resource_group_name=resource_groups["infra"].name,
)

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> CREDENTIALS STORE
# ----------------------------------------------------------------------------------------------------------------------

datafactory_acccess_to_credentials_store = ServicePrincipalRoleAssignment(
    role_name="Key Vault Secrets User",
    principal_id=datafactory.identity.principal_id,
    principal_name="orchestration-datafactory-identity",
    scope=credentials_store.key_vault.id,
    scope_description="cred-store",
)

credentials_store_linked_service = adf.LinkedService(
    resource_name=f"{datafactory_name}-link-to-credentials-store",
    factory_name=datafactory.name,
    linked_service_name="Credentials Store",
    properties=adf.AzureKeyVaultLinkedServiceArgs(
        base_url=f"https://{credentials_store.key_vault_name}.vault.azure.net",
        description="Managed by Ingenii Data Platform",
        type="AzureKeyVault",
    ),
    resource_group_name=resource_groups["infra"].name,
)  # type: ignore

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> DELTA LAKE
# ----------------------------------------------------------------------------------------------------------------------

databricks_engineering_delta_linked_service = adf.LinkedService(
    resource_name=f"{datafactory_name}-link-to-databricks-engineering-delta",
    factory_name=datafactory.name,
    linked_service_name="Databricks Engineering Delta",
    properties=adf.AzureDatabricksDeltaLakeLinkedServiceArgs(
        domain=databricks_engineering.workspace.workspace_url.apply(
            lambda url: f"https://{url}"
        ),
        access_token=databricks_engineering.datafactory_token.token_value,  # type: ignore
        cluster_id=databricks_engineering.clusters["default"].id,
        description="Managed by Ingenii Data Platform",
        type="AzureDatabricksDeltaLake",
    ),
    resource_group_name=resource_groups["infra"].name,
)  # type: ignore


# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> DATABRICKS
# ----------------------------------------------------------------------------------------------------------------------

def linked_service_cluster(resource_name, linked_service_name, workspace, cluster_id):
    return adf.LinkedService(
        resource_name=resource_name.replace(" ", "-").lower(),
        factory_name=datafactory.name,
        linked_service_name=linked_service_name,
        properties=adf.AzureDatabricksLinkedServiceArgs(
            authentication="MSI",
            domain=workspace.workspace_url.apply(lambda url: f"https://{url}"),
            existing_cluster_id=cluster_id,
            workspace_resource_id=workspace.id,
            description="Managed by Ingenii Data Platform",
            type="AzureDatabricks",
        ),
        resource_group_name=resource_groups["infra"].name,
    )  # type: ignore

def linked_service_instance_pool(resource_name, linked_service_name, workspace, instance_pool_id):
    return adf.LinkedService(
        resource_name=resource_name.replace(" ", "-").lower(),
        factory_name=datafactory.name,
        linked_service_name=linked_service_name,
        properties=adf.AzureDatabricksLinkedServiceArgs(
            authentication="MSI",
            domain=workspace.workspace_url.apply(lambda url: f"https://{url}"),
            instance_pool_id=instance_pool_id,
            workspace_resource_id=workspace.id,
            description="Managed by Ingenii Data Platform",
            type="AzureDatabricks",
        ),
        resource_group_name=resource_groups["infra"].name,
    )  # type: ignore

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> DATABRICKS -> ENGINEERING
# ----------------------------------------------------------------------------------------------------------------------

ServicePrincipalRoleAssignment(
    principal_id=datafactory.identity.principal_id,
    principal_name="orchestration-data-factory",
    role_name="Contributor",
    scope=databricks_engineering.workspace.id,
    scope_description="databricks-engineering",
)

databricks_engineering_compute_linked_service = \
    linked_service_cluster(
        f"{datafactory_name}-link-to-databricks-engineering-compute",
        "Databricks Engineering Compute",
        databricks_engineering.workspace,
        databricks_engineering.clusters["default"].id
    )


# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> DATABRICKS -> ANALYTICS
# ----------------------------------------------------------------------------------------------------------------------

ServicePrincipalRoleAssignment(
    principal_id=datafactory.identity.principal_id,
    principal_name="orchestration-data-factory",
    role_name="Contributor",
    scope=databricks_analytics.workspace.id,
    scope_description="databricks-analytics",
)

databricks_analytics_compute_linked_service = \
    linked_service_cluster(
        f"{datafactory_name}-link-to-databricks-analytics-compute",
        "Databricks Analytics Compute",
        databricks_analytics.workspace,
        databricks_analytics.clusters["default"].id
    )
