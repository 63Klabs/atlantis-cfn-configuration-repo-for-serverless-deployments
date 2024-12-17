# Scripts and CLI Commands

> To keep this document brief, it is assumed you have Python and AWS CLI installed, have reviewed the [READ ME](../README.md) document in the root of this repository which explains how to use IAM and CloudFormation to maintain a pipeline stack, and have basic knowledge of how the Atlantis project can be utilized. You don't have to be an expert AWS user, as Atlantis is set up to get even novices started in AWS deployments, but you should at least be comfortable answering prompts provided by the script and copy-pasting the generated commands.

These scripts will allow you to save tags, parameters, and the CLI commands for each project allowing you to quickly create, update, duplicate, delete, and recreate projects in seconds. The scripts will prompt for parameters and then generate and save CLI commands and input files. You can then save these files in a repository for re-use.

Before you begin make sure you have Python installed, know the answers to the questions you will be prompted for (Prefix, permission boundaries, account ID, etc), and have access to execute the AWS CLI commands `iam create-role`, `iam put-role-policy`, `cloudformation create-stack`, and `cloudformation describe-stacks`. If you do not have access to execute these commands you can provide an administrator the generated CLI commands and input files.

When you execute the scripts, instructions for filling out the prompts will be provided including "help" options. After executing the scripts, CLI input and command files will be generated and stored in the `/cloudformation-pipeline-template/pipelines/` and `/iam-cloudformation-service-role/roles/` directories.

The scripts only provide copy-paste CLI commands and CLI input files and DO NOT execute the commands. They simply assist in automating the input file generation process and provide consistent creation, management, and tagging of your service role and deployment pipeline stacks.

## Create Service Role using AWS CLI

You will need to create a service role to use for creating the CloudFormation stack that manages your pipeline.

(Note: Depending on your Python installation, you may need to use `python` or `python3` to invoke the script.)

Execute the script and provide the Prefix for the service role you wish to create.

`python service-role.py <prefix>`

Note that values entered for previous runs of this script will be listed in square brackets so they can be accepted as a default value by pressing `Enter`. They can always be over-written with new values.

Prompts:

- Prefix
- S3 Bucket Name Organization Prefix
- AWS Account ID
- AWS Region
- Role Path
- Permissions Boundary ARN

For additional information on what to enter for these prompts, refer to the root [READ ME](../README.md) or follow on-screen instructions during the execution of the script.

After values are given for each of the prompts, CLI commands and a policy file (.txt and .json respectively) will be saved to the /iam-cloudformation-service-role/roles/ directory. The trust policy is stored in the /iam-cloudformation-service-role/ directory and is the same for every service role.

## Create Pipeline Stack using AWS CLI

(Note: Depending on your Python installation, you may need to use `python` or `python3` to invoke the script.)

Execute the script and provide the Prefix, Project ID, and Stage ID as arguments for the pipeline you wish to create.

`python pipeline.py <prefix> <project_id> <stage_id>`

This script will check for any settings previously entered for the service-role script such as Role Path, S3 Bucket Name Organization Prefix, and Permissions Boundary ARN and present them as defaults.

Also, any stack parameter values which may overlap with values entered for previous runs of this script will be listed in square brackets so they can be accepted as a default value by pressing `Enter`. They can always be over-written with new values.

Prompts:

- Cloudformation Pipeline Stack Template
    - BucketName
    - BucketKey
    - FileName
- Stack Parameters
    - Prefix
    - Project ID
    - Stage ID
    - S3 Bucket Name Organization Prefix
    - Role Path
    - Deploy Environment
    - Parameter StoreHierarchy
    - Alarm Notification Email
    - Permissions Boundary ARN
    - CodeCommit Repository
    - CodeCommit Branch
- Application Information
    - Name
    - Service Role ARN

For additional information on what to enter for these prompts, refer to the root [READ ME](../README.md) or follow on-screen instructions during the execution of the script.

After values are given for each of the prompts, CLI commands and an input file (.txt and .json respectively) will be saved to the /cloudformation-pipeline-template/pipelines/ directory. You must also upload, or have access to an existing, CloudFormation template yaml file in S3.

## .gitignore

To prevent uploading settings to your repository, all generated files (CLI prompts, input files, tags, defaults, etc) are automatically excluded from commits by the `.gitignore` file found in the /scripts/, /cloudformation-pipeline-template/pipelines/, and /iam-cloudformation-service-role/roles/ directories.

However, there is no reason you can't store these files in a repository. Simply delete or comment the lines in those (and only those) 3 .gitignore files.

## Saved Defaults

In the /scripts/settings/cfn/ and /scripts/settings/iam/ directories you will find `.defaults.json` files containing default values. While you can modify these files directly, you may wish to re-run the script instead.

Default values for both tags and parameters are loaded in a hierarchical order, each set of values over-writing the previous. For example, an `AwsAccountId` value of `123456789012` in .defaults.json would be over-written by a value of `987654321098` found in `.defaults-acme.json`.

If the `service-role` script was executed with the `acme` prefix:

`python service-role.py acme`

Then the script would look for, and load in, `/iam/.defaults.json` followed by `/iam.defaults-acme.json`. Whether or not these files are found and loaded are displayed when the script runs.

