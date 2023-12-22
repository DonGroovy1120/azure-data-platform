import importlib_resources
from os import environ, mkdir, path

examples_folder = environ["HOME"] + "/quantum_example"

# Check if we need to create the 'quantum_examples' folder
if not path.isdir(examples_folder):
    mkdir(examples_folder)

# Check each file in the examples folder
for example in importlib_resources.files("ingenii_azure_quantum.examples").iterdir():
    if not (example.name.endswith(".py") or example.name.endswith(".ipynb")):
        continue

    new_file = f"{examples_folder}/{example.name}"

    # Don't overwrite the file if it already exists
    if path.exists(new_file):
        continue

    with open(new_file, "w") as example_file:
        example_file.write(example.open().read())
