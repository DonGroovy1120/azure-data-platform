from pulumi import ResourceOptions
from pulumi_azure_native import keyvault

from ingenii_azure_data_platform.defaults import KEY_VAULT_DEFAULT_FIREWALL
from ingenii_azure_data_platform.iam import (
    GroupRoleAssignment,
    ServicePrincipalRoleAssignment,
)
from ingenii_azure_data_platform.logs import log_diagnostic_settings
from ingenii_azure_data_platform.network import PlatformFirewall
from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from logs import log_analytics_workspace
from management import resource_groups
from management.user_groups import user_groups
from network import dns, private_endpoints
from project_config import azure_client, platform_config, platform_outputs

outputs = platform_outputs["security"]["config_registry"] = {}

# ----------------------------------------------------------------------------------------------------------------------
# KEY VAULT
# ----------------------------------------------------------------------------------------------------------------------
key_vault_config = platform_config.from_yml["security"]["config_registry"]
key_vault_firewall_config = key_vault_config["network"]["firewall"]
key_vault_name = generate_resource_name(
    resource_type="key_vault", resource_name="conf", platform_config=platform_config
)


if key_vault_firewall_config.get("enabled"):
    firewall = platform_config.global_firewall + PlatformFirewall(
        enabled=True,
        ip_access_list=key_vault_firewall_config.get("ip_access_list", []),
        vnet_access_list=key_vault_firewall_config.get("vnet_access_list", []),
        resource_access_list=key_vault_firewall_config.get("resource_access_list", []),
        trust_azure_services=key_vault_firewall_config.get(
            "trust_azure_services", False
        ),
    )

    key_vault_network_acl = keyvault.NetworkRuleSetArgs(
        bypass=firewall.bypass_services,
        default_action=firewall.default_action,
        ip_rules=[
            keyvault.IPRuleArgs(value=ip_add) for ip_add in firewall.ip_access_list
        ],
        virtual_network_rules=[
            keyvault.VirtualNetworkRuleArgs(id=subnet_id)
            for subnet_id in firewall.vnet_access_list
        ],
    )
else:
    key_vault_network_acl = KEY_VAULT_DEFAULT_FIREWALL

key_vault = keyvault.Vault(
    resource_name=key_vault_name,
    vault_name=key_vault_name,
    resource_group_name=resource_groups["security"].name,
    location=platform_config.region.long_name,
    properties=keyvault.VaultPropertiesArgs(
        enable_rbac_authorization=True,
        network_acls=key_vault_network_acl,
        tenant_id=azure_client.tenant_id,
        sku=keyvault.SkuArgs(family="A", name=keyvault.SkuName("standard")),
    ),
    tags=platform_config.tags,
    opts=ResourceOptions(protect=platform_config.resource_protection),
)

if platform_config.resource_protection:
    lock_resource(key_vault_name, key_vault.id)

outputs["key_vault_id"] = key_vault.id
outputs["key_vault_name"] = key_vault.name


# ----------------------------------------------------------------------------------------------------------------------
# KEY VAULT -> PRIVATE ENDPOINT
# ----------------------------------------------------------------------------------------------------------------------

private_endpoints.create_shared_private_endpoint(
    name="for-conf-registry",
    resource_id=key_vault.id,
    group_ids=["vault"],
    logs_metrics_config=key_vault_config.get("network", {}).get("private_endpoint", {}),
    private_dns_zone_id=dns.key_vault_private_dns_zone.id,
)

# ----------------------------------------------------------------------------------------------------------------------
# KEY VAULT -> IAM -> ROLE ASSIGNMENTS
# ----------------------------------------------------------------------------------------------------------------------

# Create role assignments defined in the YAML files
for assignment in key_vault_config.get("iam", {}).get("role_assignments", []):
    # User Group Assignment
    user_group_ref_key = assignment.get("user_group_ref_key")
    if user_group_ref_key is not None:
        GroupRoleAssignment(
            principal_name=user_group_ref_key,
            principal_id=user_groups[user_group_ref_key]["object_id"],
            role_name=assignment["role_definition_name"],
            scope=key_vault.id,
            scope_description="config-registry",
        )

# Grant access to the Automation Service Principal to manage the key vault.
# We are going to be creating secrets in the key vault later on, so we need the access.
ServicePrincipalRoleAssignment(
    principal_id=azure_client.object_id,
    principal_name="automation-service-principal",
    role_name="Key Vault Administrator",
    scope=key_vault.id,
    scope_description="config-registry",
)

# ----------------------------------------------------------------------------------------------------------------------
# KEY VAULT -> LOGGING
# ----------------------------------------------------------------------------------------------------------------------

log_diagnostic_settings(
    platform_config,
    log_analytics_workspace.id,
    key_vault.type,
    key_vault.id,
    key_vault_name,
    logs_config=key_vault_config.get("logs", {}),
    metrics_config=key_vault_config.get("metrics", {}),
)
