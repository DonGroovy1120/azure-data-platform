from pulumi_azure_native import insights

from ingenii_azure_data_platform.utils import generate_resource_name

from management.resource_groups import resource_groups
from project_config import platform_config

action_groups_config = platform_config["management"]["action_groups"]
resource_group_name = resource_groups["security"].name

action_groups = {
    ref_key: insights.ActionGroup(
        resource_name=generate_resource_name(
            resource_type="action_group",
            resource_name=ref_key,
            platform_config=platform_config,
        ),
        action_group_name=f"{config['display_name']} - {platform_config.stack.title()}",
        email_receivers=[
            insights.EmailReceiverArgs(
                email_address=email_address,
                name=f"{email_address.split('@')[0]} email",
                use_common_alert_schema=True
            )
            for email_address in config.get("email_addresses", [])
        ],
        enabled=config["enabled"],
        group_short_name=config["short_name"],
        location="Global",
        resource_group_name=resource_group_name,
        tags=platform_config.tags,
    )
    for ref_key, config in action_groups_config.items()
}
