ARG VARIANT="3.10-bullseye"
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

ARG PULUMI_VERSION=3.23.2

# # User vscode needs sudoers access to all users without password.
RUN echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Pulumi
# Install pulumi as vscode to allow read/write to .pulumi.
RUN cd /tmp && curl -fsSL https://get.pulumi.com | sh -s -- --version ${PULUMI_VERSION} --silent \
    && echo "export PULUMI_SKIP_UPDATE_CHECK=false" >> /root/.bashrc \
    && echo "export PULUMI_SKIP_UPDATE_CHECK=false" >> /root/.zshrc
ENV PATH="/root/.pulumi/bin:${PATH}"

# Pulumi Plugins
RUN ${HOME}/.pulumi/bin/pulumi plugin install resource databricks 0.1.0 --server https://github.com/ingenii-solutions/pulumi-databricks/releases/download/v0.1.0

# Copy the platform source code to the container
COPY src /platform/src

# This is required to make sure the vscode user can write to the GitHub workspace
RUN sudo mkdir __w && sudo chown vscode:vscode __w

# Install all platform Python packages
RUN cd /platform/src && pip install -r requirements.txt
