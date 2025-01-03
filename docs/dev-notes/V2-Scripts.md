# Atlantis for AWS SAM Deployments

Atlantis is a collection of starter SAM configuration files, CloudFormation templates, and application scripts and code for deploying near-production ready serverless applications. Their intent is to bridge the gap between example code and real-world implementations. Once a foundational understanding of Serverless and CloudFormation is acheived, these can serve as a start to developing production-ready applications.

Though a basic starter deployment using the Serverless Application Model (SAM) can generate an API Gateway and Lambda resource in as few as two dozen YAML lines, it doesn't provide all the best practices of least privilage, logging and monitoring, automated deployments, and cost monitoring. Atlantis aims to build many of these pieces in.

To maintain CloudFormation best practices, and to avoid monolithic architecture, the templates are divided into five functional and role-based infrastrucure stacks.

1. service-role (security and operations)
2. storage (developer, operations, data adminstrator role)
3. application (developer role)
4. pipeline (developer or dev/ops role)
5. network (operations role)

The service-role and pipeline infrastructure stacks (1 & 4) support the automated deployment of applications. The service, application, and network infrastructure stacks (2, 3, & 5) supports the application.

## Quick Usage Example

AWS CLI, AWS SAM, Python, and Boto PIP library must be installed first.

Generate a `samconfig` file by running the `config.py` script and filling in the prompts. (`acme` is used as an example for the naming Prefix value.)

```bash
cd scripts
python config.py service-role acme
```

Deploy using the toml file you just created.

```bash
cd ./service-role-infrastructure
sam deploy --config-env default --config-file samconfig-acme-service-role.toml --profile default
```

In this example, `acme` is used as the Prefix. More on that later. The short explaination is that Prefix can be thought of as a 3 to 6 character name-space describing the team, department, or functional area that will be developing applications under the given Prefix. This prefix is used in resource names and tags to provide organization and IAM permissions for service and execution roles. (Team `finc` cannot modify Team `mktg` applications.) Even if AWS Organizations is used to separate organizational units into their own accounts, it can be helpful to further divide a functional area's applications from dev/ops scripts and resources.

## Order of Operations

The *service-role* is set up for a team or department once. This creates boundaries used by the pipeline and should be done first.

Before development on a new project begins, the developer works with operations to set up *storage* for the application. 

The developer then creates a repository and starts working on the *application* infrastructure. 

When the application is ready for a test deployment, the developer works with Dev/Ops to establish the *pipeline*. 

Once the application is ready for production, or is at the stage where custom domains and certificates are required, the developer works with the networking operations team to create the *network* stack.

## Infrastructure Descriptions

We'll start with application infrastructure since the role associated with it, deployment strategies, and deployment frequencies are completely different than the rest of the stacks.

*Application Infrastructure* is deployed using git-based actions. When new code is committed to a branch it is picked up by a pipeline which performs automated deployments. These deployments are frequent and the primary user that interacts with the application infrastructure is the developer. Because of the frequent nature of deployments, and its functional role, application infrastructure is kept separate, in its own repository, from the remaining four infrastructure configurations.

The remaining four infrastructure stacks all support application deployment and infrastructure. These stacks are deployed manually from the command line using `sam deploy` and their configurations are maintained in `samconfig.toml` files. Their structure does not change often and are typically put in the hands of DevOps and Platform engineers. They often share the same templates and when the templates receive updates such as best practice, feature, or security enhancements, they are re-deployed across all stacks sharing the same template.

*Service Role* is created once per team, department, or functional area, and contains the IAM policy used to create the pipeline. Permission to assume this role can be granted to a developer, senior developer, or dev/ops engineer. Because the scope is limited to creating Code Pipeline resources in a specific name-space, the permissions are pretty-much self-maintained. However, the privlages associated with this role extend to the ability to create, modify, and destroy ALL pipeline stacks under the naming Prefix. (The service role template could be modified to not allow deletions, allowing deveopers to create, but not modify or delete pipeline stacks.)

A *Pipeline* is created for each application deployment. An application may have two deployments (test and production), three (test, beta, production) or more (test, test-jo, test-hotfix98, beta, production). Pipelines take the changes committed to a specific branch of a repository and performs the necessary deploy operations based on the buildspec and CloudFormation template. In order to create a pipeline a user must have the permissions to assume the Service Role for that team. The pipeline template also specifies what resources may be created, modified, or deleted in the application infrastructure stack. The starter pipeline template contains permissions to create Event, API Gateway, Lambda, Step Functions, CloudWatch, DynamoDb, and S3 resources among others. This template can be copied and extended to allow for additional resources to be maintained.

