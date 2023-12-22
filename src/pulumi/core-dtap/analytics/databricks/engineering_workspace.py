from os import getenv

import pulumi_azure_native as azure_native
import pulumi_azuread as azuread
from pulumi import FileAsset, Output, ResourceOptions
import pulumi_databricks as databricks

from ingenii_azure_data_platform.databricks import create_cluster
from ingenii_azure_data_platform.iam import (
    GroupRoleAssignment,
    ServicePrincipalRoleAssignment,
)
from ingenii_azure_data_platform.logs import log_diagnostic_settings
from ingenii_azure_data_platform.network import PlatformFirewall
from ingenii_azure_data_platform.utils import (
    generate_hash,
    generate_resource_name,
    lock_resource,
)

from logs import log_analytics_workspace
from management import resource_groups
from management.user_groups import user_groups
from network import vnet
from platform_shared import add_config_registry_secret, shared_platform_config
from project_config import azure_client, platform_config, platform_outputs
from security import credentials_store
from storage import storage_accounts

workspace_short_name = "engineering"
workspace_config = platform_config["analytics_services"]["databricks"]["workspaces"][
    workspace_short_name
]
workspace_firewall_config = workspace_config.get("network", {}).get("firewall", {})
shared_workspace_config = shared_platform_config["analytics_services"]["databricks"][
    "workspaces"
][workspace_short_name]
outputs = platform_outputs["analytics"]["databricks"]["workspaces"][
    workspace_short_name
] = {}

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE
# ----------------------------------------------------------------------------------------------------------------------
workspace_name = generate_resource_name(
    resource_type="databricks_workspace",
    resource_name=workspace_short_name,
    platform_config=platform_config,
)

workspace_managed_resource_group_short_name = generate_resource_name(
    resource_type="resource_group",
    resource_name=f"dbw-{workspace_short_name}",
    platform_config=platform_config,
)

workspace_managed_resource_group_name = f"/subscriptions/{azure_client.subscription_id}/resourceGroups/{workspace_managed_resource_group_short_name}"

workspace = azure_native.databricks.Workspace(
    resource_name=workspace_name,
    workspace_name=workspace_name,
    location=platform_config.region.long_name,
    managed_resource_group_id=workspace_managed_resource_group_name,
    parameters=azure_native.databricks.WorkspaceCustomParametersArgs(
        custom_private_subnet_name=azure_native.databricks.WorkspaceCustomStringParameterArgs(
            value=vnet.dbw_engineering_containers_subnet.name,  # type: ignore
        ),
        custom_public_subnet_name=azure_native.databricks.WorkspaceCustomStringParameterArgs(
            value=vnet.dbw_engineering_hosts_subnet.name,  # type: ignore
        ),
        custom_virtual_network_id=azure_native.databricks.WorkspaceCustomStringParameterArgs(
            value=vnet.vnet.id,
        ),
        enable_no_public_ip=azure_native.databricks.WorkspaceCustomBooleanParameterArgs(
            value=True
        ),
    ),
    sku=azure_native.databricks.SkuArgs(name="Premium"),
    resource_group_name=resource_groups["infra"].name,
    opts=ResourceOptions(
        depends_on=[
            vnet.dbw_engineering_containers_subnet,
            vnet.dbw_engineering_hosts_subnet
        ],
        protect=platform_config.resource_protection,
    ),
)
if platform_config.resource_protection:
    lock_resource(workspace_name, workspace.id)

outputs.update({
    "hostname": workspace.workspace_url,
    "id": workspace.workspace_id,
    "name": workspace.name,
    "url": workspace.workspace_url.apply(
        lambda url: f"https://{url}/login.html?o={url.split('adb-')[1].split('.')[0]}"
    ),
})

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> LOGGING
# ----------------------------------------------------------------------------------------------------------------------

log_diagnostic_settings(
    platform_config,
    log_analytics_workspace.id,
    workspace.type,
    workspace.id,
    workspace_name,
    logs_config=workspace_config.get("logs", {}),
    metrics_config=workspace_config.get("metrics", {}),
)

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> IAM ROLE ASSIGNMENTS
# ----------------------------------------------------------------------------------------------------------------------

