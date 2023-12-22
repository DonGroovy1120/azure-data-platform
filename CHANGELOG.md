# 0.4.3 (2023-05-18)

### Improvements
- [data_factory] - Integration runtime has readiness probe
- [kubernetes] - Container logs sent to Log Analytics Workspace

# 0.4.2 (2022-09-15)

### Improvements
- [storage] - Able to specify extra storage accounts and mount containers to Databricks

# 0.4.1 (2022-09-09)

### Improvements
- [databricks] - Users for each workspace are specified through config
- [databricks] - Default runtime version changed from 9.1 to 10.4, default Ingenii Runtime to 0.6.2
- [databricks] - Update Pulumi package version to 0.4.0
- [networking] - Private endpoints are configurable at the environment and resource type level

# 0.4.0 (2022-06-27)

### Improvements
- [state] - State files held in blob storage.

# 0.3.1 (2022-06-17)
### Improvements
- [databricks] - Persist cluster logs.
- [quantum] - Bump Ingenii Azure Quantum package to 0.2.0.

### Bugfixes
- [container_registry] - Better networking when SKU is not Premium.
- [databricks] - Notebook paths are now relative, not absolute.
- [databricks] - Mounts must always be replaced, not updated.
- [deployment] - Revert incorrect deployment flow changes

# 0.3.0 (2022-03-28)

### Improvements
- [permissions] - Add deployment SP as 'owner' to all service principals.
- [quantum] - Bump Ingenii Azure Quantum package to 0.1.0.

### Bugfixes
- [data_factory] - Move permissions to be against the resource group, as required by Azure https://docs.microsoft.com/en-us/azure/data-factory/concepts-roles-permissions#roles-and-requirements

# 0.2.9 (2022-03-22)

### Improvements
- [ingeniictl] - Bump version to 0.2.2 to make use of the latest changes and bug fixes.

### Bugfixes
- [workflows] - Fix destroy workflow.

### New Features
- [jupyterlab] - Databricks Connect Docker images and configuration

# 0.2.8 (2022-03-17)

### Improvements
- [databricks] - Bump provider version to 0.2.0 (corresponding to Terraform provider version 0.5.3)
- [databricks] - Replace deprecated ADLS2 mounts with generic Databricks Mount resource.

### Bugfixes
- [azure_ad] - Add the automation client id to the 'owners' list of each service principal deployed.

# 0.2.7 (2022-03-14)

### New Features
- [jupyterlab] - Deploy JupyterLab as part of the shared Kubernetes cluster, add HTTPS
- [quantum] - Deploy a Quantum Workspace and connect to the JupyterLab installation
- [quantum] - Example notebooks in the JupyterLab installation

### Bugfixes
- [kubernetes] - Resolve issue when previewing DTAP when shared Kubernetes cluster not yet deployed
- [kubernetes] - Resolve issue where Kubernetes cluster gets replaced after pulumi refresh.
- [kubernetes] - Resolve issue where Windows node pool is not possible to bring up with a specific instance type (Standard_B2ms)
- [databricks] - Rework orchestration pipeline to alert users when they need to mount tables in Analytics workspace
- [kubernetes] - Resolve issue when previewing DTAP when shared Kubernetes cluster not yet deployed

# 0.2.6 (2022-02-09)

### Improvements
- [pulumi_azure_ad] - Bump provider version to 5.16.0 (latest)

### Bugfixes
- [devops_automation] - Make sure the random generated password always matches the complexity requirements.
- [container_registry] - Private endpoints can be created and approved in cross-subscription deployments.

# 0.2.5 (2022-02-04)

### Improvements
- [global_firewall] - We now have the ability to enable/disable global firewall that works across all major resources that support network filtering: Databricks, Storage Accounts, Key Vaults, Container Registries
- [iam_roles] - IAM role ids are now retrieved automatically by querying the Azure Management API.

### Bugfixes
- [data_factory] - Ignore `last_commit_id` attribute in the `repo_configuration` to avoid unnecessary diffs.

# 0.2.4 (2022-02-01)

### New Features
- [databricks] - Repositories created in Azure DevOps, and joining to Databricks is a manual step
- [data_factory] - CI/CD pipelines integrated with data Data Factories
- [data_factory] - Alert rules for pipeline failures

