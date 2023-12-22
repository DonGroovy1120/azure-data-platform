from pulumi_azure_native import authorization

from management import resource_groups
from project_config import ENV

from .common import create_storage_account

databricks_storage_account_details = create_storage_account(
    "databricks", resource_groups["infra"])

databricks_logs_writer_role = authorization.RoleDefinition(
    "custom_role_databricks_log_writer",
    role_name="DatabricksStorageAccountLogsWriter" + ENV.title(),
    permissions=[
        authorization.PermissionArgs(
            data_actions=[
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"
            ],
        )
    ],
    assignable_scopes=[resource_groups["infra"].id],
    scope=resource_groups["infra"].id,
    )