The same is performed for `.tags.json` and `.tags-acme.json`. (More on tags in the following section)

If `.defaults-acme.json` did not exist, it would be created after the prompts are answered. If the file did exist, it would be updated with new values from the prompts.

`.defaults.json` is always updated with the latest information from the prompts.

When you run the `pipeline-stack` script, the defaults for IAM will be loaded first, then the defaults for pipelines, prefix, project, and stage.

For example, if the `pipeline-stack` script was executed with the `acme` prefix, `order-api` project ID, and `test` stage:

`python service-role.py acme order-api test`

Then the following files would be loaded in this order:

1. /settings/iam/.defaults.json
2. /settings/iam/.defaults-acme.json
3. /settings/cfn/.defaults.json
4. /settings/cfn/.defaults-acme.json
5. /settings/cfn/.defaults-acme-order-api.json
6. /settings/cfn/.defaults-acme-order-api-test.json

Don't worry, these files are generated for you based upon how you answer the prompts presented by the script.

Tag values are loaded in a similar fashion.

## Custom Tags

In the /scripts/settings/cfn/ and /scripts/settings/iam/ directories you will find `sample.tags.json` files for tags. You can copy these files, remove the `sample.`, and modify them to define your own. 

The scripts do not prompt for tags, so if you wish to tag your service role and pipeline resources you will need to add `.tags.json` files. Use the samples provided.

The format is an array of objects with Key and Value properties:

```json
[
	{
		"Key": "Department",
		"Value": "Web Services"
	},
	{
		"Key": "Creator",
		"Value": "John Doe"
	}
]
```

In your IAM folder, you can specify tags to apply to all your Service Roles in `.tags.json` and then tags specific to a prefix in `.tags-amce.json`.

Similarly, in your CFN folder, you can specify tags to apply to all your pipeline resources in `.tags.json`, prefix `.tags-acme.json`, project `.tags-acme-order-api.json` and test stage `.tags-acme-order-api-test.json`.

Note that unlike `.defaults.json`, the pipeline-stack script does not read in tags from the IAM directory.

## Custom Parameters

The /scripts/settings/cfn/ directory has `sample.params.json` for custom CloudFormation parameters for CodePipeline stacks. However, these custom parameters are only for customized Pipeline templates as the only accepted parameters for Atlantis out of the box are already available via prompts. Also note that any custom parameters added will not be prompted for. So, unless you add your own custom parameters to the CloudFormation template for the pipeline, you do not need to worry about `params.json`. (This does not affect your application CloudFormation template.)

```json
{
	"StateMachineArn": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
	"SGArn": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
}
```

You should add application specific parameters to your application's CloudFormation template. These custom parameters should be reserved for parameters relating to your CodePipeline.

## Recommended Use

In practice you will most likely separate out the scripts, IAM service role files, and CloudFormation Pipeline template from your application infrastructure repository. For example, if you have two projects, acme-orders-api and acme-subscription-api, you would most likely have three repositories. One for each of the projects, and another containing the pipeline and service role templates along with the scripts.

Orders API Repository:

- acme-orders-api-repo
    - application-infrastructure/
        - template.yml
        - src/
        - ...

Subscription API Repository:

- acme-subscription-api-repo
    - application-infrastructure/
        - template.yml
        - src/
        - ...

Pipeline Infrastructure Repository:

- pipeline-infrastructure-repo
    - cloudformation-pipeline-template/
        - pipelines/
        - template-pipeline.yml
        - ...
    - iam-cloudformation-service-role/
        - roles/
        - Trust-Policy-for-Service-Role.json
        - ...
    - scripts/
       - settings/
       - pipeline.py
       - service-role.py
       - ...
    - README.md

## Updating Pipeline Stacks

When the `pipeline-stack` script is run, the CLI file generated includes commands to create the stack as well as update the stack.

The commands used to update the stack are similar to the following:

```
# -----------------------------------------------------------------------------
# UPDATE STACK
# Update stack using change-set: After updating tags, parameters, and re-running pipeline.py, issue the following commands to update.
# Be sure to modify values as needed (such as whether to 'no-use-previous-template' or 'include-nested-stacks')
# https://awscli.amazonaws.com/v2/documentation/api/latest/reference/cloudformation/create-change-set.html

cd ../cloudformation-pipeline-template/pipelines/acme/hello-world/

aws cloudformation create-change-set \
    --stack-name acme-hello-world-test-pipeline \
    --change-set-name acme-hello-world-test-pipeline-DVGj-20240328161937 \
    --client-token TUyigVDVGj \
    --change-set-type UPDATE \
    --no-use-previous-template \
    --include-nested-stacks \
    --cli-input-json file://../scripts/cli/cfn/input-update-stack-acme-hello-world-test.json

aws cloudformation execute-change-set \
    --stack-name acme-hello-world-test \
    --change-set-name acme-hello-world-test-pipeline-DVGj-20240328161937 \
    --client-request-token TUyigVDVGj
```

Reasons you will want to update the pipeline stack include, but are not limited to, changing parameter values, updating CloudFormation Service Role for the infrastructure stack and changing the way the pipeline executes.

If you are updating the pipeline template be sure to update the location of the template when you fill in the script's prompts, and upload a new copy to S3.
