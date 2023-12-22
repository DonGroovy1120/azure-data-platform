from os import getcwd, environ
from pulumi import FileAsset, Output, ResourceOptions, \
    ResourceTransformationArgs, ResourceTransformationResult
import pulumi_azuread as azuread
from pulumi_azure_native import containerservice, network, storage
from pulumi_kubernetes import batch, core, helm, meta

from ingenii_azure_data_platform.databricks import create_cluster
from ingenii_azure_data_platform.utils import generate_resource_name

from analytics.databricks.analytics_workspace import databricks_provider, workspace
from analytics.kubernetes.storage import add_storage_account_secret, \
    kubernetes_storage_account, \
    kubernetes_storage_account_resource_group, \
    kubernetes_storage_account_secret_name
from analytics.quantum.workspace import quantum_workspace_config, \
    outputs as quantum_outputs
from platform_shared import jupyterlab_config, shared_kubernetes_provider, shared_services_provider
from project_config import azure_client, ingenii_workspace_dns_provider, \
    platform_config, platform_outputs, SHARED_OUTPUTS
from storage.datalake import datalake

outputs = platform_outputs["analytics"]["jupyterlab"] = {}

env_jupyterlab_config = platform_config["analytics_services"].get("jupyterlab", {})
resource_name = f"jupyterlab-{platform_config.stack}"
kubernetes_cluster_resource_group_name = SHARED_OUTPUTS.get(
    "analytics",
    "shared_kubernetes_cluster",
    "cluster_resource_group_name",
    preview="Preview-Kubernetes-Resource-Group-Name",
)
kubernetes_node_resource_group_name = SHARED_OUTPUTS.get(
    "analytics",
    "shared_kubernetes_cluster",
    "node_resource_group_name",
    preview="Preview-Kubernetes-Resource-Group-Name",
)

#----------------------------------------------------------------------------------------------------------------------
# JUPYTERLAB -> IP ADDRESS AND HTTPS
#----------------------------------------------------------------------------------------------------------------------

hub_public_ip = network.PublicIPAddress(
    resource_name=generate_resource_name(
        resource_type="public_ip",
        resource_name=resource_name,
        platform_config=platform_config,
    ),
    public_ip_address_version=network.IPVersion.I_PV4,
    public_ip_allocation_method=network.IPAllocationMethod.STATIC,
    resource_group_name=kubernetes_node_resource_group_name,
    sku=network.PublicIPAddressSkuArgs(
        name=network.PublicIPAddressSkuName.STANDARD,
        tier=network.PublicIPAddressSkuTier.REGIONAL,
    ),
    tags=platform_config.tags,
    opts=ResourceOptions(provider=shared_services_provider),
)

# HTTPS is on by default, Ingenii provides the hostname
relative_name = f"{platform_config.unique_id}-{platform_config.prefix}-{platform_config.stack}"
zone_name = "workspace.ingenii.io"
record_set = network.RecordSet(
    generate_resource_name(
        resource_type="dns_zone",
        resource_name=zone_name,
        platform_config=platform_config,
    ),
    a_records=[network.ARecordArgs(
        ipv4_address=hub_public_ip.ip_address,
    )],
    metadata={
        "env": platform_config.stack,
        "prefix": platform_config.prefix,
        "unique_id": platform_config.unique_id,
    },
    record_type="A",
    relative_record_set_name=relative_name,
    resource_group_name=environ["WORKSPACE_DNS_RESOURCE_GROUP_NAME"],
    ttl=3600,
    zone_name=zone_name,
    opts=ResourceOptions(provider=ingenii_workspace_dns_provider),
)
hostname = f"{relative_name}.{zone_name}"
contact_email = "support@ingenii.dev"
callback_url = f"https://{hostname}/hub/oauth_callback"

if not env_jupyterlab_config.get("https", {}).get("enabled", True):
    # Client has turned off HTTPS
    # Ingenii record set will still be created
    hostname, contact_email, record_set = None, None, None
    callback_url = hub_public_ip.ip_address.apply(
        lambda ip: f"http://{ip}/hub/oauth_callback")

#----------------------------------------------------------------------------------------------------------------------
# JUPYTERLAB -> AUTHENTICATION -> APPLICATION
#----------------------------------------------------------------------------------------------------------------------

