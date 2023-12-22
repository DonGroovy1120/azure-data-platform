from pulumi import ResourceOptions
import pulumi_azuredevops as ado
from pulumi_azure_native import compute, managedidentity
import pulumi_random

from ingenii_azure_data_platform.iam import UserAssignedIdentityRoleAssignment
from ingenii_azure_data_platform.utils import generate_resource_name
from automation.devops import ado_project
from management import resource_groups
from management.resource_groups import resource_groups_config
from network.vnet import devops_deployment_subnet
from project_config import azure_client, platform_config, platform_outputs
from security.config_registry import key_vault

ado_configs = platform_config.from_yml["automation"]["devops"]
outputs = platform_outputs["automation"]
devops_virtual_machine_scale_set_name = "devops-deployment"

resource_group_name = generate_resource_name(
    resource_type="resource_group",
    resource_name=resource_groups_config["security"]["display_name"],
    platform_config=platform_config,
)


def generate_user_assigned_identity_name(environment):
    return "-".join(
        [platform_config.prefix, "devops-deployment-managed-identity", environment]
    )


def generate_user_assigned_identity_id(environment):
    return "/".join(
        [
            "/subscriptions",
            azure_client.subscription_id,
            "resourceGroups",
            resource_group_name,
            "providers/Microsoft.ManagedIdentity/userAssignedIdentities",
            generate_user_assigned_identity_name(environment),
        ]
    )

# ----------------------------------------------------------------------------------------------------------------------
# DEVOPS VIRTUAL MACHINE SCALE SET -> USER ASSIGNED MANAGED IDENTITIES
# ----------------------------------------------------------------------------------------------------------------------

user_assigned_identities = {
    env: managedidentity.UserAssignedIdentity(
        resource_name=generate_user_assigned_identity_name(env),
        resource_name_=generate_user_assigned_identity_name(env),
        location=platform_config.region.long_name,
        resource_group_name=resource_groups["security"].name,
        tags=platform_config.tags,
    )
    for env in platform_config["general"]["environments"]
}

outputs["deployment_user_assigned_identities"] = {
    env: identity.principal_id for env, identity in user_assigned_identities.items()
}

# ----------------------------------------------------------------------------------------------------------------------
# DEVOPS VIRTUAL MACHINE SCALE SET
# ----------------------------------------------------------------------------------------------------------------------

admin_password = pulumi_random.RandomPassword(
    resource_name=generate_resource_name(
        resource_type="random_password",
        resource_name=devops_virtual_machine_scale_set_name,
        platform_config=platform_config,
    ),
    length=16,
    min_lower=3,
    min_upper=3,
    min_special=3,
    min_numeric=3,
    special=True,
    override_special="_%@",
)

