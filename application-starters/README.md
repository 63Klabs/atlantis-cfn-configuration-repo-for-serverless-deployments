# Application Infrastructure Starter Examples

The Atlantis starter templates can be used to deploy many serverless solutions.

> For your first deployment using Atlantis, it is recommend you use the [00 Basic API Gateway Lambda Node.js](./00-basic-apigw-lambda-nodejs/) application starter.

Deploy the templates and applications AS-IS. After a successful deployment, you may then modify the code as needed.

Once you have explored the basic application, you can proceed to use the starter applications listed below. Each utilize the [@chadkluck/cache-data npm package](https://www.npmjs.com/package/@chadkluck/cache-data) written and maintained by the same developer of this repository. The Cache-Data package includes functions to quickly implement routing, logging, monitoring, endpoint caching, and more.

The CloudFormation templates for each application feature definitions for CloudWatch alarms, logging, dashboards, X-Ray, Lambda Insights, and Swagger API documentation.

Start Here: 

- [00 Basic API Gateway Lambda Node.js](./00-basic-apigw-lambda-nodejs/).

Then try the near production-ready starter applications (recommended order):

1. [01 API Gateway, Lambda Python](./01-apigw-lambda-py/)
2. [02 API Gateway, Lambda Node.js with Cache-Data](./02-apigw-lambda-nodejs-cache-data/)
3. [03 Event Bridge, Lambda, Step Function](./03-event-lambda-nodejs-stepfunc/)
4. [04 API Gateway, Lambda, S3 static content](./04-apigw-lambda-s3-static/)
5. Video Processing using Event Bridge, Lambda, Step Functions, Media Convert, Transcribe (I can develop this, but reach out to me if you are interested!)
