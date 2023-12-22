from pulumi_azure_native import datafactory as adf

from analytics.datafactory.orchestration_linked_services import datalake_linked_service
from analytics.datafactory.orchestration import datafactory_name, \
    datafactory_resource_group

data_lake_folder = adf.Dataset(
    resource_name=f"{datafactory_name}-dataset-datalake-folder",
    dataset_name="DataLakeFolder",
    factory_name=datafactory_name,
    properties=adf.BinaryDatasetArgs(
        linked_service_name=adf.LinkedServiceReferenceArgs(
            reference_name=datalake_linked_service.name,
            type="LinkedServiceReference",
        ),
        location=adf.AzureBlobFSLocationArgs(
            type="AzureBlobFSLocation",
            file_system=adf.ExpressionArgs(
                type="Expression",
                value="@dataset().Container"
            ),
            folder_path=adf.ExpressionArgs(
                type="Expression",
                value="@dataset().Folder"
            ),
        ),
        parameters={
            "Container": adf.ParameterSpecificationArgs(type="String"),
            "Folder": adf.ParameterSpecificationArgs(type="String"),
        },
        type="AzureBlob",
    ),
    resource_group_name=datafactory_resource_group.name
)