*Storage* infrastructure doesn't change as frequently as application code and is typically more permanent. Also, resources such as S3 typicaly have standard security and access policies that should be maintained in a central location, independent of development activities. Also, storage can often be partitioned so that it can be shared among instances of the same application. (Access policies, encryption, and hashes unique to the application can be used.) If storage cannot be shared among instances of the same application, S3 and DynamoDb resources can always be included in the application infrastructure template.

*Network* infrastructure, like storage, doesn't change as frequently as application code. Changes to Route53 and CloudFront can take a while to propagate, and such changes are typically not handled by those in the developer role. Cache invalidation, routing, certificates, and policies also take up a great amount of the template. To separate out the roles and functionality, the Network stack takes care of the responsibility of maintaining DNS and CDN.

## Shared Parameters and Naming

While the service role encompanses all the projects for a department, team, or functional area, the pipeline, storage, application, and network stacks are application project and deployment specific. 

Storage may serve all deployments of an application. If an application needs its own storage unit per deployment (test, prod) then the storage can be included in the application infrastructure. However, many times, storage can be divided or partitioned.

Pipelines are per deployment stage. Typically there will be a test, beta/staging, and production deployment. Sometimes for features there may be a test branch deployment for a particular feature. Pipelines may be created or destroyed as needed.

Networking is for each deployment that requires a custom domain or S3 buckets that require access through the web for public assets such as hosting a web site.

### Naming

To tie resources together a common set of parameters and tags are used. Permission sets are also used to make sure that the application pieces are only accessed by the application. IAM permissions are based on either the resource name (`ACME-helloworld-test-*`) or tag (`atlantis:Application = ACME-helloworld`).

Use of Prefix, ProjectId, and StageId are important components of resource naming and tagging.

- Prefix: typically 4-6 characters that specify a department, team, or functional area
- ProjectId: a short 8-20 character project identifier
- StageId: the stage (test, beta, prod) that corresponds to a branch (test, beta, main) 

> A few notes about StageId: Very generic stages are test, beta, stage, prod, but additional branches/stages may be created for features, fixes, developers. For example, Developer Jo may create a test branch called tjo or t-jo. Or, a developer may create a test branch for a new feature such as t98, test-feat98. A StageId does not need to be the same as the branch name. A common example is the main branch uses the StageId of `prod`. Also, because StageId has limited characters, abbreviations are typically used. While the branch may be `test-fix105` the stage could be `tfx105`.

> The stage type (test, beta, stage/staging, prod) must be specified first in the StageId either in full or by first letter (t, b, s, p).

> Stages relate to the SAM Deploy Environment BUT not to the Environment setting used as a conditional in templates for determining if it is a test or production-like environment (affecting logging level, alerts, etc.) Test stages are always in the `TEST` environment. Beta, Staging, and Prod are deployed as production-like environments under the Environment `PROD`.

Naming rules:

- Prefix, ProjectId, StageId are all lowercase
- The length of Prefix + ProjectId should not exceed 28 characters
- The length of StageId can not exceed 6 characters

Maintaining stack parameter overrides and tags manually can be cumbersome, so Atlantis improves this by having consistent Parameters and Tagging across infrastructure stacks and scripts that generate and maintain samconfig files.

The naming convention for stacks are as follows:

- `<PrefixUpper>-service-role`
- `<Prefix>-<ProjectId>-storage`
- `<Prefix>-<ProjectId>-<StageId>-pipeline`
- `<Prefix>-<ProjectId>-<StageId>-network`

Similar names are used to name the samconfig files.

- `samconfig-<PrefixUpper>-service-role.toml`
- `samconfig-<Prefix>-<ProjectId>-storage.toml`
- `samconfig-<Prefix>-<ProjectId>-pipeline.toml`
- `samconfig-<Prefix>-<ProjectId>-network.toml`

> Note that StageId is used as the SAM deployment environment. (service-role and storage only have a `default` deploy environment and do not accept StageId)

## Repository Structure

It is recommended that new applications are started by creating a separate repository for the application and copying over one of the application examples from this repository.

### Infrastructure

Each infrastructure type has its own directory. The structure is like so:

- `*-infrastructure/templates/`
- `*-infrastructure/samconfig-*.toml`

Starter templates are already provided for each infrastructure type within the templates directory. These may be selected when a configuration script is ran for a new stack.

After the configurations script executes, a samconfig file for that stack is generated and stored in the infrastructure directory. The `sam deploy` command may then be used to deploy the new stack or perform changes on an existing stack.

### Scripts

A config.py script is provided to facilitate stack updates, managing tags, and parameter overrides.

## Initial Set-Up

