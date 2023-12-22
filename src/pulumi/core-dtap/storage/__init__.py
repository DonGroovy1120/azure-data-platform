# Init the platform outputs
from project_config import platform_outputs

platform_outputs["storage"] = {}

from . import databricks
from . import datalake
from . import extras

storage_accounts = {
    "databricks": databricks.databricks_storage_account_details,
    "datalake": datalake.datalake_details,
    **extras.extra_accounts,
}
