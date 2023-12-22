from typing import List, Tuple, Union

from pulumi import Resource, ResourceOptions
from pulumi_azure_native import network

from .config import PlatformConfiguration
from .logs import log_network_interfaces
from .utils import generate_resource_name, lock_resource


def create_private_endpoint(
    platform_config: PlatformConfiguration,
    name: str, resource_id: str, group_ids: List[str],
    logs_metrics_config: dict, log_analytics_workspace_id: str,
    location: str, resource_group_name: str,
    vnet_name: str, subnet_id: str,
    private_dns_zone_id: str = None, 
    provider = None, depends_on: List[Resource] = None,
) -> Tuple[network.PrivateEndpoint, Union[None, network.PrivateDnsZoneGroup]]:

    config = platform_config["network"].get("private_endpoints", {})
    if not config.get("enabled", True):
        # Turned off for the whole environment
        return None, None
    
    allowed_resources = config.get("resource_types")
    if allowed_resources:
        # Only certain group IDs allowed (e.g. 'vault' but not 'blob')
        group_ids = [gi for gi in group_ids if gi in allowed_resources]
        if not group_ids:
            # No remaining allowed group IDs
            return None, None

    depends_on = depends_on or []
    location = location or platform_config.region.long_name

    private_endpoint_name = generate_resource_name(
        resource_type="private_endpoint",
        resource_name=name,
        platform_config=platform_config,
    )

    private_endpoint = network.PrivateEndpoint(
        resource_name=private_endpoint_name,
        private_endpoint_name=private_endpoint_name,
        location=location,
        custom_dns_configs=[],
        private_link_service_connections=[
            network.PrivateLinkServiceConnectionArgs(
                group_ids=group_ids,
                name=vnet_name,
                private_link_service_id=resource_id,
                request_message="none",
            )
        ],
        resource_group_name=resource_group_name,
        subnet=network.SubnetArgs(id=subnet_id),
        tags=platform_config.tags,
        opts=ResourceOptions(
            depends_on=depends_on, provider=provider,
            replace_on_changes=["privateLinkServiceConnections[*].privateLinkServiceId"]
        ),
    )
    if platform_config.resource_protection:
        lock_resource(private_endpoint_name, private_endpoint.id, provider=provider)

    # To Log Analytics Workspace
    log_network_interfaces(
        platform_config,
        log_analytics_workspace_id,
        private_endpoint_name,
        private_endpoint.network_interfaces,
        logs_config=logs_metrics_config.get("logs", {}),
        metrics_config=logs_metrics_config.get("metrics", {}),
    )

    # Private DNS
    if private_dns_zone_id:
        private_endpoint_dns_zone_group_name = generate_resource_name(
            resource_type="private_dns_zone",
            resource_name=name,
            platform_config=platform_config,
        )
        private_endpoint_dns_zone_group = network.PrivateDnsZoneGroup(
            resource_name=private_endpoint_dns_zone_group_name,
            private_dns_zone_configs=[
                network.PrivateDnsZoneConfigArgs(
                    name=private_endpoint_name,
                    private_dns_zone_id=private_dns_zone_id,
                )
            ],
            private_dns_zone_group_name="privatelink",
            private_endpoint_name=private_endpoint.name,
            resource_group_name=resource_group_name,
            opts=ResourceOptions(provider=provider),
        )
        if platform_config.resource_protection:
            lock_resource(
                private_endpoint_dns_zone_group_name,
                private_endpoint_dns_zone_group.id,
                provider=provider,
            )
    else:
        private_endpoint_dns_zone_group = None
    
    return private_endpoint, private_endpoint_dns_zone_group