AWS CLI, AWS SAM, Python, PIP, and Boto need to be installed first. Though the `python` command is used in the examples, your system may require the use of the `python3` command.

Create a repository to store the templates and configuration files. You will use this to maintain settings and structure. Download and unzip the contents of Atlantis for AWS SAM Deployments into that repository.

Most likely you will only have one branch (main) since there is no use, and it could be confusing, to have additional branches. The repository should always reflect the current state of your stacks so be sure everyone pulls and pushes changes after deployments.

Create the service-role infrastructure stack. You will need the following:

- Prefix: A 3-6 character descriptor of the team, department, or functional area that will be developing applications under that prefix.
- Permissions boundary ARN if your organization requires it.
- Role Path if your organization requires it (or you can decide to impose one)

Execute the configuration script to generate the sam config file and fill in the prompts (`acme` is used as an example for the Prefix):

```bash
cd scripts
python config.py service-role acme
```

Fill in the prompts. The sam config file will be stored in the `service-role-infrastructure directory`. Change directories and deploy. (Make sure `--profile default` reflects an `AWS_PROFILE` that has permissions to deploy)

```bash
cd ./service-role-infrastructure
sam deploy --config-env default --config-file samconfig-acme-service-role.toml --profile default
```

## Configuration Script

The config.py script will accept arguments from the user such as Prefix and ProjectId, and whether or not to check the current (deployed) stack configuration (user needs to be logged in with valid credentials)

```text
python config.py <infra-type> <Prefix> [ProjectId] [StageId] [--named-args]
```

For example pipeline which takes a Prefix, ProjectId, and StageId:

```bash
python config.py pipeline acme process-acct test --check-stack true --profile xyzdev
```

Or, similarly for service-role that only takes a Prefix

```bash
python config.py service-role acme
```

Named arguments include:

- `--check-stack` : check the currently deployed stack and use current values as a starting point.
- `--profile` : AWS_PROFILE to use when performing operations that require sending commands to AWS. (User must be logged in with valid permissions and non-expired credentials)

Then the script does the following:

