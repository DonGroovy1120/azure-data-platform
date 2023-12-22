setup-template-repo:
	@if test -z "${PLATFORM_VERSION}"; then echo "PLATFORM_VERSION variable not set. Try 'make setup-template PLATFORM_VERSION=<platform version>'"; exit 1; fi
	@if test -z "${OUTPUT_DIR}"; then echo "OUTPUT_DIR variable not set. Try 'make setup-template OUTPUT_DIR=<platform version>'"; exit 1; fi
	@sed -i 's|platform_version_replace_me.*|${PLATFORM_VERSION}|g' default_context.template_repo.yml;
	@cruft create $(shell git rev-parse --show-toplevel) --directory $(shell pwd) --config-file default_context.template_repo.yml --output-dir ${OUTPUT_DIR} --no-input