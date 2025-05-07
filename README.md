# Atlantis Configuration Repository for Serverless Deployments using AWS SAM

A central repository structure and cli to store, manage, and deploy supporting SAM configuration files for serverless infrastructure (such as pipelines). Various cli allow for importing existing stack configurations, creating and seeding application repositories, managing tags, and updating multi-stage deployments all while using standard `samconfig` files.

While applications should be deployed using automated pipelines, those pipelines need to be created and managed. In addition to pipelines, applications may also have persistent S3, DynamoDb, Route53, and CloudFront resources outside of the main application stack.

SAM configuration files (`samconfig`) can handle stack configurations but cannot scale to handle tags and parameter overrides among multiple deployment stages. SAM config files also do not support utilizing templates stored in S3.

These cli and templates overcome those limitations and establish a structured approach to managing deployments.

## Prerequisites

1. AWS CLI installed
2. AWS SAM CLI installed
3. Git installed
4. Configured AWS profile with valid credentials

These instructions assume you have an AWS account, AWS CLI, SAM, and profile configuration set up. They also assume a Linux-like environment and CLI. On Windows you can use Git Bash or Windows Subsystem for Linux (WSL). And finally, you should have a familiarity with AWS CLI, SAM, and git.

## Install and Set Up

> **If you are the administrator** of of the AWS account (either personal or organization) perform the following first: [Set Up AWS Account and Config Repo](./docs/01-Set-Up-AWS-Account-and-Config-Repo.md).

**If you are a developer** your organization should already have the configuration repository established. Obtain necessary information about the repository location, prefix, cf bucket, and other requirements from your administrator. If you do not yet have an AWS development environment set up see [Set-Up-Local-Environment](./docs/00-Set-Up-Local-Environment.md).

1. Clone this repository from your organization's version control system
2. Make cli executable

```bash
chmod +x ./cli/*.py
chmod +x ./cli/*.sh
```

## Basic Usage Examples

```bash
# You may need to add --profile yourprofile if not using the default AWS CLI profile
# Python cli will automatically check for current credentials an initiate a login if necessary.

# Create a CodeCommit repository and seed it with an application starter from a list of choices
./cli/create_repo.py your-repo-name

# Create a CodeCommit repository and seed it with an application starter from a zip in S3
./cli/create_repo.py your-repo-name --s3-uri s3://bucket/path/to/file.zip

# Create a GitHub repository and seed it with an application starter from a zip in S3 (requires GitHub CLI)
./cli/create-gh-repo.sh your-repo-name s3://bucket/path/to/file.zip

# Create a GitHub repository and seed it with an application starter from a GitHub repository (requires GitHub CLI)
./cli/create-gh-repo.sh your-repo-name https://github.com/someacct/some-repository

# Create/Manage a pipeline infrastructure stack for your application's test branch
./cli/config.py pipeline acme your-webapp test

# Deploy a pipeline infrastructure stack for your application's test branch
./cli/deploy.py pipeline acme your-webapp test # we do this instead of sam deploy because it can handle templates in S3

# Import an existing stack
./cli/import.py stack-to-import

# Import an existing stack with template
./cli/import.py acme-blue-test-pipeline --template
```

### Create a New Repository for Your Application

Various serverless application starters are available to seed your repository depending on what type of application you wish to build.

Two cli (one for CodeCommit, one for GitHub) are provided that will automatically create your repository and seed it with the necessary code files.

#### CodeCommit

Starting a new application using a CodeCommit repository is as simple as:

```bash
./cli/create_repo.py your-webapp --profile yourprofile
```

Where `your-webapp` is the name of your repository and `yourprofile` is the AWS profile to use (it may be `default`).

You will then be prompted to choose an application starter followed by additional information such as tags for your repository. The cli will then create the repository, place the application starter code in it, and provide you with the clone url.

#### GitHub

Starting a new application using a GitHub repository is as simple as:

```bash
./cli/create-gh-repo.sh your-webapp s3://your-template-bucket/path/to/app-starter.zip yourprofile
```

This assumes you have GitHub CLI (`gh`) installed and valid GitHub and AWS credentials.

Replace `your-webapp` is the name of your repository followed by source url and `yourprofile` is the AWS profile to use (it may be `default`).

> NOTE: The source url may be either a full S3 path to a zip file, or the GitHub URL of the repository to use. (Just include the repository URL, NOT the ZIP download URL)

The cli will then create the repository, place the application starter code in it, and provide you with the clone url.

### Configure a Pipeline for Automated Deployments

Assuming you used the very basic application starter, your next step will to be set up a pipeline to deploy a test application.

If you chose an application starter beyond the basic, then you may need to set up additional infrastructure as well. Check the application starter documentation.

