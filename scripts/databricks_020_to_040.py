####
# The change of the Pulumi Databricks package from 0.2.0 to 0.4.0 involves
# breaking changes as the 'type' of resources is changed though their content
# is not. This script directly edits the Pulumi stack to bring it in line with
# version 0.4.0 without changing resources.
####
import json

def change(string):
    return string.replace("databricks:databricks/", "databricks:index/")

def change_list(string_list):
    return [change(sl) for sl in string_list]

def update_resource(resource):
    if "dependencies" in resource:
        resource["dependencies"] = change_list(resource["dependencies"])
        resource["dependencies"] = [
            dep.replace("databricksMount:DatabricksMount", "mount:Mount")
            for dep in resource["dependencies"]
        ]

    if not resource["type"].startswith("databricks"):
        return resource
    _, resource_type = resource["type"].split("/")

    resource["urn"] = change(resource["urn"])
    resource["type"] = change(resource["type"])
    resource["sequenceNumber"] = 1

    if resource_type in ("secret:Secret"):
        resource["propertyDependencies"]["scope"] = change_list(resource["propertyDependencies"]["scope"])

    if resource_type in ("databricksMount:DatabricksMount"):
        resource["propertyDependencies"]["clusterId"] = change_list(resource["propertyDependencies"]["clusterId"])
        if "abfs" in resource["propertyDependencies"]:
            resource["propertyDependencies"]["abfs"] = change_list(resource["propertyDependencies"]["abfs"])

        resource["urn"] = resource["urn"].replace("databricksMount:DatabricksMount", "mount:Mount")
        resource["type"] = resource["type"].replace("databricksMount:DatabricksMount", "mount:Mount")

    return resource

stack = "dev"

with open(f"pulumi.stack.core.dtap.{stack}.json") as file:
    stack_json = json.loads(file.read())

stack_json["deployment"]["resources"] = [
    update_resource(resource)
    for resource in stack_json["deployment"]["resources"]
]

with open("pulumi.stack.core.dtap.{stack}.json", "w") as file:
    json.dump(stack_json, file, indent=4)
