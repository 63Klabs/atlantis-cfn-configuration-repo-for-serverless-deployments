# Changelog

All notable changes to this project will be documented in this file.

NOTE: The **Pipeline** template is for **Pipeline** stacks! **NOT** your **Application Infrastructure** stacks!

You can add updates to your own copy of the pipeline stack template by manually following instructions and updating the template directly in CloudFormation or by uploading the new template to your CloudFormation stack. Review the updates and then follow instructions for applying the new template to existing CloudFormation stacks.

Updates are listed in **reverse chronological** order to aid in applying any manual updates. It is recommended you only do one version update at a time and await a successful deployment.

## v2024.xx.xx Release

- For the pipeline template, changed the created *-infrastructure stack name to *-application.
- Also updated all scripts to conform. In addition to this change, renamed the parameter `PermissionsBoundaryARN` to `PermissionsBoundaryArn` to conform to popular conventions. This is reflected in the application infrastructure template, pipeline template, and scripts.
- Moving toward SAM deployments instead of CLI for CloudFormation role and Pipeline stack.
- Added new CodeBuild environment variable: `NODE_ENV` and set to `production` so that Node devDependencies CLI formatting and testing are not installed and deployed along with the Lambda function. The current value of `NODE_ENV` is output to the CodeBuild log. It can also be reset to `development` if you truly do want to install `devDependencies` for tests and processes during build. However, it is recommended that this install be separated from the install that gets packaged with your Lambda function as `devDependencies` do NOT need to be updated to Lambda. They create extra baggage and prevent inspection through the Web Console.
- Started implementation of implementing permissions that restrict the pipeline's CodeBuild Service Role to just resources tagged with the application specific tags. This will help provide least privilege to take care of the random resource names assigned to API Gateway among others.
- Added build service role permissions to be able to copy objects to already existing S3 buckets during builds. This is for moving over static assets that are hosted from S3.

Templates and Scripts Updated:

- v2024.10.18 : template-pipeline.yml
- v2024.10.18 : template-pipeline-service-role.yml
- v2024.10.18 : pipeline.py
- v2024.10.18 : service-role.py
- v2024.10.18 : lib/atlantis.py
- v2024.06.17 : lib/templates/sample-input-create-stack.json

> All new pipelines will create *-application stacks instead of *-infrastructure. This goes with the idea that we are creating *-pipeline, *-storage, *-network, and *-application stacks, all of which are _Infrastructure_ and can be confusing. If you wish to convert old pipelines and "infrastructure" stacks to the new naming, be aware of how that will affect already created and named resources.

> All new pipelines will use `PermissionsBoundaryArn` instead of `PermissionsBoundaryARN` as a parameter.

## v2024.06.17 Release

For the pipeline template, added caching to the CodeBuild Project, and a CloudFormation stack parameter "DeployBucket" to use an existing S3 bucket for artifact storage rather than creating one for each pipeline.

Includes a fix to CloudFormationServicePolicy (IAM) by adding "iam:UpdateRoleDescription" Action to ManageWorkerRolesByResourcePrefix.

Templates and Scripts Updated:

- v2024.06.17 : template-pipeline.yml
- v2024.06.17 : pipeline.py
- v2024.06.17 : lib/atlantis.py
- v2024.06.17 : lib/templates/sample-input-create-stack.json

To update CloudFormation-Service-Role, re-run the `service-role.py` script for the Prefix you wish to update. Then update the role's policy with the generated JSON policy found in the roles directory by running just the `aws iam put-role-policy` cli command found in the generated cli text document.

## v2024.04.21 Release

Reworked the template and removed the ability to deploy using CodeStar (which is being retired by AWS summer of 2024 anyway). The new template and CLI commands simplified maintaining and using the template for both the pipeline and infrastructure stack. The [old template is still available on S3](https://63klabs.s3.us-east-2.amazonaws.com/atlantis/v0/atlantis-pipeline-files-v0-deprecated.zip).

Version 2 now has clearer parameter naming conventions, improved parameter constraints, CLI scripts, and instructions.

File versions included:

- v2024.02.29 : template-pipeline.yml
- v2024.02.29 : service-role.py
- v2024.02.29 : pipeline.py
- v2024.02.29 : lib/atlantis.py
- v2024.02.29 : lib/tools.py

The main instructions have been updated, however the tutorial has not. A new tutorial should be released in Summer of 2024.
