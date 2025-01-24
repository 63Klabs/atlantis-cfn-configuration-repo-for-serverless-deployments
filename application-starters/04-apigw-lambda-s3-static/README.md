# API Gateway with Lambda Backend and S3 Static Hosting

> This is Atlantis Application Starter #04. Atlantis provides helper scripts and starter templates and code for building serverless applications using AWS SAM (Serverless Application Model). Atlantis was developed to bridge the gap between tutorials and production ready serverless applications and deployments. An [introductory tutorial](https://github.com/chadkluck/serverless-sam-8ball-example), and a series of [intermediate tutorials](https://github.com/chadkluck/serverless-deploy-pipeline-atlantis) are provided.

## Uses

Deploy a static website using React, Vue, static site builder, etc, hosted on S3 along with a backend Lambda function fronted by API Gateway.

Can be used as an alternative to AWS Amplify (though [AWS Amplify](https://aws.amazon.com/amplify/) is a powerful tool you should check out as it comes with built-in pipelines, custom domains, and data management).

If you don't need a Lambda function or API Gateway, the `buildspec` file contains all the code you need to build and copy source files to S3.

## Includes

- `buildspec` that can build your static files (React, Vue, static, etc) and copy to an existing S3 bucket for hosting.
- `frontend-src` directory that contains your web files.
- `backend-src` directory that contains a Lambda function that can be used for an API fronted by API Gateway.
- `template.yml` file that includes infrastructure for API Gateway, Lambda (with X-Ray and Lambda Insights enabled), Lambda Execution Role, Alarms, Cloudwatch Logs, Cloudwatch Dashboard.

> With X-Ray, Lambda Insights, Alarms, Logging, Dashboard, and IAM policies following the principle of least privilege, you have everything you need to quickly implement a monitoring system for your application!

## Architecture

Infrastructure for this solution separated into 4 stacks:

1. Storage (S3)
2. Application (API Gateway and Lambda) sourced from a code repository
3. Pipeline (AWS CodePipeline)
4. Network (CloudFront and Route53)

Storage: An S3 bucket stores static content. Multiple instances (dev, test, stage, prod, etc) can share the same bucket, each having a dedicated directory. Because this bucket serves multiple instances, doesn't change, and requires some level of persistence, it is separate from the application stack. S3 is secured via Object Access Control (OAC) and can only be publicly accessed through CloudFront. 

Application: API Gateway provides access to a Lambda function that can be used in the back end. Web files for a React, Vue, or other single page application (SPA) can be stored in the `frontend-src` directory. These files are built and deployed to S3 during the CodeBuild phase.

Pipeline: For automated deployments, a CodePipeline can pick up changes committed to a particular branch of your repository. For example, a test pipeline will pick up changes from the test branch, deploy a test instance of Lambda, and build and copy static frontend files to the test path of S3.

Network: Because S3 will be using OAC, CloudFront must be placed in front to provide a custom domain name and access to the static website. CloudFront can also provide a custom domain for your API Gateway. Route53 will manage the records. Cache invalidation can be enabled to prevent old files from S3 from being served.

## Prerequisites

A degree of familiarity with the Serverless Application Model and AWS. An [introductory tutorial](https://github.com/chadkluck/serverless-sam-8ball-example), and a series of [intermediate tutorials](https://github.com/chadkluck/serverless-deploy-pipeline-atlantis) are provided.

Though Atlantis is not required to manage deployments, it provides scripts to assist in automating and managing your deployments. It is highly recommended. However, you are able to manually deploy via the Web Console, your own SAM commands, or adapting to AWS CDK or Terraform.

If using Atlantis to deploy your pipeline, then you will need a CloudFormation service role set up. (See Atlantis documentation)

Some familiarity with Atlantis (especially in regards to Prefix, ProjectId, and StageId) is necessary. (See Atlantis documentation)

## Installation

1. Create storage stack
2. Create repository and initialize with code
3. Create pipeline stack
4. Create network stack

### 1. Create storage stack

This needs to be deployed first so the build phase has somewhere to copy the files to.

You can use the Storage Infrastructure template provided by Atlantis:

- `s3://63klabs/atlantis/v2/infrastructure/storage/template-storage-s3-oac-for-cloudfront.yml`
- `https://63klabs.s3.amazonaws.com/atlantis/v2/infrastructure/storage/template-storage-s3-oac-for-cloudfront.yml`

Atlantis provides a `config.py` script that walks you through configuration.

From your Atlantis template repository:

```bash
python config.py storage <prefix> <project-id>
```

Then deploy using the sam command found in the generated `samconfig` file. For example:

```bash
cd infrastructure/storage
sam deploy --config-env default --config-file samconfig-acme-mywebapp-storage.toml --profile default
```

### 2. Create repository and initialize with code

Atlantis provides a `create_repo.py` script that will create your CodeCommit repository and seed it with the code.

From your Atlantis template repository:

```bash
python create_repo.py <repo_name> s3://63klabs/atlantis/v2/app-starter/04-apigw-lambda-s3-static.zip default
```

Be sure to replace `default` with your AWS profile.

### 3. Create a pipeline stack that will deploy your application stack

You will need one pipeline per deployment stage, and each deployment stage is tied to a branch. For example, when you have `dev`, `test`, `staging`, and `main` branches you would skip `dev` and have `test`, `staging`, and `prod` stages respectively. (You typically don't have a pipeline for the `dev` branch as a developer could be committing non-working code, and will most likely perform builds and run deployments locally during development). 

You can use the Pipeline Infrastructure template provided by Atlantis:

- `s3://63klabs/atlantis/v2/infrastructure/pipeline/template-pipeline.yml`
- `https://63klabs.s3.amazonaws.com/atlantis/v2/infrastructure/pipeline/template-pipeline.yml`

Atlantis provides a `config.py` script that walks you through configuration. 

From your Atlantis template repository:

```bash
python config.py pipeline <prefix> <project-id> <stage-id>
```

Then deploy using the sam command found in the generated `samconfig` file. For example:

```bash
cd infrastructure/pipeline
sam deploy --config-env test --config-file samconfig-acme-mywebapp-pipeline.toml --profile default
```

### 4. Create a network stack

For custom domains, and to access S3 using OAC (Object Access Control), you will need CloudFront, Route53, and cache invalidation, all provided by the Network Infrastructure template.

You will need one network stack per test, staging, or production deployment.

You will need two things first:

1. A hosted zone in Route53 (obtain the Hosted Zone ID)
2. A certificate valid for the domain you plan on using in Amazon Certificate Manager (obtain the Arn of the certificate)

You can use the Network Infrastructure template provided by Atlantis:

- `s3://63klabs/atlantis/v2/infrastructure/network/template-route53-cloudfront-s3-apigw.yml`
- `https://63klabs.s3.amazonaws.com/atlantis/v2/infrastructure/network/template-route53-cloudfront-s3-apigw.yml`

Atlantis provides a `config.py` script that walks you through configuration.

From your Atlantis template repository:

```bash
python config.py network <prefix> <project-id> <stage-id>
```

Then deploy using the sam command found in the generated `samconfig` file. For example:

```bash
cd infrastructure/network
sam deploy --config-env test --config-file samconfig-acme-mywebapp-network.toml --profile default
```

## More Information

A tutorial is available from the repository.

## Author

Chad Leigh Kluck, Software Engineer, AWS Certified, [Website](https://chadkluck.me)
