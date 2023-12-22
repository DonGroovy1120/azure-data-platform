# Init the platform outputs
from project_config import platform_outputs

platform_outputs["automation"] = {}

# Load sub-modules
from . import devops
from . import devops_deployment
