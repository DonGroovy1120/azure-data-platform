from typing import Dict, List, Union

class PlatformFirewall:
    def __init__(
        self,
        enabled: bool = False,
        ip_access_list: List[str] = None,
        vnet_access_list: List[str] = None,
        resource_access_list: List[Dict[str, str]] = None,
        default_action: str = "Deny",
        trust_azure_services: bool = False,
    ):
        self._enabled = enabled
        self._ip_access_list = sorted(list(set(ip_access_list or [])))
        self._vnet_access_list = sorted(list(set(vnet_access_list or [])))
        self._resource_access_list = sorted(resource_access_list or [])
        self._default_action = default_action
        self._trust_azure_services = trust_azure_services

    def __str__(self):
        return str(
            {
                "enabled": self._enabled,
                "ip_access_list": self._ip_access_list,
                "vnet_access_list": self._vnet_access_list,
                "resource_access_list": self._resource_access_list,
                "default_action": self._default_action,
                "trust_azure_services": self._trust_azure_services,
            }
        )

    def __add__(self, other):
        if self._enabled:
            ip_access_list = list(set(self._ip_access_list + other._ip_access_list))
            vnet_access_list = list(
                set(self._vnet_access_list + other._vnet_access_list)
            )
            resource_access_list = list(
                set(self._resource_access_list + other._resource_access_list)
            )

        else:
            ip_access_list = other._ip_access_list
            vnet_access_list = other._vnet_access_list
            resource_access_list = other._resource_access_list

        return PlatformFirewall(
            enabled=other._enabled,
            ip_access_list=ip_access_list,
            vnet_access_list=vnet_access_list,
            resource_access_list=resource_access_list,
            default_action=other._default_action,
            trust_azure_services=other._trust_azure_services,
        )

    @property
    def enabled(self):
        return self._enabled

    @property
    def ip_access_list(self) -> List[str]:
        return self._ip_access_list

    @property
    def vnet_access_list(self) -> List[str]:
        return self._vnet_access_list

    @property
    def resource_access_list(self) -> List[Dict[str, str]]:
        return self._resource_access_list

    @property
    def default_action(self) -> str:
        return self._default_action

    @property
    def bypass_services(self) -> Union[str, None]:
        if self._trust_azure_services:
            return "AzureServices"
        return None
