from pulumi.resource import ResourceOptions
from pulumi_azure_native import containerregistry as cr
from pulumi_azure_native import authorization as auth

from ingenii_azure_data_platform.defaults import CONTAINER_REGISTRY_DEFAULT_FIREWALL
from ingenii_azure_data_platform.iam import GroupRoleAssignment
from ingenii_azure_data_platform.network import PlatformFirewall
from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from management.resource_groups import resource_groups
from management.user_groups import user_groups
from project_config import platform_config, platform_outputs

outputs = platform_outputs["storage"]["container_registry"] = {}

resource_group = resource_groups["data"]

registry_config = platform_config.from_yml.get("storage", {}).get(
    "container_registry", {}
)

sku_map = {sku.value.lower(): sku.value for sku in cr.SkuName}

registries = {}

for ref_key, config in registry_config.items():

    # Generate a resource name complying with our naming conventions.
    resource_name = generate_resource_name(
        resource_type="container_registry",
        resource_name=config["display_name"],
        platform_config=platform_config,
    )
    registry_sku = sku_map[config.get("sku", "standard")]

    firewall_config = config.get("network", {}).get("firewall", {})

    if registry_sku != cr.SkuName.PREMIUM:
        network_rule_set = None
    elif firewall_config.get("enabled"):
        firewall = platform_config.global_firewall + PlatformFirewall(
            enabled=True,
            ip_access_list=firewall_config.get("ip_access_list", []),
            vnet_access_list=firewall_config.get("vnet_access_list", []),
        )

        network_rule_set = cr.NetworkRuleSetArgs(
            default_action=firewall.default_action,
            ip_rules=[
                cr.IPRuleArgs(i_p_address_or_range=ip, action="Allow")
                for ip in firewall.ip_access_list
            ],
            virtual_network_rules=[
                cr.VirtualNetworkRuleArgs(virtual_network_resource_id=subnet_id)
                for subnet_id in firewall.vnet_access_list
            ],
        )
    else:
        network_rule_set = CONTAINER_REGISTRY_DEFAULT_FIREWALL

    registry = cr.Registry(
        resource_name=resource_name,
        location=platform_config.region.long_name,
        registry_name=config["display_name"],
        resource_group_name=resource_group.name,
        admin_user_enabled=config.get("admin_user_enabled", False),
        network_rule_set=network_rule_set,
        sku=cr.SkuArgs(name=registry_sku),
        tags=platform_config.tags | config.get("tags", {}),
        opts=ResourceOptions(
            protect=platform_config.resource_protection,
            ignore_changes=[
                "policies"  # Policy management will be implemented as needed.
            ],
        ),
    )
    if platform_config.resource_protection:
        lock_resource(resource_name, registry.id)

    registries[ref_key] = registry

    # IAM Role Assignments
    # Create role assignments defined in the YAML files
    for assignment in config.get("iam", {}).get("role_assignments", []):
        # User Group Assignment
        user_group_ref_key = assignment.get("user_group_ref_key")
        if user_group_ref_key is not None:
            GroupRoleAssignment(
                principal_name=user_group_ref_key,
                principal_id=user_groups[user_group_ref_key]["object_id"],
                role_name=assignment["role_definition_name"],
                scope=registry.id,
                scope_description="container-registry",
            )

    # Export outputs
    outputs[ref_key] = {
        "id": registry.id,
        "url": registry.login_server,
        "display_name": config["display_name"],
        "resource_group_name": resource_group.name.apply(lambda name: name),
    }
