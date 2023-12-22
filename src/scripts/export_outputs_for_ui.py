"""
This script is used to parse and upload specific Pulumi outputs to an Azure
table that will be read and processed by the Ingenii UI.
"""
import argparse
import json
import subprocess
import yaml
from typing import Dict, Any

from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceNotFoundError

parser = argparse.ArgumentParser(
    description="Utility tool that helps to parse out certain output values from the Pulumi stack outputs and then push them to Azure table storage."
)

parser.add_argument(
    "--outputs-file",
    type=str,
    nargs="?",
    help="A JSON formatted file that contains the data platform pulumi outputs.",
    required=True,
)

parser.add_argument(
    "--env-name",
    type=str,
    nargs="?",
    help="The name of the platform environment. (dev, test, prod or shared)",
    required=True,
)

parser.add_argument(
    "--ui-project-name",
    type=str,
    nargs="?",
    help="The name of the platform environment. (dev, test, prod or shared)",
    required=False,
    default="iiui",
)

parser.add_argument(
    "--ui-stack-name",
    type=str,
    nargs="?",
    help="The name of the platform environment. (dev, test, prod or shared)",
    required=False,
    default="ingenii/test",
)

args = parser.parse_args()


def create_pulumi_project_file(project_name: str):
    pulumi_project_file = {"name": project_name, "runtime": {"name": "python"}}
    with open("Pulumi.yaml", "w") as outfile:
        yaml.dump(pulumi_project_file, outfile, default_flow_style=False)


def get_storage_connection_details(stack: str):
    ui_outputs = json.loads(
        subprocess.run(
            args=["pulumi", "stack", "output", "--stack", stack, "--json"],
            check=True,
            capture_output=True,
        ).stdout
    )

    connection_string = ";".join(
        [
            "DefaultEndpointsProtocol=https",
            f"AccountName={ui_outputs['general_storage_name']}",
            f"AccountKey={ui_outputs['client_services_urls_table_keys']['keys'][0]['value']}",
            "EndpointSuffix=core.windows.net",
        ]
    )

    return {
        "table_name": ui_outputs["client_services_urls_table_name"],
        "connection_string": connection_string,
    }


def get_table_client(conn_details: dict):
    table_service = TableServiceClient.from_connection_string(
        conn_details["connection_string"]
    )
    return table_service.get_table_client(conn_details["table_name"])


def parse_platform_outputs(file: str, env_name: str) -> Dict[Any, Any]:
    with open(file, "r") as f:
        outputs = json.loads(f.read())["root"]

    parsed = {
        "org_id": outputs["metadata"]["org_id"],
        "project_id": outputs["metadata"]["project_id"],
        "payload": {},
    }

    payload = parsed["payload"]

    if env_name in ["dev", "test", "prod"]:
        credentials_store = outputs["security"]["credentials_store"]
        databricks = outputs["analytics"]["databricks"]["workspaces"]
        datafactory = outputs["analytics"]["datafactory"]["user_factories"]
        datalake = outputs["storage"]["datalake"]
        dbt = outputs["analytics"]["dbt"]["documentation"]
        jupyterlab = outputs["analytics"].get("jupyterlab", {})

        payload[env_name] = {
            "credentials_store_name": credentials_store["key_vault_name"],
            "databricks_eng_workspace_url": databricks.get("engineering", {}).get(
                "url"
            ),
            "databricks_atc_workspace_url": databricks.get("analytics", {}).get("url"),
            "datafactory_data_studio_url": datafactory.get("data", {}).get("url"),
            "datalake_containers_view_url": datalake.get("containers_view_url"),
            "dbt_docs_url": dbt.get("url"),
            "jupyterlab_url": jupyterlab.get("url", {})
        }
    elif env_name == "shared":
        payload[env_name] = {
            "devops_project_url": outputs.get("devops", {})
            .get("project", {})
            .get("url")
        }

    return parsed


def save_platform_outputs(parsed_outputs: dict[str, Any], client: TableClient) -> None:

    new_entity = {
        "PartitionKey": str(parsed_outputs["org_id"]),
        "RowKey": str(parsed_outputs["project_id"]),
        "payload": parsed_outputs["payload"],
    }

    # If there is an existing record (row) in Azure Table storage,
    # let's pull it in and merge our outputs to it.
    try:
        existing_entity = client.get_entity(
            new_entity["PartitionKey"], new_entity["RowKey"]
        )

        existing_payload = json.loads(existing_entity["payload"])

        # Merge the new payload (urls) with whatever is already existing on the Azure table storage.
        # The new payload will overwrite existing data.
        new_entity["payload"] = existing_payload | new_entity["payload"]
    except ResourceNotFoundError:
        # The table row has not been found, but that's ok.
        # We'll upsert the payload which will result in the row being created.
        pass
    except KeyError:
        # A KeyError can be generated if the "payload" column is empty or does not exist for that row.
        # We can safely ignore the error and let the upsert function create a new row.
        pass

    new_entity["payload"] = json.dumps(new_entity["payload"])

    # Write to Azure table storage
    client.upsert_entity(new_entity)


if __name__ == "__main__":
    create_pulumi_project_file(project_name=args.ui_project_name)
    conn_details = get_storage_connection_details(stack=args.ui_stack_name)
    table_client = get_table_client(conn_details)
    outputs = parse_platform_outputs(args.outputs_file, str(args.env_name).lower())
    save_platform_outputs(outputs, table_client)
