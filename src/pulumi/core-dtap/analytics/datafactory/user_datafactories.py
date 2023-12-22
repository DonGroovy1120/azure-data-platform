from os import getenv

from pulumi import ResourceOptions, Output
from pulumi_azure_native import datafactory as adf, insights

from ingenii_azure_data_platform.iam import (
    GroupRoleAssignment,
    ServicePrincipalRoleAssignment,
)
from ingenii_azure_data_platform.logs import log_diagnostic_settings
from ingenii_azure_data_platform.orchestration import AdfSelfHostedIntegrationRuntime
from ingenii_azure_data_platform.utils import generate_resource_name

from analytics.databricks import engineering_workspace as databricks_engineering
from logs import log_analytics_workspace
from management import action_groups, resource_groups, user_groups

from platform_shared import (
    add_config_registry_secret,
    get_devops_principal_id,
    SHARED_OUTPUTS,
    shared_services_provider,
)
from project_config import azure_client, platform_config, platform_outputs

from security.credentials_store import key_vault
from storage.datalake import datalake

user_datafactory_configs = platform_config["analytics_services"]["datafactory"]["user_factories"]
user_datafactory_outputs = platform_outputs["analytics"]["datafactory"]["user_factories"] = {}

datafactory_resource_group = resource_groups["data"]
devops_organization_name = getenv("AZDO_ORG_SERVICE_URL").strip(" /").split("/")[-1]

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORIES
# ----------------------------------------------------------------------------------------------------------------------
datafactory_repositories = SHARED_OUTPUTS.get(
    "analytics",
    "datafactory",
    "repositories",
    preview={
        key: {"name": f"Preview Repository name: {key}"}
        for key in user_datafactory_configs
    },
)
devops_project = SHARED_OUTPUTS.get(
    "devops", "project", preview={"name": "Preview DevOps Project Name"}
)
shared_runtimes = SHARED_OUTPUTS.get(
    "analytics", "datafactory", "shared_runtimes", "runtimes", preview={}
)

# Dev is connected to the repository, all others are deployed to
if platform_config.stack != "dev":
    ServicePrincipalRoleAssignment(
        principal_name="deployment-user-identity",
        principal_id=get_devops_principal_id(),
        role_name="Data Factory Contributor",
        scope=datafactory_resource_group.id,
        scope_description="datafactory-deployer",
    )

