build-package:
	@if [ -d build ]; then rm -r build; fi
	@if [ -d dist ]; then rm -r dist; fi
	python setup.py bdist_wheel

move-package:
	cp dist/ingenii_databricks_connect* ../../images/add_databricks_connect

build-and-move-package: build-package move-package
