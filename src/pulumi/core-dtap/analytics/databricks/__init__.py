# Init the platform outputs
from project_config import platform_outputs

platform_outputs["analytics"]["databricks"] = {"workspaces": {}}

from . import analytics_notebooks
from . import analytics_workspace
from . import engineering_notebooks
from . import engineering_workspace
