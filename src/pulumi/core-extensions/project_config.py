import pulumi
from os import getenv
from pulumi_azure_native.authorization import get_client_config
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
azure_client = get_client_config()

SHARED_OUTPUTS = SharedOutput(
    CURRENT_STACK_NAME.replace(f".extensions.{ENV}", ".shared"))

if ENV == "shared":
    DTAP_OUTPUTS = SHARED_OUTPUTS
else:
    DTAP_OUTPUTS = SharedOutput(
        CURRENT_STACK_NAME.replace(".extensions", ""),
    )
