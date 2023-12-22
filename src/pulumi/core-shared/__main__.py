# All sub-components to load. Please note, this is not an execution order.
# Pulumi will load all files first and then will build the dependency graph.
import iam
import analytics
import automation
import kubernetes
import management
import network
import storage
import security
