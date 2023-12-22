from pulumi import ResourceOptions
from pulumi_azure_native.resources import ResourceGroup as BaseResourceGroup
from pulumi_azure_native.authorization import (
    ManagementLockAtResourceGroupLevel,
    LockLevel,
)
from pulumi_azuread import Group

from ingenii_azure_data_platform.config import PlatformConfiguration
from ingenii_azure_data_platform.utils import generate_resource_name


class ResourceGroup(BaseResourceGroup):
    """
    #TODO
    """

    def __init__(
        self,
        resource_group_name: str,
        enable_delete_protection: bool,
        platform_config: PlatformConfiguration,
    ):
        name = generate_resource_name(
            resource_type="resource_group",
            resource_name=resource_group_name,
            platform_config=platform_config,
        )
        super().__init__(
            resource_name=name,
            resource_group_name=name,
            location=platform_config.region.long_name,
            tags=platform_config.tags,
            opts=ResourceOptions(
                # Sometimes after a refresh Pulumi records the location as
                # lower case, flagging it as a required change. Since this is
                # very unlikely to need changing for real, this is a less than
                # ideal fix, but an acceptable one.
                ignore_changes=["location"],
                protect=platform_config.resource_protection
            ),
        )

        if enable_delete_protection:
            ManagementLockAtResourceGroupLevel(
                resource_name=name,
                lock_name="Managed by Ingenii",
                level=LockLevel.CAN_NOT_DELETE,
                resource_group_name=name,
                opts=ResourceOptions(depends_on=[self]),
            )


class UserGroup(Group):
    """
    #TODO
    """

    def __init__(
        self,
        group_name: str,
        platform_config: PlatformConfiguration,
        description: str = None,
    ):
        name = generate_resource_name(
            resource_type="user_group",
            resource_name=group_name,
            platform_config=platform_config,
        )
        super().__init__(
            resource_name=name.lower(),
            display_name=name,
            description=description,
            security_enabled=True,
            opts=ResourceOptions(protect=platform_config.resource_protection),
        )
