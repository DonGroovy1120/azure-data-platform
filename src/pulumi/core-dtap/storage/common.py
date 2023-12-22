import pulumi_azure as azure_classic
from pulumi import Output, ResourceOptions
from pulumi_azure_native import storage

from ingenii_azure_data_platform.defaults import STORAGE_ACCOUNT_DEFAULT_FIREWALL
from ingenii_azure_data_platform.iam import (
    GroupRoleAssignment,
    ServicePrincipalRoleAssignment,
)
from ingenii_azure_data_platform.logs import log_diagnostic_settings
from ingenii_azure_data_platform.network import PlatformFirewall
from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from logs import log_analytics_workspace
from management.user_groups import user_groups
from network import dns, private_endpoints, vnet
from project_config import platform_config, platform_outputs, azure_client

common_outputs = platform_outputs["storage"] = {}

# ----------------------------------------------------------------------------------------------------------------------
# FIREWALL IP ACCESS LIST
# This is the global firewall access list and applies to all resources such as key vaults, storage accounts etc.
# ----------------------------------------------------------------------------------------------------------------------
firewall_ip_access_list = [
    storage.IPRuleArgs(i_p_address_or_range=ip_address)
    for ip_address in platform_config.from_yml["network"]["firewall"].get(
        "ip_access_list", [])
]

