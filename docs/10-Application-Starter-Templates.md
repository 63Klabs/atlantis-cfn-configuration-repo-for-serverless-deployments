# Atlantis Application Stater Templates

The Atlantis starter templates can be used to deploy many serverless solutions.

> For your first deployment using Atlantis, it is recommend you use the **00 Basic API Gateway Lambda Node.js** application starter.

Deploy the templates and applications AS-IS. After a successful deployment, you may then modify the code as needed.

Once you have explored the basic application, you can proceed to use the other starter applications listed below. Each utilize the [@chadkluck/cache-data npm package](https://www.npmjs.com/package/@chadkluck/cache-data) written and maintained by the same developer of this repository. The Cache-Data package includes functions to quickly implement routing, logging, monitoring, endpoint caching, and more.

The CloudFormation templates for each application feature definitions for CloudWatch alarms, logging, dashboards, X-Ray, Lambda Insights, and Swagger API documentation.

Start Here: 

- [00 Basic API Gateway Lambda Node.js](https://github.com/63klabs/atlantis-app-starter-00-basic-apigw-lambda-nodejs/).

Then try the near production-ready application starters (recommended order):

1. 01 API Gateway, Lambda Python (coming eventually)
2. 02 API Gateway, Lambda Node.js with Cache-Data (coming eventually)
3. 03 Event Bridge, Lambda, Step Function (coming eventually)
4. 04 API Gateway, Lambda, S3 static content (coming eventually)
5. 05 Video Processing using Event Bridge, Lambda, Step Functions, Media Convert, Transcribe (coming eventually)
6. 06 Image processing using Event Bridge, Lambda, Step Functions (coming eventually)
