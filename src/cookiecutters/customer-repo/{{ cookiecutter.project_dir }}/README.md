# {{ cookiecutter.project_dir.upper() }}

> IMPORTANT - The makefile is out of date. It will be updated ASAP. (#TODO)

## Overview

Ingenii Azure Data Platform deployment for customer '{{ cookiecutter.customer_code }}'.

## Usage

## Manual Operation
```shell
# Clone the data platform repository
make clone-repo

# Initialize the Pulumi projects
make init

# Preview
make preview STACK=<stack name>

# Apply
make apply STACK=<stack name>

# Destroy
make destroy STACK=<stack name>
```

### Update Platform Version
```shell
make set-platform-version VERSION=x.x.x

# Either commit and open a PR or manually apply the new version of the platform.
```