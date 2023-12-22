# Platform Naming Conventions <!-- omit in toc -->

- [Overview](#overview)
- [Abbreviations](#abbreviations)
  - [Regions](#regions)
  - [Environments](#environments)
  - [Azure Resources](#azure-resources)
- [Examples](#examples)
  - [General Resources](#general-resources)
  - [Network Resources](#network-resources)
  - [Data Tools](#data-tools)

## Overview

- [Microsoft Resource Naming Restrictions][microsoft_resource_naming_restrictions]

## Abbreviations

The majority of the abbreviations are following the [official Microsoft standard][microsoft_resource_abbreviations].

### Regions

| Name    | Long Abbreviation | Short Abbreviation |
| ------- | ----------------- | ------------------ |
| EastUS  | `eastus`          | `eus`              |
| UKSouth | `uksouth`         | `uks`              |
| UKWest  | `ukwest`          | `ukw`              |

### Environments

| Environment | Long Abbreviation | Short Abbreviation |
| ----------- | ----------------- | ------------------ |
| Shared      | `shared`          | `s`                |
| Development | `dev`             | `d`                |
| Testing     | `test`            | `t`                |
| Acceptance  | `acc`             | `a`                |
| Production  | `prod`            | `p`                |

### Azure Resources

| Resource                          | Abbreviation |
| --------------------------------- | ------------ |
| Subscription                      | `sub`        |
| Resource Group                    | `rg`         |
| Virtual Network                   | `vnet`       |
| Route Table                       | `rt`         |
| Subnet                            | `snet`       |
| Network Security Group            | `nsg`        |
| Public IP Address                 | `pip`        |
| NAT Gateway                       | `ngw`        |
| Local Network Gateway             | `lgw`        |
| Virtual Network Gateway           | `vgw `       |
| Load Balancer                     | `lb`         |
| Storage Account                   | `st`         |
| Storage Account (Diagnostic Logs) | `stdiag`     |
| Azure Container Registry          | `acr`        |
| Key Vault                         | `kv`         |
| Azure SQL Database Server         | `sql`        |
| Azure SQL Database                | `sqldb`      |
| Azure Synapse Analytics           | `syn`        |
| Azure Cosmos DB Database          | `cosmos`     |
| Azure Databricks Workspace        | `dbw`        |
| Azure Data Factory                | `adf`        |
| Log Analytics Workspace           | `log`        |
| Azure AD Group                    | `aadg`       |

## Examples

### General Resources

| Resource Type  | Naming Format                       | Examples                                           |
| -------------- | ----------------------------------- | -------------------------------------------------- |
| Azure AD Group | `<PREFIX>-<Env>-<GroupName>`        | **ADP-Dev-Engineers** <br> **ADP-Dev-Admins**      |
| Resource Group | `<prefix>-<region>-<env>-rg-<name>` | **adp-eus-d-rg-data** <br/> **adp-eus-d-rg-infra** |

### Network Resources

| Resource Type          | Naming Format                         | Examples                                                   |
| ---------------------- | ------------------------------------- | ---------------------------------------------------------- |
| Virtual Network        | `<prefix>-<region>-<env>-vnet-<name>` | **adp-eus-d-vnet-main** <br/> **adp-eus-t-vnet-platform**  |
| Subnet                 | `<prefix>-<region>-<env>-snet-<name>` | **adp-eus-d-snet-public** <br/> **adp-eus-t-snet-private** |
| Route Table            | `<prefix>-<region>-<env>-rt-<name>`   | **adp-eus-d-rt-public** <br/> **adp-eus-p-rt-private**     |
| Network Security Group | `<prefix>-<region>-<env>-nsg-<name>`  | **adp-eus-d-nsg-databricks** <br/> **adp-eus-p-nsg-ftp**   |
| NAT Gateway            | `<prefix>-<region>-<env>-ngw-<name>`  | **adp-eus-d-ngw-main** <br/> **adp-eus-p-ngw-primary**     |
| Public IP              | `<prefix>-<region>-<env>-pip-<name>`  | **adp-eus-d-pip-nat** <br/> **adp-eus-p-pip-outbound**     |

### Data Tools

| Resource Type | Naming Format                        | Examples                        |
| ------------- | ------------------------------------ | ------------------------------- |
| Data Factory  | `<prefix>-<region>-<env>-adf-<name>` | **adp-eus-d-adf-orchestration** |
| Databricks    | `<prefix>-<region>-<env>-dbw-<name>` | **adp-eus-d-dbw-engineering**   |

[//]: # "-------------------------"
[//]: # "INSERT LINK LABELS BELOW "
[//]: # "-------------------------"
[microsoft_resource_naming_restrictions]: https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules
[microsoft_resource_abbreviations]: https://docs.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations
