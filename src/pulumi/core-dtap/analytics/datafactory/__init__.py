# Init the platform outputs
from project_config import platform_outputs
from platform_shared import datafactory_runtime_config

platform_outputs["analytics"]["datafactory"] = {}

from . import orchestration
from . import orchestration_linked_services
from . import orchestration_datasets
from . import orchestration_pipelines
from . import user_datafactories

if datafactory_runtime_config["enabled"]:
    from . import integrated_integration_runtime