# TODO: Create a function that takes care of the role assignments. Replace all role assignments using the function.
# Create role assignments defined in the YAML files
for assignment in workspace_config.get("iam", {}).get("role_assignments", []):
    # User Group Assignment
    user_group_ref_key = assignment.get("user_group_ref_key")
    if user_group_ref_key is not None:
        GroupRoleAssignment(
            principal_id=user_groups[user_group_ref_key]["object_id"],
            principal_name=user_group_ref_key,
            role_name=assignment["role_definition_name"],
            scope=workspace.id,
            scope_description="engineering-workspace",
        )

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> PROVIDER
# ----------------------------------------------------------------------------------------------------------------------
databricks_provider = databricks.Provider(
    resource_name=workspace_name,
    azure_client_id=getenv("ARM_CLIENT_ID", azure_client.client_id),
    azure_client_secret=getenv("ARM_CLIENT_SECRET"),
    azure_tenant_id=getenv("ARM_TENANT_ID", azure_client.tenant_id),
    azure_workspace_resource_id=workspace.id,
    host=workspace.workspace_url,
)

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> GENERAL CONFIG
# ----------------------------------------------------------------------------------------------------------------------
databricks.WorkspaceConf(
    resource_name=workspace_name,
    custom_config={
        "enableDcs": workspace_config["config"].get(
            "enable_container_services", "false"
        ),
        "enableIpAccessLists": str(
            workspace_firewall_config.get("enabled", "false")
        ).lower(),
    },
    opts=ResourceOptions(provider=databricks_provider),
)

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> USERS
# ----------------------------------------------------------------------------------------------------------------------
for user_config in workspace_config.get("users", []):
    roles = user_config.get("roles", [])
    is_admin = "admin" in roles
    databricks.User(
        resource_name=f"engineering_workspace_user_{user_config['email_address']}",
        active=user_config.get("active", True),
        allow_cluster_create=is_admin or "cluster_create" in roles,
        allow_instance_pool_create=is_admin or "instance_pool_create" in roles,
        databricks_sql_access=is_admin or "sql_access" in roles,
        user_name=user_config["email_address"],
        workspace_access=is_admin or "workspace_access" in roles,
        opts=ResourceOptions(provider=databricks_provider),
    )

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> FIREWALL
# ----------------------------------------------------------------------------------------------------------------------

if workspace_firewall_config.get("enabled"):
    firewall = platform_config.global_firewall + PlatformFirewall(
        enabled=True, ip_access_list=workspace_firewall_config.get("ip_access_list", [])
    )

    databricks.IpAccessList(
        resource_name=f"{workspace_name}-firewall",
        label="allow_in",
        list_type="ALLOW",
        ip_addresses=firewall.ip_access_list,
        opts=ResourceOptions(provider=databricks_provider),
    )

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> SECRETS & TOKENS
# ----------------------------------------------------------------------------------------------------------------------

# SECRET SCOPE
secret_scope_name = "main"
secret_scope = databricks.SecretScope(
    resource_name=f"{workspace_name}-secret-scope-main",
    name=secret_scope_name,
    opts=ResourceOptions(provider=databricks_provider),
)

# DBT TOKEN
dbt_token_name = f"{workspace_short_name}-token-for-dbt"
dbt_token_resource_name = f"{workspace_name}-token-for-dbt"

# Also used to generate the DBT documentation by the DevOps pipeline
dbt_token = databricks.Token(
    resource_name=dbt_token_resource_name,
    comment="Data Build Tool Token - Used for DBT automation",
    opts=ResourceOptions(provider=databricks_provider),
)

dbt_token_as_scope_secret = databricks.Secret(
    resource_name=dbt_token_resource_name,
    scope=secret_scope.id,
    string_value=dbt_token.token_value,
    key=dbt_token_name,
    opts=ResourceOptions(provider=databricks_provider),
)

dbt_token_as_key_vault_secret = azure_native.keyvault.Secret(
    resource_name=dbt_token_resource_name,
    properties=azure_native.keyvault.SecretPropertiesArgs(
        value=dbt_token.token_value,
    ),
    resource_group_name=resource_groups["security"].name,
    secret_name=dbt_token_name,
    vault_name=credentials_store.key_vault.name,
)

