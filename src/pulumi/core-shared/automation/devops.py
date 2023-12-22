import urllib.parse
from os import getenv

import pulumi_azuredevops as ado
from pulumi import ResourceOptions, Output

from ingenii_azure_data_platform.utils import generate_resource_name, generate_hash
from project_config import platform_config, platform_outputs
from management import user_groups

ado_configs = platform_config.from_yml["automation"]["devops"]

outputs = platform_outputs["devops"] = {"project": {}}

# Azure DevOps Project
PROJECT_FEATURES = ["boards", "repositories", "pipelines", "testplans", "artifacts"]

ado_project = ado.Project(
    resource_name=generate_resource_name(
        resource_type="devops_project",
        resource_name="data-platform",
        platform_config=platform_config,
    ),
    name=ado_configs["project"]["name"],
    description=ado_configs["project"]["description"],
    features={
        feature: "disabled"
        for feature in PROJECT_FEATURES
        if feature not in ado_configs["project"]["features"]
    },
    version_control=ado_configs["project"]["version_control"],
    visibility=ado_configs["project"]["visibility"],
    work_item_template=ado_configs["project"]["work_item_template"],
    opts=ResourceOptions(protect=platform_config.resource_protection),
)

outputs["project"]["id"] = ado_project.id
outputs["project"]["name"] = ado_project.name
outputs["project"]["url"] = Output.all(
    getenv("AZDO_ORG_SERVICE_URL"), ado_project.name
).apply(lambda args: f"{args[0]}/{urllib.parse.quote(args[1])}")

# Azure DevOps Project Permissions
ado_project_iam_role_assignments = (
    ado_configs["project"].get("iam", {}).get("role_assignments", [])
)


def apply_iam_role_assignments(project_id: str, role_assignments: list):
    for assignment in role_assignments:
        resource_name = generate_hash(
            assignment["azure_devops_project_group_name"],
            assignment["user_group_ref_key"],
        )
        aad_group = ado.Group(
            resource_name=resource_name,
            origin_id=user_groups[assignment["user_group_ref_key"]]["object_id"],
        )
        ado_group = ado.get_group(
            project_id=project_id, name=assignment["azure_devops_project_group_name"]
        )
        membership = ado.GroupMembership(
            resource_name=resource_name,
            group=ado_group.descriptor,
            members=[aad_group.descriptor],
        )


ado_project.id.apply(
    lambda id: apply_iam_role_assignments(
        project_id=id, role_assignments=ado_project_iam_role_assignments
    )
)


# Azure DevOps Repositories
ado_repo_configs = ado_configs.get("repositories", [])
ado_repos = {}

for repo in ado_repo_configs:

    if repo.get("import_url"):
        initialization = ado.GitInitializationArgs(
            init_type="Import",
            source_type="Git",
            source_url=repo["import_url"],
        )
    else:
        initialization = ado.GitInitializationArgs(init_type="Clean")
   
    default_branch = f"refs/heads/{repo.get('default_branch', 'main')}"

    ado_repos[repo["name"]] = ado.Git(
        resource_name=generate_resource_name(
            resource_type="devops_repo",
            resource_name=repo["name"],
            platform_config=platform_config,
        ),
        name=repo["name"],
        project_id=ado_project.id,
        default_branch=default_branch,
        initialization=initialization,
        opts=ResourceOptions(protect=platform_config.resource_protection),
    )

    for pipeline in repo.get("pipelines", []):
        ado.BuildDefinition(
            resource_name=generate_resource_name(
                resource_type="devops_pipeline",
                resource_name=pipeline["name"].replace(" ", "_").lower(),
                platform_config=platform_config,
            ),
            name=pipeline["name"],
            project_id=ado_project.id,
            ci_trigger=ado.BuildDefinitionCiTriggerArgs(
                use_yaml=pipeline.get("use_yml", True),
            ),
            repository=ado.BuildDefinitionRepositoryArgs(
                branch_name=default_branch,
                repo_type="TfsGit",
                repo_id=ado_repos[repo["name"]].id,
                yml_path=pipeline.get("yml_path", "azure-pipelines.yml"),
            ),
        )
