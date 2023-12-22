from base64 import b64decode
from pulumi import ResourceOptions
import pulumi_random
from pulumi_azure_native import containerservice
from pulumi_kubernetes import Provider as KubernetesProvider

from ingenii_azure_data_platform.iam import GroupRoleAssignment
from ingenii_azure_data_platform.kubernetes import get_cluster_config
from ingenii_azure_data_platform.utils import generate_resource_name, lock_resource

from logs import log_analytics_workspace
from management import resource_groups, resource_group_outputs, user_groups
from network.vnet import hosted_services_subnet
from project_config import azure_client, platform_config, platform_outputs

# ----------------------------------------------------------------------------------------------------------------------
# SHARED KUBERNETES CLUSTER -> BASE CONFIGURATIONS
# ----------------------------------------------------------------------------------------------------------------------

cluster_config = get_cluster_config(platform_config)
cluster_resource_name = "shared_cluster"
cluster_resource_group_name = resource_groups["infra"].name

# To avoid import issues
shared_kubernetes_provider = None

# Only create if a system requires it
if cluster_config["enabled"]:

    outputs = platform_outputs["analytics"]["shared_kubernetes_cluster"] = {}
    
    # ----------------------------------------------------------------------------------------------------------------------
    # SHARED KUBERNETES CLUSTER -> NODE RESOURCE GROUP NAME
    # ----------------------------------------------------------------------------------------------------------------------

    # Resource group for Kubernetes nodes, otherwise Azure will create one
    resource_group_config = platform_config["shared_kubernetes_cluster"]["resource_group"]
    node_resource_group_name = generate_resource_name(
            resource_type="resource_group",
            resource_name=resource_group_config["display_name"],
            platform_config=platform_config,
        )

    # ----------------------------------------------------------------------------------------------------------------------
    # SHARED KUBERNETES CLUSTER -> CLUSTER
    # ----------------------------------------------------------------------------------------------------------------------

    shared_cluster_config = platform_config["shared_kubernetes_cluster"]["cluster"]

    windows_admin_password = pulumi_random.RandomPassword(
        resource_name=generate_resource_name(
            resource_type="random_password",
            resource_name=cluster_resource_name,
            platform_config=platform_config,
        ),
        length=32,
        min_lower=1,
        min_numeric=1,
        min_special=1,
        min_upper=1,
        override_special="_%@",
    )

    add_ons = {}
    if shared_cluster_config.get("oms_agent", True):
        add_ons["omsagent"] = containerservice.ManagedClusterAddonProfileArgs(
            config={
                "logAnalyticsWorkspaceResourceID": log_analytics_workspace.id,
            },
            enabled=True,
        )

    kubernetes_cluster = containerservice.ManagedCluster(
        resource_name=generate_resource_name(
            resource_type="kubernetes_cluster",
            resource_name=cluster_resource_name,
            platform_config=platform_config,
        ),
        aad_profile=containerservice.ManagedClusterAADProfileArgs(
            admin_group_object_ids=[user_groups["admins"]["object_id"]],
            enable_azure_rbac=True,
            managed=True,
        ),
        addon_profiles=add_ons if add_ons else None,
        agent_pool_profiles=[
            # At minimum, the cluster requires a system Linux pool
            containerservice.ManagedClusterAgentPoolProfileArgs(
                availability_zones=["1"],
                count=1,
                enable_auto_scaling=True,
                max_count=1,
                min_count=1,
                mode=containerservice.AgentPoolMode.SYSTEM,
                name="systempool",
                node_labels={"OS": containerservice.OSType.LINUX},
                os_type=containerservice.OSType.LINUX,
                type=containerservice.AgentPoolType.VIRTUAL_MACHINE_SCALE_SETS,
                vm_size="Standard_B2ms",
                vnet_subnet_id=hosted_services_subnet.id,
            ),
        ],
        auto_upgrade_profile=containerservice.ManagedClusterAutoUpgradeProfileArgs(
            upgrade_channel=containerservice.UpgradeChannel.STABLE
        ),
        disable_local_accounts=False,
        dns_prefix=cluster_resource_name.replace("_", ""),
        enable_rbac=True,
        identity=containerservice.ManagedClusterIdentityArgs(
            type=containerservice.ResourceIdentityType.SYSTEM_ASSIGNED
        ),
        location=platform_config.region.long_name,
        network_profile=containerservice.ContainerServiceNetworkProfileArgs(
            network_mode=containerservice.NetworkMode.TRANSPARENT,
            network_plugin=containerservice.NetworkPlugin.AZURE,
            network_policy=containerservice.NetworkPolicy.AZURE,
        ),
        node_resource_group=node_resource_group_name,
        resource_group_name=cluster_resource_group_name,
        sku=containerservice.ManagedClusterSKUArgs(
            name=containerservice.ManagedClusterSKUName.BASIC,
            tier=containerservice.ManagedClusterSKUTier.FREE,
        ),
        tags=platform_config.tags,
        windows_profile=containerservice.ManagedClusterWindowsProfileArgs(
            admin_password=windows_admin_password.result,
            admin_username="runtimeclusteradmin",
        ),
        opts=ResourceOptions(
            delete_before_replace=True,
            ignore_changes=["agentPoolProfiles", "kubernetesVersion"]
        ),
    )
    if platform_config.resource_protection:
        lock_resource("shared_kubernetes_cluster", kubernetes_cluster.id)

    # TODO: Potentially implement
    #    identity_profile: Optional[Mapping[str, ManagedClusterPropertiesIdentityProfileArgs]] = None,
    #    private_link_resources: Optional[Sequence[PrivateLinkResourceArgs]] = None,

    outputs.update({
        "cluster_resource_group_name": cluster_resource_group_name.apply(lambda name: name),
        "enabled": True,
        "fqdn": kubernetes_cluster.fqdn,
        "id": kubernetes_cluster.id,
        "name": kubernetes_cluster.name,
        "node_resource_group_name": node_resource_group_name,
        "principal_id": kubernetes_cluster.identity.principal_id,
    })

    # ----------------------------------------------------------------------------------------------------------------------
    # SHARED KUBERNETES CLUSTER -> ROLE ASSIGNMENTS
    # ----------------------------------------------------------------------------------------------------------------------

    for assignment in shared_cluster_config["iam"]["role_assignments"]:
        # User Group Assignment
        user_group_ref_key = assignment.get("user_group_ref_key")
        if user_group_ref_key is not None:
            GroupRoleAssignment(
                principal_id=user_groups[user_group_ref_key]["object_id"],
                principal_name=user_group_ref_key,
                role_name=assignment["role_definition_name"],
                scope=kubernetes_cluster.id,
                scope_description="kubernetes-cluster",
            )

    # ----------------------------------------------------------------------------------------------------------------------
    # SHARED KUBERNETES CLUSTER -> NODE RESOURCE GROUP ASSIGNMENTS
    # ----------------------------------------------------------------------------------------------------------------------

    node_resource_group_id = kubernetes_cluster.node_resource_group.apply(
        lambda rg_name: f"/subscriptions/{azure_client.subscription_id}/resourceGroups/{rg_name}"
    )

    # Export resource group metadata
    resource_group_outputs["kubernetes"] = {
        "name": node_resource_group_name,
        "location": kubernetes_cluster.location,
        "id": node_resource_group_id,
    }
    for assignment in resource_group_config["iam"]["role_assignments"]:
        # User Group Assignment
        user_group_ref_key = assignment.get("user_group_ref_key")
        if user_group_ref_key is not None:
            GroupRoleAssignment(
                principal_id=user_groups[user_group_ref_key]["object_id"],
                principal_name=user_group_ref_key,
                role_name=assignment["role_definition_name"],
                scope=node_resource_group_id,
                scope_description="kubernetes-cluster-node-resource-group",
            )

    # ----------------------------------------------------------------------------------------------------------------------
    # SHARED KUBERNETES CLUSTER -> AGENT POOLS
    # ----------------------------------------------------------------------------------------------------------------------

    for idx, pool in enumerate(shared_cluster_config.get("linux_agent_pools", [])):
        agent_pool_name = pool.get("name", f"linux{idx}")
        autoscaling = pool.get("auto_scaling", True)
        ignore_changes = ["orchestratorVersion"]
        if autoscaling:
            ignore_changes.append("count")
        containerservice.AgentPool(
            resource_name=generate_resource_name(
                resource_type="kubernetes_agent_pool",
                resource_name=agent_pool_name,
                platform_config=platform_config,
            ),
            agent_pool_name=agent_pool_name,
            availability_zones=pool.get("availability_zones", ["1"]),
            count=pool.get("count", 1),
            enable_auto_scaling=autoscaling,
            max_count=pool.get("max_count", 1),
            min_count=pool.get("min_count", 1),
            mode=containerservice.AgentPoolMode.USER,
            node_labels={
                **pool.get("labels", {}),
                "OS": containerservice.OSType.LINUX,
            },
            os_type=containerservice.OSType.LINUX,
            resource_group_name=cluster_resource_group_name,
            resource_name_=kubernetes_cluster.name,
            tags=platform_config.tags,
            type=containerservice.AgentPoolType.VIRTUAL_MACHINE_SCALE_SETS,
            vm_size=pool.get("vm_size", "Standard_B2ms"),
            vnet_subnet_id=hosted_services_subnet.id,
            opts=ResourceOptions(ignore_changes=ignore_changes),
        )

    # Check if any of the enabled features need Windows machines
    windows_pools = shared_cluster_config.get("windows_agent_pools", [])
    if cluster_config["windows"] and not windows_pools:
        windows_pools = [{
            "labels": {"addedBy": "platform"},
            "name": "win1"
        }]

    for idx, pool in enumerate(windows_pools):
        # Note: Windows pool names must be 6 characters or fewer: https://docs.microsoft.com/en-us/azure/aks/windows-container-cli#limitations
        agent_pool_name = pool.get("name", f"win{idx}")
        autoscaling = pool.get("auto_scaling", True)
        ignore_changes = ["orchestratorVersion", "osSKU"]
        if autoscaling:
            ignore_changes.append("count")
        containerservice.AgentPool(
            resource_name=generate_resource_name(
                resource_type="kubernetes_agent_pool",
                resource_name=agent_pool_name,
                platform_config=platform_config,
            ),
            agent_pool_name=agent_pool_name,
            availability_zones=pool.get("availability_zones", ["1"]),
            count=pool.get("count", 1),
            enable_auto_scaling=autoscaling,
            max_count=pool.get("max_count", 1),
            min_count=pool.get("min_count", 1),
            mode=containerservice.AgentPoolMode.USER,
            node_labels={
                **pool.get("labels", {}),
                "OS": containerservice.OSType.WINDOWS,
            },
            os_type=containerservice.OSType.WINDOWS,
            resource_group_name=cluster_resource_group_name,
            resource_name_=kubernetes_cluster.name,
            tags=platform_config.tags,
            type=containerservice.AgentPoolType.VIRTUAL_MACHINE_SCALE_SETS,
            vm_size=pool.get("vm_size", "Standard_D2_v4"),
            vnet_subnet_id=hosted_services_subnet.id,
            opts=ResourceOptions(ignore_changes=ignore_changes),
        )

    # ----------------------------------------------------------------------------------------------------------------------
    # SHARED KUBERNETES CLUSTER -> CREDENTIALS
    # ----------------------------------------------------------------------------------------------------------------------

    kube_config = kubernetes_cluster.name.apply(
        lambda name:
        b64decode(
            containerservice.list_managed_cluster_admin_credentials(
                resource_group_name=cluster_resource_group_name,
                resource_name=name,
            ).kubeconfigs[0].value
        ).decode()
    )

    shared_kubernetes_provider = KubernetesProvider(
        "shared_kubernetes_provider", kubeconfig=kube_config
    )
