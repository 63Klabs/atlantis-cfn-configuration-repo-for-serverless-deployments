# API Gateway with Lambda Backend and S3 Static Hosting

Atlantis Application Infrastructure Starter #04

> Atlantis for serverless deployments provides scripts, starter templates, and code for building serverless infrastructure using AWS SAM (Serverless Application Model). Atlantis was developed to bridge the gap between tutorials and production-ready serverless deployments. An [introductory tutorial](https://github.com/chadkluck/serverless-sam-8ball-example), and a series of [intermediate tutorials](https://github.com/chadkluck/serverless-deploy-pipeline-atlantis) are provided to get developers of all levels started in serverless.

## Uses

Deploy a static website using React, Vue, static site builder, etc, hosted on S3 along with a backend Lambda function fronted by API Gateway.

Can be used as an alternative to AWS Amplify (though [AWS Amplify](https://aws.amazon.com/amplify/) is a powerful tool you should check out as it comes with built-in storage, pipelines, custom domains, and data management).

If you don't need a Lambda function or API Gateway, the `buildspec` file contains all the code you need to build and copy source files to S3.

## Includes

- `buildspec` file that can build your static public files and copy to an existing S3 bucket for hosting.
- `frontend-src` directory that contains your web files.
- `backend-src` directory that contains a Lambda function to be used for an API fronted by API Gateway.
- `template.yml` file that includes infrastructure for API Gateway, Lambda (with X-Ray and Lambda Insights enabled), Lambda Execution Role, Alarms, Cloudwatch Logs, Cloudwatch Dashboard.

> With X-Ray, Lambda Insights, Alarms, Logging, Dashboard, and IAM policies following the principle of least privilege, you have everything you need to quickly implement a secure and observable infrastructure for your application!

## Architecture

> Stack separation is used to limit the blast radius if something goes wrong, separates the ephemeral from the persistent, and [organizes by lifecycle and ownership](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html#organizingstacks). This prevents monolithic architecture and breaks the application down into manageable pieces.

Infrastructure for this solution is separated into 4 stacks:

1. Application (API Gateway and Lambda) sourced from a code repository
2. Storage (S3)
3. Deployment Pipeline (AWS CodePipeline triggered from CodeCommit)
4. Network (CloudFront, Route53, and cache invalidation)


*Application*: API Gateway provides access to a Lambda function that can be used in the back end. Web files for a React, Vue, or other single page application (SPA) can be stored in the `frontend-src` directory. These files are built and deployed to S3 during the CodeBuild phase.

*Storage*: An S3 bucket stores static content. Multiple instances (dev, test, stage, prod, etc) can share the same bucket, each having a dedicated directory. Because this bucket serves multiple instances, doesn't change, and requires some level of persistence, it is separate from the application stack. S3 is secured via Object Access Control (OAC) and can only be publicly accessed through CloudFront.

*Deployment Pipeline*: For automated deployments, a CodePipeline can pick up changes committed to a particular branch of your repository. For example, a test pipeline will pick up changes from the test branch, deploy a test instance of Lambda, and build and copy static frontend files to the test path of S3.

*Network*: Because S3 will be using OAC, CloudFront must be placed in front to provide a custom domain name and access to the static website. CloudFront can also provide a custom domain for your API Gateway. Route53 will manage the records. Cache invalidation can be enabled to prevent old versions of files from being served when replacements are copied to S3.

## Prerequisites

- AWS CLI installed
- AWS SAM CLI installed
- A profile configured with valid AWS credentials (profile name `default` is used in the examples, be sure to change it)
- AWS credential helper configured for git

*A degree of familiarity with the Serverless Application Model and AWS*: An [introductory tutorial](https://github.com/chadkluck/serverless-sam-8ball-example), and a series of [intermediate tutorials](https://github.com/chadkluck/serverless-deploy-pipeline-atlantis) are available.

*An Atlantis template and configuration repository for serverless deployments*: Although Atlantis is not required to manage deployments, it provides scripts and organization to assist in automating and managing your deployments and is highly recommended as these templates are designed for its use. Download the Atlantis scripts and templates into a repository to manage and store your configuration files. However, if you wish, you are still able to manually deploy via the Web Console, using your own scripts, or adapting the templates to AWS CDK or Terraform.

*CloudFormation service role for deploying pipeline infrastructure*: The role you use to deploy the pipeline stack must have permission to perform CloudFormation operations, or be able to assume the CloudFormation service role provided by the Atlantis service-role template. The provided Atlantis service-role can be given to developers to assume in order to deploy and manage their own pipelines.

*Familiarity with Atlantis parameters*: Especially in regards to Prefix, ProjectId, and StageId.

## Deployment Steps

1. Create repository and initialize with code
2. Deploy storage stack
3. Deploy pipeline stack
4. Deploy network stack

### 1. Create a repository and initialize with code

Before you begin this step, you will need:

- A good name for your repository. It does NOT need to follow the Atlantis Prefix-ProjectId naming convention.
- A profile configured with valid AWS credentials.

Atlantis provides a `create_repo.py` script that will create a new CodeCommit repository and seed it with the code.

From your Atlantis template and configuration repository run the following Python script (replace `widget-inventory-website` with your repository name and `default` with the AWS profile to use. Also, `python` may be `py`, `py3`, or `python3` depending on your system):

```bash
python create_repo.py widget-inventory-website s3://63klabs/atlantis/v2/app-starter/04-apigw-lambda-s3-static.zip default
```

After successful execution of the script, it will output the URLs for cloning.

Or, if you wish to create your repository manually, `git init` or `git clone` and use the following one-liner to download and extract the files to populate the repository.

```bash
aws s3 cp s3://63klabs/atlantis/v2/app-starter/04-apigw-lambda-s3-static.zip temp.zip --profile default && unzip temp.zip && rm temp.zip
```

It is recommended you deploy the application AS-IS to make sure you have everything configured correctly. Complete the following steps before modifying the template, buildspec, or code.

### 2. Deploy storage stack

The S3 bucket for hosting your website needs to be deployed so the pipeline build phase has somewhere to copy the files to.

You can use the Storage Infrastructure template provided by Atlantis:

- `s3://63klabs/atlantis/v2/infrastructure/storage/template-storage-s3-oac-for-cloudfront.yml`
- `https://63klabs.s3.amazonaws.com/atlantis/v2/infrastructure/storage/template-storage-s3-oac-for-cloudfront.yml`
- Or, from your Atlantis template and configuration repository: `infrastructure/storage/templates/template-storage-s3-oac-for-cloudfront.yml`

Atlantis provides a `config.py` script that walks you through configuration.

From your Atlantis template and configuration repository (Replace `acme` with your Prefix, and `widget-inventory-site` with your ProjectId):

```bash
python config.py storage acme widget-inventory-site
```

Then deploy using the sam command found in the generated `samconfig` file. For example:

```bash
cd infrastructure/storage
sam deploy --config-env default --config-file samconfig-acme-widget-inventory-site-storage.toml --profile default
```

### 3. Deploy a pipeline stack that will automatically deploy your application stack after code commits

You will need one pipeline per deployment stage, and each deployment stage is tied to a branch. For example, when you have `dev`, `test`, `staging`, and `main` branches you would skip `dev` and have `test`, `staging`, and `prod` stages respectively. (You typically don't have a pipeline for the `dev` branch as a developer could be committing non-working code, and will most likely perform builds and run deployments locally during development). 

You can use the Pipeline Infrastructure template provided by Atlantis:

- `s3://63klabs/atlantis/v2/infrastructure/pipeline/template-pipeline.yml`
- `https://63klabs.s3.amazonaws.com/atlantis/v2/infrastructure/pipeline/template-pipeline.yml`
- Or, from your Atlantis template and configuration repository: `infrastructure/pipeline/templates/template-pipeline.yml`

Atlantis provides a `config.py` script that walks you through configuration. 

From your Atlantis template and configuration repository:

```bash
python config.py pipeline <prefix> <project-id> <stage-id>
```

Then deploy using the sam command found in the generated `samconfig` file. For example:

```bash
cd infrastructure/pipeline
sam deploy --config-env test --config-file samconfig-acme-widget-inventory-site-pipeline.toml --profile default
```

### 4. Deploy a network stack

For custom domains, and to access S3 using OAC (Object Access Control), you will need CloudFront, Route53, and cache invalidation, all provided by the Network Infrastructure template.

You will need one network stack per test, staging, or production deployment.

You will need two things first:

1. A hosted zone in Route53 (obtain the Hosted Zone ID)
2. A certificate valid for the domain you plan on using in Amazon Certificate Manager (obtain the Arn of the certificate)

You can use the Network Infrastructure template provided by Atlantis:

- `s3://63klabs/atlantis/v2/infrastructure/network/template-route53-cloudfront-s3-apigw.yml`
- `https://63klabs.s3.amazonaws.com/atlantis/v2/infrastructure/network/template-route53-cloudfront-s3-apigw.yml`
- Or, from your Atlantis template and configuration repository: `infrastructure/network/templates/template-route53-cloudfront-s3-apigw.yml`

Atlantis provides a `config.py` script that walks you through configuration.

From your Atlantis template repository:

```bash
python config.py network acme widget-inventory-site test
```

Then deploy using the sam command found in the generated `samconfig` file. For example:

```bash
cd infrastructure/network
sam deploy --config-env test --config-file samconfig-acme-widget-inventory-site-network.toml --profile default
```

Note the use of `--config-env test`. If you configured a staging or production deployment you can use `stage` or `prod` respectively.

## More Information

A tutorial is available from the repository.

## Author

Chad Leigh Kluck, Software Engineer, AWS Certified, [Website](https://chadkluck.me)
