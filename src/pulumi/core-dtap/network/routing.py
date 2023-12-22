import pulumi_azure_native as azure_native

from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from project_config import platform_config, platform_outputs
from management import resource_groups

outputs = platform_outputs["network"]["route_tables"] = {}

main_route_table_resource_name = generate_resource_name(
    resource_type="route_table", resource_name="main", platform_config=platform_config
)
main_route_table = azure_native.network.RouteTable(
    resource_name=main_route_table_resource_name,
    route_table_name=main_route_table_resource_name,
    resource_group_name=resource_groups["infra"].name,
    disable_bgp_route_propagation=True,
    tags=platform_config.tags,
)
if platform_config.resource_protection:
    lock_resource(main_route_table_resource_name, main_route_table.id)

# Export route table metadata
outputs["main"] = {
    "name": main_route_table.name,
    "id": main_route_table.id,
}
