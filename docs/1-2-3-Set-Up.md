# Set Up: Easy as 1-2-3!

1. Create an IAM Role for your CloudFormation Service using the scripts and CLI commands
2. Create a CodeCommit repository for your code and place `/application-infrastructure/` at the root.
3. Create a CloudFormation Pipeline stack using the scripts and CLI commands

In these examples we will use the Prefix `acme`.

> These instructions use the AWS CLI. [Web Console documentation](./Set-Up-via-Web-Console.md) and [AWS CDK and Terraform documentation](./Set-Up-via-Terraform-or-CDK.md) is also available.

#### Step 1: Create Service Role

> Make sure you have the proper [permissions to create a role](./Set-Up-User-Role.md).

There needs to be one service role created per Prefix.

From the `scripts/` directory run `python service-role.py acme` replacing `acme` with your prefix and following on-screen prompts.

Follow instructions displayed after script has run. A copy of the CLI commands will be stored in `iam-cloudformation-service-role/`.

#### Step 2: Create a CodeCommit Repository for Your Application

Place the `application-infrastructure/` directory at the root of your repository.

Commit your code and then create and push a `dev` and `test` branch in addition to your `main` branch.

Your repository is now primed for the next step.

#### Step 3: Create the Pipeline

From the `scripts/` directory, run `python pipeline.py acme hello-world test` replacing `acme` and `hello-world` with appropriate values (your Prefix and Project Id). Leave test as is.

Follow on-screen prompts.

Follow instructions displayed after script has run. A copy of the CLI commands will be stored in `cloudformation-pipeline-template/`

Once you have a successful deploy, create your Production pipeline:

`python pipeline.py acme hello-world prod`

Follow the same on-screen and CLI steps as you did for your test pipeline.

## Tutorials and Additional Documentation

There are various [tutorials](./Tutorials.md) that will help walk you through your first deployment and get you familiar with your options. If you are new to AWS CodePipeline and SAM, then the tutorials are a great resource in helping you learn about the process.

Additional documentation is found in the /docs/ directory as well as /scripts/ and /application-infrastructure/

- [User Role Set-Up](./User-Role-Set-Up.md)
- [1-2-3 Set-Up](./1-2-3-Set-Up.md)
- [Set-Up via Web Console](./Set-Up-via-Web-Console.md)
- [Set-Up via Terraform or CDK](./Set-Up-via-Terraform-or-CDK.md)
- [Pipeline Parameters Reference](./Pipeline-Parameters-Reference.md)
- [Tutorials](./Tutorials.md)
- [Scripts and CLI](../scripts/README-CLI.md)
- [Updating the Pipeline Stack](./Updating-Pipeline-Stack.md)
- [Deleting and Clean-Up](./Deleting-and-Clean-Up.md)
