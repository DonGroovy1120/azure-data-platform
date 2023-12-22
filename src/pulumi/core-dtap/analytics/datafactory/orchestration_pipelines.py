from pulumi import ResourceOptions
from pulumi_azure_native import datafactory as adf

from analytics.datafactory.orchestration import datafactory, \
    datafactory_config, datafactory_name
from analytics.datafactory.orchestration_datasets import data_lake_folder
from analytics.datafactory.orchestration_linked_services import databricks_analytics_compute_linked_service, \
    databricks_engineering_compute_linked_service, datalake_linked_service
from management import resource_groups
from storage.datalake import datalake

def minutes_to_string(n_mins):
    """ Take the number of minutes and return a string Data Factory understands """
    hr = 60
    day = 24 * hr
    n_days, n_mins = n_mins // day, n_mins % day
    n_hrs, n_mins = n_mins // hr, n_mins % hr
    return f"{str(n_days)}.{str(n_hrs).zfill(2)}:{str(n_mins).zfill(2)}:00"

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> INGESTION PIPELINE AND TRIGGER
# ----------------------------------------------------------------------------------------------------------------------

ingestion_policy = datafactory_config.get("ingestion_policy", {})

databricks_file_ingestion_pipeline = adf.Pipeline(
    resource_name=f"{datafactory_name}-raw-databricks-file-ingestion",
    factory_name=datafactory.name,
    pipeline_name="Trigger ingest file notebook",
    description="Managed by Ingenii Data Platform",
    concurrency=1,
    parameters={
        "fileName": adf.ParameterSpecificationArgs(type="String"),
        "filePath": adf.ParameterSpecificationArgs(type="String"),
    },
    activities=[
        adf.DatabricksNotebookActivityArgs(
            name="Trigger ingest file notebook",
            notebook_path="/Shared/Ingenii Engineering/data_pipeline",
            type="DatabricksNotebook",
            linked_service_name=adf.LinkedServiceReferenceArgs(
                reference_name=databricks_engineering_compute_linked_service.name,
                type="LinkedServiceReference",
            ),
            depends_on=[],
            base_parameters={
                "file_path": {
                    "value": "@pipeline().parameters.filePath",
                    "type": "Expression",
                },
                "file_name": {
                    "value": "@pipeline().parameters.fileName",
                    "type": "Expression",
                },
                "increment": "0",
            },
            policy=adf.ActivityPolicyArgs(
                timeout=minutes_to_string(ingestion_policy.get("timeout", 20)),
                retry=ingestion_policy.get("retry", 0),
                retry_interval_in_seconds=ingestion_policy.get("retry_interval", 30),
                secure_output=False,
                secure_input=False,
            ),
            user_properties=[],
        )
    ],
    policy=adf.PipelinePolicyArgs(),
    annotations=["Created by Ingenii"],
    opts=ResourceOptions(ignore_changes=["annotations"]),
    resource_group_name=resource_groups["infra"].name,
)

databricks_file_ingestion_trigger = adf.Trigger(
    resource_name=f"{datafactory_name}-raw-databricks-file-ingestion",
    factory_name=datafactory.name,
    trigger_name="Raw file created",
    properties=adf.BlobEventsTriggerArgs(
        type="BlobEventsTrigger",
        scope=datalake.id,
        events=[adf.BlobEventTypes.MICROSOFT_STORAGE_BLOB_CREATED],
        blob_path_begins_with="/raw/blobs/",
        ignore_empty_blobs=True,
        pipelines=[
            adf.TriggerPipelineReferenceArgs(
                pipeline_reference=adf.PipelineReferenceArgs(
                    reference_name=databricks_file_ingestion_pipeline.name,
                    type="PipelineReference",
                ),
                parameters={
                    "fileName": "@trigger().outputs.body.fileName",
                    "filePath": "@trigger().outputs.body.folderPath",
                },
            )
        ],
        annotations=["Created by Ingenii"],
    ),
    opts=ResourceOptions(ignore_changes=["properties.annotations"]),
    resource_group_name=resource_groups["infra"].name,
)

