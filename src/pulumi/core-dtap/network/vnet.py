import pulumi_azure_native.network as net
from pulumi import ResourceOptions

from ingenii_azure_data_platform.utils import (
    generate_cidr,
    generate_resource_name,
    lock_resource,
)

from management import resource_groups
from project_config import platform_config, platform_outputs

from . import nat, nsg, routing

outputs = platform_outputs["network"]

# ----------------------------------------------------------------------------------------------------------------------
# VNET
# ----------------------------------------------------------------------------------------------------------------------
vnet_config = platform_config.from_yml["network"]["virtual_network"]
vnet_address_space = vnet_config["address_space"]
vnet_name = generate_resource_name(
    resource_type="virtual_network",
    resource_name="main",
    platform_config=platform_config,
)

vnet = net.VirtualNetwork(
    resource_name=vnet_name,
    virtual_network_name=vnet_name,
    resource_group_name=resource_groups["infra"].name,
    location=platform_config.region.long_name,
    address_space=net.AddressSpaceArgs(address_prefixes=[vnet_address_space]),
    tags=platform_config.tags,
    # Tags are added in the ignore_changes list because of:
    # https://github.com/ingenii-solutions/azure-data-platform/issues/71
    opts=ResourceOptions(
        protect=platform_config.resource_protection,
        ignore_changes=["subnets", "tags"],
    ),
)

if platform_config.resource_protection:
    lock_resource(vnet_name, vnet.id)

# Export VNET metadata
outputs["virtual_network"] = {
    "name": vnet.name,
    "address_space": vnet.address_space,
    "id": vnet.id,
}

# ----------------------------------------------------------------------------------------------------------------------
# VNET -> SUBNETS
# ----------------------------------------------------------------------------------------------------------------------

# TODO: Remove duplication. Keep it DRY.

subnet_outputs = outputs["virtual_network"]["subnets"] = {}

# GATEWAY SUBNET
gateway_subnet = net.Subnet(
    resource_name=generate_resource_name(
        resource_type="subnet", resource_name="gateway", platform_config=platform_config
    ),
    subnet_name="Gateway",  # Microsoft requires the Gateway subnet to be called "Gateway"
    resource_group_name=resource_groups["infra"].name,
    virtual_network_name=vnet.name,
    address_prefix=generate_cidr(vnet_address_space, 24, 0),
    route_table=net.RouteTableArgs(id=routing.main_route_table.id),
)

# Export subnet metadata
subnet_outputs["gateway"] = {
    "name": gateway_subnet.name,
    "id": gateway_subnet.id,
    "address_prefix": gateway_subnet.address_prefix,
}

# PRIVATELINK SUBNET
privatelink_subnet_name = generate_resource_name(
    resource_type="subnet", resource_name="privatelink", platform_config=platform_config
)
privatelink_subnet = net.Subnet(
    resource_name=privatelink_subnet_name,
    subnet_name=privatelink_subnet_name,
    resource_group_name=resource_groups["infra"].name,
    virtual_network_name=vnet.name,
    address_prefix=generate_cidr(vnet_address_space, 24, 1),
    private_endpoint_network_policies=net.VirtualNetworkPrivateEndpointNetworkPolicies.DISABLED,
    route_table=net.RouteTableArgs(id=routing.main_route_table.id),
    opts=ResourceOptions(depends_on=[gateway_subnet]),
)

# Export subnet metadata
subnet_outputs["privatelink"] = {
    "name": privatelink_subnet.name,
    "id": privatelink_subnet.id,
    "address_prefix": privatelink_subnet.address_prefix,
}

# HOSTED SERVICES SUBNET
hosted_services_subnet_name = generate_resource_name(
    resource_type="subnet",
    resource_name="hosted-services",
    platform_config=platform_config,
)
hosted_services_subnet = net.Subnet(
    resource_name=hosted_services_subnet_name,
    subnet_name=hosted_services_subnet_name,
    resource_group_name=resource_groups["infra"].name,
    virtual_network_name=vnet.name,
    address_prefix=generate_cidr(vnet_address_space, 24, 2),
    route_table=net.RouteTableArgs(id=routing.main_route_table.id),
    nat_gateway=net.SubResourceArgs(id=nat.gateway.id),
    service_endpoints=[
        net.ServiceEndpointPropertiesFormatArgs(service=service)
        for service in [
            "Microsoft.ContainerRegistry",
            "Microsoft.KeyVault",
            "Microsoft.Storage",
            "Microsoft.SQL",
        ]
    ],
    opts=ResourceOptions(depends_on=[privatelink_subnet]),
)

# Export subnet metadata
subnet_outputs["hosted_services"] = {
    "name": hosted_services_subnet.name,
    "id": hosted_services_subnet.id,
    "address_prefix": hosted_services_subnet.address_prefix,
}

# DATABRICKS ENGINEERING HOSTS SUBNET
dbw_engineering_hosts_subnet_name = generate_resource_name(
    resource_type="subnet",
    resource_name="dbw-eng-hosts",
    platform_config=platform_config,
)
dbw_engineering_hosts_subnet = net.Subnet(
    resource_name=dbw_engineering_hosts_subnet_name,
    subnet_name=dbw_engineering_hosts_subnet_name,
    resource_group_name=resource_groups["infra"].name,
    virtual_network_name=vnet.name,
    address_prefix=generate_cidr(vnet_address_space, 22, 1),
    route_table=net.RouteTableArgs(id=routing.main_route_table.id),
    network_security_group=net.NetworkSecurityGroupArgs(
        id=nsg.databricks_engineering.id
    ),
    nat_gateway=net.SubResourceArgs(id=nat.gateway.id),
    service_endpoints=[
        net.ServiceEndpointPropertiesFormatArgs(service=service)
        for service in [
            "Microsoft.ContainerRegistry",
            "Microsoft.KeyVault",
            "Microsoft.Storage",
            "Microsoft.SQL",
        ]
    ],
    delegations=[
        net.DelegationArgs(
            name="databricks", service_name="Microsoft.Databricks/workspaces"
        )
    ],
    opts=ResourceOptions(depends_on=[hosted_services_subnet]),
)

