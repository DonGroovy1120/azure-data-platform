from base64 import b64decode
from os import getenv

from pulumi import InvokeOptions, ResourceOptions
from pulumi_azure_native import containerservice, Provider, keyvault
from pulumi_azure_native.authorization import get_client_config
from pulumi_kubernetes import Provider as KubernetesProvider

from ingenii_azure_data_platform.config import PlatformConfiguration
from ingenii_azure_data_platform.kubernetes import get_cluster_config

from project_config import azure_client, platform_config, SHARED_OUTPUTS


shared_services_provider = Provider(
    resource_name="shared-services",
    client_id=getenv("SHARED_ARM_CLIENT_ID"),
    client_secret=getenv("SHARED_ARM_CLIENT_SECRET"),
    tenant_id=getenv("SHARED_ARM_TENANT_ID"),
    subscription_id=getenv("SHARED_ARM_SUBSCRIPTION_ID"),
)

shared_platform_config = PlatformConfiguration(
    stack="shared",
    config_schema_file_path=getenv(
        "ADP_CONFIG_SCHEMA_FILE_PATH", "../../platform-config/schema.yml"
    ),
    default_config_file_path=getenv(
        "ADP_DEFAULT_CONFIG_FILE_PATH", "../../platform-config/defaults.yml"
    ).replace("defaults.yml", "defaults.shared.yml"),
    metadata_file_path=getenv("ADP_METADATA_FILE_PATH"),
    custom_config_file_path=getenv("ADP_CUSTOM_CONFIGS_FILE_PATH").replace(
        f"{platform_config.stack}.yml", "shared.yml"
    ),
)

shared_azure_client = \
    get_client_config(opts=InvokeOptions(provider=shared_services_provider))


def get_devops_principal_id():
    return SHARED_OUTPUTS.get(
        "automation",
        "deployment_user_assigned_identities",
        platform_config.stack,
        preview="Preview-Devops-Principal-ID",
    )

#----------------------------------------------------------------------------------------------------------------------
# DEVOPS CONFIG REGISTRY
#----------------------------------------------------------------------------------------------------------------------

def get_devops_config_registry_resource_group():
    return SHARED_OUTPUTS.get(
        "security",
        "config_registry",
        "key_vault_id",
        preview="////PrviewDevOpsConfigRegistryResourceGroup",
    ).apply(lambda id_str: id_str.split("/")[4])


def add_config_registry_secret(
    secret_name, secret_value,
    resource_name=None, infrastructure_identifier=False,
    depends_on = None
):
    if infrastructure_identifier:
        tags = {"infrastructure_identifier": True}
    else:
        tags = None
    return keyvault.Secret(
        resource_name=resource_name or f"devops-{secret_name}",
        resource_group_name=get_devops_config_registry_resource_group(),
        vault_name=SHARED_OUTPUTS.get(
            "security",
            "config_registry",
            "key_vault_name",
            preview="previewkeyvaultname",
        ),
        secret_name=f"{secret_name}-{platform_config.stack}",
        properties=keyvault.SecretPropertiesArgs(value=secret_value),
        tags=tags,
        opts=ResourceOptions(
            depends_on=depends_on or [],
            provider=shared_services_provider
        ),
    )

add_config_registry_secret(
    "subscription-id", azure_client.subscription_id, infrastructure_identifier=True
)

container_registry_configs = shared_platform_config.from_yml.get("storage", {}).get(
    "container_registry", {}
)

container_registry_private_endpoint_configs = {
    ref_key: config
    for ref_key, config in container_registry_configs.items()
    if platform_config.stack
    in config.get("network", {}).get("private_endpoint", {}).get("enabled_in", [])
}

#----------------------------------------------------------------------------------------------------------------------
# SHARED KUBERNETES CLUSTER
#----------------------------------------------------------------------------------------------------------------------

cluster_config = get_cluster_config(shared_platform_config)
cluster_created = cluster_config["enabled"]
datafactory_runtime_config = cluster_config["configs"]["datafactory_runtime"]
jupyterlab_config = cluster_config["configs"]["jupyterlab"]

# Only create if required
if cluster_created:
    # Use the admin credential as it's static
    # TODO: Don't do this - add Pulumi service principal as Azure Kubernetes Service RBAC Cluster Admin

    def get_credentials(cluster_config):
        if cluster_config is None:
            return "Preview Kubernetes Config"
        return b64decode(
            containerservice.list_managed_cluster_admin_credentials(
                resource_group_name=cluster_config["cluster_resource_group_name"],
                resource_name=cluster_config["name"],
                opts=InvokeOptions(provider=shared_services_provider)
            ).kubeconfigs[0].value
        ).decode()

    kube_config = SHARED_OUTPUTS.get(
        "analytics", "shared_kubernetes_cluster").apply(get_credentials)

    shared_kubernetes_provider = KubernetesProvider(
        "datafactory_kubernetes_provider", kubeconfig=kube_config
    )
else:
    shared_kubernetes_provider = None