# DATAFACTORY TOKEN
datafactory_token = databricks.Token(
    resource_name=f"{workspace_name}-token-for-datafactory",
    comment="Data Factory Token - Used for Data Factory integration",
    opts=ResourceOptions(provider=databricks_provider),
)

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> INSTANCE POOLS
# ----------------------------------------------------------------------------------------------------------------------
instance_pools = {}
for ref_key, config in workspace_config.get("instance_pools", {}).items():

    instance_pool_resource_name = generate_resource_name(
        resource_type="databricks_instance_pool",
        resource_name=f"{workspace_short_name}-{ref_key}",
        platform_config=platform_config,
    )

    instance_pools[ref_key] = databricks.InstancePool(
        resource_name=instance_pool_resource_name,
        instance_pool_name=config["display_name"],
        node_type_id=config["node_type_id"],
        min_idle_instances=config.get("min_idle_instances", 0),
        max_capacity=config.get("max_capacity", 5),
        enable_elastic_disk=config.get("enable_elastic_disk", True),
        azure_attributes=databricks.InstancePoolAzureAttributesArgs(
            availability=config.get("availability", "ON_DEMAND_AZURE"),
            spot_bid_max_price=config.get("spot_bid_max_price", 0),
        ),
        disk_spec=databricks.InstancePoolDiskSpecArgs(
            disk_type=databricks.InstancePoolDiskSpecDiskTypeArgs(
                azure_disk_volume_type=config.get("disk_type", "STANDARD_LRS")
            ),
            disk_count=config.get("disk_count", 1),
            disk_size=config.get("disk_size", 30),
        ),
        idle_instance_autotermination_minutes=config.get(
            "idle_instance_auto_termination_minutes", 0
        ),
        custom_tags=config.get("custom_tags", None),
        opts=ResourceOptions(
            provider=databricks_provider,
            delete_before_replace=True,
        ),
    )

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> AZURE DEVOPS REPOSITORIES
# ----------------------------------------------------------------------------------------------------------------------
# Unable to assign this using a service principal
# for repo_config in shared_workspace_config.get("devops_repositories", []):
#     repo_name = repo_config["name"]
#     databricks.Repo(
#         resource_name=f"databricks-{workspace_short_name}-devops-repository-{repo_name}",
#         git_provider="azureDevOpsServices",
#         path=f"/Repos/AzureDevOps/{repo_name}",
#         url=SHARED_OUTPUTS.get(
#             "analytics", "databricks", workspace_short_name, "repositories", repo_name, "remote_url",
#             preview="https://Preview.URL"
#         ),
#         opts=ResourceOptions(
#             provider=databricks_provider,
#             delete_before_replace=True,
#         ),
#     )

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> CLUSTER TAGS
# ----------------------------------------------------------------------------------------------------------------------

# https://docs.microsoft.com/en-us/azure/databricks/administration-guide/account-settings/usage-detail-tags-azure#tag-conflict-resolution
cluster_default_tags = {"x_" + k: v for k, v in platform_config.tags.items()}

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> CLUSTERS -> SYSTEM CLUSTER
# ----------------------------------------------------------------------------------------------------------------------

system_cluster = create_cluster(
    databricks_provider=databricks_provider, platform_config=platform_config, 
    resource_name=f"{workspace_short_name}-system",
    cluster_config=workspace_config["clusters"]["system"],
    cluster_defaults={
        "spark_conf": {
            "spark.databricks.cluster.profile": "singleNode",
            "spark.master": "local[*]",
            "spark.databricks.delta.preview.enabled": "true",
        }
    },
    instance_pools=instance_pools,
    custom_tags={"ResourceClass": "SingleNode", **cluster_default_tags}
)

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> STORAGE MOUNTS
# ----------------------------------------------------------------------------------------------------------------------

# AZURE AD SERVICE PRINCIPAL USED FOR STORAGE MOUNTING
storage_mounts_sp_name = generate_resource_name(
    resource_type="service_principal",
    resource_name="dbw-eng-mounts",
    platform_config=platform_config,
)
storage_mounts_sp_app = azuread.Application(
    resource_name=storage_mounts_sp_name,
    display_name=storage_mounts_sp_name,
    identifier_uris=[f"api://{storage_mounts_sp_name}"],
    owners=[azure_client.object_id],
    opts=ResourceOptions(ignore_changes=["owners"]),
)

