SHELL := /bin/bash

PULUMI_PARALLELISM  := 2

PROJECT_ROOT    := $(realpath .)
SOURCE_DIR      := /platform/src
CONFIGS_DIR     := ${PROJECT_ROOT}/configs
STATES_DIR      := ${PROJECT_ROOT}/states
VENV_DIR        := ${PROJECT_ROOT}/venv
RUNTIME_DIR     := ${PROJECT_ROOT}/runtime

PULUMI_SOURCE_DIR               := ${SOURCE_DIR}/pulumi
PULUMI_CORE_SHARED_SRC_DIR      := ${PULUMI_SOURCE_DIR}/core-shared
PULUMI_CORE_DTAP_SRC_DIR        := ${PULUMI_SOURCE_DIR}/core-dtap
PULUMI_CORE_EXTENSIONS_SRC_DIR  := ${PULUMI_SOURCE_DIR}/core-extensions
PULUMI_PRJ_CONF_TEMPLATES_DIR   := ${PULUMI_SOURCE_DIR}/templates/pulumi-project-conf

PLATFORM_CONF_SCHEMA_FILE           := ${SOURCE_DIR}/platform-config/schema.yml
PLATFORM_CONF_DEFAULTS_FILE         := ${SOURCE_DIR}/platform-config/defaults.yml
PLATFORM_CONF_SHARED_DEFAULTS_FILE  := ${SOURCE_DIR}/platform-config/defaults.shared.yml

PLATFORM_CONF_METADATA_FILE 		:= ${CONFIGS_DIR}/metadata.yml

UI_PULUMI_STACK_NAME := "ingenii/test"

# This variable is intentionally left empty.
EXTRA_ARGS :=

#####################################################################################################################
# Imports
#####################################################################################################################
-include .env	# Optional way to set credentials
include platform.cfg	# Import platform config

#####################################################################################################################
# Functions and Helpers
#####################################################################################################################
define pulumi_init
	pulumi --cwd $(1) stack select $(2) --create --color always --non-interactive $(3)
endef

define pulumi_preview
	ADP_CONFIG_SCHEMA_FILE_PATH=${PLATFORM_CONF_SCHEMA_FILE} \
	ADP_DEFAULT_CONFIG_FILE_PATH=$(4) \
	ADP_CUSTOM_CONFIGS_FILE_PATH=$(5) \
	ADP_METADATA_FILE_PATH=${PLATFORM_CONF_METADATA_FILE} \
	pulumi --cwd $(1) preview --stack $(2) --color always --diff --non-interactive $(3)
endef

define pulumi_refresh
	ADP_CONFIG_SCHEMA_FILE_PATH=${PLATFORM_CONF_SCHEMA_FILE} \
	ADP_DEFAULT_CONFIG_FILE_PATH=$(4) \
	ADP_CUSTOM_CONFIGS_FILE_PATH=$(5) \
	ADP_METADATA_FILE_PATH=${PLATFORM_CONF_METADATA_FILE} \
	pulumi --cwd $(1) refresh --stack $(2) --color always --diff --skip-preview --non-interactive --yes $(3)
endef

define pulumi_apply
	ADP_CONFIG_SCHEMA_FILE_PATH=${PLATFORM_CONF_SCHEMA_FILE} \
	ADP_DEFAULT_CONFIG_FILE_PATH=$(4) \
	ADP_CUSTOM_CONFIGS_FILE_PATH=$(5) \
	ADP_METADATA_FILE_PATH=${PLATFORM_CONF_METADATA_FILE} \
	pulumi --cwd $(1) up --stack $(2) --parallel ${PULUMI_PARALLELISM} --color always --diff --skip-preview --non-interactive --yes $(3)
endef

define pulumi_export_stack
	pulumi --cwd $(1) stack export --stack $(2) --file $(4) $(3) 
endef

define pulumi_import_stack
	pulumi --cwd $(1) stack import --stack $(2) --file $(4) $(3) 
endef

define pulumi_export_stack_outputs
	pulumi --cwd $(1) stack output --stack $(2) --json > $(4) $(3) 
endef

