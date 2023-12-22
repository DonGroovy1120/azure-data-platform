from pulumi import ResourceOptions
from pulumi_azure import storage
from pulumi_kubernetes import core, meta

from ingenii_azure_data_platform.utils import generate_resource_name

from management import resource_groups
from project_config import platform_config
from platform_shared import cluster_created, shared_kubernetes_provider

kubernetes_storage_account_resource_group = resource_groups["infra"].name
kubernetes_storage_account_secret_name = "kubernetes-storage-account-details"

if cluster_created:

    location = platform_config.region.long_name

    storage_account_name = generate_resource_name(
        resource_type="storage_account",
        resource_name=f"kubernetes{platform_config.stack}",
        platform_config=platform_config,
    )

    kubernetes_storage_account = storage.Account(
        resource_name=storage_account_name,
        account_kind="StorageV2",
        account_replication_type="GRS",
        account_tier="Standard",
        location=location,
        min_tls_version="TLS1_2",
        name=storage_account_name,
        resource_group_name=kubernetes_storage_account_resource_group,
        tags=platform_config.tags,
        opts=ResourceOptions(
            protect=platform_config.resource_protection,
        ),
    )

else:

    kubernetes_storage_account = None

def add_storage_account_secret(namespace_id):
    return core.v1.Secret(
        resource_name=kubernetes_storage_account_secret_name,
        string_data={
            "azurestorageaccountname": kubernetes_storage_account.name,
            "azurestorageaccountkey": kubernetes_storage_account.primary_access_key,
        },
        metadata=meta.v1.ObjectMetaArgs(
            name=kubernetes_storage_account_secret_name,
            namespace=namespace_id,
        ),
        type="Opaque",
        opts=ResourceOptions(
            protect=platform_config.resource_protection,
            provider=shared_kubernetes_provider,
        ),
    )
