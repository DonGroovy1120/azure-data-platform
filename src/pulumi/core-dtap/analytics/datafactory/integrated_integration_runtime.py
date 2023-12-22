from base64 import b64encode
from pulumi import ResourceOptions
from pulumi_azure_native import containerservice, datafactory
from pulumi_kubernetes import apps, core, meta

from analytics.datafactory.user_datafactories import datafactory_resource_group, user_datafactories
from platform_shared import datafactory_runtime_config, shared_kubernetes_provider
from project_config import platform_config, platform_outputs

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> INTEGRATED INTEGRATION RUNTIME
# ----------------------------------------------------------------------------------------------------------------------

overall_outputs = platform_outputs["analytics"]["datafactory"]["integrated_integration_runtime"] = {}

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY RUNTIME -> NAMESPACE
# ----------------------------------------------------------------------------------------------------------------------

namespace = core.v1.Namespace(
    resource_name=f"datafactory-runtime-{platform_config.stack}",
    metadata={},
    opts=ResourceOptions(provider=shared_kubernetes_provider)
)
overall_outputs["namespace"] = namespace.metadata.name


# A container per Data Factory
for ref_key, datafactory_config in user_datafactories.items():

    outputs = overall_outputs[ref_key] = {}

    factory_name = datafactory_config["name"]
    integrated_integration_runtime = datafactory.IntegrationRuntime(
        resource_name=f"datafactory_integrated_runtime_{platform_config.stack}",
        resource_group_name=datafactory_resource_group.name,
        factory_name=factory_name,
        integration_runtime_name="IntegratedIntegrationRuntime",
        properties=datafactory.SelfHostedIntegrationRuntimeArgs(
            description="Integrated integration runtime provided by Ingenii",
            type="SelfHosted"
        ),
    )

    iir_keys = datafactory.list_integration_runtime_auth_keys_output(
        resource_group_name=datafactory_resource_group.name,
        factory_name=factory_name,
        integration_runtime_name=integrated_integration_runtime.name,
    )

    labels = {
        "data_factory": factory_name,
        "type": "DataFactorySelfHostedIntegrationRuntime",
        "system": "IngeniiDataPlatform"
    }

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY RUNTIME -> SECRET -> AUTH KEY
    # ----------------------------------------------------------------------------------------------------------------------

    auth_key_secret_name = f"data-factory-runtime-auth-key-{ref_key}-{platform_config.stack}"
    auth_key_secret = core.v1.Secret(
        resource_name=auth_key_secret_name,
        data={
            auth_key_secret_name: iir_keys.auth_key1.apply(
                lambda key: b64encode(key.encode()).decode()
            ),
        },
        metadata=meta.v1.ObjectMetaArgs(
            labels=labels, 
            namespace=namespace.id
        ),
        opts=ResourceOptions(provider=shared_kubernetes_provider, ignore_changes=["data"])
    )

    # ----------------------------------------------------------------------------------------------------------------------
    # DATA FACTORY RUNTIME -> RUNTIME CONTAINER
    # ----------------------------------------------------------------------------------------------------------------------

    deployment = apps.v1.Deployment(
        resource_name=f"datafactory-runtime-deployment-{ref_key}-{platform_config.stack}",
        metadata=meta.v1.ObjectMetaArgs(
            labels=labels,
            namespace=namespace.id
        ),
        spec=apps.v1.DeploymentSpecArgs(
            replicas=1,
            selector=meta.v1.LabelSelectorArgs(
                match_labels=labels,
            ),
            template=core.v1.PodTemplateSpecArgs(
                metadata=meta.v1.ObjectMetaArgs(
                    labels=labels,
                ),
                spec=core.v1.PodSpecArgs(
                    containers=[core.v1.ContainerArgs(
                        name=f"datafactory-runtime-{ref_key}-{platform_config.stack}",
                        image=datafactory_runtime_config["image"],
                        env=[
                            core.v1.EnvVarArgs(
                                name="NODE_NAME", 
                                value=f"kubernetes_node_{ref_key}_{platform_config.stack}"
                            ),
                            core.v1.EnvVarArgs(
                                name="AUTH_KEY",
                                value_from=core.v1.EnvVarSourceArgs(
                                    secret_key_ref=core.v1.SecretKeySelectorArgs(
                                        key=auth_key_secret_name,
                                        name=auth_key_secret.metadata.name,
                                    )
                                )
                            ),
                            core.v1.EnvVarArgs(name="ENABLE_HA", value="true"),
                        ],
                        liveness_probe=core.v1.ProbeArgs(
                            exec_=core.v1.ExecActionArgs(command=[
                                "cmd", "/c", "powershell", "c:\\adf-runtime\healthcheck.ps1"
                            ]),
                            initial_delay_seconds=120,
                            period_seconds=60,
                            timeout_seconds=20,
                        ),
                        ports=[
                            core.v1.ContainerPortArgs(container_port=port)
                            for port in (80, 8060)
                        ],
                    )],
                    node_selector={"OS": containerservice.OSType.WINDOWS},
                ),
            ),
        ),
        opts=ResourceOptions(provider=shared_kubernetes_provider, depends_on=[auth_key_secret])
    )

    outputs["deployment"] = deployment.metadata.name