user_datafactories = {}
for ref_key, datafactory_config in user_datafactory_configs.items():

    datafactory_name = generate_resource_name(
        resource_type="datafactory",
        resource_name=datafactory_config.get("display_name", ref_key),
        platform_config=platform_config,
    )

    outputs = user_datafactory_outputs[ref_key] = {}

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> DEVOPS REPOSITORY
    # ----------------------------------------------------------------------------------------------------------------------

    datafactory_repository = datafactory_config.get("repository", {})
    if datafactory_repository.get("devops_integrated"):
        repo_configuration = adf.FactoryVSTSConfigurationArgs(
            account_name=devops_organization_name,
            collaboration_branch=datafactory_repository.get(
                "collaboration_branch", "main"
            ),
            project_name=devops_project["name"],
            repository_name=datafactory_repositories[ref_key]["name"],
            root_folder=datafactory_repository.get("root_folder", "/"),
            tenant_id=azure_client.tenant_id,
            type="FactoryVSTSConfiguration",
        )
    else:
        repo_configuration = None

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> FACTORY
    # ----------------------------------------------------------------------------------------------------------------------
    datafactory = adf.Factory(
        resource_name=datafactory_name,
        factory_name=datafactory_name,
        location=platform_config.region.long_name,
        resource_group_name=datafactory_resource_group.name,
        identity=adf.FactoryIdentityArgs(type=adf.FactoryIdentityType.SYSTEM_ASSIGNED),
        repo_configuration=repo_configuration,
        opts=ResourceOptions(
            protect=platform_config.resource_protection,
            ignore_changes=["repoConfiguration.lastCommitId"],
        ),
    )

    user_datafactories[ref_key] = {"name": datafactory_name, "obj": datafactory}

    outputs["id"] = datafactory.id
    outputs["name"] = datafactory.name
    outputs["url"] = Output.all(
        datafactory_resource_group.name, datafactory.name
    ).apply(
        lambda args: f"https://adf.azure.com/en-us/home?factory=%2Fsubscriptions%2F{azure_client.subscription_id}%2FresourceGroups%2F{args[0]}%2Fproviders%2FMicrosoft.DataFactory%2Ffactories%2F{args[1]}"
    )

    add_config_registry_secret(
        f"data-factory-name-{ref_key}", datafactory.name, infrastructure_identifier=True
    )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> IAM -> ROLE ASSIGNMENTS
    # ----------------------------------------------------------------------------------------------------------------------

    # Create role assignments defined in the YAML files
    for assignment in datafactory_config.get("iam", {}).get("role_assignments", []):
        # User Group Assignment
        user_group_ref_key = assignment.get("user_group_ref_key")
        if user_group_ref_key is not None:
            GroupRoleAssignment(
                principal_id=user_groups[user_group_ref_key]["object_id"],
                principal_name=user_group_ref_key,
                role_name=assignment["role_definition_name"],
                scope=datafactory.id,
                scope_description=f"{ref_key}-datafactory",
            )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> INTEGRATION RUNTIMES
    # ----------------------------------------------------------------------------------------------------------------------
    for config in datafactory_config.get("integration_runtimes", []):
        if config["type"] == "self-hosted":
            runtime = AdfSelfHostedIntegrationRuntime(
                name=config["name"],
                description=config.get("description"),
                factory_name=datafactory.name,
                resource_group_name=datafactory_resource_group.name,
                platform_config=platform_config,
            )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> IAM
    # ----------------------------------------------------------------------------------------------------------------------
    ServicePrincipalRoleAssignment(
        principal_id=datafactory.identity.principal_id,
        principal_name=f"{ref_key}-datafactory-identity",
        role_name="Storage Blob Data Contributor",
        scope=datalake.id,
        scope_description="datalake",
    )

    ServicePrincipalRoleAssignment(
        principal_id=datafactory.identity.principal_id,
        principal_name=f"{ref_key}-datafactory-identity",
        role_name="Key Vault Secrets User",
        scope=key_vault.id,
        scope_description="cred-store",
    )

    ServicePrincipalRoleAssignment(
        principal_id=datafactory.identity.principal_id,
        principal_name=f"{ref_key}-datafactory-identity",
        role_name="Contributor",
        scope=databricks_engineering.workspace.id,
        scope_description="databricks-engineering",
    )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> SHARED RUNTIMES
    # ----------------------------------------------------------------------------------------------------------------------
    def access_runtimes(runtime_details):
        if runtime_details is None:
            return
        for runtime_name, runtime_id in runtime_details.items():
            ServicePrincipalRoleAssignment(
                principal_id=datafactory.identity.principal_id,
                principal_name=f"{ref_key}-datafactory-identity",
                role_name="Contributor",
                scope=runtime_id,
                scope_description=f"shared-runtime-{runtime_name}",
                opts=ResourceOptions(provider=shared_services_provider),
            )

    shared_runtimes.apply(access_runtimes)

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY -> PIPELINE FAILURE ALERT RULE
    # ----------------------------------------------------------------------------------------------------------------------
    if datafactory_config.get("pipeline_failure_action_groups"):
        insights.MetricAlert(
            resource_name=generate_resource_name(
                resource_type="metric_alert",
                resource_name=f"datafactory_{ref_key}_pipeline_failure",
                platform_config=platform_config,
            ),
            actions=[
                insights.MetricAlertActionArgs(action_group_id=action_groups[pfac])
                for pfac in datafactory_config["pipeline_failure_action_groups"]
            ],
            auto_mitigate=False,
            criteria=insights.MetricAlertMultipleResourceMultipleMetricCriteriaArgs(
                odata_type="Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria",
                all_of=[
                    insights.MetricCriteriaArgs(
                        criterion_type="StaticThresholdCriterion",
                        metric_name="PipelineFailedRuns",
                        name="Pipeline failure",
                        operator=insights.ConditionalOperator.GREATER_THAN_OR_EQUAL,
                        threshold=0,
                        time_aggregation=insights.AggregationTypeEnum.TOTAL,
                    )
                ],
            ),
            description="Alerts on pipeline failures",
            enabled=True,
            evaluation_frequency="PT15M",
            location="global",
            resource_group_name=datafactory_resource_group.name,
            rule_name=f"Pipeline Failures - {ref_key}",
            scopes=[datafactory.id],
            severity=1,
            tags=platform_config.tags,
            window_size="PT15M",
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

# Permissions must be granted against the resource group, not the individual resource
# https://docs.microsoft.com/en-us/azure/data-factory/concepts-roles-permissions#roles-and-requirements
for group_ref in platform_config["analytics_services"]["datafactory"].get("user_factories_contributors", []):
    if group_ref.get("user_group_ref_key"):
        group_object_id = user_groups[group_ref["user_group_ref_key"]]["object_id"]
        group_name = group_ref["user_group_ref_key"]
    elif group_ref.get("object_id"):
        group_object_id = group_ref["object_id"]
        group_name = group_ref["object_id"]
    else:
        raise Exception("No group reference key or object ID in user_factories_contributors setting!")
    GroupRoleAssignment(
        principal_id=group_object_id,
        principal_name=group_name,
        role_name="Data Factory Contributor",
        scope=datafactory_resource_group.id,
        scope_description="datafactory-resourcegroup",
    )