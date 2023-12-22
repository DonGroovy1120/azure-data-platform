from pulumi import Output
from pulumi_azure_native import keyvault, storage

from ingenii_azure_data_platform.iam import UserAssignedIdentityRoleAssignment

from management import resource_groups
from platform_shared import (
    add_config_registry_secret,
    get_devops_principal_id,
)
from security import credentials_store

from .common import create_storage_account

datalake_details = create_storage_account("datalake", resource_groups["data"])
datalake = datalake_details["account"]

# ----------------------------------------------------------------------------------------------------------------------
# DATA LAKE -> TABLES -> SAS
# ----------------------------------------------------------------------------------------------------------------------

table_storage_sas = datalake.name.apply(
    lambda account_name: storage.list_storage_account_sas(
        account_name=account_name,
        protocols=storage.HttpProtocol.HTTPS,
        resource_types=storage.SignedResourceTypes.O,
        services=storage.Services.T,
        shared_access_start_time="2021-08-31T00:00:00Z",
        shared_access_expiry_time="2041-08-31T00:00:00Z",
        permissions="".join(
            [
                storage.Permissions.R,
                storage.Permissions.W,
                storage.Permissions.D,
                storage.Permissions.L,
                storage.Permissions.A,
                storage.Permissions.C,
                storage.Permissions.U,
            ]
        ),
        resource_group_name=datalake_details["resource_group"].name,
    )
)

# Save to Key Vault
keyvault.Secret(
    resource_name="datalake-table-storage-sas-uri-secret",
    resource_group_name=resource_groups["security"].name,
    vault_name=credentials_store.key_vault.name,
    secret_name="datalake-table-storage-sas-uri",
    properties=keyvault.SecretPropertiesArgs(
        value=Output.concat(
            datalake.primary_endpoints.table, "?", table_storage_sas.account_sas_token
        ),
    ),
)

# ----------------------------------------------------------------------------------------------------------------------
# DEVOPS ASSIGNMENT
# ----------------------------------------------------------------------------------------------------------------------

devops_principal_id = get_devops_principal_id()
devops_principal_name = "deployment-user-identity"
for container in ["dbt", "preprocess"]:
    UserAssignedIdentityRoleAssignment(
        principal_id=devops_principal_id,
        principal_name=devops_principal_name,
        role_name="Storage Blob Data Contributor",
        scope=datalake_details["containers"][container].id,
        scope_description=f"datalake-container-{container}",
    )

add_config_registry_secret(
    "data-lake-name", datalake.name, infrastructure_identifier=True
)

# Required while the Azure CLI command 'sync' does not support MSI authentication
# https://docs.microsoft.com/en-us/cli/azure/storage/blob?view=azure-cli-latest#az_storage_blob_sync
UserAssignedIdentityRoleAssignment(
    principal_id=devops_principal_id,
    principal_name=devops_principal_name,
    role_name="Reader and Data Access",
    scope=datalake.id,
    scope_description="datalake",
)