auth_application = azuread.Application(
    resource_name=resource_name,
    display_name=f"Ingenii Azure Data Platform JupyterHub Authentication - {platform_config.stack}",
    feature_tags=[azuread.ApplicationFeatureTagArgs(enterprise=True)],
    owners=[azure_client.object_id],
    required_resource_accesses=[
        azuread.ApplicationRequiredResourceAccessArgs(
            resource_accesses=[azuread.ApplicationRequiredResourceAccessResourceAccessArgs(
                id="e1fe6dd8-ba31-4d61-89e7-88639da4683d",
                type="Scope",
            )],
            resource_app_id="00000003-0000-0000-c000-000000000000",
        )
    ],
    web=azuread.ApplicationWebArgs(redirect_uris=[callback_url]),
)
auth_service_principal = azuread.ServicePrincipal(
    resource_name=resource_name,
    application_id=auth_application.application_id,
    app_role_assignment_required=jupyterlab_config.get("require_assignment", True),
    owners=[azure_client.object_id]
)
auth_service_principal_password = azuread.ServicePrincipalPassword(
    resource_name=resource_name,
    service_principal_id=auth_service_principal.object_id,
)

namespace = core.v1.Namespace(
    resource_name=resource_name,
    metadata=meta.v1.ObjectMetaArgs(name=resource_name),
    opts=ResourceOptions(provider=shared_kubernetes_provider)
)

#----------------------------------------------------------------------------------------------------------------------
# JUPYTERLAB -> DEFAULTS
#----------------------------------------------------------------------------------------------------------------------

node_selector = {"OS": containerservice.OSType.LINUX}

#----------------------------------------------------------------------------------------------------------------------
# JUPYTERLAB -> DATABRICKS CONNECT
#----------------------------------------------------------------------------------------------------------------------

databricks_connect = any([
    jupyterlab_config.get("databricks_connect", {}).get("enabled", False),
    env_jupyterlab_config.get("databricks_connect", {}).get("enabled", False)
])
single_user_clusters = {}
if databricks_connect:
    for user in env_jupyterlab_config.get("databricks_connect", {}).get("users", []):

        cluster = user.get("cluster", {})

        cluster_version = cluster.get("spark_version", "10.4")

        if not any([cluster_version.startswith(ver) for ver in ("9.1", "10.4")]):
            raise Exception(
                f"Databricks Connect, user {user['email_address']}. "
                f"Spark version set to {cluster.get('spark_version')}, "
                "but needs to be set to '9.1.x-scala2.12' or '10.4.x-scala2.12' to support "
                "Databricks Connect and match the python version 3.8. "
                "See https://docs.microsoft.com/en-us/azure/databricks/dev-tools/databricks-connect#requirements"
            )

        user_name = user["email_address"].split("@")[0]

        single_user_clusters[user_name] = create_cluster(
            databricks_provider=databricks_provider,
            platform_config=platform_config,
            resource_name=f"analytics-singleuser-{user_name}",
            cluster_name=f"singleuser-{user_name}",
            cluster_config=cluster,
            cluster_defaults={
                "autotermination_minutes": 15,
                "node_type_id": "Standard_F4s",
                "num_workers": 1,
                "single_user_name": user["email_address"],
                "spark_env_vars": {
                    "PYSPARK_PYTHON": "/databricks/python3/bin/python3",
                    "DATABRICKS_WORKSPACE_HOSTNAME": workspace.workspace_url,
                    "DATABRICKS_CLUSTER_NAME": f"singleuser-{user_name}",
                    "DATA_LAKE_NAME": datalake.name,
                },
                "spark_conf": {
                    "spark.databricks.delta.preview.enabled": "true",
                    "spark.databricks.passthrough.enabled": "true"
                },
                "spark_version": "10.4.x-scala2.12",
            },
        )

#----------------------------------------------------------------------------------------------------------------------
# JUPYTERLAB -> STARTUP SCRIPTS
#----------------------------------------------------------------------------------------------------------------------

# Add startup files
startup_name = "jupyterhub-startup"
startup_file_share = storage.FileShare(
    resource_name=generate_resource_name(
        resource_type="storage_file_share",
        resource_name="jupyterhub_startup",
        platform_config=platform_config,
    ),
    access_tier=storage.ShareAccessTier.TRANSACTION_OPTIMIZED,
    account_name=kubernetes_storage_account.name,
    resource_group_name=kubernetes_storage_account_resource_group,
    share_name=startup_name,
    share_quota=5120,
    opts=ResourceOptions(
        depends_on=[kubernetes_storage_account],
    ),
)
startup_blob_container = storage.BlobContainer(
    resource_name=generate_resource_name(
        resource_type="storage_blob_container",
        resource_name=startup_name,
        platform_config=platform_config,
    ),
    account_name=kubernetes_storage_account.name,
    container_name=startup_name,
    resource_group_name=kubernetes_storage_account_resource_group,
    opts=ResourceOptions(
        depends_on=[kubernetes_storage_account],
        protect=platform_config.resource_protection,
        ignore_changes=[
            "public_access",
            "default_encryption_scope",
            "deny_encryption_scope_override",
        ],
    ),
)