### Improvements
- [data_factory] - Pipeline generation pipelines moved out of the Data Engineering repository
- [outputs] - Share outputs between Pulumi and Ingenii UI using Azure Tables as storage.
- [resource_locks] - Automatically remove resource locks before Pulumi changes are applied.
- [pulumi] - Bump version to 3.23.2
- [databricks] - Update default runtime version from 8.4 to 9.1
- [shared] - Set which environments are deployed


### Bugfixes
- [dev_env] - Dev env was using the platform source code that is published in the Docker image. Added a fix to make sure the local source code is used instead.

# 0.2.3 (2022-01-17)

### New Features
- [container_registry] - Deploy and manage Azure Container Registry as a shared service to all DTAP environments
- [data_factory] - Add Factory to obtain data integrated with a corresponding DevOps repository
- [data_factory] - Pipeline to keep the Analytics workspace tables in sync

### Improvements
- [devops] - Better defaults when defining the virtual machine scale set
- [devops] - Virtual machine scale set extensions are ignored
- [preprocess] - Better initial preprocessing package
- [resource_protection] - Enabling Azure locks to protect resource groups from accidental deletion.
- [shared] - Handle concurrent previews when a resource is deployed in two stacks at the same time

### Bugfixes
- [datalake] - Use the correct VirtualNetworkRuleArgs, correct the argument used

## 0.2.2 (2022-01-03)

### New Features
- [databricks] - Allowing for instance pools to be created

### Improvments
- [databricks] - Boost Databricks engineering runtime to 0.6.0  
- [databricks/provider] - Bump the version to 0.4.1. Also lock the version to the exact semver.
- [dbt] - Added containers for `models` and `snapshots`
- [devcontainer] - Additional extensions to improve the dev experience
- [docker_image/iac_runtime] - Create a new Dockerfile. Use the same IaC runtime for the platform deployment and for the devcontainers.
- [platform/cicd] - Making use of the built in source code in the Docker image (/platform/src).
- [platform/source] - Publish the source of the platform in the Docker image (/platform/src). Make the Docker image `private` in the dockerhub.
- [platform/source] - Add Docker image build support for ARM architecture.
- [secrets] - Better default access for administrators and engineers

### Bugfixes
- [dbt] - Ignoring branch and repository_url attributes on the dbt static web site resource 
- [data_factory] - Correct group assignment for access to Kubernetes cluster

## 0.2.1 (2021-12-15)

### Improvments
- [databricks/provider] - Bumping the version to 0.4.0.

### New Features
- [data_factory] - Add a vNet-integrated self-hosted integration runtime on a Kubernetes cluster

### Bugfixes
- [databricks/provider] - Removing the "subscription_id" attribute from the provider resource. It is no longer needed with the latest 0.4.0 version.
- [platform/role_assignments] - Changing how role assignment resources are created. This will allow other resources to depend on them.

## 0.2.0 (2021-12-09)

### New Features
- [platform/resource_protection] - Implement Pulumi resource protection on key services like Data Lake, Databricks Workspaces, Key Vaults, etc.
- [platform/cicd] - DevOps configuration registry has the environment subscription IDs

### Bugfixes
- [cookiecutter/makefile] - Updating the 'set-platform-version' target to make sure all Github workflows are updated to the latest Docker image.
- [databricks] - Handle issue when workspace and cluster tags conflict

## 0.1.24 (2021-12-07)

### New Features
- [platform/cicd] - Introduce a new "Preview Only" scheduled CICD pipeline. The pipeline will notify Teams channel, whenever a drift between Pulumi state and infrastructure is detected.
- [dbt] - Static Site to host dbt documentation

### Bugfixes
- [logging] - Diagnostic settings handles when the resource does not yet exist
- [logging] - Make sure the 'log_analytics_destination_type' property of the Diagnostic Settings resource is ignored by Pulumi to prevent infinite drifts
- [network] - Make sure the 'nat_gateway' property of the PublicIP resource is ignored by Pulumi to prevent infinite drifts
- [databricks] - Update to data pipline notebook

## 0.1.23 (2021-11-29)

### Bugfixes
- [devops] - Environment name syncing
- [data_factory] - Enable our trigger in post-deployment script

## 0.1.22 (2021-11-25)

