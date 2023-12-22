from ingenii_azure_data_platform.iam import GroupRoleAssignment
from ingenii_azure_data_platform.management import ResourceGroup
from project_config import platform_config, platform_outputs

from .user_groups import user_groups

resource_groups_config = platform_config.from_yml["management"]["resource_groups"]

outputs = platform_outputs["management"]["resource_groups"] = {}

resource_groups = {}

for ref_key, config in resource_groups_config.items():
    resource = ResourceGroup(
        resource_group_name=config["display_name"],
        enable_delete_protection=config.get("enable_delete_protection", False),
        platform_config=platform_config,
    )
    resource_groups[ref_key] = resource

    # Export resource group metadata
    outputs[ref_key] = {
        "name": resource.name,
        "location": resource.location,
        "id": resource.id,
    }

    # IAM role assignments
    for assignment in config.get("iam", {}).get("role_assignments", []):
        # User group role assignment
        user_group_ref_key = assignment.get("user_group_ref_key")

        if user_group_ref_key is not None:
            GroupRoleAssignment(
                principal_name=user_group_ref_key,
                principal_id=user_groups[user_group_ref_key]["object_id"],
                role_name=assignment["role_definition_name"],
                scope=resource_groups[ref_key].id,
                scope_description=f"resource-group-{ref_key}",
            ),
