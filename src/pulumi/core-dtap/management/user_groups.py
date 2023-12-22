from project_config import platform_config, platform_outputs
from ingenii_azure_data_platform.management import UserGroup
from ingenii_azure_data_platform.utils import generate_resource_name

user_groups_config = platform_config.from_yml["management"]["user_groups"]

outputs = platform_outputs["management"]["user_groups"] = {}

user_groups = {}

for ref_key, config in user_groups_config.items():

    # If no group object is provided we will go ahead and create the Azure AD group.
    if config.get("object_id") is None:
        resource = UserGroup(config["display_name"], platform_config)
        outputs[ref_key] = {
            "display_name": resource.display_name,
            "object_id": resource.object_id,
        }
    # If an object_id key has been set, we will pass that as an output.
    # It means the Azure AD groups have been created beforehand.
    else:
        outputs[ref_key] = {
            "display_name": generate_resource_name(
                resource_type="user_group",
                resource_name=config["display_name"],
                platform_config=platform_config,
            ),
            "object_id": config["object_id"],
        }

    # Save the current user group metadata in the user_groups dictionary.
    user_groups[ref_key] = outputs[ref_key]