We will be using git-based deployments, commonly referred to as GitOps. In its simplest form, your repository will have several branches. The `dev` branch for work-in-progress, the `test` branch for deploying your application remotely, and a `main` branch fro deploying your application to production. There may be additional branches for features, staging, beta, etc, but we'll start off with these three main branches first.

As you start to develop new features you will begin with a `dev` branch. You will deploy and test changes locally on your machine. When you have working code you will then merge that code into the `test` branch. The act of merging and pushing your code to the test branch will kick off an automated deployment (you will no longer do `sam deploy` for anything other than local testing in the dev branch).

We need to create a pipeline to monitor changes pushed to the test branch and then perform the deployment process. Luckily we have pipeline templates to use and a simple procedure to create that pipeline.

You can use the configure cli script to manage your pipeline.

```bash
./cli/config.py pipeline acme your-webservice test --profile yourprofile
```

Where `pipeline` is the type of infrastructure you are creating (more on that later), `acme` is your Prefix, `your-webservice` is your application Project Identifier, `test` is the branch/deployment stage identifier, and profile is your configured profile.

The cli will then ask you to choose a template, add application deployment information, what repository and branch to monitor, and tags.

> Note: Current pipeline templates only utilize CodeCommit repositories. You can download and modify an existing template to use a GitHub or other provider as a Code Source. Store the template in the `./local-templates/pipeline` directory. When you run config.py with the `pipeline` infrastructure type, it will present you with the option to use your custom, local template.

### Deploy Pipeline infrastructure

To deploy the pipeline infrastructure stack:

```bash
./cli/deploy.py acme your-webservice test --profile yourprofile
```

This will then utilize the stored configuration and deploy the pipeline stack using `sam deploy` on your behalf. 

After the deployment is complete you should commit your configuration changes back to the central repository.

You'll notice that all the `samconfig` files are stored in the `samconfig` directory. The `deploy.py` cli provides additional functionality that `sam deploy` doesn't provide (such as S3 urls for template source).

Remember:

- Even though we are utilizing `samconfig` files to store configurations, do not edit them directly. Utilize the `config.py` cli as it will prevent `toml` format errors and can handle `parameter_overrides`, `tags`, and multiple deployment stages.
- Always commit and push your configuration changes back to the repository so that it remains current.

### Additional Infrastructure

To maintain CloudFormation best practices, and to avoid monolithic architecture, the infrastructure to support your application stack is divided into three additional functional and role-based infrastructure stacks.

1. storage: S3, DynamoDb, etc (developer, operations, data administrator role)
2. pipeline: Code Pipeline, Code Build, Code Deploy (developer or dev/ops role)
3. network: CloudFront, Route53, Certificate Manager (operations role)

Through the use of cli you can manage these stacks and store their configurations in this repository. They do not change as frequently as your application, are relatively static, do not rely on Git-based pipelines, and may be handled by different roles within your organization.

#### Storage

While your application stack is capable of managing its own S3 buckets and DynamoDb resources, it may not be efficient when the same resource can be shared among various application or deployment stages. Also, if your storage needs to already exist during the build phase of a pipeline you need to manage it externally from your application stack.

Because it is managed externally of your application stack, it does not have a StageId argument.

```bash
# Storage
./cli/config.py storage your-webservice --profile yourprofile
```

#### Network

We separate out domain names (Route53) and Content Delivery Network (CloudFormation) because they do not change as frequently as appplication code does. They are more or less static and are often handled by operations or network administrators and not left in the hands of developers.

```bash
# Network
./cli/config.py network your-webservice test --profile yourprofile
```

## Templates Should Utilize the Principle of Least Privilege

Utilize the Principle of Least Privilege through the use of resource naming and tagging. Construct IAM roles so that they limit actions to related resources. 

For example, the CloudFormation pipeline templates can only create a pipeline for applications under the same Prefix, and each pipeline can only create, delete, and modify resources under the same Prefix, ProjectId, and StageId it was created. (`acme-your-webservice-test-pipeline` cannot modify any resources named or tagged `acme-your-webservice-prod-*` or `acme-jane-webservice-test-*`).

## Updates

> Still in development

To update the cli and documentation from the GitHub repository run the `update.py` cli script.

The following settings will eventually be moved to the `defaults/settings.json` directory. For now you will need to update environment variables. You can also download a zip file (such as a prior release) and update from there.

```bash
# For Git repository
export UPDATE_SOURCE_TYPE=git
export SOURCE_LOCATION=https://github.com/63klabs/atlantis-cfn-configuration-repo-for-serverless-deployments.git
# OR for CodeCommit
export SOURCE_LOCATION=https://git-codecommit.region.amazonaws.com/v1/repos/your-repo

# For ZIP file
export UPDATE_SOURCE_TYPE=zip
export SOURCE_LOCATION=/path/to/your/archive.zip
```
