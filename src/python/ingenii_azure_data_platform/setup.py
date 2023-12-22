# import re
from setuptools import setup, find_packages

# with open("README.md", "r") as fh:
#     readme = fh.read()

# regex = r"^\-\sCurrent\sVersion:\s(\d+.\d+.\d+)$"
# match = re.search(regex, readme, re.MULTILINE)

# if match:
#     current_version = match.group(1)
# else:
#     raise Exception("Current version is missing from the README.md")

# with open("requirements.txt", "r") as r:
#     requirements = [p for p in r.read().split("\n") if p]
#     dependencies = [p.split("=")[0] for p in requirements]

setup(packages=find_packages())
