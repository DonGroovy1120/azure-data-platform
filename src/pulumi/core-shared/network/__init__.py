# Init the platform outputs
from project_config import platform_outputs

platform_outputs["network"] = {}

# Load sub-modules
from . import nat
from . import routing
from . import nsg
from . import vnet
from . import dns