# ----------------------------------------------------------------------------------------------------------------------
# DATA FACTORY -> WORKSPACE SYNCING
# ----------------------------------------------------------------------------------------------------------------------

containers = ["models", "snapshots", "source"]

default_policy = adf.ActivityPolicyArgs(
    timeout=minutes_to_string(1),
    retry=3,
    retry_interval_in_seconds=30,
    secure_output=False,
    secure_input=False,
)

def depends_successful(*activity_names):
    return [
        adf.ActivityDependencyArgs(
            activity=activity_name,
            dependency_conditions=[adf.DependencyCondition.SUCCEEDED]
        )
        for activity_name in activity_names
    ]

def per_container_activities(container_name):
    return [
        adf.GetMetadataActivityArgs(
            type="GetMetadata",
            name=f"Get {container_name} top-level folders",
            description=None,
            dataset=adf.DatasetReferenceArgs(
                reference_name=data_lake_folder.name,
                type="DatasetReference",
                parameters={"Container": container_name, "Folder": "/"}
            ),
            field_list=["childItems"],
            format_settings=adf.BinaryReadSettingsArgs(
                type="BinaryReadSettings"
            ),
            policy=default_policy,
            store_settings=adf.AzureBlobFSReadSettingsArgs(
                type="AzureBlobFSReadSettings",
                enable_partition_discovery=False
            )
        ),
        adf.ForEachActivityArgs(
            name=f"Find new {container_name} table folders",
            type="ForEach",
            depends_on=depends_successful(f"Get {container_name} top-level folders"),
            items=adf.ExpressionArgs(
                type="Expression",
                value=f"@activity('Get {container_name} top-level folders').output.childItems"
            ),
            activities=[
                adf.GetMetadataActivityArgs(
                    type="GetMetadata",
                    name=f"List {container_name} table folders",
                    description=None,
                    dataset=adf.DatasetReferenceArgs(
                        reference_name=data_lake_folder.name,
                        type="DatasetReference",
                        parameters={
                            "Container": container_name,
                            "Folder": adf.ExpressionArgs(
                                type="Expression",
                                value="@item().name"
                            )
                        }
                    ),
                    field_list=["childItems"],
                    format_settings=adf.BinaryReadSettingsArgs(
                        type="BinaryReadSettings"
                    ),
                    linked_service_name=datalake_linked_service.name,
                    policy=default_policy,
                    store_settings=adf.AzureBlobFSReadSettingsArgs(
                        type="AzureBlobFSReadSettings",
                        enable_partition_discovery=False,
                        modified_datetime_start=adf.ExpressionArgs(
                                type="Expression",
                                value="@addToTime(utcNow(), -3, 'Day')"
                        )
                    )
                ),
                adf.FilterActivityArgs(
                    type="Filter",
                    name=f"Find only {container_name} table folders",
                    description=None,
                    depends_on=depends_successful(f"List {container_name} table folders"),
                    items=adf.ExpressionArgs(
                        type="Expression",
                        value=f"@activity('List {container_name} table folders').output.childItems"
                    ),
                    condition=adf.ExpressionArgs(
                        type="Expression",
                        value="@equals(item().type, 'Folder')"
                    )
                ),
                adf.IfConditionActivityArgs(
                    type="IfCondition",
                    name=f"If new {container_name} tables",
                    description=None,
                    depends_on=depends_successful(f"Find only {container_name} table folders"),
                    expression=adf.ExpressionArgs(
                        type="Expression",
                        value=f"@greater(length(activity('Find only {container_name} table folders').output.Value), 0)"
                    ),
                    if_true_activities=[
                        adf.SetVariableActivityArgs(
                            type="SetVariable",
                            name=f"Set found {container_name} folders temp",
                            description=None,
                            variable_name=f"{container_name}TablesTemp",
                            value=adf.ExpressionArgs(
                                type="Expression",
                                value=f"@union(variables('{container_name}Tables'), array(concat('/mnt/{container_name}/', item().Name, '|', join(activity('Find only {container_name} table folders').output.Value, ';'))))"
                            )
                        ),
                        adf.SetVariableActivityArgs(
                            type="SetVariable",
                            name=f"Set found {container_name} folders",
                            description=None,
                            depends_on=depends_successful(f"Set found {container_name} folders temp"),
                            variable_name=f"{container_name}Tables",
                            value=adf.ExpressionArgs(
                                type="Expression",
                                value=f"@variables('{container_name}TablesTemp')"
                            )
                        ),
                    ]
                )
            ]
        ),
        adf.ForEachActivityArgs(
            name=f"For each new {container_name} schema",
            type="ForEach",
            depends_on=depends_successful(f"Find new {container_name} table folders"),
            is_sequential=True,
            items=adf.ExpressionArgs(
                type="Expression",
                value=f"@variables('{container_name}Tables')"
            ),
            activities=[
                adf.DatabricksNotebookActivityArgs(
                    name=f"Check {container_name} tables exist in Analytics workspace",
                    notebook_path="/Shared/Ingenii Engineering/check_tables_exist_adf",
                    type="DatabricksNotebook",
                    base_parameters={
                        "table_details": {
                            "value": "@item()",
                            "type": "Expression",
                        },
                    },
                    linked_service_name=adf.LinkedServiceReferenceArgs(
                        reference_name=databricks_analytics_compute_linked_service.name,
                        type="LinkedServiceReference",
                    ),
                    policy=adf.ActivityPolicyArgs(
                        timeout=minutes_to_string(20),
                        retry=0,
                        retry_interval_in_seconds=30,
                        secure_output=False,
                        secure_input=False,
                    ),
                )
            ]
        )
    ]

