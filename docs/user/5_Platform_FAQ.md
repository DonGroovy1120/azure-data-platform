# Platform FAQ <!-- omit in toc -->

**Table of Contents**

- [Cost](#cost)
  - [Do you make use of Azure Reservations?](#do-you-make-use-of-azure-reservations)
  - [Do you make use of Spot instances?](#do-you-make-use-of-spot-instances)
- [Security](#security)
  - [Is the data encrypted at rest?](#is-the-data-encrypted-at-rest)
  - [Is the data encrypted in transit?](#is-the-data-encrypted-in-transit)
  - [Are VPNs required to connect to the platform?](#are-vpns-required-to-connect-to-the-platform)
  - [What are the security settings of the platform?](#what-are-the-security-settings-of-the-platform)
  - [Is access to the data monitored?](#is-access-to-the-data-monitored)
  - [Is our data safe from outside access and/or other customers?](#is-our-data-safe-from-outside-access-andor-other-customers)
- [Authentication and Permissions](#authentication-and-permissions)
  - [How do the users access the platform?](#how-do-the-users-access-the-platform)
  - [Do I need to install anything on my computer?](#do-i-need-to-install-anything-on-my-computer)
  - [How do users or administrators authenticate?](#how-do-users-or-administrators-authenticate)
  - [Is Multifactor Authentication (MFA) enabled?](#is-multifactor-authentication-mfa-enabled)
  - [How is access controlled to the platform? How are permissions managed?](#how-is-access-controlled-to-the-platform-how-are-permissions-managed)
  - [We don't use our Azure AD directly but federate from on-premise AD. How do we work with the prerequisites?](#we-dont-use-our-azure-ad-directly-but-federate-from-on-premise-ad-how-do-we-work-with-the-prerequisites)
  - [How do you manage access credentials? Are they rotated frequently?](#how-do-you-manage-access-credentials-are-they-rotated-frequently)
- [Azure Tenants and Subscriptions](#azure-tenants-and-subscriptions)
  - [Can the platform be deployed in a separate tenant from our Azure AD?](#can-the-platform-be-deployed-in-a-separate-tenant-from-our-azure-ad)
- [Support](#support)
  - [We have a third party providing support for our cloud environments. What would they be responsible for?](#we-have-a-third-party-providing-support-for-our-cloud-environments-what-would-they-be-responsible-for)

## Cost

### Do you make use of Azure Reservations?

- All compute resources in the platform are ephemeral. There are no long-running instances.

### Do you make use of Spot instances?

- It depends. We do have the option to use Spot instances for the Databricks workers.

## Security

### Is the data encrypted at rest?

- Yes, all data stored via the Ingenii Platform is encrypted at rest. We use Azure Data Lake Gen 2 which encrypts data at rest by default. [Reference](https://docs.microsoft.com/en-us/azure/storage/common/storage-service-encryption)

### Is the data encrypted in transit?

- Yes. Data moving within the platform is only possible via secure protocols such as HTTPS/TLS. Following the [Azure networking security recommendations](https://docs.microsoft.com/en-us/azure/storage/blobs/security-recommendations#networking) we enforce a minimum of TLS 1.2 for data moving in and out of any Data Lake. [Reference](https://docs.microsoft.com/en-us/azure/storage/common/transport-layer-security-configure-minimum-version?tabs=portal#configure-the-minimum-tls-version-for-a-storage-account)

### Are VPNs required to connect to the platform?

- No. VPNs are not necessary or recommended. All user access is protected by standard Microsoft authentication mechanisms used in services such as Office 365.
- All access to the platform is possible only via secure protocols such as HTTPS/TLS.

### What are the security settings of the platform?

TODO

### Is access to the data monitored?

TODO

- <CHECK IF THIS IS HAPPENING IN THE TERRAFORM> Data Lake: Access logging is enabled by default, which writes logs to a separate storage container called $logs. By default this data is deleted after 7 days. We are looking to use storage logs in Azure Monitor, but this is a feature currently in public preview. [Reference](https://docs.microsoft.com/en-us/azure/storage/common/storage-analytics-logging)
- Databricks
- Other resources?

### Is our data safe from outside access and/or other customers?

- Your data is your data. No one else has access to it.
- Our deployment of the platform is done in your subscription, which only you have access to.
- All component pieces are deployed to communicate and move data over your private, isolated network.

## Authentication and Permissions

### How do the users access the platform?

- We provide direct access to the Databricks Workspace or access via the Azure Portal.
- User access can be protected using Microsoft's best practices such as Conditional Access, Risky Logins etc. Check with your system administrator or MSP on how to enable these features.

### Do I need to install anything on my computer?

- Not necessarily. Depending on your choice for Dashboard access (e.g. PowerBI), you might need to install a PowerBI client on your machine. All of our default tools support web-based interaction.

### How do users or administrators authenticate?

- All users (including administrators) authenticate via Azure Active Directory (AAD).

### Is Multifactor Authentication (MFA) enabled?

- MFA can be enabled via Azure Active Directory. [Reference](https://docs.microsoft.com/en-us/azure/active-directory/authentication/concept-mfa-howitworks)

### How is access controlled to the platform? How are permissions managed?

- Access is controlled via Roles Based Access Control (RBAC). AAD Groups are granted permissions to the platform, and individual users' permissions are managed by adding and removing them from these groups.
- Additionally, we recommend our customers to make use of Azure Conditional Access policies to control further how users can authenticate and so access the platform. [Reference](https://docs.microsoft.com/en-us/azure/active-directory/conditional-access/overview)

### We don't use our Azure AD directly but federate from on-premise AD. How do we work with the prerequisites?

- All access is enabled through cloud identities, so ideally, these are synced from on-premise AD to Azure AD to fit easily with the platform. [Reference](https://docs.microsoft.com/en-us/azure/active-directory/hybrid/how-to-connect-sync-whatis)
- Alternatively, separate cloud identities can be created for platform access.

### How do you manage access credentials? Are they rotated frequently?

- We do not manage access credentials to the platform. All authentication is handled by Azure AD and follow your password rotation policy.

## Azure Tenants and Subscriptions

### Can the platform be deployed in a separate tenant from our Azure AD?

- Yes, but you will have to manage user identities in this new tenant. The easiest way to achieve this would be to invite users from your primary tenant as guest users in the platform tenant. We don't think this provides any security advantage and would recommend using your primary tenant.
- The Azure Ingenii Data Platform is deployed in a separate subscription to any resources you have at the moment, which provides you sufficient separation of environments to control access.

## Support

### We have a third party providing support for our cloud environments. What would they be responsible for?

See the [Requirements](./platform_requirements.md) for the prerequisites that are required from a third-party outsourced support or managed service provider (MSP). As a summary, the support that the third party would have to provide is:

- General vendor management of Microsoft for any escalations
- Ensuring the [Requirements](./platform_requirements.md) for the prerequisites are available on an ongoing basis
- Troubleshooting any issues with the prerequisites such as:
  - Subscription
  - Azure Principals and Azure AD permissions
