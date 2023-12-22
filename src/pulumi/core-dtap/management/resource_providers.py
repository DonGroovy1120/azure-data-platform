from pulumi.resource import ResourceOptions
from pulumi_azure.core import ResourceProviderRegistration
from pulumi_azure.provider import Provider

from project_config import platform_config

azure_classic_provider = Provider(
    resource_name="azure_classic", skip_provider_registration=True
)

resource_providers_config = platform_config.from_yml["management"].get(
    "resource_providers", {}
)

resource_providers = [
    ResourceProviderRegistration(
        resource_name=provider,
        name=provider,
        opts=ResourceOptions(provider=azure_classic_provider),
    )
    for provider in resource_providers_config
]
