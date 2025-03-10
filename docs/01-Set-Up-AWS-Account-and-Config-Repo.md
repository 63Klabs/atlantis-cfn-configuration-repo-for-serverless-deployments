# Set Up Account Including CloudFormation Role for Developers

> Note: This step may have already been done for you if you are provided an account from your AWS administrator. If you are working on your **personal** AWS account, then please proceed in setting it up.

If you are using an AWS Account provided for you by your administrator then skip to [Using Preconfigured AWS Account and Config Repo](./02-Using-Preconfigured-AWS-Account-and-Config-Repo.md).

If you are an AWS Account Administrator, or using your personal AWS Account, then please proceed.

> Note: CodeCommit is no longer available on new AWS accounts unless it is created from an AWS Organization Account that already had CodeCommit. The pipeline infrastructure template and `create_repo.py` script will only work with CodeCommit repositories. GitHub and GitLab will be supported at a later date.

## 1. Set Up Configuration Repository

The repository can reside in the repository provider of your choice (CodeCommit, GitHub, GitLab, etc).

Initialize a new repository and download and extract the Atlantis CloudFormation Configuration Repository For Serverless Deployments into it.

```bash
# 
curl -L -o repo.zip "https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/archive/refs/heads/main.zip" && unzip -o -v repo.zip && mv */docs . && mv */scripts . && mv */README.md . 2>/dev/null && rm -rf repo.zip && rm -rf */

```

This repository will host the scripts and deployment configurations for storage, network, pipeline, and IAM roles. Developers will use the scripts to manage their deployment configurations and commit and push their changes into the repository.

Make the scripts executable:

```bash
chmod +x ./scripts/*.py
chmod +x ./scripts/*.sh
```

> It is important to **pull** any changes to the local machine, **configure** and **deploy** an infrastructure stack using the scripts, and then **commit** and **push** the configuration changes back to the remote repository for proper version control.

## 2. Configure CloudFormation Roles for Developers

The Principle of Least Privilege is maintained through resource naming and tagging.

At the very base is the naming Prefix. The Prefix can be assigned to an entire organization account, team, or department. A single AWS account may contain multiple Prefix namespaces if the account is shared among teams or a single Prefix if a team or department is a single tenant of the account.

Any developer assigned to the team that utilizes that Prefix at the very least should have access to create and maintain a pipeline for the application they are developing. In order to create the CloudFormation stack that generates the pipeline infrastructure for application deployments, the developer must have access to assume a role that allows them to do so. The CloudFormation role they assume will grant them access to only create a pipeline under a specific Prefix. This limits their abilities to create, modify, or delete pipelines outside of the Prefix organization they are assigned to.

Additional roles may be created if the developer should be allowed to create storage or network stacks.

As of right now, only the pipeline role template is available as a starter template in this repository. However, it can be used as an example for creating additional roles for the developer to assume.

To start out, you must determine the following:

- Prefix
- Role Path (optional but recommended)
- S3 Bucket Name Prefix (optional but recommended)
- Permission Boundaries (optional)

### Prefix

> A Prefix can be 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number.

As stated earlier, a Prefix is a namespace that is used in resource naming and tags.

For example, an application created under the Prefix `acme` would have all of its resources named `acme-*` and tagged `atlantis:Prefix=acme`. (Except for resources that can't receive a name such as API Gateway. Then it will just be tagged with `atlantis:Prefix=acme`)

These can be used for specifying resources under `Resources` and conditionals using tags in IAM policies for Execution Roles.

Choose a Prefix that best describes the team, account, department, or function using that Prefix. You may also decide to separate out job function. For example, the finance development team may have their own AWS organization account. All developers on that team can use the `finc` Prefix. However, there may also be senior developers, or systems operators that develop solutions under the `finops` Prefix. Junior developers will be able to use `finc` but not have access to `finops` infrastructure. Senior developers may have access to both `finc` and `finops` and systems operators only have access to `finops`.

Make sure the number of Prefixes you implement remain manageable.

### Role Path

Including `RolePath` will require the `RolePath` parameter be supplied for ALL deployments.

Even though IAM doesn't provide a heirarchical structure for Roles, you can include a role path as a method for providing permissions and organization. For example, you can allow application infrastructure stacks to create Execution Roles only under the RolePath `/app-infra/`. 

### Permissions Boundaries

Permissions Boundaries can be used by administrators to limit what can and cannot be created by a user. If supplied, they must be included for ALL deployments.

### S3 Bucket Name Prefix

This is not to be confused with Prefix or S3 object prefix. This is purely for naming the S3 bucket.

If supplied this will pre-pend this value to all S3 buckets created by infrastructure stacks (as long as it is included in the template). 

This can be used to provide permissions (requires templates to only create S3 buckets under this prefix) and shorten the bucket name. If this is not required and not supplied then bucket names will include the account and region. This makes for a unique but long name. S3 names have a limit of 63 characters. If your organization requires a prefix, it is up to you to make sure they are unique.
