# Ingenii Azure Data Platform Helper Package

[![Maintainer](https://img.shields.io/badge/maintainer%20-ingenii-orange?style=flat)](https://ingenii.dev/)
[![License](https://img.shields.io/badge/license%20-MPL2.0-orange?style=flat)](https://github.com/ingenii-solutions/azure-data-platform-python-package/blob/main/LICENSE)
[![Contributing](https://img.shields.io/badge/howto%20-contribute-blue?style=flat)](https://github.com/ingenii-solutions/azure-data-platform-python-package/blob/main/CONTRIBUTING.md)

## Details

- Current Version: 0.1.0

## Overview

This python package has config loaders, schema validators and helper functions needed by the Azure Data Platform Pulumi solution.

## Usage

```bash
pip install ingenii-azure-data-platform
```

## PyPi Project Page

https://pypi.org/project/ingenii-azure-data-platform

## Releasing A New Version

There is a GitHub workflow (release.yml) that triggers on any GitHub releases.
**Make sure to update the package version in README.md** otherwise PyPi will reject the upload, if the same version is already uploaded.

## TODOS

- [ ] Improve the documentation for this repo
- [ ] Add readme file for the python package
- [ ] Add tests
- [ ] Add makefile for easier interaction
- [ ] Add a build/test only GitHub workflow
