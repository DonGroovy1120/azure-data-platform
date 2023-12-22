from pulumi_azure_native import storage, keyvault, containerregistry

STORAGE_ACCOUNT_DEFAULT_FIREWALL = storage.NetworkRuleSetArgs(
    default_action=storage.DefaultAction.ALLOW,
    bypass=storage.Bypass.AZURE_SERVICES,
    ip_rules=None,
    virtual_network_rules=None,
)

KEY_VAULT_DEFAULT_FIREWALL = keyvault.NetworkRuleSetArgs(
    default_action=keyvault.NetworkRuleAction.ALLOW,
    bypass=keyvault.NetworkRuleBypassOptions.AZURE_SERVICES,
    ip_rules=None,
    virtual_network_rules=None,
)

CONTAINER_REGISTRY_DEFAULT_FIREWALL = containerregistry.NetworkRuleSetArgs(
    default_action=containerregistry.DefaultAction.ALLOW,
    ip_rules=[],
    virtual_network_rules=[],
)