# ----------------------------------------------------------------------------------------------------------------------
# DATA LAKE
# ----------------------------------------------------------------------------------------------------------------------
def create_storage_account(storage_ref_key, datalake_resource_group):
    """ Create storage account and associated resources """
    datalake_config = platform_config.from_yml["storage"]["accounts"][storage_ref_key]

    outputs = common_outputs[storage_ref_key] = {}

    datalake_name = generate_resource_name(
        resource_type="storage_account",
        resource_name=datalake_config["display_name"],
        platform_config=platform_config,
    )

    datalake_firewall_config = datalake_config.get("network", {}).get("firewall", {})
    if datalake_firewall_config.get("enabled"):
        account_firewall = platform_config.global_firewall + PlatformFirewall(
            enabled=True,
            ip_access_list=datalake_firewall_config.get("ip_access_list", []),
            vnet_access_list=datalake_firewall_config.get("vnet_access_list", []),
            resource_access_list=datalake_firewall_config.get("resource_access_list", []),
            trust_azure_services=datalake_firewall_config.get(
                "trust_azure_services", False
            ),
        )

        trusted_subnet_ids = [
            subnet.id
            for subnet in (
                vnet.dbw_engineering_hosts_subnet,
                vnet.dbw_engineering_containers_subnet,
                vnet.dbw_analytics_hosts_subnet,
                vnet.dbw_analytics_containers_subnet,
            )
        ]

        network_rule_set = storage.NetworkRuleSetArgs(
            bypass=account_firewall.bypass_services,
            default_action=account_firewall.default_action,
            ip_rules=[
                storage.IPRuleArgs(i_p_address_or_range=ip_add)
                for ip_add in account_firewall.ip_access_list
            ],
            virtual_network_rules=[
                storage.VirtualNetworkRuleArgs(
                    virtual_network_resource_id=subnet_id,
                )
                for subnet_id in set(trusted_subnet_ids + account_firewall.vnet_access_list)
            ],
        )
    else:
        network_rule_set = STORAGE_ACCOUNT_DEFAULT_FIREWALL

    datalake = storage.StorageAccount(
        resource_name=datalake_name,
        account_name=datalake_name,
        allow_blob_public_access=False,
        network_rule_set=network_rule_set,
        is_hns_enabled=True,
        kind=storage.Kind.STORAGE_V2,
        location=platform_config.region.long_name,
        minimum_tls_version=storage.MinimumTlsVersion.TLS1_2,
        resource_group_name=datalake_resource_group.name,
        sku=storage.SkuArgs(name=storage.SkuName.STANDARD_GRS),
        tags=platform_config.tags,
        opts=ResourceOptions(
            protect=platform_config.resource_protection,
        ),
    )
    if platform_config.resource_protection:
        lock_resource(datalake_name, datalake.id)

    outputs["id"] = datalake.id
    outputs["name"] = datalake.name
    outputs["containers_view_url"] = Output.all(
        datalake_resource_group.name, datalake.name
    ).apply(
        lambda args: f"https://portal.azure.com/#@/resource/subscriptions/{azure_client.subscription_id}/resourceGroups/{args[0]}/providers/Microsoft.Storage/storageAccounts/{args[1]}/containersList"
    )


    # ----------------------------------------------------------------------------------------------------------------------
    # DATA LAKE -> LOGGING
    # ----------------------------------------------------------------------------------------------------------------------

    log_diagnostic_settings(
        platform_config,
        log_analytics_workspace.id,
        datalake.type,
        datalake.id,
        datalake_name,
        logs_config=datalake_config.get("logs", {}),
        metrics_config=datalake_config.get("metrics", {}),
    )

    blob_logs_and_metrics = datalake_config.get("storage_type_logging", {}).get("blob", {})
    log_diagnostic_settings(
        platform_config,
        log_analytics_workspace.id,
        datalake.type,
        datalake.id.apply(lambda dl_id: f"{dl_id}/blobservices/default"),
        f"{datalake_name}-blob",
        logs_config=blob_logs_and_metrics.get("logs", {}),
        metrics_config=blob_logs_and_metrics.get("metrics", {}),
    )

    table_logs_and_metrics = datalake_config.get("storage_type_logging", {}).get("table", {})
    log_diagnostic_settings(
        platform_config,
        log_analytics_workspace.id,
        datalake.type,
        datalake.id.apply(lambda dl_id: f"{dl_id}/tableservices/default"),
        f"{datalake_name}-table",
        logs_config=table_logs_and_metrics.get("logs", {}),
        metrics_config=table_logs_and_metrics.get("metrics", {}),
    )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA LAKE -> PRIVATE ENDPOINTS
    # ----------------------------------------------------------------------------------------------------------------------

    private_endpoint_config = \
        datalake_config.get("network", {}).get("private_endpoint", {})

    private_endpoints.create_dtap_private_endpoint(
        name=f"for-{storage_ref_key}-blob",
        resource_id=datalake.id,
        group_ids=["blob"],
        logs_metrics_config=private_endpoint_config.get("blob", {}),
        private_dns_zone_id=dns.storage_blob_private_dns_zone.id,
    )

    private_endpoints.create_dtap_private_endpoint(
        name=f"for-{storage_ref_key}-dfs",
        resource_id=datalake.id,
        group_ids=["dfs"],
        logs_metrics_config=private_endpoint_config.get("dfs", {}),
        private_dns_zone_id=dns.storage_dfs_private_dns_zone.id,
    )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA LAKE -> IAM -> ROLE ASSIGNMENTS
    # ----------------------------------------------------------------------------------------------------------------------

    # Create role assignments defined in the YAML files
    for assignment in datalake_config.get("iam", {}).get("role_assignments", {}):
        # User Group Assignment
        user_group_ref_key = assignment.get("user_group_ref_key")
        if user_group_ref_key is not None:
            GroupRoleAssignment(
                principal_id=user_groups[user_group_ref_key]["object_id"],
                principal_name=user_group_ref_key,
                role_name=assignment["role_definition_name"],
                scope=datalake.id,
                scope_description=storage_ref_key,
            )

    # Service principal, for mounting containers
    service_principal_access = ServicePrincipalRoleAssignment(
        principal_id=azure_client.object_id,
        principal_name="deployment_principal",
        role_name="Storage Blob Data Reader",
        scope=datalake.id,
        scope_description=storage_ref_key,
    )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA LAKE -> LIFECYCLE MANAGEMENT
    # ----------------------------------------------------------------------------------------------------------------------

    if datalake_config.get("lifecycle_management") and any(
        val is not None for val in datalake_config["lifecycle_management"].values()
    ):

        lm_config = datalake_config["lifecycle_management"]
        details = {}
        if lm_config.get("archive_after") is not None:
            details["tier_to_archive"] = lm_config["archive_after"]
        if lm_config.get("cool_after") is not None:
            details["tier_to_cool"] = lm_config["cool_after"]
        if lm_config.get("delete_after") is not None:
            details["delete"] = lm_config["delete_after"]

        storage.ManagementPolicy(
        generate_resource_name(
            resource_type="storage_management_policy",
            resource_name=f"{storage_ref_key}-blob-overall",
            platform_config=platform_config,
        ),
        account_name=datalake.name,
        management_policy_name="default",
        policy=storage.ManagementPolicySchemaArgs(
            rules=[
                storage.ManagementPolicyRuleArgs(
                    definition=storage.ManagementPolicyDefinitionArgs(
                        actions=storage.ManagementPolicyActionArgs(
                            base_blob=storage.ManagementPolicyBaseBlobArgs(**{
                                k: storage.DateAfterModificationArgs(
                                    days_after_modification_greater_than=v
                                )
                                for k, v in details.items()
                            }),
                            snapshot=storage.ManagementPolicySnapShotArgs(**{
                                k: storage.DateAfterCreationArgs(
                                    days_after_creation_greater_than=v
                                )
                                for k, v in details.items()
                            }),
                            version=storage.ManagementPolicyVersionArgs(**{
                                k: storage.DateAfterCreationArgs(
                                    days_after_creation_greater_than=v
                                )
                                for k, v in details.items()
                            }),
                        ),
                        filters=storage.ManagementPolicyFilterArgs(
                            blob_types=["blockBlob"],
                        ),
                    ),
                    enabled=True,
                    name="All Blob Management",
                    type="Lifecycle",
                ),
            ],
        ),
        resource_group_name=datalake_resource_group.name)


    # ----------------------------------------------------------------------------------------------------------------------
    # DATA LAKE -> CONTAINERS
    # ----------------------------------------------------------------------------------------------------------------------

    # This dict will keep all container resources.
    datalake_containers = {}

    # If no containers are defined in the YAML files, we'll not attempt to create any.
    for ref_key, container_config in datalake_config.get("containers", {}).items():
        datalake_container_name = generate_resource_name(
            resource_type="storage_blob_container",
            resource_name=ref_key, # What if two accounts have a contianer with the same name?
            platform_config=platform_config,
        )
        datalake_containers[ref_key] = storage.BlobContainer(
            resource_name=datalake_container_name,
            account_name=datalake.name,
            container_name=container_config["display_name"],
            resource_group_name=datalake_resource_group.name,
            opts=ResourceOptions(
                protect=platform_config.resource_protection,
                ignore_changes=[
                    "public_access",
                    "default_encryption_scope",
                    "deny_encryption_scope_override",
                ],
            ),
        )
        if platform_config.resource_protection:
            lock_resource(datalake_container_name, datalake_containers[ref_key].id)

        # Container Role Assignments
        role_assignments = container_config.get("iam", {}).get("role_assignments", [])
        for assignment in role_assignments:
            # User Group Role Assignment
            if assignment.get("user_group_ref_key") is not None:
                user_group_ref_key = assignment.get("user_group_ref_key")
                GroupRoleAssignment(
                    principal_id=user_groups[user_group_ref_key]["object_id"],
                    principal_name=user_group_ref_key,
                    role_name=assignment["role_definition_name"],
                    scope=datalake_containers[ref_key].id,
                    scope_description=f"{storage_ref_key}-container-{ref_key}",
                )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA LAKE -> TABLES
    # ----------------------------------------------------------------------------------------------------------------------

    # This dict will keep all table resources.
    datalake_tables = {}

    # If no containers are defined in the YAML files, we'll not attempt to create any.
    for ref_key, table_config in datalake_config.get("tables", {}).items():

        table_name = table_config["display_name"]

        datalake_table_resource_name = (
            f"{datalake_name}-{table_config['display_name']}".lower()
        )
        datalake_tables[ref_key] = storage.Table(
            resource_name=datalake_table_resource_name,
            resource_group_name=datalake_resource_group.name,
            account_name=datalake.name,
            table_name=table_name,
        )
        if platform_config.resource_protection:
            lock_resource(datalake_table_resource_name, datalake_tables[ref_key].id)

        entities = table_config.get("entities", {})

        for entity_ref_key, entity_config in entities.items():
            azure_classic.storage.TableEntity(
                resource_name=f"{datalake_name}-{table_name}-{entity_ref_key}".lower(),
                storage_account_name=datalake.name,
                table_name=datalake_tables[ref_key].name,
                partition_key=entity_config.get("partition_key"),
                row_key=entity_config.get("row_key"),
                entity=entity_config.get("entity", {}),
            )

    return {
        "account": datalake,
        "resource_group": datalake_resource_group,
        "service_principal_access": service_principal_access,
        "containers": datalake_containers,
        "tables": datalake_tables, 
    }