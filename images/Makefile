BLOB_TO_SHARE_NAME=ingeniisolutions/utility-blob-to-share
JUPYTERLAB_BASE_NOTEBOOK_NAME=ingeniisolutions/jupyterlab-base-notebook
JUPYTERLAB_SINGLE_USER_NAME=ingeniisolutions/jupyterlab-single-user
JUPYTERLAB_SINGLE_USER_DATABRICKS_NAME=ingeniisolutions/jupyterlab-single-user-databricks
JUPYTERLAB_SINGLE_USER_QUANTUM_NAME=ingeniisolutions/jupyterlab-single-user-quantum
JUPYTERLAB_SINGLE_USER_DATABRICKS_QUANTUM_NAME=ingeniisolutions/jupyterlab-single-user-databricks-quantum

$(eval BLOB_TO_SHARE_VERSION=$(shell grep '^* Blob to Share Version:' README.md | awk -F ':' '{print $$2}' | sed 's/ //g'))
$(eval JUPYTERLAB_BASE_NOTEBOOK_VERSION=$(shell grep '^* JupyterLab Base Notebook Version:' README.md | awk -F ':' '{print $$2}' | sed 's/ //g'))
$(eval JUPYTERLAB_SINGLE_USER_VERSION=$(shell grep '^* JupyterLab Single User Version:' README.md | awk -F ':' '{print $$2}' | sed 's/ //g'))

build-blob-to-share:
	docker build blob_to_share -t ${BLOB_TO_SHARE_NAME}:${BLOB_TO_SHARE_VERSION}

push-blob-to-share:
	docker push ${BLOB_TO_SHARE_NAME}:${BLOB_TO_SHARE_VERSION}

build-jupyterlab-base-notebook:
	docker build \
		--build-arg PYTHON_VERSION=3.8 \
		jupyterlab_base_notebook -t ${JUPYTERLAB_BASE_NOTEBOOK_NAME}:${JUPYTERLAB_BASE_NOTEBOOK_VERSION}

push-jupyterlab-base-notebook:
	docker push ${JUPYTERLAB_BASE_NOTEBOOK_NAME}:${JUPYTERLAB_BASE_NOTEBOOK_VERSION}

build-jupyterlab-single-user:
	docker build \
		--build-arg BASE_IMAGE=${JUPYTERLAB_BASE_NOTEBOOK_NAME}:${JUPYTERLAB_BASE_NOTEBOOK_VERSION} \
		jupyterlab_singleuser -t ${JUPYTERLAB_SINGLE_USER_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION}

push-jupyterlab-single-user:
	docker push ${JUPYTERLAB_SINGLE_USER_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION}

build-jupyterlab-single-user-databricks:
	docker build \
		--build-arg BASE_IMAGE=${JUPYTERLAB_SINGLE_USER_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION} \
		--build-arg CLUSTER_VERSION=9.1 \
		add_databricks_connect -t ${JUPYTERLAB_SINGLE_USER_DATABRICKS_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION}

push-jupyterlab-single-user-databricks:
	docker push ${JUPYTERLAB_SINGLE_USER_DATABRICKS_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION}

build-jupyterlab-single-user-quantum:
	docker build \
		--build-arg BASE_IMAGE=${JUPYTERLAB_SINGLE_USER_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION} \
		add_quantum -t ${JUPYTERLAB_SINGLE_USER_QUANTUM_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION}

push-jupyterlab-single-user-quantum:
	docker push ${JUPYTERLAB_SINGLE_USER_QUANTUM_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION}

build-jupyterlab-single-user-databricks-quantum:
	docker build \
		--build-arg BASE_IMAGE=${JUPYTERLAB_SINGLE_USER_DATABRICKS_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION} \
		add_quantum -t ${JUPYTERLAB_SINGLE_USER_DATABRICKS_QUANTUM_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION}

push-jupyterlab-single-user-databricks-quantum:
	docker push ${JUPYTERLAB_SINGLE_USER_DATABRICKS_QUANTUM_NAME}:${JUPYTERLAB_SINGLE_USER_VERSION}

all-single-user:
	make build-jupyterlab-single-user
	make push-jupyterlab-single-user
	make build-jupyterlab-single-user-databricks
	make push-jupyterlab-single-user-databricks
	make build-jupyterlab-single-user-quantum
	make push-jupyterlab-single-user-quantum
	make build-jupyterlab-single-user-databricks-quantum
	make push-jupyterlab-single-user-databricks-quantum
