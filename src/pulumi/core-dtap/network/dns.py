from pulumi_azure_native import network as net

from ingenii_azure_data_platform.utils import lock_resource

from project_config import platform_config
from platform_shared import container_registry_private_endpoint_configs
from management import resource_groups

from .vnet import vnet

# ----------------------------------------------------------------------------------------------------------------------
# STORAGE BLOB PRIVATE DNS ZONE
# ----------------------------------------------------------------------------------------------------------------------
storage_blob_private_dns_zone = net.PrivateZone(
    resource_name="privatelink-blob-core-windows-net",
    location="Global",
    private_zone_name="privatelink.blob.core.windows.net",
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
)
if platform_config.resource_protection:
    lock_resource("privatelink-blob-core-windows-net", storage_blob_private_dns_zone.id)

storage_blob_private_dns_zone_link = net.VirtualNetworkLink(
    resource_name="privatelink-blob-core-windows-net",
    virtual_network_link_name=vnet.name,
    location="Global",
    private_zone_name=storage_blob_private_dns_zone.name,
    registration_enabled=False,
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
    virtual_network=net.SubResourceArgs(
        id=vnet.id,
    ),
)
if platform_config.resource_protection:
    lock_resource(
        "privatelink-blob-core-windows-net-link", storage_blob_private_dns_zone_link.id
    )

# ----------------------------------------------------------------------------------------------------------------------
# STORAGE DFS PRIVATE DNS ZONE
# ----------------------------------------------------------------------------------------------------------------------
storage_dfs_private_dns_zone = net.PrivateZone(
    resource_name="privatelink-dfs-core-windows-net",
    location="Global",
    private_zone_name="privatelink.dfs.core.windows.net",
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
)
if platform_config.resource_protection:
    lock_resource("privatelink-dfs-core-windows-net", storage_dfs_private_dns_zone.id)

storage_dfs_private_dns_zone_link = net.VirtualNetworkLink(
    resource_name="privatelink-dfs-core-windows-net",
    virtual_network_link_name=vnet.name,
    location="Global",
    private_zone_name=storage_dfs_private_dns_zone.name,
    registration_enabled=False,
    resource_group_name=resource_groups["infra"].name,
    virtual_network=net.SubResourceArgs(
        id=vnet.id,
    ),
    tags=platform_config.tags,
)

if platform_config.resource_protection:
    lock_resource(
        "privatelink-dfs-core-windows-net-link", storage_dfs_private_dns_zone_link.id
    )

# ----------------------------------------------------------------------------------------------------------------------
# KEYVAULT PRIVATE DNS ZONE
# ----------------------------------------------------------------------------------------------------------------------
key_vault_private_dns_zone = net.PrivateZone(
    resource_name="privatelink-vaultcore-azure-net",
    location="Global",
    private_zone_name="privatelink.vaultcore.azure.net",
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
)
if platform_config.resource_protection:
    lock_resource("privatelink-vaultcore-azure-net", key_vault_private_dns_zone.id)

key_vault_private_dns_zone_link = net.VirtualNetworkLink(
    resource_name="privatelink-vaultcore-azure-net",
    virtual_network_link_name=vnet.name,
    location="Global",
    private_zone_name=key_vault_private_dns_zone.name,
    registration_enabled=False,
    resource_group_name=resource_groups["infra"].name,
    tags=platform_config.tags,
    virtual_network=net.SubResourceArgs(
        id=vnet.id,
    ),
)

if platform_config.resource_protection:
    lock_resource(
        "privatelink-vaultcore-azure-net-link", key_vault_private_dns_zone_link.id
    )

# ----------------------------------------------------------------------------------------------------------------------
# CONTAINER REGISTRY PRIVATE DNS ZONE
# ----------------------------------------------------------------------------------------------------------------------

# The container registry DNS zone and zone link are deployed only if a container registry is also deployed in the shared
# stack. This behavior might have to change if there is a need for container registry private link access that is not
# dependent on the shared stack's registry.

if container_registry_private_endpoint_configs:
    container_registry_dns_zone = net.PrivateZone(
        resource_name="privatelink-azurecr-io",
        location="Global",
        private_zone_name="privatelink.azurecr.io",
        resource_group_name=resource_groups["infra"].name,
        tags=platform_config.tags,
    )
    if platform_config.resource_protection:
        lock_resource("privatelink-azurecr-io", container_registry_dns_zone.id)

    container_registry_dns_zone_link = net.VirtualNetworkLink(
        resource_name="privatelink-azurecr-io",
        virtual_network_link_name=vnet.name,
        location="Global",
        private_zone_name=container_registry_dns_zone.name,
        registration_enabled=False,
        resource_group_name=resource_groups["infra"].name,
        tags=platform_config.tags,
        virtual_network=net.SubResourceArgs(
            id=vnet.id,
        ),
    )
    if platform_config.resource_protection:
        lock_resource("privatelink-azurecr-io-link", container_registry_dns_zone_link.id)
else:
    container_registry_dns_zone = None
    container_registry_dns_zone_link = None