### New Features
- [devops] - Pipeline generation pipelines
- [logging] - Add Log Analytics Workspace per environment, and configurations
- [databricks] - Initial pre-processing package added

### Improvements
- [databricks] - Makefile commands to upload notebooks
- [extensions/general] - Rename the 'packages' folder to 'extensions'.
- [extensions/sql_results_server] - Ignore changes to the SQL Server administrators. I.e. Leave the users to freely assign Administrators using the Azure Portal.

## 0.1.21 (2021-11-19)

### Improvements
- [core/runtime] - Update Pulumi to v3.18.0
- [shared_services] - Export outputs
- [docs] - Update documentation
- [core/makefile] - Updating makefile
- [data_factory] - Increase timeout, add base annotation, defaults for better Pulumi comparison
- [databricks] - Add the ability to install Python packages from custom repos on the Databricks clusters.

## 0.1.20 (2021-10-29)

- [databricks] - Add Ingenii Engineering notebooks
- [devops] - Adding default AAD group permissions to ADO project
- [docs] - Update documentation and migrate to the user section

## 0.1.19 (2021-10-13)

### New Features
- [core/python] - Adding config registry client using Key Vault as a storage engine.
- [shared_services] - Add the management resources
- [shared_services] - Add the network resources
- [shared_services] - Add the config registry
- [devops] - Add the Azure DevOps project and repos.

### Improvements
- [databricks] - Make sure the default clusters are pinned by default. This would prevent Databricks from automatically removing them.

## 0.1.18 (2021-10-03)

### Bug Fixes

- [general] - Fix naming conventions for the SQL package.

## 0.1.17 (2021-10-02)

### Bug Fixes

- [general] - Bugfixes around the make file and the first package to deploy.

## 0.1.16 (2021-10-02)

### Improvements

- [general] - Migrating the defaults into a centralized location.

## 0.1.15 (2021-10-02)

### Improvements

- [github-workflows] - Adding a check to make sure the Changelog has been updated.
- [general] - Exporting outputs from the platform
- [packages] - Getting a very rough packaging system in place.
- [packages] - Preview of ADP SQL Results Server package.
- [cookiecutters] - Updating the cookiecutter templates.

### Bug Fixes

- [data_factory] - Update Table storage permissions
- [data_factory] - Fix ingestion pipeline parameters

## 0.1.14 (2021-09-22)

### Improvements

- [data_lake] - Update the name of the Table storage SAS token when stored in Azure Key Vault.
- [data_lake] - Append the Data Lake Table storage endpoint to the SAS token when stored in the Azure Key Vault.

## 0.1.13 (2021-09-22)

### New Features

- [data_factory] - Create self-hosted integration runtimes using the YAML config.

## 0.1.12 (2021-09-16)

### Improvements

- [general] - Update to Pulumi version 3.12.0
- [data_factory] - Adding 'Data Factory Contributor' access for the 'Engineers' group.

### Bug Fixes

- [general] - Creating a relationship for Storage Tables and Entities. Without the relationship deployments had to be retried multiple times as entities were to be created before tha storage table to exist.

## 0.1.11 (2021-09-14)

### Improvements

- [general] - Improving naming conventions.
- [general] - Add the ability to register Azure Resource Providers.
- [data engineering] - Add table storage to keep track of sftp file ingestion.

### Bug Fixes

- [general] - Improving naming convetions.
- [general] - Add the ability to register Azure Resource Providers.
- [data engineering] - Add table storage to keep track of sftp file ingestion.

### Bug Fixes

- [general] - Fix Databricks linked services for Data Factory.

## 0.1.6

### Improvements

- [databricks] - Making sure all storage mounts are done using the default clusters for Engineering and Analytics workspaces.

## 0.1.5

### Improvements

- [databricks] - Mounting the 'utilities' container in the Analytics workspace.
- [development] - Improving the .devcontainer experience

## 0.1.4

### Improvements

- [databricks] - Provide additional environment variables to the Engineering and Analytics cluster.
- [databricks] - Add default cluster docker image for the Engineering cluster.
- [databricks] - Make sure the "users" group has "CAN_ATTACH_TO" access to the Databricks clusters.

## 0.1.3

### Improvements

- [databricks] - Add the DBT token to the Databricks 'main' secret scope.
