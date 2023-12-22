from ingenii_azure_data_platform.contracts.packages import PackageInputArgs

from importlib import import_module
from project_config import (
    SHARED_OUTPUTS,
    platform_config,
    CURRENT_STACK_NAME,
    DTAP_OUTPUTS,
)

namespaces = []


class PackageNamespaceDuplicateError(Exception):
    ...


def register_namespace(namespace: str, namespaces: list) -> str:
    if namespace not in namespaces:
        namespaces.append(namespace)
        return namespace
    else:
        raise PackageNamespaceDuplicateError(
            f"The namespace {namespace} is already taken."
        )


# Load all packages
region = platform_config.region
packages = platform_config.from_yml.get("packages", [])

for package in packages:
    package_name = package.get("name")
    package_config = package.get("config")
    namespace = register_namespace(package_name, namespaces)
    module = import_module(package_name)
    module.init(
        PackageInputArgs(
            package_config=package_config,
            namespace=namespace,
            platform_config=platform_config,
            dtap_outputs=DTAP_OUTPUTS,
            shared_outputs=SHARED_OUTPUTS,
        )
    )
