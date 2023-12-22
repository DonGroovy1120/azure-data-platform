from typing import Union

from azure.core.credentials import AccessToken
from azure.mgmt.authorization import AuthorizationManagementClient
from pulumi import Output, ResourceOptions
from pulumi_azure_native import authorization


class AzureAccessToken(AccessToken):
    def get_token(self, *args, **kwargs):
        return self


class RoleInfo:

    _cache = {}

    def __init__(self):
        config = authorization.get_client_config()
        client_token = authorization.get_client_token()
        self._client = AuthorizationManagementClient(
            AzureAccessToken(token=client_token.token, expires_on=-1),
            config.subscription_id,
        )

    def get_role_id_by_name(self, name: str, scope: str = "") -> str:
        if name in self._cache:
            return self._cache[name]

        result = self._client.role_definitions.list(
            scope, filter=f"roleName eq '{name}'"
        )
        err_msg = f"role '{name}' not found at scope '{scope}'"
        try:
            role = result.next()
        except StopIteration:
            raise Exception(err_msg)

        if role is None:
            raise Exception(err_msg)

        self._cache[name] = role.id
        self._cache[role.id] = name

        return role.id

    def get_role_name_by_id(self, id: str, scope: str = "") -> str:
        if id in self._cache:
            return self._cache[id]

        result = self._client.role_definitions.list(scope, filter=f"name eq '{id}'")

        err_msg = f"role id '{id}' not found at scope '{scope}'"
        try:
            role = result.next()
        except StopIteration:
            raise Exception(err_msg)

        if role is None:
            raise Exception(err_msg)

        self._cache[role.role_name] = role.id
        self._cache[role.id] = role.role_name

        return role.role_name


role_info = RoleInfo()


class RoleAssignment(authorization.RoleAssignment):
    """
    #TODO
    """

    def __init__(
        self,
        principal_name: str,
        principal_type: str,
        principal_id: Union[str, Output[str]],
        scope: Union[str, Output[str]],
        scope_description: str,
        role_name: Union[str, None] = None,
        role_id: Union[str, Output[str]] = None,
        opts: ResourceOptions = None,
    ) -> None:

        if role_name is None and role_id is None:
            raise ValueError("Either 'role_name' or 'role_id' have to be provided...")

        if role_name is None:
            role_name = role_info.get_role_name_by_id(role_id)

        resource_name = (
            "-".join(
                [
                    f"{title}-[{name}]"
                    for title, name in (
                        ("principal", principal_name),
                        ("type", principal_type),
                        ("role", role_name),
                        ("to", scope_description),
                    )
                ]
            )
            .lower()
            .replace(" ", "-")
        )

        super().__init__(
            resource_name=resource_name,
            principal_id=principal_id,
            scope=scope,
            role_definition_id=role_id or role_info.get_role_id_by_name(role_name),
            principal_type=principal_type,
            opts=ResourceOptions.merge(
                ResourceOptions(delete_before_replace=True), opts
            ),
        )


class UserRoleAssignment(RoleAssignment):
    """
    #TODO
    """

    def __init__(
        self,
        scope: Union[str, Output[str]],
        scope_description: str,
        principal_name: str,
        principal_id: Union[str, Output[str]],
        role_name: Union[str, None] = None,
        role_id: Union[str, Output[str]] = None,
        opts: ResourceOptions = None,
    ) -> None:
        super().__init__(
            principal_name=principal_name,
            principal_id=principal_id,
            principal_type="User",
            role_id=role_id,
            role_name=role_name,
            scope=scope,
            scope_description=scope_description,
            opts=opts,
        )


class GroupRoleAssignment(RoleAssignment):
    """
    #TODO
    """

    def __init__(
        self,
        principal_name: str,
        principal_id: Union[str, Output[str]],
        scope: Union[str, Output[str]],
        scope_description: str,
        role_name: Union[str, None] = None,
        role_id: Union[str, Output[str]] = None,
        opts: ResourceOptions = None,
    ) -> None:
        super().__init__(
            principal_id=principal_id,
            principal_name=principal_name,
            principal_type="Group",
            role_id=role_id,
            role_name=role_name,
            scope=scope,
            scope_description=scope_description,
            opts=opts,
        )


class ServicePrincipalRoleAssignment(RoleAssignment):
    """
    #TODO
    """

    def __init__(
        self,
        principal_name: str,
        principal_id: Union[str, Output[str]],
        scope: Union[str, Output[str]],
        scope_description: str,
        role_name: Union[str, None] = None,
        role_id: Union[str, Output[str]] = None,
        opts: ResourceOptions = None,
    ) -> None:
        super().__init__(
            principal_name=principal_name,
            principal_id=principal_id,
            principal_type="ServicePrincipal",
            role_id=role_id,
            role_name=role_name,
            scope=scope,
            scope_description=scope_description,
            opts=opts,
        )


class UserAssignedIdentityRoleAssignment(RoleAssignment):
    """
    #TODO
    """

    def __init__(
        self,
        principal_name: str,
        principal_id: Union[str, Output[str]],
        scope: Union[str, Output[str]],
        scope_description: str,
        role_name: Union[str, None] = None,
        role_id: Union[str, Output[str]] = None,
        opts: ResourceOptions = None,
    ) -> None:
        super().__init__(
            principal_name=principal_name,
            principal_id=principal_id,
            principal_type="ServicePrincipal",
            role_id=role_id,
            role_name=role_name,
            scope=scope,
            scope_description=scope_description,
            opts=opts,
        )