define pulumi_destroy_role_assignments
	$(shell ADP_CONFIG_SCHEMA_FILE_PATH=${PLATFORM_CONF_SCHEMA_FILE} \
	ADP_DEFAULT_CONFIG_FILE_PATH=$(4) \
	ADP_CUSTOM_CONFIGS_FILE_PATH=$(5) \
	ADP_METADATA_FILE_PATH=${PLATFORM_CONF_METADATA_FILE} \
	pulumi --cwd $(1) preview --stack $(2) --json --non-interactive $(3) > output.json)
	$(shell python scripts/filter_resources.py output.json delete "azure-native:authorization:RoleAssignment" > output.filtered)
	pulumi --cwd $(1) destroy --stack $(2) $(shell cat output.filtered)
	$(shell rm -rf output.json output.filtered)
endef

define upload_outputs_to_azure_table_storage
	@python ${SOURCE_DIR}/scripts/export_outputs_for_ui.py --outputs-file "$(1)" --env-name $(2) --ui-stack-name ${UI_PULUMI_STACK_NAME}
endef

_check-for-stack-var:
	@if test -z "${STACK}"; then echo "STACK variable not set. Try 'make <your command> STACK=<stack-name>'"; exit 1; fi

_check-for-output-file-var:
	@if test -z "${OUTPUT_FILE}"; then echo "OUTPUT_FILE variable not set. Try 'make <your command> OUTPUT_FILE=<file name>'"; exit 1; fi

_check-for-cust-code-var:
	@if test -z "${CUSTOMER_CODE}"; then echo "CUSTOMER_CODE variable not set. Check if platform.cfg exist in the current directory."; exit 1; fi

_TITLE := "\033[32m[%s]\033[0m %s\n" # Green text for "printf"
_ERROR := "\033[31m[%s]\033[0m %s\n" # Red text for "printf"
_confirm:
	@REPLY="" ; \
	read -p "⚠ Are you sure? [y/n] > " -r ; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
		printf $(_ERROR) "KO" "Stopping" ; \
		exit 1 ; \
	else \
		printf $(_TITLE) "OK" "Continuing" ; \
		exit 0; \
	fi

#####################################################################################################################
# Post-Deployment
#####################################################################################################################

az_login:
	@$(info Logging into Azure . . .)
	@az login --service-principal -t ${ARM_TENANT_ID} -u ${ARM_CLIENT_ID} -p ${ARM_CLIENT_SECRET} > /dev/null

define enable_trigger
	@$(info Enabling Data Factory triggers . . .)
	@$(eval DATAFACTORY_ID=$(shell pulumi stack output --cwd $(1) --stack $(2) --json $(3) | jq '.root.analytics.datafactory.factories.orchestration.id' | sed 's/"//g'))
	@az datafactory trigger start --ids "${DATAFACTORY_ID}/triggers/Raw file created"
	@az datafactory trigger start --ids "${DATAFACTORY_ID}/triggers/Daily sync"
endef

#####################################################################################################################
# Stacks
#####################################################################################################################

# Files
CORE_SHARED_STACK := ${CUSTOMER_CODE}.shared
CORE_SHARED_EXTENSIONS_STACK := ${CUSTOMER_CODE}.extensions.shared
DTAP_CORE_STACK := ${CUSTOMER_CODE}.${STACK}
DTAP_EXTENSIONS_STACK := ${CUSTOMER_CODE}.extensions.${STACK}

CORE_SHARED_STACK_OUTPUT_FILE := ${PROJECT_ROOT}/pulumi.stack.core.shared.json
CORE_SHARED_EXTENSIONS_STACK_OUTPUT_FILE := ${PROJECT_ROOT}/pulumi.stack.core.shared.extensions.json
CORE_DTAP_STACK_OUTPUT_FILE := ${PROJECT_ROOT}/pulumi.stack.core.dtap.${STACK}.json
CORE_DTAP_EXTENSIONS_STACK_OUTPUT_FILE := ${PROJECT_ROOT}/pulumi.stack.core.dtap.extensions.${STACK}.json

