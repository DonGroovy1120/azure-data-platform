from pulumi import ResourceOptions
from pulumi_azure_native import datafactory as adf

from ingenii_azure_data_platform.iam import GroupRoleAssignment
from ingenii_azure_data_platform.logs import log_diagnostic_settings
from ingenii_azure_data_platform.orchestration import AdfSelfHostedIntegrationRuntime
from ingenii_azure_data_platform.utils import generate_resource_name

from logs import log_analytics_workspace
from management import resource_groups
from management.user_groups import user_groups
from project_config import platform_config, platform_outputs

datafactory_config = platform_config["analytics_services"]["datafactory"]["shared_self_hosted_runtime_factory"]
outputs = platform_outputs["analytics"]["datafactory"]["shared_runtimes"] = {}
datafactory_resource_group = resource_groups["data"].name

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORIES
# ----------------------------------------------------------------------------------------------------------------------
if datafactory_config["enabled"]:

    resource_name = generate_resource_name(
        resource_type="datafactory",
        resource_name="runtimes",
        platform_config=platform_config,
    )
    if datafactory_config.get("name"):
        datafactory_name = datafactory_config["name"] 
    else:
        datafactory_name = resource_name

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> FACTORY
    # ----------------------------------------------------------------------------------------------------------------------
    datafactory = adf.Factory(
        resource_name=resource_name,
        factory_name=datafactory_name,
        location=platform_config.region.long_name,
        resource_group_name=datafactory_resource_group,
        identity=adf.FactoryIdentityArgs(type=adf.FactoryIdentityType.SYSTEM_ASSIGNED),
        opts=ResourceOptions(protect=platform_config.resource_protection),
    )

    outputs["id"] = datafactory.id
    outputs["name"] = datafactory.name

    outputs["runtimes"] = {}

    for runtime_name in datafactory_config.get("runtime_names", []):
        runtime = adf.IntegrationRuntime(
            resource_name=runtime_name,
            factory_name=datafactory.name,
            resource_group_name=datafactory_resource_group,
            properties=adf.SelfHostedIntegrationRuntimeArgs(
                description="Managed by the Ingenii's deployment process. Manual changes will be overridden on each deployment.",
                type="SelfHosted",
            ),
        )
        outputs["runtimes"][runtime_name] = runtime.id

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> IAM -> ROLE ASSIGNMENTS
    # ----------------------------------------------------------------------------------------------------------------------

    # Create role assignments defined in the YAML files
    for assignment in datafactory_config["iam"].get("role_assignments", []):
        # User Group Assignment
        user_group_ref_key = assignment.get("user_group_ref_key")
        if user_group_ref_key is not None:
            GroupRoleAssignment(
                principal_id=user_groups[user_group_ref_key]["object_id"],
                principal_name=user_group_ref_key,
                role_name=assignment["role_definition_name"],
                scope=datafactory.id,
                scope_description=f"runtimes-datafactory",
            )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> LOGGING
    # ----------------------------------------------------------------------------------------------------------------------
    log_diagnostic_settings(
        platform_config,
        log_analytics_workspace.id,
        datafactory.type,
        datafactory.id,
        datafactory_name,
        logs_config=datafactory_config.get("logs", {}),
        metrics_config=datafactory_config.get("metrics", {}),
    )

