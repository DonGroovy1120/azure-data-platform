import json
import sys

args = sys.argv[1:]

file_path = args[0]
operation = args[1]
resource_type = args[2]


def load_file(path: str):
    with open(path, "r") as f:
        return json.load(f)


def print_urn(data: dict, operation: str, resource_type: str):
    _ = {
        print(f"--target {assignment['urn']}", end=" ")
        for assignment in data["steps"]
        if assignment["op"] == operation and resource_type in assignment["urn"]
    }


if __name__ == "__main__":
    data = load_file(file_path)
    print_urn(data, operation, resource_type)
