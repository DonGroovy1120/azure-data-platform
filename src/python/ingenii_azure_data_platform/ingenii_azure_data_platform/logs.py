from pulumi import Output
from pulumi.resource import ResourceOptions
from pulumi_azure import monitoring
from pulumi_azure_native import insights


def _log_diagnostic_settings(
    log_analytics_workspace_id,
    resource_id,
    resource_name,
    log_config_obj,
    metrics_config_obj,
):

    # Instead of None, empty dictionary
    log_config_obj = log_config_obj or {}
    metrics_config_obj = metrics_config_obj or {}

    # Determine if we need to find what all the categories are
    if (
        log_config_obj.get("categories") is None
        or metrics_config_obj.get("categories") is None
    ):
        all_categories = monitoring.get_diagnostic_categories(resource_id=resource_id)
    else:
        all_categories = None

    # Set the categories if specified, all if not
    # Also set the setting name
    setting_name_log, setting_name_metric = "All", "All"
    if log_config_obj.get("categories") is None:
        log_categories = all_categories.logs
    else:
        log_categories = log_config_obj.get("categories")
        setting_name_log = "Configured"
    if metrics_config_obj.get("categories") is None:
        metric_categories = all_categories.metrics
    else:
        metric_categories = metrics_config_obj.get("categories")
        setting_name_metric = "Configured"

    # Change the categories from strings to objects
    if log_config_obj.get("enabled", True):
        log_objects = [
            insights.LogSettingsArgs(
                category=log,
                enabled=True,
                retention_policy=insights.RetentionPolicyArgs(
                    days=0,
                    enabled=False,
                ),
            )
            for log in sorted(log_categories)
        ]
    else:
        log_objects = []

    # Change the categories from strings to objects
    if metrics_config_obj.get("enabled", True):
        metric_objects = [
            insights.MetricSettingsArgs(
                category=metric,
                enabled=True,
                retention_policy=insights.RetentionPolicyArgs(
                    days=0,
                    enabled=False,
                ),
            )
            for metric in sorted(metric_categories)
        ]
    else:
        metric_objects = []

    insights.DiagnosticSetting(
        f"{resource_name}-diagnostic-setting",
        name=f"{setting_name_log} Logs, {setting_name_metric} Metrics",
        workspace_id=log_analytics_workspace_id,
        log_analytics_destination_type="Dedicated",
        resource_uri=resource_id,
        logs=log_objects,
        metrics=metric_objects,
        opts=ResourceOptions(ignore_changes=["log_analytics_destination_type"]),
    )


def log_diagnostic_settings(
    platform_config,
    log_analytics_workspace_id,
    resource_type,
    resource_id,
    resource_name,
    logs_config={},
    metrics_config={},
):

    # If any of these three are set, we will add the diagnostics
    # If the resource type is disabled, then the individual object must be
    # explicitly enabled
    if not any(
        [
            platform_config["logs"]["resource_types"].get(resource_type, True),
            logs_config.get("enabled", False),
            metrics_config.get("enabled", False),
        ]
    ):
        return

    # If logs and metrics both disabled, don't go any further
    if not logs_config.get("enabled", True) and not metrics_config.get("enabled", True):
        return

    if isinstance(resource_id, Output):
        resource_id.apply(lambda r_id: 
            _log_diagnostic_settings(
                log_analytics_workspace_id, r_id, resource_name,
                logs_config, metrics_config)
        )
    else:
        _log_diagnostic_settings(
            log_analytics_workspace_id, resource_id, resource_name,
            logs_config, metrics_config)


def log_network_interfaces(
    platform_config,
    log_analytics_workspace_id,
    resource_name,
    network_interfaces,
    logs_config={},
    metrics_config={},
):
    network_interfaces.apply(
        lambda network_interfaces: [
            log_diagnostic_settings(
                platform_config,
                log_analytics_workspace_id,
                "Microsoft.Network/networkInterfaces",
                network_interface.id,
                f"{resource_name}-network_interface-{str(idx)}",
                logs_config=logs_config,
                metrics_config=metrics_config,
            )
            for idx, network_interface in enumerate(network_interfaces)
        ]
    )
