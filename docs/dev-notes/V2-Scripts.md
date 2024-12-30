There are four types of infrastructure stacks:

- service-role
- pipeline
- storage
- network

These are refered to as "infrastructure type" and pertain to specific roles and functions of what they manage and who manages them.

- service-role: The IAM Role used to create the pipeline infrastructure stack
- pipeline: the CodePipeline stack that is used to deploy changes from a repository branch (stage)
- storage: the stack that maintains S3, DynamoDb, or other resources used for data storage.
- network: the stack that maintains CloudFront distributions in front of S3 and API Gateway resources. Also maintains Route53 records and cache invalidation scripts.

For naming there are 3 identifiers:

- Prefix: typically 4-6 characters that specify a department, team, or functional area
- ProjectId: a short 4-12 character project identifier
- StageId: the stage (test, beta, prod) that corresponds to a branch (test, beta, main) 

> A few notes about StageId: Very generic stages are test, beta, stage, prod, but additional branches/stages may be created for features, fixes, developers. For example, Developer Jo may create a test branch called tjo or t-jo. Or, a developer may create a test branch for a new feature such as t98, test-feat98. A StageId does not need to be the same as the branch name. A common example is the main branch uses the StageId of `prod`. Also, because StageId has limited characters, abbreviations are typically used. While the branch may be `test-fix105` the stage could be `tfx105`.

> The stage type (test, beta, stage/staging, prod) must be specified first in the StageId either in full or by first letter (t, b, s, p).

> Stages relate to the SAM Deploy Environment BUT not to the Environment setting used as a conditional in templates for determining if it is a test or production-like environment (affecting logging level, alerts, etc.) Test stages are always in the `TEST` environment. Beta, Staging, and Prod are deployed as production-like environments under the Environment `PROD`.

Naming rules:

- Prefix, ProjectId, StageId are all lowercase
- The length of Prefix + ProjectId should not exceed 28 characters
- The length of StageId should not exceed 6 characters

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

Each infrastructure type has its own directory. The structure is like so:

- pipeline-infrastructure/templates/
- pipeline-infrastructure/samconfig-*.toml

service-role and pipeline each have a default template stored in their infrastructure template directory. These default templates are named: template-service-role.yml and template-pipeline.yml. Additional templates may be created based on the organization's needs.

A config.py script can be helpful for keeping track of stack updates, managing tags, and parameter overrides.

The config.py script will accept arguments from the user such as Prefix and ProjectId, and whether or not to check the current (deployed) stack configuration (user needs to be logged in with valid credentials)

```text
python config.py <infra-type> <Prefix> [ProjectId] [StageId] [--named-args]
```

For example pipeline which takes a Prefix, ProjectId, and StageId:

```bash
python config.py pipeline acme acctproject test --check-stack true --profile xyzdev
```

Or, similarly for service-role that only takes a Prefix

```bash
python config.py service-role acme
```

Named arguments include:

- `--check-stack` : check the currently deployed stack and use current values as a starting point.
- `--profile` : AWS_PROFILE to use when performing operations that require sending commands to AWS. (User must be logged in with valid permissions and non-expired credentials)

Then the script does the following:

1. Read in the current samconfig file (if exists)
2. If `--check-stack` is `true` then check the existing stack (user needs to have valid credentials and may need to use `--profile`)
3. If exisitng stack differs from samconfig then notify the user. Display the differences. Allow user to continue with local or deployed settings, or cancel.
4. If existing stack with tag "atlantis:TemplateFile", or existing samconfig with template_file, read in that file and grab the parameters. (if no template is named, then allow user to choose from a list of templates in the template directory for that infrastructure type.) The template_file may point to an S3 location (s3://) or local (template-pipeline.yml) If local, then the template is located in the infrastructure's template directory. (full path is not listed for local files in the tag)
5. First, prompt the user for global parameters (s3_bucket, template_file, region, confirm_changeset, role (if pipeline)). (s3_bucket, region, and role may be pre-set in a settings/defaults.json file)
6. Next, Prompt the user to enter values for each parameter. Present the existing value or default if it does not exist in square brackets as a default value if the user accepts by hitting enter. The entries should be validated based on the template's parameter definitions.
6. Save the new TOML file

Note that when StageId is used, global parameters are updated, but only the deploy environment for that stage is updated.

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

```

The deploy environment specific information follows:

```toml
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

The parameter `capabilities` is set as `CAPABILITY_IAM`

The role parameter is set only for pipeline and is set to the corresponding <PrefixUpper>-service-role arn

For generating the environment specific section the following are asked of the user:

- parameter_overrides : iterate through the template parameters

All tags are set either automatically or from a tags settings file. 

Tags starting with `Atlantis` and `atlantis:*` are automated, as are `Provisioner`, `DeployedUsing`, `Name`, `Environment`, `Stage`, `AlarmNotificationEmail`, `Repository`, and `RepositoryBranch`. 

Atlantis autogenerated tags for all types of infrastructure:

- Atlantis = `service-role|pipeline|network|storage`
- atlantis:Prefix = `<Prefix>`
- atlantis:TemplateVer = `Atlantis.v2.0.0`
- atlantis:TemplateFile = S3 location or local file name of template file used
- Provisioner = `CloudFormation`
- DeployedUsing = `AWS SAM CLI`

Additional tags for pipeline, network, and storage:

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