databricks_workspace_syncing_pipeline = adf.Pipeline(
    resource_name=f"{datafactory_name}-databricks-workspace-syncing",
    factory_name=datafactory.name,
    pipeline_name="Sync workspaces for new tables",
    description="Managed by Ingenii Data Platform",
    concurrency=1,
    activities=[
        per_container_activity
        for container in containers
        for per_container_activity in per_container_activities(container)
    ],
    variables={
        **{
            f"{container}Tables": adf.VariableSpecificationArgs(type=adf.VariableType.ARRAY)
            for container in containers
        },
        **{
            f"{container}TablesTemp": adf.VariableSpecificationArgs(type=adf.VariableType.ARRAY)
            for container in containers
        }
    },
    policy=adf.PipelinePolicyArgs(),
    annotations=["Created by Ingenii"],
    opts=ResourceOptions(ignore_changes=["annotations"]),
    resource_group_name=resource_groups["infra"].name,
)

databricks_sync_workspaces_trigger = adf.Trigger(
    resource_name=f"{datafactory_name}-databricks-workspace-syncing",
    factory_name=datafactory.name,
    trigger_name="Daily sync",
    properties=adf.ScheduleTriggerArgs(
        type="ScheduleTrigger",
        description=None,
        recurrence=adf.ScheduleTriggerRecurrenceArgs(
            frequency=adf.RecurrenceFrequency.DAY,
            interval=1,
            time_zone="UTC",
            start_time="2021-01-01T00:00:00Z",
            schedule=adf.RecurrenceScheduleArgs(hours=[0], minutes=[0])
        ),
        pipelines=[
            adf.TriggerPipelineReferenceArgs(
                pipeline_reference=adf.PipelineReferenceArgs(
                    reference_name=databricks_workspace_syncing_pipeline.name,
                    type="PipelineReference",
                ),
                parameters={},
            )
        ],
        annotations=["Created by Ingenii"],
    ),
    opts=ResourceOptions(ignore_changes=["properties.annotations"]),
    resource_group_name=resource_groups["infra"].name,
)