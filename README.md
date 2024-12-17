# CloudFormation Template for CI/CD using AWS CodePipeline

Monitor and deploy changes to a CodeCommit branch using AWS CodePipeline.

It is recommended that you familiarize yourself with AWS CloudFormation, CodePipeline, and the Serverless Application Framework.

The intent of this Pipeline template is to bridge the gap between pieced together tutorials (and solutions from Stack Overflow) and practical, production ready solutions.

- Precisely scoped IAM Policies and Roles for a team and application (more secure, Principle of Least Privilege)
- Structured naming and tagging (better organization)
- No need to start from scratch
- No reason to create a messy application base and say "I'll structure, organize, and add security controls later"
- A tutorial for creating production-ready applications rather than examples pieced together

## About

Each branch will have its own pipeline stack and application infrastructure stack. This allows you to separate dev, test, and prod, grant developer access via CodeCommit policies, and create or destroy temporary or per-developer/feature test and staging branches/pipelines as necessary.

As you begin to look under the hood you can use it as a model for learning AWS Cloud Concepts such as Infrastructure as Code (IaC), CloudFormation, AWS CodePipeline, and serverless architecture. Once you have played around with it, the sky is the limit as you add your own modifications for your own use case.

## Repository Structure

There are 4 main directories in the root of this repository which corresponds to the 4 main steps necessary to get the solution up and running.

Divide these among two repositories: One for your application infrastructure, and another for your development operations.

Application Repository:

```text
/
|- application-infrastructure/
|   |- src/
|   |- buildspec.yml
|   |- template-configuration.json
|   |- template.yml
```

DevOps Repository:

```text
/
|- cloudformation-pipeline-template/
|   |- pipelines/
|   |- template-pipeline.yml
|
|- iam-cloudformation-service-role/
|   |- roles/
|   |- SAMPLE-CloudFormationServicePolicy.json
|   |- Trust-Policy-for-Service-Role.json
|
|- scripts-cli/
|   |- lib/
|   |- settings/
|   |- pipeline.py
|   |- service-role.py
```

### Application Infrastructure directory

This repository contains a sample SAM project in the `application-infrastructure` directory. Place the entire directory in the root of its own repository. CodePipeline will look for `application-infrastructure/` in your repository during build and deploy.

The sample application will deploy as-is. For customization options and a tutorial, refer to the [Tutorials in docs](./docs/Tutorials.md).

### IAM CloudFormation Service Role directory

CloudFormation needs a service role to assume in order to create and manage the pipeline stacks and this directory contains the Trust and Service Policy for the Service Role.

After running `scripts-cli/service-role.py`, the generated input.json and copy-paste AWS CLI `create-role` and `put-role-policy` commands will be stored in `cloudformation-pipeline-template/roles/`.

### Pipeline CloudFormation Template directory

This contains `template-pipeline.yml`, the CloudFormation template that defines CodePipeline and associated resources. 

After running `scripts-cli/pipeline.py`, the generated `create-stack` input.json and copy-paste AWS CLI commands will be stored in this directory.

## Usage

### Parameters

Review the necessary parameters in [Pipeline Parameters Reference](./docs/Pipeline-Parameters-Reference.md).

When you run the `service-role.py` and `pipeline.py` scripts, prompts will help guide you in choosing the parameters that meet your organizational needs.

Before you start you will need to think through and establish a `PREFIX`. It is recommended that for your first time through use the given prefix `acme`. Once you have completed your first run-though of the steps you will have a better understanding of how you can group permissions using different prefixes for your applications. Each prefix and service role can be assigned to different departments, teams, or application groups in your organization. A prefix is 2 to 8 characters (`acme`, `finc`, `ws`, `ops`, `dev-ops`, `sec`), all lower-case.

### Set Up: Easy as 1-2-3!

1. Create an IAM Role for your CloudFormation Service using the scripts and CLI commands
2. Create a CodeCommit repository for your code and place `/application-infrastructure/` at the root.
3. Create a CloudFormation Pipeline stack using the scripts and CLI commands

In these examples we will use the Prefix `acme`.

> These instructions use the AWS CLI. [Web Console documentation](./docs/Set-Up-via-Web-Console.md) and [AWS CDK and Terraform documentation](./docs/Set-Up-via-Terraform-or-CDK.md) is also available.

#### Step 1: Create Service Role

> Make sure you have the proper [permissions to create a role](./docs/Set-Up-User-Role.md).

There needs to be one service role created per Prefix.

From the `scripts-cli/` directory run `python service-role.py acme` replacing `acme` with your prefix and following on-screen prompts.

Follow instructions displayed after script has run. A copy of the CLI commands will be stored in `iam-cloudformation-service-role/`.

#### Step 2: Create a CodeCommit Repository for Your Application

Place the `application-infrastructure/` directory at the root of your repository.

Commit your code and then create and push a `dev` and `test` branch in addition to your `main` branch.

Your repository is now primed for the next step.

#### Step 3: Create the Pipeline

From the `scripts-cli/` directory, run `python pipeline.py acme hello-world test` replacing `acme` and `hello-world` with appropriate values (your Prefix and Project Id). Leave test as is.

Follow on-screen prompts.

Follow instructions displayed after script has run. A copy of the CLI commands will be stored in `cloudformation-pipeline-template/`

Once you have a successful deploy, create your Production pipeline:

`python pipeline.py acme hello-world prod`

Follow the same on-screen and CLI steps as you did for your test pipeline.

## Tutorials and Additional Documentation

There are various [tutorials](./docs/Tutorials.md) that will help walk you through your first deployment and get you familiar with your options. If you are new to AWS CodePipeline and SAM, then the tutorials are a great resource in helping you learn about the process.

Additional documentation is found in the /docs/ directory as well as /scripts-cli/ and /application-infrastructure/

- [User Role Set-Up](./docs/User-Role-Set-Up.md)
- [1-2-3 Set-Up](./docs/1-2-3-Set-Up.md)
- [Set-Up via Web Console](./docs/Set-Up-via-Web-Console.md)
- [Set-Up via Terraform or CDK](./docs/Set-Up-via-Terraform-or-CDK.md)
- [Pipeline Parameters Reference](./docs/Pipeline-Parameters-Reference.md)
- [Tutorials](./docs/Tutorials.md)
- [Scripts and CLI](./scripts-cli/README-CLI.md)
- [Updating the Pipeline Stack](./docs/Updating-Pipeline-Stack.md)
- [Deleting and Clean-Up](./docs/Deleting-and-Clean-Up.md)

## Review Change Log

Once you have your pipeline set up you may want to watch the [CloudFormation Template for a Deployment Pipeline (CI/CD)](https://github.com/chadkluck/serverless-deploy-pipeline-atlantis) repository for any updates. Using the instructions for editing your deployment pipeline stack above you can walk through the instructions in the Change Log and make updates to your deploy pipeline stack.
