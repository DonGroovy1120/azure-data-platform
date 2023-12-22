from os import getenv, listdir, path

from ingenii_azure_data_platform.config import PlatformConfiguration

dtap_configs = {}

configs_folder = getenv("ADP_CUSTOM_CONFIGS_FILE_PATH").replace("shared.yml", "")
for file in listdir(configs_folder):

    full_path = configs_folder + file

    if path.isdir(full_path):
        continue
    if not file.endswith(".yml"):
        continue
    if file == "metadata.yml":
        continue

    env = file.strip(".yml")

    dtap_configs[env] = PlatformConfiguration(
        stack=env,
        config_schema_file_path=getenv(
            "ADP_CONFIG_SCHEMA_FILE_PATH", "../../platform-config/schema.yml"
        ),
        default_config_file_path=getenv(
            "ADP_DEFAULT_CONFIG_FILE_PATH", "../../platform-config/defaults.shared.yml"
        ).replace("defaults.shared.yml", "defaults.yml"),
        metadata_file_path=getenv("ADP_METADATA_FILE_PATH"),
        custom_config_file_path=full_path,
    )
