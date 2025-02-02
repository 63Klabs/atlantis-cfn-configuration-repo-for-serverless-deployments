# Atlantis Configuration Repository for Serverless Deployments using AWS SAM

## Prerequisites

1. AWS CLI installed
2. AWS SAM CLI installed
3. Git installed
4. Configured AWS profile with valid credentials

## Install and Set Up

1. Create a repository with a name similar to `cfn-sam-configurations`
2. Place the files from this repository into it.
3. Perform the following operations:

### Make scripts executable

If using Linux or Mac OS, make the scripts executable.

```bash
chmod +x ./scripts/*.py
chmod +x ./scripts/*.sh
```

Doing this allows you to execute the scripts without having to specify `python`, `python3`, or `bash`. You can just do this:

```bash
./scripts/config.py service-role acme
```

### Configure default deployment configuration settings

1. Determine a Prefix to use: A Prefix can be considered a namespace that groups your applications and permissions by organizational unit or team. It further divides the naming of resources in your AWS Account even if you practice separation of units among AWS Organization Accounts.
2. Gather any Role Path and Permissions Boundaries information from your AWS administrator. Developers will need to be able to create execution roles. If there are requirements around Role Paths and Permissions Boundaries to use, then we will need that to create the service role and require the developers to utilize when deploying their application templates.

### Create the service role

The service role is what gives developers the proper permissions to manage their pipelines for automated application deployments. It restricts them to the creation of pipeline resources with tags and naming that fall under the assigned Prefix, and enforces the Role Path and Permissions Boundaries. The pipeline further enforces these permission constraints on the application resources being deployed.

The service role prevents developers from deploying AWS resources they are not permitted to deploy, and ensures that each application stack manages only those resources it is allowed under the Prefix naming and tagging convention.

Ensure your AWS CLI has valid credentials. If you are not using the default profile, be sure to add `--profile` to the commands. We will specify the `default` profile in these examples. Also, in these examples, we will use `acme` as the Prefix.

```bash
./scripts/config.py service-role acme --profile default
```

You will be given a series of prompts. If you are asked for a template to use, choose `template-service-role-pipeline.yml`.

