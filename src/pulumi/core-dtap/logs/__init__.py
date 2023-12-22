# Init the platform outputs
from project_config import platform_outputs

platform_outputs["logs"] = {}

# Load sub-modules
from .log_analytics_workspace import log_analytics_workspace