# Export subnet metadata
subnet_outputs["databricks_engineering_hosts"] = {
    "name": dbw_engineering_hosts_subnet.name,
    "id": dbw_engineering_hosts_subnet.id,
    "address_prefix": dbw_engineering_hosts_subnet.address_prefix,
}

# DATABRICKS ENGINEERING CONTAINERS SUBNET
dbw_engineering_containers_subnet_name = generate_resource_name(
    resource_type="subnet",
    resource_name="dbw-eng-cont",
    platform_config=platform_config,
)
dbw_engineering_containers_subnet = net.Subnet(
    resource_name=dbw_engineering_containers_subnet_name,
    subnet_name=dbw_engineering_containers_subnet_name,
    resource_group_name=resource_groups["infra"].name,
    virtual_network_name=vnet.name,
    address_prefix=generate_cidr(vnet_address_space, 22, 2),
    route_table=net.RouteTableArgs(id=routing.main_route_table.id),
    network_security_group=net.NetworkSecurityGroupArgs(
        id=nsg.databricks_engineering.id
    ),
    nat_gateway=net.SubResourceArgs(id=nat.gateway.id),
    service_endpoints=[
        net.ServiceEndpointPropertiesFormatArgs(service=service)
        for service in [
            "Microsoft.ContainerRegistry",
            "Microsoft.KeyVault",
            "Microsoft.Storage",
            "Microsoft.SQL",
        ]
    ],
    delegations=[
        net.DelegationArgs(
            name="databricks", service_name="Microsoft.Databricks/workspaces"
        )
    ],
    opts=ResourceOptions(depends_on=[dbw_engineering_hosts_subnet]),
)

# Export subnet metadata
subnet_outputs["databricks_engineering_containers"] = {
    "name": dbw_engineering_containers_subnet.name,
    "id": dbw_engineering_containers_subnet.id,
    "address_prefix": dbw_engineering_containers_subnet.address_prefix,
}

# DATABRICKS ANALYTICS HOSTS SUBNET
dbw_analytics_hosts_subnet_name = generate_resource_name(
    resource_type="subnet",
    resource_name="dbw-atc-hosts",
    platform_config=platform_config,
)
dbw_analytics_hosts_subnet = net.Subnet(
    resource_name=dbw_analytics_hosts_subnet_name,
    subnet_name=dbw_analytics_hosts_subnet_name,
    resource_group_name=resource_groups["infra"].name,
    virtual_network_name=vnet.name,
    address_prefix=generate_cidr(vnet_address_space, 22, 3),
    route_table=net.RouteTableArgs(id=routing.main_route_table.id),
    network_security_group=net.NetworkSecurityGroupArgs(id=nsg.databricks_analytics.id),
    nat_gateway=net.SubResourceArgs(id=nat.gateway.id),
    service_endpoints=[
        net.ServiceEndpointPropertiesFormatArgs(service=service)
        for service in [
            "Microsoft.ContainerRegistry",
            "Microsoft.KeyVault",
            "Microsoft.Storage",
            "Microsoft.SQL",
        ]
    ],
    delegations=[
        net.DelegationArgs(
            name="databricks", service_name="Microsoft.Databricks/workspaces"
        )
    ],
    opts=ResourceOptions(depends_on=[dbw_engineering_containers_subnet]),
)

# Export subnet metadata
subnet_outputs["databricks_analytics_hosts"] = {
    "name": dbw_analytics_hosts_subnet.name,
    "id": dbw_analytics_hosts_subnet.id,
    "address_prefix": dbw_analytics_hosts_subnet.address_prefix,
}

# DATABRICKS ANALYTICS CONTAINERS SUBNET
dbw_analytics_containers_subnet_name = generate_resource_name(
    resource_type="subnet",
    resource_name="dbw-atc-cont",
    platform_config=platform_config,
)
dbw_analytics_containers_subnet = net.Subnet(
    resource_name=dbw_analytics_containers_subnet_name,
    subnet_name=dbw_analytics_containers_subnet_name,
    resource_group_name=resource_groups["infra"].name,
    virtual_network_name=vnet.name,
    address_prefix=generate_cidr(vnet_address_space, 22, 4),
    route_table=net.RouteTableArgs(id=routing.main_route_table.id),
    network_security_group=net.NetworkSecurityGroupArgs(id=nsg.databricks_analytics.id),
    nat_gateway=net.SubResourceArgs(id=nat.gateway.id),
    service_endpoints=[
        net.ServiceEndpointPropertiesFormatArgs(service=service)
        for service in [
            "Microsoft.ContainerRegistry",
            "Microsoft.KeyVault",
            "Microsoft.Storage",
            "Microsoft.SQL",
        ]
    ],
    delegations=[
        net.DelegationArgs(
            name="databricks", service_name="Microsoft.Databricks/workspaces"
        )
    ],
    opts=ResourceOptions(depends_on=[dbw_analytics_hosts_subnet]),
)

subnet_outputs["databricks_analytics_containers"] = {
    "name": dbw_analytics_containers_subnet.name,
    "id": dbw_analytics_containers_subnet.id,
    "address_prefix": dbw_analytics_containers_subnet.address_prefix,
}
