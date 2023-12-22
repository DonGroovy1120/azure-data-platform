from pulumi import ResourceOptions
from pulumi_azure_native import quantum, storage

from ingenii_azure_data_platform.iam import ServicePrincipalRoleAssignment
from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from management import resource_groups
from project_config import platform_config, platform_outputs, quantum_workspace_config

platform_outputs["analytics"]["quantum"] = outputs = {}

resource_group_name = resource_groups["infra"].name
location = platform_config.region.long_name

storage_account_name = generate_resource_name(
    resource_type="storage_account",
    resource_name="quantum",
    platform_config=platform_config,
)

storage_account = storage.StorageAccount(
    resource_name=storage_account_name,
    account_name=storage_account_name,
    allow_blob_public_access=False,
    is_hns_enabled=True,
    kind=storage.Kind.STORAGE_V2,
    location=location,
    minimum_tls_version=storage.MinimumTlsVersion.TLS1_2,
    resource_group_name=resource_group_name,
    sku=storage.SkuArgs(name=storage.SkuName.STANDARD_GRS),
    tags=platform_config.tags,
    opts=ResourceOptions(
        protect=platform_config.resource_protection,
    ),
)
if platform_config.resource_protection:
    lock_resource(storage_account.name, storage_account.id)

outputs["storage"] = {
    "id": storage_account.id,
    "name": storage_account.name,
}

quantum_workspace_name = generate_resource_name(
    resource_type="quantum_workspace",
    resource_name="quantumworkspace",
    platform_config=platform_config,
)

workspace = quantum.Workspace(
    resource_name=quantum_workspace_name,
    identity=quantum.QuantumWorkspaceIdentityArgs(
        type=quantum.ResourceIdentityType.SYSTEM_ASSIGNED
    ),
    location=location,
    providers=[
        quantum.ProviderArgs(
            provider_id=provider["id"], provider_sku=provider["sku"]
        )
        for provider in quantum_workspace_config["providers"]
    ],
    resource_group_name=resource_group_name,
    storage_account=storage_account.id,
    tags=platform_config.tags,
    opts=ResourceOptions(
        protect=platform_config.resource_protection,
    ),
    workspace_name=quantum_workspace_name
)
    # providers: Optional[Sequence[ProviderArgs]] = None,

outputs["workspace"] = {
    "id": workspace.id,
    "location": location,
    "name": workspace.name,
    "resource_group_name": resource_group_name,
}

# Storage account access
ServicePrincipalRoleAssignment(
    principal_id=workspace.identity.principal_id,
    principal_name="quantum_workspace_managed_identity",
    role_name="Contributor",
    scope=storage_account.id,
    scope_description="storage_account",
)