def upload_startup_file(title, file_name):
    file_asset = FileAsset(f"analytics/jupyterlab/files/{file_name}")
    return storage.Blob(
        resource_name=generate_resource_name(
            resource_type="storage_blob",
            resource_name=title,
            platform_config=platform_config,
        ),
        account_name=kubernetes_storage_account.name,
        blob_name=file_name,
        container_name=startup_name,
        resource_group_name=kubernetes_storage_account_resource_group,
        source=file_asset,
        opts=ResourceOptions(depends_on=[startup_blob_container]),
    )

install_packages_blob = upload_startup_file(
    "README", "README")
startup_files = [install_packages_blob]
if databricks_connect:
    databricks_connect_blob = upload_startup_file(
        "databricks_connect", "10_databricks_connect.py")
    startup_files.append(databricks_connect_blob)

if quantum_workspace_config["enabled"]:
    quantum_examples_blob = upload_startup_file(
        "quantum_examples", "10_quantum.py")
    startup_files.append(quantum_examples_blob)

# Move files to be mounted
storage_account_secret = add_storage_account_secret(namespace.id)
to_file_share_job = batch.v1.Job(
    resource_name=generate_resource_name(
        resource_type="kubernetes_job",
        resource_name="startup-blob-to-share",
        platform_config=platform_config,
    ),
    spec=batch.v1.JobSpecArgs(
        template=core.v1.PodTemplateSpecArgs(
            spec=core.v1.PodSpecArgs(
                containers=[core.v1.ContainerArgs(
                    name="blob-to-share",
                    image="ingeniisolutions/utility-blob-to-share:0.1.0",
                    env=[
                        core.v1.EnvVarArgs(
                            name=k, value_from=core.v1.EnvVarSourceArgs(
                                secret_key_ref=core.v1.SecretKeySelectorArgs(
                                    name=kubernetes_storage_account_secret_name,
                                    key=v
                                )
                            )
                        )
                        for k, v in {
                            "ACCOUNT_NAME": "azurestorageaccountname",
                            "ACCOUNT_KEY": "azurestorageaccountkey",
                        }.items()
                    ] + [
                        core.v1.EnvVarArgs(name=k, value=v)
                        for k, v in {
                            "CONTAINER_NAME": startup_blob_container.name,
                            "SHARE_NAME": startup_file_share.name,
                        }.items()
                    ],
                    image_pull_policy="Always",
                )],
                node_selector=node_selector,
                restart_policy="Never",
            ),
        ),
        backoff_limit=4,
    ),
    metadata=meta.v1.ObjectMetaArgs(
        labels={
            # Record MD5 hashes to prompt recreation of job on file changes
            f"MD5_{idx}": startup_file.content_md5.apply(
                lambda md5: "".join([char for char in md5 if char.isalnum()])
            )
            for idx, startup_file in enumerate(startup_files)
        },
        namespace=namespace.id,
    ),
    opts=ResourceOptions(
        depends_on=[storage_account_secret] + startup_files,
        provider=shared_kubernetes_provider,
    ),
)

#----------------------------------------------------------------------------------------------------------------------
# JUPYTERLAB -> CHART AND DEPLOYMENT
#----------------------------------------------------------------------------------------------------------------------

# Persisting the authentication state reference
# https://github.com/jupyterhub/oauthenticator/blob/main/oauthenticator/azuread.py
# https://github.com/jupyterhub/oauthenticator/blob/main/examples/auth_state/jupyterhub_config.py

