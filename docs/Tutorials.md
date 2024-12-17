# Tutorials

> NOTE: This tutorial has been updated for Atlantis Pipeline V2 but its accuracy has not yet been verified.

## AWS Costs

This deploy template will create resources necessary to provide an AWS CodePipeline. After performing any tutorials you will want to delete unused stacks to prevent incurring any unexpected costs. However, most experimentation, and even low production loads, rarely rise above [AWS Free Tier](https://aws.amazon.com/free).

> You get 1 free active pipeline per month. New pipelines are free for the first 30 days. "An active pipeline is a pipeline that has existed for more than 30 days and has at least one code change that runs through it during the month. There is no charge for pipelines that have no new code changes running through them during the month." [CodePipeline Pricing](https://aws.amazon.com/codepipeline/pricing)

In short: Pipelines can sit idle without incurring any cost.

You are also charged for AWS CodeBuild if you go over 100 build minutes per month. If you are committing and deploying only a few changes a month you should not see any charges for CodeBuild. If you are frequently committing changes for deployment several times a day, several days a week during the month, you may see charges. [CodeBuild Pricing](https://aws.amazon.com/codebuild/pricing)

To delete the stacks and resources refer [Deleting and Clean-Up](./Deleting-And-Clean-Up.md).

## Tutorial 0

Complete the steps listed in the [main README](../README.md) including the 1-2-3 Set-Up until you have a working initial deployment from your main branch. If you completed the steps using the Web Console, go back and perform the steps using the AWS CLI as this tutorial will utilize the CLI.

Once you have created your first pipeline and deployed your first application stack, then congratulations! Your tutorial journey has already begun!

Before continuing, make sure your repository has 4 branches:

- dev
- test
- beta
- main (default)

In the following tutorials we will end up with 3 deployment pipelines and three instances of the application.

We will continue to use the `acme` Prefix and the `hello-world` Project ID.

For Stage Id and Deploy Environment, we will use the following values for each branch:

| Branch  | Stage Id | Deploy Environment |
|---------|----------|--------------------|
| test    | test     | TEST               |
| beta    | beta     | PROD               |
| main    | prod     | PROD               |

As depicted in the table, each branch is mapped to a Stage Id. The Stage Id can be the same as the branch name, however due to character limitations, if feature branches have long names, an abbreviated form of Stage Id should be used instead. While the tutorials will not cover these types of branches, feel free to experiment with some of these examples.

| Example Branch | Stage Id | Deploy Environment |
|----------------|----------|--------------------|
| feature-bri-98 | fbri98   | TEST               |
| test-joseph    | tjsph    | TEST               |
| hotfix-4278    | hf4278   | TEST               |

### Create Additional Pipelines

Once the branches have been created, make sure the test, beta, and main branches each have a pipeline. We will not need a pipeline for dev as we will leave that for local and incomplete work that we don't want to automatically deploy. Branches that are not mapped to a deploy are a safe spot to continually check-in code that is a work-in-progress.

### Review

Let us review what has been completed:

1. IAM CloudFormation Service Role
2. CodeCommit Repository
3. Pipeline deploy stack creation

When you create a CloudFormation stack you must assign it a service role so it has permissions to create the resources specified in the CloudFormation stack template. The IAM policy and service role we created grants the deploy stack permission to create the AWS CodePipeline including the AWS CodeBuild and CodeDeploy stages. It also grants access to CodePipeline to monitor repositories assigned to the pipeline using AWS Event Bridge.

The combination of the Prefix, Project Id, and Stage Id play an important role in assigning and scoping permissions.

The IAM policy and service role is scoped down to just the prefix and resource types assigned to it. So, for example, if you have two teams, Accounting (ACCT) and Engineering (ENGR), each can have their own Service Role to create their own deploy and application stacks. The engineering team will only have access to create stacks under the ENGR prefix, and the accounting team will only have access to create stacks under the ACCT prefix.

Similarly, ENGR deploy stacks can only modify ENGR resources. For example, an ENGR stack cannot delete or modify resources assigned to an ACCT stack. Furthermore, each stack has its own policy that restricts its own access to resources under its name and stage.

Stacks `ENGR-atomic-particle-manager-test-pipeline` and `ENGR-atomic-particle-manager-infrastructure` can only modify resources with names (or specified tags) starting with `ENGR-atomic-particle-manager-test-*` and cannot modify resources under the name `ENGR-atomic-particle-manager-beta-*` and certainly not `ACCT-payroll-prod-*`.

The deployment stacks also create Worker Roles specific to the application infrastructure stack. The Worker CFRole takes the place of the Service Role for the infrastructure stack. Just like how the Service Role grants the deploy stack permissions, the Worker CFRole grants the infrastructure stack permission to create all the resources necessary for your application infrastructure.

Right now the infrastructure stack has permission to create resources such as S3, DynamoDb, and Lambda functions. If it tried to create an EC2 instance, Event Bridge rule, or Step Function it would fail due to inadequate permissions.

However, depending on the needs of your application, you can add and remove permissions to these Roles. We will have a tutorial on this later.

For now remember the following:

1. The Service Role grants the pipeline stack permission to create the Code Pipeline and worker roles for the application infrastructure stack. If you want to add resources to your pipeline stack such as pipeline execution notifications via SNS or other event triggers, add permission to create them via the service role.
2. The worker roles created by the pipeline stack grant permission for the infrastructure stack to create all resources and execution roles for your application. If you need your infrastructure stack to create EC2 instances, Databases, and Step Functions, you need to add these permissions to the CloudFormation Worker Role definition in the template-pipeline.yml template.
3. Execution roles are created and defined in the infrastructure stack template. If your application needs additional access to S3 buckets or databases that are not created by the stack then you can add them to the execution role definitions in the template.yml file.

## Tutorial 1: Deploying Changes

Create a pipeline stack to deploy your application from the test branch. Set the Stage Id to `test` and Deploy Environment to `TEST`.

Checkout the `test` branch of your repository:

`git checkout test`

Open the `src/index.js` file.

Let's add some responses!

```javascript
const answers = [ "It is certain",
//... add in any of the following or your own
	"Everything will come up roses",
	"I'd bet my magic on it",
    "Are puppies cute?",
    "Stars are aligned in your favor",
    "I'm pulling for you!",
    "You might want to focus on something else",
    "The answer may surprise you",
    "The answer lies in the stars",
    "Nope.",
    "Never",
//...
    "My sources say no",
    "Outlook not so good"
];
```

Add your changes, commit, and push.

`git add --all`

`git commit -m "added new responses"`

`git push`

Go into CloudFormation and go to the pipeline for your test deploy stack to watch the CodeBuild and Deploy process.

When it is done, go into CloudFormation and view the updated test infrastructure stack. Go under Outputs and click on WebApp.

Everything look good? Great! Now we are ready to merge our changes into beta to check our work in a production environment!

`git checkout beta`

`git merge test`

`git push`

Hopefully you now know your way around the infrastructure and test stacks for test and beta so check out the deploy process!

Note that since we set the `DeployEnvironment` for beta to `PROD` there will be a gradual deploy so you may not see your new sayings in production for a while.

Why is this? Because we are deploying to a `PROD` environment, even if it is beta, we are treating it like a production environment, a test production, if you will.

In your application's CloudFormation template, Conditions are defined:

```yaml
Conditions:
  IsProduction: !Equals [!Ref DeployEnvironment, "PROD"]
  IsNotProduction: !Not [!Equals [!Ref DeployEnvironment, "PROD"]]
  IsTest: !Equals [!Ref DeployEnvironment, "TEST"]
  IsDevelopment: !Equals [!Ref DeployEnvironment, "DEV"]
  CreateProdResources: !Equals [!Ref DeployEnvironment, "PROD"]
  CreateTestResources: !Equals [!Ref DeployEnvironment, "TEST"]
  CreateDevResources: !Equals [!Ref DeployEnvironment, "DEV"]
  UseS3BucketNameOrgPrefix: !Not [!Equals [!Ref S3BucketNameOrgPrefix, ""]]
  HasPermissionsBoundaryArn: !Not [!Equals [!Ref PermissionsBoundaryArn, ""]]
  CreateAlarms: !Equals [!Ref DeployEnvironment, "PROD"]
```

These can be used to change the way certain resources are created. For example, we may want different retention policies for TEST vs PROD environments:

```yaml
  # -- Log Group with a retention policy --
  AppLogGroup:
    Type: AWS::Logs::LogGroup
    Properties: 
      LogGroupName: !Sub '/aws/lambda/${Prefix}-${ProjectId}-${StageId}-AppFunction'
      RetentionInDays: !If [ IsProduction, !Ref LogRetentionInDaysForPROD,  !Ref LogRetentionInDaysForDEVTEST]
```

If you go into CloudWatch Logs and check the retention policy for your Lambda test logs vs beta logs, you'll see the difference in retention.

We can deploy AllAtOnce during dev and test, but perform gradual deployments in production environments.

```yaml
  # -- Lambda Function --
  AppFunction:
  Type: AWS::Serverless::Function
    Properties:

      DeploymentPreference:
        Enabled: !If [ IsProduction, True,  False] #Gradual deployment only if in production so DEV and TEST aren't hindered
        Type: !If [ IsProduction, !Ref FunctionGradualDeploymentType, "AllAtOnce"]
        Role: !Ref DeployRole
```

We can also decide not to create certain resources, such as alarms or dashboards as we don't need them in test environments and they cost money.

```yaml

  # -- Lambda Function Error Alarm --

  AppFunctionErrorsAlarm:
    Type: "AWS::CloudWatch::Alarm"
    Condition: CreateAlarms
    Properties:
      AlarmDescription: Lambda Function Error > 1

  Dashboard:
    Type: AWS::CloudWatch::Dashboard
    Condition: CreateProdResources
    Properties:
      DashboardName: 'My-Dashboard'
```

Once you are satisfied with your changes in beta, you can merge the changes into the main branch to deploy to production.

`git checkout main`

`git merge beta`

`git push`

## Tutorial 2: Expand the Types of Resources the Infrastructure Stack Can Create

The template-pipeline.yml for the pipeline stack limits what resources can be defined and created in the infrastructure stack. These limits are defined in the `CloudFormationSvcRole` definition under `Policies`.

```yaml
  CloudFormationSvcRole:
    Type: AWS::IAM::Role
    Properties:
      Path: !Ref RolePath
      RoleName: !Sub "${Prefix}-Worker-${ProjectId}-${StageId}-CloudFormationSvcRole"
      Description: Creating service role in IAM for AWS CloudFormation
      PermissionsBoundary: !If [HasPermissionsBoundaryArn, !Ref PermissionsBoundaryArn, !Ref 'AWS::NoValue' ]
      AssumeRolePolicyDocument:
        Statement:
        - Sid: "CloudFormationTrustPolicy"
          Effect: Allow
          Action: sts:AssumeRole
          Principal:
            Service:
            - cloudformation.amazonaws.com
      Policies:
      - PolicyName: CloudFormationRolePolicy
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
            # IAM policy statements that define what the infrastructure stack can (and cannot) create
```

Statements can also limit reach of the CloudFormation infrastructure stack by making sure it only has access to modify it's own resources as defined by name or tag.

For example, let's look at the `LambdaCRUDThisDeploymentOnly` statement which allows All (*) Create, Read, Update, and Delete (CRUD) actions on Lambda functions as long as they are in the same account and region and match the naming convention for this stack's Prefix, Project Id, and Stage Id.

```yaml
          # == Lambda Function == If application infrastructure manages a Lambda function
          - Sid: "LambdaCRUDThisDeploymentOnly"
            Action:
            - lambda:*
            Effect: Allow
            Resource:
            - !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:${Prefix}-${ProjectId}-${StageId}-*'
```

So, if we are creating the CloudFormation stack `acme-hello-world-test-infrastructure`, that infrastructure stack would be allowed to create, read, update, and delete any Lambda function in the same region and account as the stack AND had a name starting with `acme-hello-world-test-`.

The `acme-hello-world-test-infrastructure` stack could perform all actions on the following Lambda functions in this region and account:

- acme-hello-world-test-AppFunction
- acme-hello-world-test-PredictionModel
- acme-hello-world-test-AccessCosmicRandomizer

But could not access:

- acme-hello-world-beta-AppFunction
- acme-hello-universe-test-AppFunction
- acct-payroll-prod-AppFunction

By default, the CloudFormation Service Role (`CloudFormationSvcRole`) defined in the pipeline template allows for management of:

- IAM policies and roles (used for Execution Roles)
- API Gateway
- S3
- Lambda
- LambdaLayers
- DynamoDb
- SSM Parameter Store (read only)
- CloudWatch Dashboards
- CloudWatch Alarms
- CloudWatch Logs

Though present, the following are commented out and can be enabled by uncommenting:

- Event Bridge
- State Machines

Note that EC2 instances, VPCs, and many, many more resources are not listed. This means that unless they are explicitly added to the CloudFormation Service Role in the pipeline template, then your developers cannot manage them through the application infrastructure stack.

Typically, the only time you will be updating the pipeline stack is when you need to change the way it functions, such as adding alarms, notifications, or permissions to the CloudFormationSvcRole.

Let's update the stack by granting permission to manage State Machines. (We aren't actually going to go through creating a state machine, but we are going to update the pipeline so we could expand our application infrastructure in the future).

1. Create a copy of `template-pipeline.yml` and name it `template-pipeline-state-machine.yml`
2. In the new template, under the `CloudFormationSvcRole` policy statements, find the State Machine Statement and uncomment it.

The statement should now look like:

```yaml
          # == State Machines / Step Functions == If application infrastructure is managing a state machine with step functions
          - Sid: "CreateUpdateDeleteStateMachine" # Statement Written by Q
            Action:  
            - states:CreateStateMachine
            - states:UpdateStateMachine
            - states:DeleteStateMachine
            - states:ListStateMachines
            - states:DescribeStateMachine
            - states:TagResource
            - states:UntagResource
            - states:ListTagsForResource
            Effect: Allow
            Resource:
              - !Sub 'arn:aws:states:${AWS::Region}:${AWS::AccountId}:stateMachine:${Prefix}-${ProjectId}-${StageId}-*'
```

In the next tutorial you will learn how to update the pipeline stack using a new template.

## Tutorial 3: Update a Pipeline Stack

> This part of the tutorial has not yet been written. However, you can refer to Updating Pipeline Stacks in the [CLI README](../scripts/README-CLI.md).

## Deleting stacks

You can add stacks all day long, you can also delete them without affecting the branches. However, there is an order for deleting:

1. Delete the infrastructure stack. You may need to disable termination protection.
2. Empty the S3 bucket for the deploy. The bucket with the format: `${AWS::Region}-${AWS::AccountId}-${ProjectStageId}-pipeline`
3. Delete the deploy stack. Again, you may need to disable termination protection.

## Congratulations!

You made it all the way through the tutorials!

When you are ready for a more advanced application tutorial for your CI/CD pipeline, check out the repository: [Serverless Web Service Template for Pipeline Atlantis](https://github.com/chadkluck/serverless-webservice-template-for-pipeline-atlantis).