storage_mounts_sp = azuread.ServicePrincipal(
    resource_name=storage_mounts_sp_name,
    application_id=storage_mounts_sp_app.application_id,
    app_role_assignment_required=False,
    owners=[azure_client.object_id],
)

storage_mounts_sp_password = azuread.ServicePrincipalPassword(
    resource_name=storage_mounts_sp_name,
    service_principal_id=storage_mounts_sp.object_id,
)

storage_mounts_dbw_password = databricks.Secret(
    resource_name=storage_mounts_sp_name,
    scope=secret_scope.id,
    string_value=storage_mounts_sp_password.value,
    key=storage_mounts_sp_name,
    opts=ResourceOptions(provider=databricks_provider),
)

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> STORAGE MOUNTS -> ADLS GEN 2
# ----------------------------------------------------------------------------------------------------------------------

storage_mount_configs = workspace_config.get("storage_mounts", [])

# Distinct list of all accounts that have storage mounts
accounts_with_mounts = set([
    mount["account_ref_key"]
    for mount in storage_mount_configs
    if mount["type"] == "mount"
])

# IAM ROLE ASSIGNMENT
# Allow the Storage Mounts service principal to access the Datalake.
mounting_role_assignments = [
    ServicePrincipalRoleAssignment(
        principal_id=storage_mounts_sp.object_id,
        principal_name="engineering-storage-mounts-service-principal",
        role_name="Storage Blob Data Contributor",
        scope=storage_accounts[account_key]["account"].id,
        scope_description=account_key,
    )
    for account_key in accounts_with_mounts
]

# STORAGE MOUNTS
# If no storage mounts are defined in the YAML files, we'll not attempt to create any.
storage_mounts = {}

for config in storage_mount_configs:

    storage_account = storage_accounts[config["account_ref_key"]]
    container_name = config["container_name"]
    cluster_id = system_cluster.id
    name = config["mount_name"]

    if config["type"] == "passthrough":
        storage_mounts[name] = databricks.Mount(
            resource_name=f"{workspace_name}-{name}",
            name=name,
            cluster_id=cluster_id,
            extra_configs={
                "fs.azure.account.auth.type": "CustomAccessToken",
                # "fs.azure.account.custom.token.provider.class": spark.conf.get("spark.databricks.passthrough.adls.gen2.tokenProviderClassName"),
                "fs.azure.account.custom.token.provider.class": "com.databricks.backend.daemon.data.client.adl.AdlGen2CredentialContextTokenProvider"
            },
            uri=Output.concat("abfss://", container_name, "@", storage_account["account"].name, ".dfs.core.windows.net/"),
            opts=ResourceOptions(
                delete_before_replace=True,
                depends_on=[storage_account["service_principal_access"]],
                provider=databricks_provider,
                replace_on_changes=["*"],
            ),
        )
    elif config["type"] == "mount":
        storage_mounts[name] = databricks.Mount(
            resource_name=f'{workspace_name}-{name}',
            name=name,
            abfs=databricks.MountAbfsArgs(
                client_id=storage_mounts_sp.application_id,
                client_secret_key=storage_mounts_dbw_password.key,
                client_secret_scope=secret_scope.name,
                container_name=container_name,
                initialize_file_system=False,
                storage_account_name=storage_account["account"].name,
                tenant_id=azure_client.tenant_id,
            ),
            cluster_id=cluster_id,
            opts=ResourceOptions(
                delete_before_replace=True,
                depends_on=mounting_role_assignments,
                provider=databricks_provider,
                replace_on_changes=["*"],
            ),
        )
    else:
        raise Exception(f"Mount type not recognised: {config['type']}")

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> PRE-PROCESSING PACKAGE
# ----------------------------------------------------------------------------------------------------------------------

blob_name = "pre_process-1.0.0-py3-none-any.whl"
pre_processing_package = FileAsset(f"assets/{blob_name}")
pre_processing_blob = azure_native.storage.Blob(
    resource_name=f"{workspace_name}-pre_processing_package",
    account_name=storage_accounts["datalake"]["account"].name,
    blob_name=blob_name,
    container_name=storage_accounts["datalake"]["containers"]["preprocess"].name,
    resource_group_name=resource_groups["data"].name,
    source=pre_processing_package,
    opts=ResourceOptions(ignore_changes=["content_md5"]),
)

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> CLUSTERS
# ----------------------------------------------------------------------------------------------------------------------

