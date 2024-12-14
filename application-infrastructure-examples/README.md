# Application Infrastructure Example Templates

> Note: This repository of examples is still being developed. If you have specific questions please reach out to me.

The Atlantis Pipeline template for AWS CodePipeline can be used to deploy many serverless solutions.

> For your first deployment using Atlantis, it is recommend you use the [Basic API Gateway Lambda Node.js](./00-basic-apigw-lambda-nodejs/) application template.

Once you have explored the basic template, you can proceed to use the near-production ready templates listed below. Each utilize the [@chadkluck/cache-data npm package](https://www.npmjs.com/package/@chadkluck/cache-data) written and maintained by the same developer of this repository. The Cache-Data package includes functions to quickly implement routing, logging, monitoring, endpoint caching, and more.

The near production CloudFormation templates also feature additional definitions for CloudWatch alarms, logging, dashboards, X-Ray, Lambda Insights, and Swagger API documentation.

Start Here: [Basic API Gateway Lambda Node.js](./00-basic-apigw-lambda-nodejs/).

Then try the near production-ready templates (recommended order):

1. [API Gateway, Lambda Python](./01-apigw-lambda-py/)
2. [API Gateway, Lambda Node.js with Cache-Data](./02-apigw-lambda-nodejs-cache-data/)
3. [Event Bridge, Lambda, Step Function](./03-event-lambda-nodejs-stepfunc/)
4. [API Gateway, Lambda, S3 static content](./04-apigw-lambda-s3-static/)
5. Video Processing using Event Bridge, Lambda, Step Functions, Media Convert, Transcribe (someday, but reach out to me if you are interested!)
