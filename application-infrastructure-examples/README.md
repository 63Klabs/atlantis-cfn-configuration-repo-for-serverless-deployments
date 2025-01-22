# Application Infrastructure Starter Examples

> Note: This repository of examples is still being developed. If you have specific questions please reach out to me.

The Atlantis Pipeline template for AWS CodePipeline can be used to deploy many serverless solutions.

> For your first deployment using Atlantis, it is recommend you use the [Basic API Gateway Lambda Node.js](./00-basic-apigw-lambda-nodejs/) application template.

It is recommended you deploy the templates and applications AS-IS. After a successful deployment, you may then modify the code as needed.

Once you have explored the basic application, you can proceed to use the starter applications listed below. Each utilize the [@chadkluck/cache-data npm package](https://www.npmjs.com/package/@chadkluck/cache-data) written and maintained by the same developer of this repository. The Cache-Data package includes functions to quickly implement routing, logging, monitoring, endpoint caching, and more.

The CloudFormation templates for each application feature definitions for CloudWatch alarms, logging, dashboards, X-Ray, Lambda Insights, and Swagger API documentation.

Start Here: 

- [00 Basic API Gateway Lambda Node.js](./00-basic-apigw-lambda-nodejs/).

Then try the near production-ready starter templates (recommended order):

1. [01 API Gateway, Lambda Python](./01-apigw-lambda-py/)
2. [02 API Gateway, Lambda Node.js with Cache-Data](./02-apigw-lambda-nodejs-cache-data/)
3. [03 Event Bridge, Lambda, Step Function](./03-event-lambda-nodejs-stepfunc/)
4. [04 API Gateway, Lambda, S3 static content](./04-apigw-lambda-s3-static/)
5. Video Processing using Event Bridge, Lambda, Step Functions, Media Convert, Transcribe (someday, but reach out to me if you are interested!)

## Steps:

1. Create a repository for your application project. (Currently only CodeCommit is supported for use with Atlantis starter CodePipeline).
2. Clone the repository to your local machine and `cd` into it.
3. Use the following one-line bash command to download, unzip, and extract your preferred application starter into your repository. Replace <profile> with the aws profile to use. Also, replace `00-basic-apigw-lambda-nodejs` with the directory name of the app starter you wish to use.

```bash
aws s3 cp s3://63klabs/app-starters/00-basic-apigw-lambda-nodejs.zip temp.zip --profile default && unzip temp.zip && rm temp.zip
```

When you view your repository, you should see the application-infrastructure directory at the root. It is recommended you put your READMEs, CHANGELOGs, etc, in the root of your repository as well. It is important you do not re-name the application-infrastructure directory because that is where CodePipeline will look for it.
