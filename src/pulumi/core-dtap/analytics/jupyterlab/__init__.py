from platform_shared import jupyterlab_config

if jupyterlab_config["enabled"]:
    from . import deployment