SHARED_OUTPUTS_FILE_PATH := ${PROJECT_ROOT}/shared_outputs.json
DTAP_OUTPUTS_FILE_PATH := ${PROJECT_ROOT}/${STACK}_outputs.json

# Shared Stack
init-core-shared: _check-for-cust-code-var
	@cp ${PULUMI_PRJ_CONF_TEMPLATES_DIR}/core-shared/Pulumi.yaml	${PULUMI_SOURCE_DIR}/core-shared/Pulumi.yaml
	@sed -i 's|ingenii-|${CUSTOMER_CODE}-|g'		${PULUMI_SOURCE_DIR}/core-shared/Pulumi.yaml
	@cp ${STATES_DIR}/shared.yaml	${PULUMI_SOURCE_DIR}/core-shared/Pulumi.${CORE_SHARED_STACK}.yaml
	@$(call pulumi_init,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS})

preview-core-shared:
ifdef SHARED_ARM_CLIENT_ID
	@ARM_CLIENT_ID=${SHARED_ARM_CLIENT_ID}  \
	&& ARM_CLIENT_SECRET=${SHARED_ARM_CLIENT_SECRET} \
	&& ARM_SUBSCRIPTION_ID=${SHARED_ARM_SUBSCRIPTION_ID} \
	&& ARM_TENANT_ID=${SHARED_ARM_TENANT_ID} \
	&& $(call pulumi_preview,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
else
	@$(call pulumi_preview,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
endif

refresh-core-shared:
ifdef SHARED_ARM_CLIENT_ID
	@ARM_CLIENT_ID=${SHARED_ARM_CLIENT_ID}  \
	&& ARM_CLIENT_SECRET=${SHARED_ARM_CLIENT_SECRET} \
	&& ARM_SUBSCRIPTION_ID=${SHARED_ARM_SUBSCRIPTION_ID} \
	&& ARM_TENANT_ID=${SHARED_ARM_TENANT_ID} \
	&& $(call pulumi_refresh,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
else
	$(call pulumi_refresh,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
endif

apply-core-shared:
ifdef SHARED_ARM_CLIENT_ID
	@ARM_CLIENT_ID=${SHARED_ARM_CLIENT_ID}  \
	&& ARM_CLIENT_SECRET=${SHARED_ARM_CLIENT_SECRET} \
	&& ARM_SUBSCRIPTION_ID=${SHARED_ARM_SUBSCRIPTION_ID} \
	&& ARM_TENANT_ID=${SHARED_ARM_TENANT_ID} \
	&& $(call pulumi_apply,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
else
	$(call pulumi_apply,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
endif

export-stack-core-shared: 
	@$(info Exporting stack to ${CORE_SHARED_STACK_OUTPUT_FILE})
	@$(call pulumi_export_stack,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${CORE_SHARED_STACK_OUTPUT_FILE})

import-stack-core-shared: 
	@$(info Importing stack file ${CORE_SHARED_STACK_OUTPUT_FILE})
	@$(call pulumi_import_stack,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${CORE_SHARED_STACK_OUTPUT_FILE})

destroy-tainted-role-assignments-core-shared:
	@$(info Deleting all role assignments for ${CORE_SHARED_STACK})
	@$(call pulumi_destroy_role_assignments,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)

export-stack-outputs-core-shared:
	@$(info Exporting stack outputs to ${SHARED_OUTPUTS_FILE_PATH})
	@$(call pulumi_export_stack_outputs,${PULUMI_CORE_SHARED_SRC_DIR},${CORE_SHARED_STACK},${EXTRA_ARGS},${SHARED_OUTPUTS_FILE_PATH})

upload-stack-outputs-core-shared:
	@$(info Uploading stack outputs to Azure Table...)
	@$(call upload_outputs_to_azure_table_storage,${SHARED_OUTPUTS_FILE_PATH}, "shared")

# Shared Stack Extensions
init-core-shared-extensions: _check-for-cust-code-var
	@cp ${PULUMI_PRJ_CONF_TEMPLATES_DIR}/core-extensions/Pulumi.yaml ${PULUMI_SOURCE_DIR}/core-extensions/Pulumi.yaml
	@sed -i 's|ingenii-|${CUSTOMER_CODE}-|g' ${PULUMI_SOURCE_DIR}/core-extensions/Pulumi.yaml
	@cp ${STATES_DIR}/extensions.shared.yaml	${PULUMI_SOURCE_DIR}/core-extensions/Pulumi.${CORE_SHARED_EXTENSIONS_STACK}.yaml
	@$(call pulumi_init,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS})

preview-core-shared-extensions:
ifdef SHARED_ARM_CLIENT_ID
	@ARM_CLIENT_ID=${SHARED_ARM_CLIENT_ID}  \
	&& ARM_CLIENT_SECRET=${SHARED_ARM_CLIENT_SECRET} \
	&& ARM_SUBSCRIPTION_ID=${SHARED_ARM_SUBSCRIPTION_ID} \
	&& ARM_TENANT_ID=${SHARED_ARM_TENANT_ID} \
	&& $(call pulumi_preview,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
else
	@$(call pulumi_preview,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
endif
	

refresh-core-shared-extensions:
ifdef SHARED_ARM_CLIENT_ID
	@ARM_CLIENT_ID=${SHARED_ARM_CLIENT_ID}  \
	&& ARM_CLIENT_SECRET=${SHARED_ARM_CLIENT_SECRET} \
	&& ARM_SUBSCRIPTION_ID=${SHARED_ARM_SUBSCRIPTION_ID} \
	&& ARM_TENANT_ID=${SHARED_ARM_TENANT_ID} \
	&& $(call pulumi_refresh,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
else
	@$(call pulumi_refresh,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
endif
	

apply-core-shared-extensions:
ifdef SHARED_ARM_CLIENT_ID
	@ARM_CLIENT_ID=${SHARED_ARM_CLIENT_ID}  \
	&& ARM_CLIENT_SECRET=${SHARED_ARM_CLIENT_SECRET} \
	&& ARM_SUBSCRIPTION_ID=${SHARED_ARM_SUBSCRIPTION_ID} \
	&& ARM_TENANT_ID=${SHARED_ARM_TENANT_ID} \
	&& $(call pulumi_apply,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
else
	@$(call pulumi_apply,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)
endif
	

export-stack-core-shared-extensions: 
	@$(info Exporting stack to ${CORE_SHARED_EXTENSIONS_STACK_OUTPUT_FILE})
	@$(call pulumi_export_stack,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${CORE_SHARED_EXTENSIONS_STACK_OUTPUT_FILE})

import-stack-core-shared-extensions: 
	@$(info Importing stack file ${CORE_SHARED_EXTENSIONS_STACK_OUTPUT_FILE})
	@$(call pulumi_import_stack,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${CORE_SHARED_EXTENSIONS_STACK_OUTPUT_FILE})

destroy-tainted-role-assignments-core-shared-extensions: _check-for-stack-var
	@$(info Deleting all role assignments for ${CORE_SHARED_EXTENSIONS_STACK})
	@$(call pulumi_destroy_role_assignments,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_SHARED_DEFAULTS_FILE},${CONFIGS_DIR}/shared.yml)

export-stack-outputs-core-shared-extensions: _check-for-output-file-var
	@$(info Exporting stack outputs to ${PROJECT_ROOT}/${OUTPUT_FILE})
	@$(call pulumi_export_stack_outputs,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${CORE_SHARED_EXTENSIONS_STACK},${EXTRA_ARGS},${PROJECT_ROOT}/${OUTPUT_FILE})

# DTAP Stack
init-core-dtap: _check-for-stack-var _check-for-cust-code-var
	@cp ${PULUMI_PRJ_CONF_TEMPLATES_DIR}/core-dtap/Pulumi.yaml ${PULUMI_SOURCE_DIR}/core-dtap/Pulumi.yaml
	@sed -i 's|ingenii-|${CUSTOMER_CODE}-|g' ${PULUMI_SOURCE_DIR}/core-dtap/Pulumi.yaml
	@cp ${STATES_DIR}/${STACK}.yaml	${PULUMI_SOURCE_DIR}/core-dtap/Pulumi.${DTAP_CORE_STACK}.yaml
	@$(call pulumi_init,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS})

preview-core-dtap: _check-for-stack-var
	@$(call pulumi_preview,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS},${PLATFORM_CONF_DEFAULTS_FILE},${CONFIGS_DIR}/${STACK}.yml)

refresh-core-dtap: _check-for-stack-var
	@$(call pulumi_refresh,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS},${PLATFORM_CONF_DEFAULTS_FILE},${CONFIGS_DIR}/${STACK}.yml)

apply-core-dtap: _check-for-stack-var
	@$(call pulumi_apply,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS},${PLATFORM_CONF_DEFAULTS_FILE},${CONFIGS_DIR}/${STACK}.yml)

post-deploy-core-dtap: az_login _check-for-stack-var
	@$(call enable_trigger,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS})

export-stack-core-dtap: _check-for-stack-var
	@$(info Exporting stack to ${CORE_DTAP_STACK_OUTPUT_FILE})
	@$(call pulumi_export_stack,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS},${CORE_DTAP_STACK_OUTPUT_FILE})

import-stack-core-dtap: _check-for-stack-var
	@$(info Importing stack file ${CORE_DTAP_STACK_OUTPUT_FILE})
	@$(call pulumi_import_stack,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS},${CORE_DTAP_STACK_OUTPUT_FILE})

destroy-tainted-role-assignments-core-dtap: _check-for-stack-var
	@$(info Deleting all role assignments for ${DTAP_CORE_STACK})
	@$(call pulumi_destroy_role_assignments,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS},${PLATFORM_CONF_DEFAULTS_FILE},${CONFIGS_DIR}/${STACK}.yml)

export-stack-outputs-core-dtap:
	@$(info Exporting stack outputs to ${DTAP_OUTPUTS_FILE_PATH})
	@$(call pulumi_export_stack_outputs,${PULUMI_CORE_DTAP_SRC_DIR},${DTAP_CORE_STACK},${EXTRA_ARGS},${DTAP_OUTPUTS_FILE_PATH})

upload-stack-outputs-core-dtap:
	@$(info Uploading stack outputs to Azure Table...)
	@$(call upload_outputs_to_azure_table_storage,${DTAP_OUTPUTS_FILE_PATH}, "${STACK}")

# DTAP Stack Extensions
init-core-dtap-extensions: _check-for-stack-var _check-for-cust-code-var
	@cp ${PULUMI_PRJ_CONF_TEMPLATES_DIR}/core-extensions/Pulumi.yaml ${PULUMI_SOURCE_DIR}/core-extensions/
	@sed -i 's|ingenii-|${CUSTOMER_CODE}-|g' ${PULUMI_SOURCE_DIR}/core-extensions/Pulumi.yaml
	@cp ${STATES_DIR}/extensions.${STACK}.yaml	${PULUMI_SOURCE_DIR}/core-dtap/Pulumi.${DTAP_EXTENSIONS_STACK}.yaml
	@$(call pulumi_init,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${DTAP_EXTENSIONS_STACK},${EXTRA_ARGS})

preview-core-dtap-extensions: _check-for-stack-var
	@$(call pulumi_preview,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${DTAP_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_DEFAULTS_FILE},${CONFIGS_DIR}/${STACK}.yml)

refresh-core-dtap-extensions: _check-for-stack-var
	@$(call pulumi_refresh,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${DTAP_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_DEFAULTS_FILE},${CONFIGS_DIR}/${STACK}.yml)

apply-core-dtap-extensions: _check-for-stack-var
	@$(call pulumi_apply,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${DTAP_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_DEFAULTS_FILE},${CONFIGS_DIR}/${STACK}.yml)

export-stack-core-dtap-extensions: _check-for-stack-var
	@$(info Exporting stack to ${CORE_DTAP_EXTENSIONS_STACK_OUTPUT_FILE})
	@$(call pulumi_export_stack,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${DTAP_EXTENSIONS_STACK},${EXTRA_ARGS},${CORE_DTAP_EXTENSIONS_STACK_OUTPUT_FILE})

import-stack-core-dtap-extensions: _check-for-stack-var
	@$(info Importing stack file ${CORE_DTAP_EXTENSIONS_STACK_OUTPUT_FILE})
	@$(call pulumi_import_stack,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${DTAP_EXTENSIONS_STACK},${EXTRA_ARGS},${CORE_DTAP_EXTENSIONS_STACK_OUTPUT_FILE})

destroy-tainted-role-assignments-core-dtap-extensions: _check-for-stack-var
	@$(info Deleting all role assignments for ${DTAP_EXTENSIONS_STACK})
	@$(call pulumi_destroy_role_assignments,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${DTAP_EXTENSIONS_STACK},${EXTRA_ARGS},${PLATFORM_CONF_DEFAULTS_FILE},${CONFIGS_DIR}/${STACK}.yml)

export-stack-outputs-core-dtap-extensions: _check-for-stack-var _check-for-output-file-var
	@$(info Exporting stack outputs to ${PROJECT_ROOT}/${OUTPUT_FILE})
	@$(call pulumi_export_stack_outputs,${PULUMI_CORE_EXTENSIONS_SRC_DIR},${DTAP_EXTENSIONS_STACK},${EXTRA_ARGS},${PROJECT_ROOT}/${OUTPUT_FILE})

#####################################################################################################################
# SETUP
#####################################################################################################################
.PHONY: clone-repo
clone-repo:
	@if test -d ${SOURCE_DIR}; then echo "The Ingenii Azure Data Platform repo has been cloned already. Run 'make clean' and try again."; exit 1; fi
	@if test -z "${PLATFORM_VERSION}"; then echo "PLATFORM_VERSION not set."; exit 1; fi
	@git clone \
	--depth 1 -b ${PLATFORM_VERSION} https://github.com/ingenii-solutions/azure-data-platform.git temp_clone \
	&& mv temp_clone/src ${SOURCE_DIR} \
	&& rm -rf temp_clone

.PHONY: clone-repo-using-ssh
clone-repo-using-ssh:
	@if test -d ${SOURCE_DIR}; then echo "The Ingenii Azure Data Platform repo has been cloned already. Run 'make clean' and try again."; exit 1; fi
	@if test -z "${PLATFORM_VERSION}"; then echo "PLATFORM_VERSION not set."; exit 1; fi
	@git clone \
	--depth 1 -b ${PLATFORM_VERSION} git@github.com:ingenii-solutions/azure-data-platform.git temp_clone \
	&& mv temp_clone/src ${SOURCE_DIR} \
	&& rm -rf temp_clone

.PHONY: set-platform-version
set-platform-version:
	@if test -z "${VERSION}"; then echo "VERSION variable not set. Try make update-platform-version VERSION=xxx"; exit 1; fi
	@sed -i 's/PLATFORM_VERSION=.*/PLATFORM_VERSION=${VERSION}/g' ${PROJECT_ROOT}/platform.cfg
	@sed -i 's/azure-data-platform-iac-runtime:.*/azure-data-platform-iac-runtime:${VERSION}/g' ${PROJECT_ROOT}/.github/workflows/*.yml
	@sed -i 's/azure-data-platform-iac-runtime:.*/azure-data-platform-iac-runtime:${VERSION}",/g' ${PROJECT_ROOT}/.devcontainer/devcontainer.json

.PHONY: clean
clean:
	@rm -rf ${SOURCE_DIR}
	@rm -rf ${PROJECT_ROOT}/temp_clone

#####################################################################################################################
# API
#####################################################################################################################
init-shared: init-core-shared
preview-shared: preview-core-shared
refresh-shared: refresh-core-shared
apply-shared: apply-core-shared

init-shared-extensions: init-core-shared-extensions
preview-shared-extensions: preview-core-shared-extensions
refresh-shared-extensions: refresh-core-shared-extensions
apply-shared-extensions: apply-core-shared-extensions

init-dtap: init-core-dtap
preview-dtap: preview-core-dtap
refresh-dtap: refresh-core-dtap
apply-dtap: apply-core-dtap
post-deploy-dtap: post-deploy-core-dtap

init-dtap-extensions: init-core-dtap-extensions
preview-dtap-extensions: preview-core-dtap-extensions
refresh-dtap-extensions: refresh-core-dtap-extensions
apply-dtap-extensions: apply-core-dtap-extensions

init-extensions: init-core-dtap-extensions init-core-shared-extensions
preview-extensions: preview-core-dtap-extensions preview-core-shared-extensions
refresh-extensions: refresh-core-dtap-extensions refresh-core-shared-extensions
apply-extensions: apply-core-dtap-extensions apply-core-shared-extensions

init: _check-for-stack-var init-shared init-dtap init-extensions
preview: _check-for-stack-var preview-shared preview-dtap preview-extensions
refresh: _check-for-stack-var refresh-shared refresh-dtap refresh-extensions
apply: _check-for-stack-var apply-shared apply-dtap apply-extensions


#####################################################################################################################
# CI/CD API
# This API is used by GitHub Workflows.
#####################################################################################################################

_check_if_ci:
	@if test -z "${CI}"; then echo "This target should not be run outside of GitHub Workflows. For debug, set env var 'CI' to true and try again."; exit 1; fi

# Shared Stack
cicd-init-shared: _check_if_ci init-core-shared
cicd-refresh-shared: _check_if_ci refresh-core-shared
cicd-preview-shared: _check_if_ci
	@ingeniictl infra disable-resource-protection ${CORE_SHARED_STACK} --pulumi-project-dir ${PULUMI_CORE_SHARED_SRC_DIR} --pulumi-locks-only \
	&& make preview-core-shared

cicd-apply-shared: _check_if_ci
	@ingeniictl infra disable-resource-protection ${CORE_SHARED_STACK} --pulumi-project-dir ${PULUMI_CORE_SHARED_SRC_DIR} \
	&& ENABLE_RESOURCE_PROTECTION=0 make apply-core-shared EXTRA_ARGS="-f" \
	&& ENABLE_RESOURCE_PROTECTION=1 make apply-core-shared EXTRA_ARGS="-f" \
	&& make export-stack-outputs-core-shared \
	&& make upload-stack-outputs-core-shared

# DTAP Stack
cicd-init-dtap: _check_if_ci init-core-dtap
cicd-refresh-dtap: _check_if_ci refresh-core-dtap
cicd-preview-dtap: _check_if_ci
	@ingeniictl infra disable-resource-protection ${DTAP_CORE_STACK} --pulumi-project-dir ${PULUMI_CORE_DTAP_SRC_DIR} --pulumi-locks-only \
	&& make preview-core-dtap

cicd-apply-dtap: _check_if_ci
	@ingeniictl infra disable-resource-protection ${DTAP_CORE_STACK} --pulumi-project-dir ${PULUMI_CORE_DTAP_SRC_DIR} \
	&& ENABLE_RESOURCE_PROTECTION=0 make apply-core-dtap EXTRA_ARGS="-f" \
	&& ENABLE_RESOURCE_PROTECTION=1 make apply-core-dtap EXTRA_ARGS="-f" \
	&& make export-stack-outputs-core-dtap \
	&& make upload-stack-outputs-core-dtap

# Extensions
cicd-init-shared-ext: _check_if_ci init-core-shared-extensions
cicd-refresh-shared-ext: _check_if_ci refresh-core-shared-extensions
cicd-preview-shared-ext: _check_if_ci preview-core-shared-extensions
cicd-apply-shared-ext:
	@make _check_if_ci \
	&& ENABLE_RESOURCE_PROTECTION=0 make apply-core-shared-extensions EXTRA_ARGS="-f" \
	&& ENABLE_RESOURCE_PROTECTION=1 make apply-core-shared-extensions EXTRA_ARGS="-f"

cicd-init-dtap-ext: _check_if_ci init-core-dtap-extensions 
cicd-refresh-dtap-ext: _check_if_ci refresh-core-dtap-extensions
cicd-preview-dtap-ext: _check_if_ci preview-core-dtap-extensions 
cicd-apply-dtap-ext:
	@make _check_if_ci \
	&& ENABLE_RESOURCE_PROTECTION=0 make apply-core-dtap-extensions  EXTRA_ARGS="-f" \
	&& ENABLE_RESOURCE_PROTECTION=1 make apply-core-dtap-extensions  EXTRA_ARGS="-f"

#####################################################################################################################
# Danger Zone
#####################################################################################################################

define pulumi_destroy
	pulumi destroy --cwd $(1) --stack $(2) --parallel ${PULUMI_PARALLELISM} --color always $(3)
	pulumi stack rm --cwd $(1) --stack $(2) --non-interactive --yes $(3)
endef

_check_destroy_possible:
ifneq ($(DESTROY_ENABLED), 1)
	$(error Calling 'destroy' command, but destroy not enabled through DESTROY_ENABLED)
endif

destroy-shared: destroy-core-shared

destroy-shared-extensions:
	-make destroy-core-shared-extensions

destroy-dtap:
	-make destroy-core-dtap STACK=dev
	-make destroy-core-dtap STACK=test
	-make destroy-core-dtap STACK=prod

destroy-dtap-extensions:
	-make destroy-core-dtap-extensions STACK=dev 
	-make destroy-core-dtap-extensions STACK=test
	-make destroy-core-dtap-extensions STACK=prod

destroy-extensions: destroy-dtap-extensions destroy-shared-extensions

destroy: _confirm destroy-extensions destroy-dtap destroy-shared

destroy-core-shared: _check_destroy_possible init-core-shared
ifdef SHARED_ARM_CLIENT_ID
	@ARM_CLIENT_ID=${SHARED_ARM_CLIENT_ID}  \
	&& ARM_CLIENT_SECRET=${SHARED_ARM_CLIENT_SECRET} \
	&& ARM_SUBSCRIPTION_ID=${SHARED_ARM_SUBSCRIPTION_ID} \
	&& ARM_TENANT_ID=${SHARED_ARM_TENANT_ID} \
	&& ingeniictl infra destroy ${CORE_SHARED_STACK} --pulumi-project-dir ${PULUMI_CORE_SHARED_SRC_DIR}
else
	@ingeniictl infra destroy ${CORE_SHARED_STACK} --pulumi-project-dir ${PULUMI_CORE_SHARED_SRC_DIR}
endif

destroy-core-shared-extensions: _check_destroy_possible init-core-shared-extensions
ifdef SHARED_ARM_CLIENT_ID
	@ARM_CLIENT_ID=${SHARED_ARM_CLIENT_ID}  \
	&& ARM_CLIENT_SECRET=${SHARED_ARM_CLIENT_SECRET} \
	&& ARM_SUBSCRIPTION_ID=${SHARED_ARM_SUBSCRIPTION_ID} \
	&& ARM_TENANT_ID=${SHARED_ARM_TENANT_ID} \
	&& ingeniictl infra destroy ${CORE_SHARED_EXTENSIONS_STACK} --pulumi-project-dir ${PULUMI_CORE_EXTENSIONS_SRC_DIR}
else
	@ingeniictl infra destroy ${CORE_SHARED_EXTENSIONS_STACK} --pulumi-project-dir ${PULUMI_CORE_EXTENSIONS_SRC_DIR}
endif

destroy-core-dtap: _check_destroy_possible _check-for-stack-var init-core-dtap
	@ingeniictl infra destroy ${DTAP_CORE_STACK} --pulumi-project-dir ${PULUMI_CORE_DTAP_SRC_DIR}

destroy-core-dtap-extensions: _check_destroy_possible _check-for-stack-var init-core-dtap-extensions
	@ingeniictl infra destroy ${DTAP_EXTENSIONS_STACK} --pulumi-project-dir ${PULUMI_CORE_EXTENSIONS_SRC_DIR}

# Platform Destroy
cicd-destroy: _check_if_ci
	@-make destroy-core-dtap-extensions STACK=dev 
	@-make destroy-core-dtap-extensions STACK=test
	@-make destroy-core-dtap-extensions STACK=prod
	@-make destroy-core-shared-extensions
	@-make destroy-core-dtap STACK=dev
	@-make destroy-core-dtap STACK=test
	@-make destroy-core-dtap STACK=prod
	@-make destroy-core-shared