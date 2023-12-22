from pulumi import log, ResourceOptions

from ingenii_azure_data_platform.iam import ServicePrincipalRoleAssignment

from project_config import platform_config, azure_client
from platform_shared import (
    SHARED_OUTPUTS,
    container_registry_configs,
    container_registry_private_endpoint_configs,
    shared_services_provider,
)

from .dns import container_registry_dns_zone
from .private_endpoints import create_dtap_private_endpoint

# ----------------------------------------------------------------------------------------------------------------------
# CONTAINER REGISTRY PRIVATE ENDPOINTS
# ----------------------------------------------------------------------------------------------------------------------

for ref_key, config in container_registry_private_endpoint_configs.items():

    registry_name = container_registry_configs[ref_key]["display_name"]
    registry_sku = container_registry_configs[ref_key]["sku"]

    # Check the registry SKU. Create an endpoint for "premium" SKUs only.
    if registry_sku != "premium":
        log.warn(
            f"Unable to create PrivateLink endpoint for the container registry {registry_name}. "
            f"Only 'premium' SKU suppots PrivateLink. The current registry SKU is '{registry_sku}'."
        )
        continue

    container_registry_resource_id = SHARED_OUTPUTS.get(
        "storage",
        "container_registry",
        ref_key,
        "id",
        preview="Preview Container Registry ID",
    )

    container_registry_role_definition_id = SHARED_OUTPUTS.get(
        "iam",
        "role_definitions",
        "container_registry_private_endpoint_connection_creator",
        "id",
        preview="/subscriptions/preview-only/providers/Microsoft.Authorization/roleDefinitions/preview-only",
    )

    role_assignment = ServicePrincipalRoleAssignment(
        principal_id=azure_client.object_id,
        principal_name=f"{platform_config.stack_short_name}-provider",
        role_id=container_registry_role_definition_id,
        scope=container_registry_resource_id,
        scope_description=f"container-registry-{ref_key}",
        opts=ResourceOptions(provider=shared_services_provider),
    )

    create_dtap_private_endpoint(
        name=f"for-container-registry-{ref_key}",
        resource_id=container_registry_resource_id,
        group_ids=["registry"],
        logs_metrics_config={},
        depends_on=[role_assignment],
        private_dns_zone_id=container_registry_dns_zone.id,
    )
