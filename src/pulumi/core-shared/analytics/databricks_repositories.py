from pulumi import ResourceOptions
import pulumi_azuredevops as ado

from ingenii_azure_data_platform.utils import generate_resource_name

from automation.devops import ado_project
from project_config import platform_config, platform_outputs

runtime_config = platform_config["analytics_services"]["databricks"]["workspaces"]

outputs = platform_outputs["analytics"]["databricks"] = {}

for ref_key, workspace_config in runtime_config.items():

    repositories = workspace_config.get("devops_repositories", [])
    if not repositories:
        continue

    outputs[ref_key] = {"repositories": {}}

    for repository in repositories:
        repository_name = repository["name"]
        git_repository = ado.Git(
            resource_name=generate_resource_name(
                resource_type="devops_repo",
                resource_name=f"databricks-{ref_key}-repository-{repository_name}",
                platform_config=platform_config,
            ),
            name=f"Databricks - {ref_key} - {repository_name}",
            project_id=ado_project.id,
            initialization=ado.GitInitializationArgs(init_type="Clean",),
            opts=ResourceOptions(protect=platform_config.resource_protection),
        )

    outputs[ref_key]["repositories"][repository_name] = {
        "id": git_repository.id,
        "name": git_repository.name,
        "remote_url": git_repository.remote_url,
        "web_url": git_repository.web_url
    }
