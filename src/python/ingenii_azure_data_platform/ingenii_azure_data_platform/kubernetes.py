from pulumi_azure_native import containerservice

config_os = {
    "datafactory_runtime": containerservice.OSType.WINDOWS,
    "jupyterlab": containerservice.OSType.LINUX,
}

def get_cluster_config(platform_config):
    """ Given the platform config, find the Kubernetes cluster details """
    configs = {
        "datafactory_runtime": platform_config["analytics_services"]["datafactory"]["integrated_self_hosted_runtime"],
        "jupyterlab": platform_config["analytics_services"]["jupyterlab"],
    }

    return {
        "enabled": any(config["enabled"] for config in configs.values()),
        "windows": any(
            config["enabled"] and config_os[name] == containerservice.OSType.WINDOWS
            for name, config in configs.items()
        ),
        "configs": configs,
    }