# A dict of all clusters that are deployed.
clusters = {}

# If no clusters are defined in the YAML files, we'll not attempt to create any.
for ref_key, cluster_config in workspace_config.get("clusters", {}).items():
    if ref_key == "system":
        continue

    cluster_defaults = {
        "autotermination_minutes": 15,
        "spark_env_vars": {
            "PYSPARK_PYTHON": "/databricks/python3/bin/python3",
        },
    }

    # Cluster for file ingestion
    if ref_key == "default":
        if "libraries" not in cluster_defaults:
            cluster_defaults["libraries"] = {}
        if "whl" not in cluster_defaults["libraries"]:
            cluster_defaults["libraries"]["whl"] = []
        cluster_defaults["libraries"]["whl"].append(
            "dbfs:/mnt/preprocess/pre_process-1.0.0-py3-none-any.whl"
        )
        cluster_defaults["spark_env_vars"].update(
            {
                "DATABRICKS_WORKSPACE_HOSTNAME": workspace.workspace_url,
                "DATABRICKS_CLUSTER_NAME": cluster_config["display_name"],
                "DBT_TOKEN_SCOPE": secret_scope_name,
                "DBT_TOKEN_NAME": dbt_token_name,
                "DBT_ROOT_FOLDER": "/dbfs/mnt/dbt",
                "DBT_LOGS_FOLDER": "/dbfs/mnt/dbt-logs",
            }
        )

    # Single Node Cluster Type
    if cluster_config["type"] == "single_node":
        cluster_defaults["spark_conf"] = {
            "spark.databricks.cluster.profile": "singleNode",
            "spark.master": "local[*]",
            "spark.databricks.delta.preview.enabled": "true",
        }
        custom_tags = {"ResourceClass": "SingleNode", **cluster_default_tags}
    # High Concurrency or Standard Cluster Type
    else:
        cluster_defaults["spark_conf"] = {
            "spark.databricks.cluster.profile": "serverless",
            "spark.databricks.repl.allowedLanguages": "python,sql",
            "spark.databricks.passthrough.enabled": "true",
            "spark.databricks.pyspark.enableProcessIsolation": "true",
            "spark.databricks.delta.preview.enabled": "true",
        }
        custom_tags = {"ResourceClass": "Serverless", **cluster_default_tags}

    clusters[ref_key] = create_cluster(
        databricks_provider=databricks_provider,
        platform_config=platform_config,
        resource_name=f"{workspace_short_name}-{ref_key}",
        cluster_config=cluster_config,
        cluster_defaults=cluster_defaults,
        custom_tags=custom_tags,
        depends_on=[pre_processing_blob] + list(storage_mounts.values()),
        instance_pools=instance_pools,
    )

# ----------------------------------------------------------------------------------------------------------------------
# ENGINEERING DATABRICKS WORKSPACE -> CLUSTERS -> PERMISSIONS
# ----------------------------------------------------------------------------------------------------------------------

# Allow all users to be able to use the clusters
for ref_key, cluster_config in clusters.items():
    databricks.Permissions(
        resource_name=generate_hash(workspace_short_name, ref_key, "users"),
        cluster_id=clusters[ref_key].cluster_id,
        access_controls=[
            databricks.PermissionsAccessControlArgs(
                permission_level="CAN_RESTART", group_name="users"
            )
        ],
        opts=ResourceOptions(provider=databricks_provider),
    )

# ----------------------------------------------------------------------------------------------------------------------
# DEVOPS ASSIGNMENT
# ----------------------------------------------------------------------------------------------------------------------

workspace_id_secret = add_config_registry_secret(
    "databricks-engineering-workspace-id",
    workspace.id,
    infrastructure_identifier=True
)
workspace_hostname_secret = add_config_registry_secret(
    "databricks-engineering-workspace-hostname",
    workspace.workspace_url,
    infrastructure_identifier=True,
    depends_on=[workspace_id_secret]
)
cluster_id_secret = add_config_registry_secret(
    "databricks-engineering-cluster-id",
    clusters["default"].cluster_id,
    infrastructure_identifier=True,
    depends_on=[workspace_hostname_secret]
)
add_config_registry_secret(
    "databricks-engineering-cluster-name",
    clusters["default"].cluster_name,
    depends_on=[cluster_id_secret]
)
