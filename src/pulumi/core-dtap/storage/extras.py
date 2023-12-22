from management import resource_groups
from project_config import platform_config

from .common import create_storage_account

extra_accounts = {
    key: create_storage_account(key, resource_groups["data"])
    for key in platform_config["storage"]["accounts"]
    if key not in ("databricks", "datalake")
}
