import pulumi_azure_native as azure_native
import pulumi_random as random

from pulumi import ResourceOptions

from ingenii_azure_data_platform.contracts.packages import PackageInputArgs


def init(args: PackageInputArgs) -> None:
    STACK_SHORT_NAME = args.platform_config.stack_short_name
    REGION = args.platform_config.region
    PREFIX = args.platform_config.prefix
    UNIQUE_ID = args.platform_config.unique_id

    # Package Config Inputs
    _server_name = args.package_config.get("server_name", "results")
    _admin_username = args.package_config.get("admin_username", "dbadmin")
    _database_name = args.package_config.get("database_name", "results")
    _database_sku_capacity = args.package_config.get("database_sku_capacity", 1)
    _database_sku_family = args.package_config.get("database_sku_family", "Gen5")
    _database_sku_name = args.package_config.get("database_sku_name", "GP_S_Gen5_1")
    _enable_public_access = args.package_config.get("enable_public_access", True)
    _resource_group_name = args.package_config.get("resource_group_name", "data")
    _minimal_tls_version = args.package_config.get("minimal_tls_version", "1.2")

    server_name = f"{PREFIX}-{STACK_SHORT_NAME}-{REGION.short_name}-sql-{_server_name}-{UNIQUE_ID}"

    resource_group_name = args.dtap_outputs.get(
        "management", "resource_groups", _resource_group_name, "name"
    )

    admin_password = random.RandomPassword(
        f"{args.namespace}-{server_name}", length=16, special=True
    ).result

    # Save admin creds in the credentials store
    azure_native.keyvault.Secret(
        resource_name=f"{args.namespace}-{server_name}-admin-creds",
        secret_name=f"{server_name}-admin-creds",
        properties=azure_native.keyvault.SecretPropertiesArgs(
            value=admin_password.apply(
                lambda password: f"username: {_admin_username}, password: {password}"
            )
        ),
        resource_group_name=args.dtap_outputs.get(
            "management", "resource_groups", "security", "name"
        ),
        vault_name=args.dtap_outputs.get(
            "security", "credentials_store", "key_vault_name"
        ),
    )

    # SQL server object
    server = azure_native.sql.Server(
        resource_name=f"{args.namespace}-{server_name}",
        server_name=server_name,
        administrator_login=_admin_username,
        administrator_login_password=admin_password,
        location=REGION.long_name,
        resource_group_name=resource_group_name,
        public_network_access=azure_native.sql.ServerPublicNetworkAccess.ENABLED
        if _enable_public_access
        else azure_native.sql.ServerPublicNetworkAccess.DISABLED,
        minimal_tls_version=_minimal_tls_version,
        opts=ResourceOptions(ignore_changes=["administrators"])
    )

    # Database
    database = azure_native.sql.Database(
        resource_name=f"{args.namespace}-{_database_name}",
        database_name=_database_name,
        location=REGION.long_name,
        resource_group_name=resource_group_name,
        server_name=server.name,
        sku=azure_native.sql.SkuArgs(
            capacity=_database_sku_capacity,
            family=_database_sku_family,
            name=_database_sku_name,
        ),
    )
