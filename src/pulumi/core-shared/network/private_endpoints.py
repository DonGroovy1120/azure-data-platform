from pulumi import Resource
from pulumi_azure_native import network
from typing import List, Tuple, Union

from ingenii_azure_data_platform.private_endpoints import create_private_endpoint

from logs import log_analytics_workspace
from management.resource_groups import resource_groups
from network.vnet import privatelink_subnet, vnet
from project_config import platform_config

def create_shared_private_endpoint(
    name: str, resource_id: str, group_ids: List[str],
    logs_metrics_config: dict,
    private_dns_zone_id: str = None, 
    provider = None, depends_on: List[Resource] = None,
    location: str = None, resource_group_name: str = None,
    vnet_name: str = None, subnet_id: str = None, 
) -> Tuple[network.PrivateEndpoint, Union[None, network.PrivateDnsZoneGroup]]:

    resource_group_name = resource_group_name or resource_groups["infra"].name
    vnet_name = vnet_name or vnet.name
    subnet_id = subnet_id or privatelink_subnet.id

    return create_private_endpoint(
        platform_config=platform_config,
        name=name,
        resource_id=resource_id,
        group_ids=group_ids,
        logs_metrics_config=logs_metrics_config,
        log_analytics_workspace_id=log_analytics_workspace.id,
        location=location,
        resource_group_name=resource_group_name,
        vnet_name=vnet_name,
        subnet_id=subnet_id,
        private_dns_zone_id=private_dns_zone_id,
        provider=provider,
        depends_on=depends_on
    )
