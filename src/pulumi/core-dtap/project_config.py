from os import getenv
import pulumi
from pulumi_azure_native import authorization, Provider

from ingenii_azure_data_platform.config import PlatformConfiguration, SharedOutput

CURRENT_STACK_NAME = pulumi.get_stack()
ENV = CURRENT_STACK_NAME.split(".")[-1]

# Load the config files.
platform_config = PlatformConfiguration(
    stack=ENV,
    config_schema_file_path=getenv(
        "ADP_CONFIG_SCHEMA_FILE_PATH", "../../platform-config/schema.yml"
    ),
    default_config_file_path=getenv(
        "ADP_DEFAULT_CONFIG_FILE_PATH", "../../platform-config/defaults.yml"
    ),
    metadata_file_path=getenv("ADP_METADATA_FILE_PATH"),
    custom_config_file_path=getenv("ADP_CUSTOM_CONFIGS_FILE_PATH"),
)

# Load the current Azure auth session metadata
azure_client = authorization.get_client_config()

SHARED_OUTPUTS = SharedOutput(CURRENT_STACK_NAME.replace(ENV, "shared"))

# Particular configs
quantum_workspace_config = platform_config["analytics_services"]["quantum"]

# Outputs
platform_outputs = {
    "metadata": platform_config.metadata
}

pulumi.export("root", platform_outputs)

# Ingenii provided workspace DNS
ingenii_workspace_dns_provider = Provider(
    resource_name="ingenii-dns",
    client_id=getenv("WORKSPACE_DNS_ARM_CLIENT_ID"),
    client_secret=getenv("WORKSPACE_DNS_ARM_CLIENT_SECRET"),
    tenant_id=getenv("WORKSPACE_DNS_ARM_TENANT_ID"),
    subscription_id=getenv("WORKSPACE_DNS_ARM_SUBSCRIPTION_ID"),
)
