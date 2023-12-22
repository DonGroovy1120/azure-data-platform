from pulumi import ResourceOptions
import pulumi_databricks as databricks

from ingenii_azure_data_platform.utils import generate_resource_name

def create_cluster(
    databricks_provider, platform_config, resource_name,
    cluster_config, cluster_defaults, cluster_name=None,
    instance_pools=None, is_pinned=True,
    depends_on=None, **extra_settings):
    """ Given cluster configuration and defaults, create the object """

    instance_pools = instance_pools or {}

    # Cluster Libraries
    cluster_libraries = [
        # PyPi libraries
        databricks.ClusterLibraryArgs(
            pypi=databricks.ClusterLibraryPypiArgs(
                package=lib.get("package"), repo=lib.get("repo")
            )
        )
        for lib in cluster_config.get("libraries", {}).get("pypi", [])
            + cluster_defaults.get("libraries", {}).get("pypi", [])
    ] + [
        # WHL libraries
        databricks.ClusterLibraryArgs(whl=whl) for whl in set(
            cluster_config.get("libraries", {}).get("whl", []) + \
            cluster_defaults.get("libraries", {}).get("whl", [])
        )
    ]

    # Collate the configuration

    def get_config(name, default=None):
        """
        Get the setting from the cluster configuration.
        If it's not there, get it from the cluster defaults.
        """
        return cluster_config.get(name, cluster_defaults.get(name, default))

    configuration = {
        "autotermination_minutes": get_config("autotermination_minutes", 15),
        "cluster_name": cluster_name or get_config("display_name"),
        "cluster_log_conf": databricks.ClusterClusterLogConfArgs(
            dbfs=databricks.ClusterClusterLogConfDbfsArgs(
                destination="dbfs:/mnt/cluster_logs"
            )
        ),
        "is_pinned": is_pinned or get_config("is_pinned", True),
        "libraries": cluster_libraries or None,
        "node_type_id": get_config("node_type_id"),
        "single_user_name": get_config("single_user_name"),
        "spark_conf": {
            **cluster_defaults.get("spark_conf", {}),
            **cluster_config.get("spark_conf", {}),
        },
        "spark_env_vars": {
            **cluster_defaults.get("spark_env_vars", {}),
            **cluster_config.get("spark_env_vars", {}),
        },
        "spark_version": get_config("spark_version"),
        **extra_settings,
    }

    if get_config("type") != "single_node":
        if get_config("auto_scale_min_workers") and get_config("auto_scale_max_workers"):
            configuration["autoscale"] = databricks.ClusterAutoscaleArgs(
                min_workers=get_config("auto_scale_min_workers"),
                max_workers=get_config("auto_scale_max_workers"),
            )
        else:
            configuration["num_workers"] = get_config("num_workers")

        if get_config("use_spot_instances"):
            spot_instance_config = get_config("use_spot_instances")
            configuration["azure_attributes"] = databricks.ClusterAzureAttributesArgs(
                availability="SPOT_WITH_FALLBACK_AZURE",
                first_on_demand=spot_instance_config.get("first_on_demand", 1),
                spot_bid_max_price=spot_instance_config.get("spot_bid_max_price", 100)
            )
        else:
            configuration["azure_attributes"] = databricks.ClusterAzureAttributesArgs(
                availability="ON_DEMAND_AZURE",
                spot_bid_max_price=100,
            )

    if get_config("docker_image_url"):
        configuration["docker_image"] = databricks.ClusterDockerImageArgs(
            url=get_config("docker_image_url")
        )
    if get_config("instance_pool_ref_key"):
        configuration["instance_pool_id"] = instance_pools[
            get_config("instance_pool_ref_key")
        ].id
        if configuration.get("node_type_id") is not None:
            del configuration["node_type_id"]

    if get_config("driver_instance_pool_ref_key"):
        configuration["driver_instance_pool_id"] = instance_pools[
            get_config("driver_instance_pool_ref_key")
        ].id
        if configuration.get("node_type_id") is not None:
            del configuration["node_type_id"]

    return databricks.Cluster(
        resource_name=generate_resource_name(
            resource_type="databricks_cluster",
            resource_name=resource_name,
            platform_config=platform_config,
        ),
        **configuration,
        opts=ResourceOptions(
            provider=databricks_provider, depends_on=depends_on or []
        ),
    )
