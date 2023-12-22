import os
from ipaddress import ip_network
from hashlib import md5
from typing import Any

from pulumi import Output, ResourceOptions
from pulumi_azure_native.authorization import ManagementLockByScope, LockLevel

from ingenii_azure_data_platform.config import PlatformConfiguration


def generate_resource_name(
    resource_type: str, resource_name: str, platform_config: PlatformConfiguration
) -> str:
    """
    Generate a resource names based on consistent naming conventions.

    Parameters
    ----------
    resource_type: str
        The Azure resource type, e.g. 'resource_group', 'route_table'.

        Possible options are: resource_group, virtual_network, subnet, route_table,
        network_security_group, nat_gateway, public_ip, private_endpoint, service_principal,
        storage_blob_container,dns_zone, private_dns_zone, datafactory, databricks_workspace,
        databricks_cluster

    resource_name: str
        The name of the resource for which we are generating a consistent name.

    Returns
    -------
    str
        The generated resource name.
    """
    resource_names = {
        "action_group": "ag",
        "container_registry": "cr",
        "databricks_cluster": "dbwc",
        "databricks_directory": "dbd",
        "databricks_instance_pool": "dbwip",
        "databricks_job": "dbj",
        "databricks_notebook": "dbn",
        "databricks_workspace": "dbw",
        "devops_pipeline": "adopipe",
        "devops_project": "adoproj",
        "devops_repo": "adorepo",
        "devops_variable_group": "adovg",
        "dns_zone": "dz",
        "kubernetes_agent_pool": "kap",
        "kubernetes_cluster": "kc",
        "kubernetes_job": "kj",
        "kubernetes_persistent_volume": "kpv",
        "log_analytics_workspace": "law",
        "metric_alert": "ma",
        "nat_gateway": "ngw",
        "network_security_group": "nsg",
        "private_dns_zone": "prdz",
        "private_endpoint": "pe",
        "public_ip": "pip",
        "quantum_workspace": "qw",
        "random_password": "rp",
        "random_string": "rs",
        "resource_group": "rg",
        "route_table": "rt",
        "service_principal": "sp",
        "static_site": "sts",
        "static_site_custom_domain": "stscd",
        "storage_blob": "sb",
        "storage_blob_container": "sbc",
        "storage_file_share": "sfs",
        "storage_management_policy": "smp",
        "subnet": "snet",
        "user_assigned_managed_identity": "uami",
        "virtual_machine_scale_set": "vmss",
        "virtual_network": "vnet",
    }

    resource_type = resource_type.lower()
    prefix = platform_config.prefix
    stack = platform_config.stack_short_name
    region_short_name = platform_config.region.short_name
    unique_id = platform_config.unique_id
    use_legacy_naming = platform_config.use_legacy_naming

    # User Groups (Azure AD Groups)
    if resource_type == "user_group":
        # Example
        # ADP-Dev-Engineers
        return f"{prefix.upper()}-{stack.title()}-{resource_name.title()}"

    # Gateway Subnet
    elif resource_type == "gateway_subnet":
        return "Gateway"

    # Key Vault
    elif resource_type == "key_vault":
        # Example:
        # adp-tst-eus-kv-cred-ixk1
        return f"{prefix}-{stack}-{region_short_name}-kv-{resource_name}-{unique_id}"

    # Data Factory
    elif resource_type == "datafactory":
        if use_legacy_naming:
            return f"{prefix}-{stack}-{region_short_name}-adf-{resource_name.lower()}"

        return f"{prefix}-{stack}-{region_short_name}-adf-{resource_name}-{unique_id}"

    # Data Factory: Self Hosted Integration Runtime
    elif resource_type == "adf_integration_runtime":
        return f"{prefix}-{stack}-{resource_name}-{unique_id}"

    # Storage Account
    elif resource_type == "storage_account":
        return f"{prefix}{stack}{resource_name}{unique_id}"

    # Log Analytics Workspace
    elif resource_type == "log_analytics_workspace":
        return f"{prefix}-{stack}-{region_short_name}-law-{resource_name.lower()}-{unique_id}"

    # Other Resources
    elif resource_type in resource_names:
        return f"{prefix}-{stack}-{region_short_name}-{resource_names[resource_type]}-{resource_name.lower()}"

    else:
        raise Exception(f"Resource type {resource_type} not recognised.")


def generate_hash(*args: str) -> str:
    """
    This function takes arbitrary number of string arguments, joins them together and returns and MD5 hash
    based on the joined string.

    Parameters
    ----------
    *args: str
        Arbitrary number of strings.

    Returns
    -------
    str
        An MD5 hash based on the provided strings.
    """
    concat = "".join(args).encode("utf-8")
    return md5(concat).hexdigest()


def generate_cidr(cidr_subnet: str, new_prefix: int, network_number: int) -> Any:
    """
    Calculates a new subnet number based on the inputs provided.
    # TODO
    """
    return list(ip_network(cidr_subnet).subnets(new_prefix=new_prefix))[
        network_number
    ].exploded


def get_os_root_path() -> str:
    """
    Returns the root path of the current operating system.
    Unix/MacOS = "/"
    Windows = "c:"
    # TODO
    """
    return os.path.abspath(os.sep)


def ensure_type(value, types):
    """
    This function checks if a value is of certain type.
    # TODO
    """
    if isinstance(value, types):
        return value
    else:
        raise TypeError(f"Value {value} is {type(value),}, but should be {types}!")


def lock_resource(
    resource_name: str,
    resource_id: Output,
    lock_level: LockLevel = LockLevel.CAN_NOT_DELETE,
    provider = None,
):
    ManagementLockByScope(
        resource_name=resource_name,
        level=lock_level,
        lock_name="Managed by Ingenii",
        scope=resource_id,
        opts=ResourceOptions(
            delete_before_replace=True,
            provider=provider,
        )
    )
