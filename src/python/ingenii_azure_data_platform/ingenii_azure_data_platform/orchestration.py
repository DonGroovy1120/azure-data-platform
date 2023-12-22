from pulumi_azure_native import datafactory as adf

from ingenii_azure_data_platform.config import PlatformConfiguration
from ingenii_azure_data_platform.utils import generate_resource_name


class AdfSelfHostedIntegrationRuntime(adf.IntegrationRuntime):
    """
    #TODO
    """

    def __init__(
        self,
        name: str,
        description: str,
        factory_name: str,
        resource_group_name: str,
        platform_config: PlatformConfiguration,
    ) -> None:
        name = generate_resource_name(
            resource_type="adf_integration_runtime",
            resource_name=name,
            platform_config=platform_config,
        )
        super().__init__(
            resource_name=name,
            factory_name=factory_name,
            resource_group_name=resource_group_name,
            properties=adf.SelfHostedIntegrationRuntimeArgs(
                description=description
                or "Managed by the Ingenii's deployment process. Manual changes will be overridden on each deployment.",
                type="SelfHosted",
            ),
        )
