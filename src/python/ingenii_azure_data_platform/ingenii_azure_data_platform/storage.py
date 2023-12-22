def get_container_registry_resource_id(
    subscription_id: str, resource_group_name: str, registry_name: str
):
    return f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.ContainerRegistry/registries/{registry_name}"
