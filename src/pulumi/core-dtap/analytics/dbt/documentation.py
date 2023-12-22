from pulumi import ResourceOptions
from pulumi_azure_native import web

from ingenii_azure_data_platform.iam import UserAssignedIdentityRoleAssignment
from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from management import resource_groups
from project_config import platform_config, platform_outputs
from platform_shared import (
    add_config_registry_secret,
    get_devops_principal_id,
)

outputs = platform_outputs["analytics"]["dbt"]["documentation"] = {}

# fmt: off
dbt_docs_config = platform_config["analytics_services"].get("dbt", {}).get("documentation", {})
# fmt: on

docs_enabled = dbt_docs_config.get("enabled", False)

add_config_registry_secret("dbt-docs-enabled", str(docs_enabled))

# Add these regardless to avoid purging issues
site_resource_name = generate_resource_name(
    resource_type="static_site",
    resource_name=f"dbt-documentation-{platform_config.stack}",
    platform_config=platform_config,
)
add_config_registry_secret(
    "dbt-docs-name", site_resource_name, infrastructure_identifier=True
)

if docs_enabled:

    # Note: While this is a global resource, we do need to specify a location for
    # the Functions API and staging environments. At time of writing there are 5
    # choices: Central US, East US 2, East Asia, West Europe, and West US 2

    static_site = web.StaticSite(
        resource_name=site_resource_name,
        build_properties=web.StaticSiteBuildPropertiesArgs(
            api_location="",
            app_artifact_location="",
            app_location="/",
        ),
        location=dbt_docs_config.get("location", "East US 2"),
        name=site_resource_name,
        resource_group_name=resource_groups["infra"].name,
        sku=web.SkuDescriptionArgs(
            name=dbt_docs_config.get("sku_name", "Standard"),
            tier=dbt_docs_config.get("sku_tier", "Standard"),
        ),
        tags=platform_config.tags,
        opts=ResourceOptions(ignore_changes=["branch", "repository_url"]),
    )
    if platform_config.resource_protection:
        lock_resource(site_resource_name, static_site.id)

    outputs["name"] = static_site.name
    outputs["url"] = static_site.default_hostname

    # ----------------------------------------------------------------------------------------------------------------------
    # DEVOPS ASSIGNMENT
    # ----------------------------------------------------------------------------------------------------------------------

    UserAssignedIdentityRoleAssignment(
        principal_id=get_devops_principal_id(),
        principal_name="deployment-user-identity",
        role_name="Contributor",
        scope=static_site.id,
        scope_description="dbt-documentation",
    )

    # ----------------------------------------------------------------------------------------------------------------------
    # CUSTOM DOMAINS
    # ----------------------------------------------------------------------------------------------------------------------

    for custom_domain in dbt_docs_config.get("custom_domains", []):
        custom_domain_name = generate_resource_name(
            resource_type="static_site_custom_domain",
            resource_name=f"dbt-documentation-custom-domain-{custom_domain['domain']}",
            platform_config=platform_config,
        )
        web.StaticSiteCustomDomain(
            resource_name=custom_domain_name,
            domain_name=custom_domain["domain"],
            name=static_site.name,
            resource_group_name=resource_groups["infra"].name,
            validation_method=custom_domain.get("validation", "cname-delegation"),
        )
