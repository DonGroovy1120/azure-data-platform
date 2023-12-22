# Init the platform outputs
from project_config import platform_outputs

platform_outputs["management"] = {}

# Load sub-modules
from . import resource_providers
from .user_groups import user_groups
from .resource_groups import resource_groups, outputs as resource_group_outputs
