from abc import ABC, abstractmethod
from typing import Union

import pulumi
from pulumi_azure_native import keyvault
from pulumi_azure import keyvault as keyvault_classic


class ConfigRegistryBaseClient(ABC):
    """
    Base class for a Config Registry client.
    All Config Registry clients should inherit from this class.

    Attributes
    ---------
    None

    Methods
    -------
    get_value(key):
        Retrieves the value of the provided key.

    set_value(key, value):
        Stores the value under the provided key.
    """

    @abstractmethod
    def get_value(self, key: str) -> str:
        """
        Returns the value of the requested key parameter.

        Parameters
        ----------
            key (str): The key name of the stored value.
        """

    @abstractmethod
    def set_value(self, key: str, value: str) -> None:
        """
         Stores a value under a specified key.

        Parameters
        ----------
            key (str): The key under which to store the value.
            value (str): The value to store.

        Returns
        -------
            None
        """


class ConfigRegistryKeyVaultClient(ConfigRegistryBaseClient):
    """
    Config registry client that uses the Azure Key Vault as underlying storage engine.

    Attributes
    ----------

    Methods
    -------
    get_value(key):
        Retrieves the value of the provided key.

    set_value(key, value)
        Stores the value under the provided key.
    """

    _values = {}

    # TODO: Use regex or another approach to extract the values.
    @classmethod
    def _parse_key_vault_resource_id(cls, resource_id: str) -> dict[str, str]:
        _split = list(filter(None, resource_id.split("/")))

        return {"id": resource_id, "name": _split[7], "resource_group_name": _split[3]}

    def __init__(
        self,
        key_vault_resource_id: Union[str, pulumi.Output],
    ):
        """
        Constructs a config registry client.

        Parameters
        ----------
        key_vault_resource_id: str or pulumi.Output
            The resource id of the Azure Key Vault tha will be used as a storage engine.
            It can be provided directly as a string or from a Pulumi KeyVault
            resource (e.g. vault.id)
        """
        if isinstance(key_vault_resource_id, pulumi.Output):
            self._kv = key_vault_resource_id.apply(
                lambda id: self._parse_key_vault_resource_id(resource_id=id)
            )
        elif isinstance(key_vault_resource_id, str):
            self._kv = self._parse_key_vault_resource_id(
                resource_id=key_vault_resource_id
            )
        else:
            raise TypeError(
                "key_vault_resource_id should be of type 'pulumi.Output' or 'str'."
            )

    def get_value(self, key: str) -> str:
        """
        Returns the value of the requested key parameter.

        Parameters
        ----------
            key (str): The key name of the stored value.

        Returns
        -------
            A string representation of the value.

        Raises
        ------
        KeyError
            If the key is not found in memory or in the Azure Key Vault, a KeyError will be raised.
        """
        try:
            return keyvault_classic.get_secret(self._kv["id"], key).value
        except Exception as ex:
            print(self._kv)
            print(ex)
            if (
                str(ex).find("KeyVault") is not -1
                and str(ex).find("does not exist") is not -1
            ):
                try:
                    return self._values[key]
                except KeyError:
                    raise KeyError(
                        f"The key '{key}' not found in the config registry vault."
                    ) from ex
            raise ex

    def set_value(self, key: str, value: str) -> None:
        """
         Stores a value under a specified key.

        Parameters
        ----------
            key (str): The key under which to store the value.
            value (str): The value to store.

        Returns
        -------
            None
        """
        self._values[key] = value

        keyvault.Secret(
            resource_name=f"config-registry-{key}",
            secret_name=key,
            properties=keyvault.SecretPropertiesArgs(value=value),
            resource_group_name=self._kv["resource_group_name"],
            vault_name=self._kv["name"],
            opts=pulumi.ResourceOptions(delete_before_replace=True),
        )