def create_chart_values(kwargs):
    values = {
        "hub": {
            "config": {
                "Authenticator": {
                    "auto_login": True,
                },
                "AzureAdOAuthenticator": {
                    "client_id": auth_application.application_id,
                    "client_secret": auth_service_principal_password.value,
                    "oauth_callback_url": kwargs["callback_url"],
                    "tenant_id": azure_client.tenant_id,
                },
                "JupyterHub": {
                    "authenticator_class": "azuread"
                },
            },
            "extraConfig":{
                "add-jupyterlab": "c.Spawner.cmd=['jupyter-labhub']",
            },
            "nodeSelector": node_selector
        },
        "prePuller": {
            "hook": {
                "nodeSelector": node_selector
            }
        },
        "proxy": {
            "chp": {
                "nodeSelector": node_selector
            },
            "service": {
                "loadBalancerIP": kwargs["public_ip"]
            },
            "traefik": {
                "nodeSelector": node_selector
            }
        },
        "scheduling": {
            "userScheduler": {
                "nodeSelector": node_selector
            }
        },
        "singleuser": {
            "extraEnv": {},
            "nodeSelector": node_selector,
            "storage": {
                "extraVolumes": [
                    {
                        "azureFile": {
                            "secretName": kubernetes_storage_account_secret_name,
                            "shareName": startup_file_share.name,
                            "readOnly": True,
                        },
                        "name": "startup"
                    }
                ],
                "extraVolumeMounts": [
                    {
                        "mountPath": "/home/jovyan/.ipython/profile_default/startup",
                        "name": "startup"
                    }
                ]
            }
        },
    }
    if hostname:
        values["proxy"]["https"] = {
            "enabled": True,
            "hosts": [hostname],
            "letsencrypt": {"contactEmail": contact_email,},
        }

    custom_extensions = ""
    if databricks_connect:
        # Need to check the Databricks version (9.1)
        values["singleuser"]["extraEnv"].update({
            "DATABRICKS_ADDRESS": "https://" + kwargs["databricks_url"],
            "DATABRICKS_SUBSCRIPTION_ID": azure_client.subscription_id,
            "DATABRICKS_ORG_ID": kwargs["databricks_id"],
            "DATABRICKS_PORT": "15001",
        })
        custom_extensions += "-databricks"
    if quantum_workspace_config["enabled"]:
        values["singleuser"]["extraEnv"].update({
            "WORKSPACE_SUBSCRIPTION_ID": azure_client.subscription_id,
            "WORKSPACE_RESOURCE_GROUP": quantum_outputs["workspace"]["resource_group_name"],
            "WORKSPACE_LOCATION": quantum_outputs["workspace"]["location"],
            "WORKSPACE_NAME": kwargs["quantum_workspace_name"],
        })
        custom_extensions += "-quantum"
    if custom_extensions:
        values["singleuser"]["image"] = {
            "name": "ingeniisolutions/jupyterlab-single-user" + custom_extensions,
            "tag": env_jupyterlab_config["single_user_image_version"],
            "pullPolicy": "Always",
        }

    return values

chart_values = Output.all(
    callback_url=callback_url, public_ip=hub_public_ip.ip_address,
    record_set=record_set,
    databricks_url=workspace.workspace_url, databricks_id=workspace.workspace_id,
    quantum_workspace_name=quantum_outputs.get("workspace", {}).get("name"),
).apply(create_chart_values)

def remove_compat(args: ResourceTransformationArgs):
    if "compat" in args.props:
        del args.props["compat"]
    return ResourceTransformationResult(
        props=args.props,
        opts=args.opts,
        )

jupyterlab = helm.v3.Release(
    resource_name=resource_name,
    atomic=False,
    chart=f"{getcwd()}/../../helm_charts/jupyterhub",
    cleanup_on_fail=False,
    create_namespace=False,
    dependency_update=False,
    description="Jupyterlab Deployment",
    devel=False,
    disable_crd_hooks=False,
    disable_openapi_validation=False,
    disable_webhooks=False,
    force_update=False,
    keyring="",
    lint=False,
    namespace=namespace.metadata.name,
    postrender="",
    recreate_pods=False,
    render_subchart_notes=False,
    replace=False,
    reset_values=False,
    reuse_values=False,
    skip_await=False,
    skip_crds=False,
    timeout=600,
    values=chart_values,
    verify=False,
    version=jupyterlab_config["version"],
    wait_for_jobs=False,
    opts=ResourceOptions(
        ignore_changes=["apiVersion", "kind", "resourceNames"],
        provider=shared_kubernetes_provider,
        transformations=[remove_compat],
    )
)
# For when we can run the full image: https://github.com/traefik/traefik/issues/8803
#     chart="jupyterhub",
#     repository_opts=helm.v3.RepositoryOptsArgs(repo="https://jupyterhub.github.io/helm-chart/"),

outputs.update({
    "id": jupyterlab.id,
    "name": jupyterlab.name,
    "namespace": jupyterlab.namespace,
    "url": hostname or hub_public_ip.ip_address
})
