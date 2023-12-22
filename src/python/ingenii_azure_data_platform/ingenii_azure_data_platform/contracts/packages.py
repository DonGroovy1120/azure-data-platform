from ingenii_azure_data_platform.config import PlatformConfiguration
from typing import Any, OrderedDict
from pulumi.output import Output


class PackageInputArgs:
    def __init__(
        self,
        package_config: OrderedDict[str, Any],
        namespace: str,
        platform_config: PlatformConfiguration,
        dtap_outputs: Output[Any] = None,
        shared_outputs: Output[Any] = None,
    ):
        self._package_config = package_config
        self._namespace = namespace
        self._platform_config = platform_config
        self._dtap_outputs = dtap_outputs
        self._shared_outputs = shared_outputs

    @property
    def package_config(self):
        return self._package_config

    @property
    def namespace(self):
        return self._namespace.lower()

    @property
    def platform_config(self):
        return self._platform_config

    @property
    def dtap_outputs(self):
        return self._dtap_outputs

    @property
    def shared_outputs(self):
        return self._shared_outputs
