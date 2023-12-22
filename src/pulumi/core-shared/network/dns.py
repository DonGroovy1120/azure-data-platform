import pulumi_azure_native as azure_native

from ingenii_azure_data_platform.utils import lock_resource

from project_config import platform_config, platform_outputs
from management import resource_groups

from .vnet import vnet

outputs = platform_outputs["network"]["dns"] = {"private_zones": {}}

# ----------------------------------------------------------------------------------------------------------------------
# KEYVAULT PRIVATE DNS ZONE
# ----------------------------------------------------------------------------------------------------------------------
key_vault_private_dns_zone = azure_native.network.PrivateZone(
    resource_name="privatelink-vaultcore-azure-net",
    location="Global",
    private_zone_name="privatelink.vaultcore.azure.net",
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
)

if platform_config.resource_protection:
    lock_resource("privatelink-vaultcore-azure-net", key_vault_private_dns_zone.id)

outputs["private_zones"]["key_vault"] = {
    "id": key_vault_private_dns_zone.id,
    "name": key_vault_private_dns_zone.name,
}

key_vault_private_dns_zone_link = azure_native.network.VirtualNetworkLink(
    resource_name="privatelink-vaultcore-azure-net",
    virtual_network_link_name=vnet.name,
    location="Global",
    private_zone_name=key_vault_private_dns_zone.name,
    registration_enabled=False,
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
    virtual_network=azure_native.network.SubResourceArgs(
        id=vnet.id,
    ),
)
if platform_config.resource_protection:
    lock_resource(
    "privatelink-vaultcore-azure-net-zone-link", key_vault_private_dns_zone_link.id
)