1. Reads in the current samconfig file (based on infrastructure type and naming convention - if exists)
2. If `--check-stack` is `true` then it checks the existing stack (user needs to have valid credentials and may need to use `--profile`)
3. If exisitng stack configuration differs from samconfig then the user is notified. The script will display the differences. The user will then be allowed to continue with either the local or deployed settings, or cancel.
4. If it is an existing stack with tag "atlantis:TemplateFile", or existing samconfig with template_file, read in that file and grab the CloudFormation parameters. The `template_file` may point to an S3 location (`s3://`) or local file (such as template-pipeline.yml). If local, then the template is located in the infrastructure's template directory. (Full path is not listed for local files in the tag)
5. If no stack and no samconfig exists, then the script will allow user to choose from a list of templates discovered in the templates directory for that infrastructure type. Default global values will be read in from default.json files specific to Prefix and/or ProjectId.
6. After the script examines the template file, the user will be prompted for global deploy parameters (`s3_bucket`, `template_file`, `region`, `confirm_changeset`, and `role` (if pipeline)). (`s3_bucket`, `region`, and `role` may be pre-set in a settings/defaults.json file)
7. Next, the user will be prompted to enter values for each parameter. Existing or default values will be presented in square brackets. This value will be used if the user accepts it by leaving the prompt blank and hitting enter. (if the user types in `-`, `?`, or `^` and presses enter the script will clear out the default value, provide help information, or exit script respectively. The entries should be validated based on the template's parameter definitions.
6. The script will then save the TOML file. If a StageId was provided as a script argument then that will be the sam deployment environment. Otherwise (for service-role and storage which do not have stages) `default` will be used.

Note that when StageId is used, global parameters are updated and affect all deployments for that project, but the only deploy environment parameters updated is for that stage.

The toml file uses the following format:

```toml
version = 0.1

# !!! DO NOT EDIT THIS FILE !!!

# Make changes and re-generate this file by running the python script:

# python $SCRIPT_NAME$ $SCRIPT_ARGS$

# Using the script provides consistent parameter overrides and tags and ensures your changes are not overwritten!


[global.deploy.parameters]
s3_bucket = "$S3_BUCKET_FOR_DEPLOY_ARTIFACTS$"
template_file = "$TEMPLATE_FILE$"
region = "$REGION$"
confirm_changeset = $CONFIRM_CHANGESET$
capabilities = [$CAPABILITIES$]
$ROLE_ARN$

[default.deploy.parameters]
# =====================================================
# default Deployment Configuration

# Deploy command:
# sam deploy --config-env default --config-file samconfig-acme-service-role.toml --profile default

# Do not update this file!
# To update parameter_overrides or tags for this deployment, use the generate script:
# python service-role.py acme

stack_name = "acme-service-role"
s3_prefix = "acme-service-role"
parameter_overrides = "\"S3BucketNameOrgPrefix\"=\"acmeco\" \"RolePath\"=\"/acmeco_app_roles/\" \"PermissionsBoundaryArn\"=\"arn:aws:iam::123456789012:policy/xyz-org-boundary-policy\" \"PrefixUpper\"=\"ACME\" \"Prefix\"=\"acme\""
tags = "\"Atlantis\"=\"service-role\" \"atlantis:Prefix\"=\"acme\" \"Provisioner\"=\"CloudFormation\" \"DeployedUsing\"=\"AWS SAM CLI\" \"atlantis:TemplateVer\"=\"Atlantis.v2.0.0\" \"atlantis:TemplateFile\"=\"template-service-role.yml\""
```

For generating the global section, the only parameters asked from the user are:

- s3_bucket
- template_file
- region
- confirm_changeset
- role (if pipeline)

The parameter `capabilities` is set as `CAPABILITY_NAMED_IAM`

The role parameter is set only for pipeline and is set to the corresponding `<PrefixUpper>-service-role` arn.

For generating the environment specific section the following are asked of the user:

- `parameter_overrides` : iterate through the template parameters

All tags are set either automatically or from a tags settings file. 

Tags starting with `Atlantis` and `atlantis:` are automated, as are `Provisioner`, `DeployedUsing`, `Name`, `Environment`, `Stage`, `AlarmNotificationEmail`, `Repository`, and `RepositoryBranch`. These tags cannot be overridden and are ignored if present in tags.json files.

Atlantis specific tags such as `atlantis:ApplicationDeploymentId` and `atlantis:Application` are used in IAM policies such as Service and Execution Roles, granting access to resources specific to that application or project. It is recommended you utilize these tags to provision policies that represent the principle of least privilage. These tags can also be used for observability and cost reporting.

Atlantis autogenerated tags for all types of infrastructure:

- Atlantis = `service-role|pipeline|network|storage`
- atlantis:Prefix = `<Prefix>`
- atlantis:TemplateVer = `Atlantis.Pipeline.v2.0.0` (From comment section at top of template)
- atlantis:TemplateFile = S3 location or local file name of template file used
- Provisioner = `CloudFormation`
- DeployedUsing = `AWS SAM CLI` (Application Infrastructure stacks will be `CodePipeline`)

Additional tags for application, pipeline, network, and storage:

- atlantis:Application = `<Prefix>-<ProjectId>`
- Name = `<Prefix>-<ProjectId>`

Additional tags for pipeline and network:

- atlantis:ApplicationDeploymentId = `<Prefix>-<ProjectId>-<StageId>`
- Environment = `DEV|TEST|PROD` (The overall environment - used to provision alarms, log level, etc)
- Stage = `<StageId>`
- AlarmNotificationEmail = `Email` (if AlarmNotificationEmail is present as a stack parameter)

Additional tags just for pipeline:

- Repository = `[github: | gitlab: | codecommit: ]<repository-name>`
- RepositoryBranch = `<branch>`

> Some tags are duplicates such as Name, Provisioner, etc because they are widely used outside of Atlantis.

Custom tags are set by the user in json files stored in the settings directory. These could be used for departments, designating owners, cost centers, or other pieces of information. They are brought in in the following order:

1. `scripts/settings/tags.json`
2. `scripts/settings/tags-<Prefix>.json`
3. `scripts/settings/tags-<Prefix>-<ProjectId>.json`
5. `scripts/settings/<infra-specific>/tags.json`
6. `scripts/settings/<infra-specific>/tags-<Prefix>.json`
7. `scripts/settings/<infra-specific>/tags-<Prefix>-<ProjectId>.json`

Finally, any remainging tags (except atlantis reserved tags) are read in from the deployed stack or existing toml file for that deployment.

(If an infrastructure template does not use ProjectId or Stage, then it does not check for such file).

These rules apply when loading in tags:

1. Any settings for the same tag in a later file overwrites that of an earlier file
2. Each file only contains keys and values that are unique/different from an earlier loaded file. This keeps the files small.
3. There are no empty files. If nothing changes from the previously loaded file to the next, the file with no changes is skipped/deleted.

The format for the tag json file is:

```json
[
	{
		"Key": "<tag-key1>",
		"Value": "<tag-value>"
	},
	{
		"Key": "<tag-key2>",
		"Value": "<tag-value>"
	}
]
```

