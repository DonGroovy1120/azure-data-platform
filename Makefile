SHELL := /bin/bash

REGION := EastUS

PROJECT_ROOT    := $(realpath .)
TEMP_DIR        := ${PROJECT_ROOT}/tmp
DOCKERFILE      := ${PROJECT_ROOT}/Dockerfile

VENV_DIR            := ${PROJECT_ROOT}/venv
SOURCE_DIR          := ${PROJECT_ROOT}/src
PULUMI_SOURCE_DIR   := ${PROJECT_ROOT}/src/pulumi

DEV_DIR_NAME    := dev
DEV_DIR         := ${PROJECT_ROOT}/${DEV_DIR_NAME}

RANDOM_STR			:= $(shell python -c "import random, string; print(''.join(random.SystemRandom().choice(string.ascii_lowercase) for _ in range(10)))")
RANDOM_STR_LEN_3	:= $(shell python -c "print('${RANDOM_STR}'[:3])")
RANDOM_STR_LEN_4	:= $(shell python -c "print('${RANDOM_STR}'[:4])")

#####################################################################################################################
# Helper Targets
# Please only use these targets if really necessary. Scroll down to the API section for the list of targets to use.
#####################################################################################################################
COOKIECUTTER_CUSTOMER_REPO_DIR				:= ${SOURCE_DIR}/cookiecutters/customer-repo
COOKIECUTTER_CUSTOMER_REPO_CONFIG_TPL_FILE	:= ${COOKIECUTTER_CUSTOMER_REPO_DIR}/cookiecutter.tpl
setup-cruft-project:
	$(info [INFO] Setting up the Cookiecutter project in ${DEV_DIR})
	@mkdir -p ${TEMP_DIR}
	@echo ${TEMP_DIR}
	@cp ${COOKIECUTTER_CUSTOMER_REPO_CONFIG_TPL_FILE} ${TEMP_DIR}/${RANDOM_STR}.yml
	@sed -i 's|customer_code_replace_me.*|${RANDOM_STR_LEN_3}|g' ${TEMP_DIR}/${RANDOM_STR}.yml;
	@sed -i 's|region_replace_me.*|${REGION}|g' ${TEMP_DIR}/${RANDOM_STR}.yml;
	@sed -i 's|resource_prefix_replace_me.*|${RANDOM_STR_LEN_3}|g' ${TEMP_DIR}/${RANDOM_STR}.yml;
	@sed -i 's|unique_id_replace_me.*|${RANDOM_STR_LEN_4}|g' ${TEMP_DIR}/${RANDOM_STR}.yml;
	@sed -i 's|platform_version_replace_me.*|development|g' ${TEMP_DIR}/${RANDOM_STR}.yml;
	@sed -i 's|project_dir_replace_me.*|${DEV_DIR_NAME}|g' ${TEMP_DIR}/${RANDOM_STR}.yml;
	@cruft create ${PROJECT_ROOT} --directory src/cookiecutters/customer-repo --config-file ${TEMP_DIR}/${RANDOM_STR}.yml --no-input
	@echo "" >> ${DEV_DIR}/configs/shared.yml
	@echo "automation:" >> ${DEV_DIR}/configs/shared.yml
	@echo "  devops:" >> ${DEV_DIR}/configs/shared.yml
	@echo "    project:" >> ${DEV_DIR}/configs/shared.yml
	@echo "      name: Ingenii Data Platform ${RANDOM_STR_LEN_3}" >> ${DEV_DIR}/configs/shared.yml
	@sed -i 's|\/platform\/src|$${PROJECT_ROOT}/src|g' ${DEV_DIR}/Makefile
	@rm -rf ${TEMP_DIR}

setup-dir-links:
	@ln -s ${SOURCE_DIR} ${DEV_DIR}/src

setup-env-file:
	$(info [INFO] Setting up the .env file)
	@if [ ! -f ${DEV_DIR}/.env ]; then cp ${DEV_DIR}/.env-dist ${DEV_DIR}/.env ; else echo "[INFO] '${DEV_DIR}/.env' file already exist. Skipping env file setup."; fi