# https://docs.microsoft.com/en-us/azure/devops/pipelines/agents/scale-set-agents?view=azure-devops
devops_virtual_machine_scale_set = compute.VirtualMachineScaleSet(
    resource_name=generate_resource_name(
        resource_type="virtual_machine_scale_set",
        resource_name=devops_virtual_machine_scale_set_name,
        platform_config=platform_config,
    ),
    location=platform_config.region.long_name,
    orchestration_mode=compute.OrchestrationMode.UNIFORM,
    overprovision=False,
    resource_group_name=resource_groups["infra"].name,
    sku=compute.SkuArgs(
        capacity=0,
        name="Standard_F2s_v2",
        tier="Standard",
    ),
    upgrade_policy=compute.UpgradePolicyArgs(
        mode=compute.UpgradeMode.MANUAL
    ),
    virtual_machine_profile=compute.VirtualMachineScaleSetVMProfileArgs(
        network_profile=compute.VirtualMachineScaleSetNetworkProfileArgs(
            network_interface_configurations=[
                compute.VirtualMachineScaleSetNetworkConfigurationArgs(
                    dns_settings=compute.VirtualMachineScaleSetNetworkConfigurationDnsSettingsArgs(
                        dns_servers=[],
                    ),
                    enable_accelerated_networking=False,
                    enable_ip_forwarding=True,
                    ip_configurations=[
                        compute.VirtualMachineScaleSetIPConfigurationArgs(
                            name=devops_virtual_machine_scale_set_name,
                            private_ip_address_version=compute.IPVersion.I_PV4,
                            subnet=compute.ApiEntityReferenceArgs(
                                id=devops_deployment_subnet.id,
                            ),
                        )
                    ],
                    name=devops_virtual_machine_scale_set_name,
                    primary=True,
                )
            ],
        ),
        os_profile=compute.VirtualMachineScaleSetOSProfileArgs(
            computer_name_prefix=devops_virtual_machine_scale_set_name,
            admin_username="azuredevopsdeploymentadmin",
            admin_password=admin_password.result,
            linux_configuration=compute.LinuxConfigurationArgs(
                disable_password_authentication=False,
                provision_vm_agent=True,
            ),
            secrets=[],
        ),
        storage_profile=compute.VirtualMachineScaleSetStorageProfileArgs(
            image_reference=compute.ImageReferenceArgs(
                offer="UbuntuServer",
                publisher="Canonical",
                sku="18.04-LTS",
                version="latest",
            ),
            os_disk=compute.VirtualMachineScaleSetOSDiskArgs(
                caching=compute.CachingTypes.READ_ONLY,
                create_option=compute.DiskCreateOptionTypes.FROM_IMAGE,
                disk_size_gb=30,
                diff_disk_settings=compute.DiffDiskSettingsArgs(
                    option=compute.DiffDiskOptions.LOCAL,
                    placement=compute.DiffDiskPlacement.CACHE_DISK,
                ),
                managed_disk=compute.VirtualMachineScaleSetManagedDiskParametersArgs(
                    storage_account_type=compute.StorageAccountType.STANDARD_LRS,
                ),
                os_type=compute.OperatingSystemTypes.LINUX,
            ),
        ),
    ),
    identity=compute.VirtualMachineScaleSetIdentityArgs(
        type=compute.ResourceIdentityType.USER_ASSIGNED,
        user_assigned_identities={
            generate_user_assigned_identity_id(env): {}
            for env in user_assigned_identities
        },
    ),
    vm_scale_set_name=platform_config.prefix
    + "-"
    + devops_virtual_machine_scale_set_name,
    tags=platform_config.tags,
    opts=ResourceOptions(
        ignore_changes=[
            "sku.capacity",
            "virtualMachineProfile.extensionProfile",
            "virtualMachineProfile.osProfile.adminPassword",
        ]
    ),
)

# ----------------------------------------------------------------------------------------------------------------------
# DEVOPS VIRTUAL MACHINE SCALE SET -> DEVOPS VARIABLE GROUPS
# ----------------------------------------------------------------------------------------------------------------------

variable_group_managed_identities = ado.VariableGroup(
    resource_name=generate_resource_name(
        resource_type="devops_variable_group",
        resource_name="managed-identity-ids-variable-group",
        platform_config=platform_config,
    ),
    name="Managed Identity IDs",
    project_id=ado_project.id,
    description="IDs of deployment managed identities",
    allow_access=True,
    variables=[
        ado.VariableGroupVariableArgs(
            name=f"USER_ASSIGNED_MANAGED_IDENTITY_{env.upper()}",
            value=identity.client_id,
        )
        for env, identity in user_assigned_identities.items()
    ],
)

variable_group_config_registry = ado.VariableGroup(
    resource_name=generate_resource_name(
        resource_type="devops_variable_group",
        resource_name="configuration_registry",
        platform_config=platform_config,
    ),
    name="Configuration Registry",
    project_id=ado_project.id,
    description="Details of the configuration registry",
    allow_access=True,
    variables=[
        ado.VariableGroupVariableArgs(
            name=f"CONFIGURATION_REGISTRY_NAME",
            value=key_vault.name,
        )
    ],
)

# Grant access to configuration registry

for env, identity in user_assigned_identities.items():
    UserAssignedIdentityRoleAssignment(
        principal_id=identity.principal_id,
        principal_name=f"deployment-user-identity-{env}",
        role_name="Key Vault Secrets User",
        scope=key_vault.id,
        scope_description="config-registry",
    )
