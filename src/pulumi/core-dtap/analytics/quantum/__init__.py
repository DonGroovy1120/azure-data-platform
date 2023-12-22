from project_config import quantum_workspace_config

if quantum_workspace_config["enabled"]:
    from . import workspace