setup-python-venv:
	$(info [INFO] Setting up the Python virtual environment at ${VENV_DIR})
	@python3 -m venv ${VENV_DIR}
	@source ${VENV_DIR}/bin/activate && cd ${SOURCE_DIR} && pip install -r requirements-dev.txt

show-setup-banner:
	@$(info ####################################################################################)
	@$(info	Success! A new development environment has been created at ${DEV_DIR})
	@$(info )
	@$(info Step 1 -> Populate the ${DEV_DIR}/.env file with your credentials)
	@$(info ------------------------------------------------------------------------------------)
	@$(info )
	@$(info Step 2 -> Activate the virtual environment by running the command below:)
	@$(info source ${VENV_DIR}/bin/activate)
	@$(info ------------------------------------------------------------------------------------)
	@$(info )
	@$(info Important)
	@$(info ------------------------------------------------------------------------------------)
	@$(info Please note that the ${PROJECT_ROOT}/src directory is linked to the)
	@$(info ${DEV_DIR}/src directory.)
	@$(info ####################################################################################)

set-pulumi-version:
	@if test -z "${VERSION}"; then echo "VERSION variable not set. Try 'make set-pulumi-version VERSION=<pulumi version>'"; exit 1; fi
	$(info Setting the Pulumi version to ${VERSION})
	@sed -i 's|pulumi==.*|pulumi==${VERSION}|g'	${SOURCE_DIR}/requirements-common.txt
	@sed -i 's|PULUMI_VERSION=.*|PULUMI_VERSION=${VERSION}|g' ${DOCKERFILE}
	$(info Rebuild the VSCode dev container for the changes to take an effect.)

set-python-version:
	@if test -z "${VERSION}"; then echo "VERSION variable not set. Try 'make set-python-version VERSION=<python version>'"; exit 1; fi
	$(info Setting the Python version to ${VERSION})
	@sed -i 's|PYTHON_VERSION=.*|PYTHON_VERSION=${VERSION}|g' ${DOCKERFILE}
	$(info Rebuild the VSCode dev container for the changes to take an effect.)

remove-dev-dir:
	$(info Removing the Development directory at: ${DEV_DIR})
	@rm -r ${DEV_DIR} || true

remove-venv-dir:
	$(info Removing the Python Virtual Environment directory at: ${VENV_DIR})
	@rm -r ${VENV_DIR} || true

remove-pulumi-project-configs:
	$(info Removing the Pulumi project configuration files)
	@rm  ${PULUMI_SOURCE_DIR}/core-shared/Pulumi.yaml || true
	@rm  ${PULUMI_SOURCE_DIR}/core-dtap/Pulumi.yaml || true
	@rm  ${PULUMI_SOURCE_DIR}/core-extensions/Pulumi.yaml || true

remove-tmp-dir:
	$(info Removing the temporary directory at: ${TEMP_DIR})
	@rm -r ${TEMP_DIR} || true

#####################################################################################################################
# API
#####################################################################################################################

# Project Setup
setup-native: setup-cruft-project setup-dir-links setup-env-file setup-python-venv show-setup-banner

setup-devcontainer: setup-cruft-project setup-dir-links setup-env-file

setup:
	# There is no need to set up a venv for the devcontainer. 
	@if test -z "${REMOTE_CONTAINERS}"; then "echo make setup-native"; else make setup-devcontainer; fi

project-reset: remove-dev-dir remove-pulumi-project-configs

reset: project-reset remove-venv-dir remove-tmp-dir

# Docker Image Build and Publish
DOCKER_IMAGE_NAME="ingeniisolutions/azure-data-platform-iac-runtime"

build-docker-image:
	@docker build . -t ${DOCKER_IMAGE_NAME}

publish-docker-image:
	@if test -z "${DOCKER_IMAGE_TAG}"; then echo "DOCKER_IMAGE_TAG not set. Try 'make publish-docker-image DOCKER_IMAGE_TAG=xxx"; exit 1; fi
	@docker tag ${DOCKER_IMAGE_NAME} "${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}"
	@docker push "${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}"