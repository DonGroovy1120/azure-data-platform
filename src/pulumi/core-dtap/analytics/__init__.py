# Init the platform outputs
from project_config import platform_outputs

platform_outputs["analytics"] = {}

from . import datafactory
from . import databricks
from . import dbt
from . import jupyterlab
from . import kubernetes
