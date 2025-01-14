# 

I've come to find that the documentation and resources to help get started with AWS Serverless development is great for just that: getting started. However, when I start to extend the application past what is presented in tutorials, examples in documentation, etc, my questions seem to quickly expand outside the scope of easy to find answers.

One of my latest struggles was creating Serverless Application Model (SAM) configuration files for stacks that don't require CI/CD pipelines and can be deployed from the command line.

SAM config files are often used in tutorials and local dev environments before a CI/CD pipeline is set up to take on automated deployments. When you define your SAM CloudFormation template you'll no doubt have parameters, tags, and deployment options to include each time you deploy the template to manage your stack.

When you look at tutorials you'll most likely find a samconfig file example that looks like this:

```toml
[default.global.parameters]
region = "us-east-2"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true

[default.deploy.parameters]
stack_name = "lab-service-role"
s3_prefix = "lab-service-role"
parameter_overrides = "\"Environment\"=\"production\""
```

However, when you expand the number of templates and stack parameters, and add tags to the mix it can become more complex, primarily with the way `parameter_overrides` and `tags` accept their list of values.

```toml
[default.global.parameters]
template_file = "./templates/template-service-role.yml"
s3_bucket = "cf-templates-somerandomchars-us-east-2"
region = "us-east-2"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true

[default.deploy.parameters]
stack_name = "lab-service-role"
s3_prefix = "lab-service-role"
parameter_overrides = "\"Prefix\"=\"lab\" \"PrefixUpper\"=\"LAB\" \"S3BucketNameOrgPrefix\"=\"acme\" \"RolePath\"=\"/lab_apps/\" \"PermissionsBoundaryArn\"=\"\" \"GroupNames\"=\"\" \"RoleNames\"=\"\" \"UserNames\"=\"\""
tags = "\"Owner\"=\"chadkluck\" \"Creator\"=\"chadkluck\" \"CostCenter\"=\"123456\" \"Department\"=\"AppDev\""
```

The example above is for a simple stack that deploys a single IAM role. Since the role doesn't receive frequent updates (probably would go at least a year or two) it makes sense to deploy it manually using the following command:

```bash
sam deploy
```

It gets more complex when I am deploying a template for a pipeline as I define separate pipelines for test, beta, and production (one for each branch of my repository). Instead of using the textbook `default` deploy environment, I can specify `test.deploy.parameters`, `beta.deploy.parameters`, and `prod.deploy.parameters`.

```toml
[test.deploy.parameters]
s3_bucket = "cf-acme-deploys"
template_file = "./templates/template-pipeline.yml"
region = "us-east-2"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
image_repositories = []
role_arn = "arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role"
stack_name = "acme-accounting-test-pipeline"
s3_prefix = "acme-accounting-test-pipeline"
parameter_overrides = "\"ProjectId\"=\"accounting-app\" \"CodeCommitRepository\"=\"asdf\" \"DeployEnvironment\"=\"TEST\" \"CodeCommitBranch\"=\"test\" \"AlarmNotificationEmail\"=\"asdf@asdf.com\" "
tags = "\"Owner\"=\"chadkluck\" \"Creator\"=\"chadkluck\" \"CostCenter\"=\"123456\" \"Department\"=\"AppDev\""

[beta.deploy.parameters]
s3_bucket = "cf-acme-deploys"
template_file = "./templates/template-pipeline.yml"
region = "us-east-2"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
image_repositories = []
role_arn = "arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role"
stack_name = "acme-accounting-beta-pipeline"
s3_prefix = "acme-accounting-beta-pipeline"
parameter_overrides = "\"ProjectId\"=\"accounting-app\" \"CodeCommitRepository\"=\"asdf\" \"DeployEnvironment\"=\"PROD\" \"CodeCommitBranch\"=\"beta\" \"AlarmNotificationEmail\"=\"asdf@asdf.com\" "
tags = "\"Owner\"=\"chadkluck\" \"Creator\"=\"chadkluck\" \"CostCenter\"=\"123456\" \"Department\"=\"AppDev\""

[prod.deploy.parameters]
s3_bucket = "cf-acme-deploys"
template_file = "./templates/template-pipeline.yml"
region = "us-east-2"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
image_repositories = []
role_arn = "arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role"
stack_name = "acme-accounting-prod-pipeline"
s3_prefix = "acme-accounting-prod-pipeline"
parameter_overrides = "\"ProjectId\"=\"accounting-app\" \"CodeCommitRepository\"=\"asdf\" \"DeployEnvironment\"=\"PROD\" \"CodeCommitBranch\"=\"main\" \"AlarmNotificationEmail\"=\"asdf@asdf.com\" "
tags = "\"Owner\"=\"chadkluck\" \"Creator\"=\"chadkluck\" \"CostCenter\"=\"123456\" \"Department\"=\"AppDev\""
```

If I make changes to the pipeline template or any of the parameters or tags, I can just run the `sam deploy` command with the `--config-env` flag.

```bash
sam deploy --config-env beta
```

However, that `samconfig` file is ugly as there is a lot of repeated information. It would be nice if there were something like a `global` section I could use to declare `s3_bucket`, `template_file`, `region` and more just once to be used across all the environments.

"But wait, there is, right?"

No.

"Are you sure? What about that `default.global.parameters`? Default means default parameter values, right?"

Nope. `default` refers to the environment, just like `test` or `beta` in my example. It does not specify the "default" values.

"But, there's got to be a `global.parameters`, right?"

I'm sorry, that would make too much sense. As would having `[test.deploy.parameters.parameter_overrides]` (or `.tags`) so you don't need to do that funky list with escaped quotes. I mean, that _is_ valid toml mark-up, but I'll get to that later.

"What about--"

No. Okay, let me break down how I spent hours trying to figure this out and came to the sad realization that as much as I would love an awesome way to do things natively within SAM without resorting to Terraform or other deployment strategies, _this is how SAM is_. Period.

I looked through documentation. I tried many iterations of a samconfig file. I went through many wrong paths.

Then I tried AI.

That is when I discovered AI has the same dreams I do. That it _could_ be done.

But, I remind you, as I reminded Amazon Q and Google Gemini, it was just a dream. I even got an appology from Q.

I've had a wonderful experience using Google Gemini (just by "Googling" developer questions and receiving answers in my search results), and I have both GitHub CoPilot and Amazon Q installed in Visual Studio Code. (I haven't used ChatGPT for coding, but I have for designing learning modules). I've taken many roles with the AI coding assistants, like giving them tasks as I would a junior developer and reviewing the code, a second set of eyes on an error I can't figure out, adding in a new library, or completely moving from one packaging platform to another.

AI has been very helpful in assisting me do more, as if I had a team of peers working with me (I have a team, but our projects are small enough that we are typically working solo). 

However, they know as much as I do about what you can and cannot do in a `samconfig.toml` file.

This wasn't my first struggle with `samconfig` and Q. I thought if I really wanted to dig into the nooks and crannies of AWS, Amazon Q Developer would be able to help me with some obscure references. Early on I asked about the whole mess of

```toml
parameter_overrides = "\"ProjectId\"=\"accounting-app\" \"CodeCommitRepository\"=\"asdf\" \"DeployEnvironment\"=\"PROD\" \"CodeCommitBranch\"=\"main\" \"AlarmNotificationEmail\"=\"asdf@asdf.com\" "
tags = "\"Owner\"=\"chadkluck\" \"Creator\"=\"chadkluck\" \"CostCenter\"=\"123456\" \"Department\"=\"AppDev\""
```

Amazon Q said I could certainly break it apart [spoiler alert: you can't]:

```toml
[default.deploy.parameters]
stack_name = "acme-accounting-prod-pipeline"
s3_prefix = "acme-accounting-prod-pipeline"

[default.deploy.parameters.parameter_overrides]
ProjectId="accounting-app"
CodeCommitRepository="asdf"
DeployEnvironment="PROD"
CodeCommitBranch="main"
AlarmNotificationEmail="asdf@asdf.com"

[default.deploy.parameters.tags]
Owner="chadkluck"
Creator="chadkluck"
CostCenter="123456"
Department="AppDev"
```

After all, _it is valid toml_. However, as much as I live and breathe developing serverless on AWS, it seems some development team got to a point of "good enough" where they didn't fully implement the way SAM parses `parameter_overrides` and `tags`.

I nicely told Q that it was wrong, and that didn't work that way (after some time of struggling with figuring out why what Q gave me didn't work that way). Q appologized. I continued messing with the escaping of quotes in the long list of parameters and tags. It was so much of a pain that I ended up having Q assist me in developing a python script to help manage and update all my `samconfig` files.

Soon I got to a point where I really needed to know, can I at least break things out into a global section that is shared among all environments? I did a lot of research. I scouered the documentation. As I mentioned before, all tutorials, documentation examples, and blog posts came just short of answering my question.

So I asked Google.

"in a samconfig toml file what is the purpose of default.global.parameters?"

<blockquote>
In a samconfig.toml file, the default.global.parameters section is used to define a set of default parameter values that will be applied across all SAM CLI commands unless explicitly overridden by command line arguments or other configuration settings within the file; essentially, it acts as a central location to store commonly used parameters for your serverless application deployment, allowing you to easily manage and reuse them throughout your project. 

Key points about default.global.parameters:

- Global Scope: The "global" part means these parameters will be applied to any SAM command you run unless you specify different values for a specific operation (like deployment or local invoke). 
- Overriding Values: You can still override individual parameters at the command line or within different sections of your samconfig.toml file for specific use cases.

Example usage:

```toml
[default.global.parameters]
Region = "us-east-1"
StackNamePrefix = "my-app-"
EnvironmentType = "development" 
```
</blockquote>

Well, that didn't help. And, it was a bit suspect since you don't capitalize `Region`, I know there isn't an `EnvironmentType` parameter, and as for `StackNamePrefix`, maybe, but probably not.

So, I asked a follow-up:

"how do i use global parameters across all environments in a samconfig toml file?"

<blockquote>
To use global parameters across all environments in a samconfig.toml file, define them under the [default.global.parameters] section; this ensures the parameters are applied to any environment unless specifically overridden within individual environment sections.
</blockquote>

There was more, but I'm just going to stop there. (Full response at end of article.)

Okay, so Gemini says I can do it.

So I asked Q what the purpose of default was and it gave me a similar answer, but using examples from my samconfig file which I had open in the editor.

I then asked about defining global parameters:

"how do i use global parameters across all environments in a samconfig toml file"

And it give me something that (spoiler) it completely pulled from thin air with reasons as to why it would be better (full response at end of article).

<blockquote>
To use global parameters across all environments in a samconfig.toml file, you can create a section with the environment name all. This will apply those parameters across every environment (like dev, prod, staging, etc.).

Here's an example structure:

```toml
[all.global.parameters]
region = "us-east-2"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true

[dev.deploy.parameters]
stack_name = "dev-stack"
parameter_overrides = "Environment=dev"

[prod.deploy.parameters]
stack_name = "prod-stack"
parameter_overrides = "Environment=prod"
```

This approach:

1. Reduces duplication
2. Makes global settings easier to maintain
3. Ensures consistency across environments
4. Still allows environment-specific overrides when needed

The parameters in [all.global.parameters] will be used unless specifically overridden in an environment-specific configuration.
</blockquote>

It seemed reasonable so I tried it. Nope.

"Are you sure? When I change it to all, then neither environment works"

<blockquote>
I apologize for my previous incorrect response. You are right to question this.

Looking at your file again and based on AWS SAM's configuration behavior, the correct approach is to keep using [default.global.parameters] rather than [all.global.parameters]. The all prefix is not actually supported by SAM CLI for global parameters.

The correct structure would be:

```toml
[default.global.parameters]
template_file = "./templates/template-service-role.yml"
s3_bucket = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
region = "us-east-2"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true

[default.deploy.parameters]
stack_name = "lab-service-role"
s3_prefix = "lab-service-role"
parameter_overrides = "..."
tags = "..."

[asdf.deploy.parameters]
stack_name = "lab-service-role"
s3_prefix = "lab-service-role"
parameter_overrides = "..."
tags = "..."
```

If you need to share parameters across environments, you would need to repeat them in each environment's configuration. I apologize for any confusion my previous response may have caused.
</blockquote>

Well, at least Q appologized for sending me down the wrong path. Q might be great at many things, but it is just as confused about `samconfig.toml` files as I am.

So, in summary, you do need to repeat yourself (can't use DRY) in `samconfig.toml` and `parameter_overrides` and `tags` get a little unruley.

Luckily, Q and I were at least able to collaborate on a python script that assists with managing samconfig files.

## Gemini's Incorrect Responses

> how do i use global parameters across all environments in a samconfig toml file?

To use global parameters across all environments in a samconfig.toml file, define them under the [default.global.parameters] section; this ensures the parameters are applied to any environment unless specifically overridden within individual environment sections. [1, 2, 3]  
Example:

```toml
[default.global.parameters]
StackName = "my-application"
Region = "us-east-1"
```

Explanation: 

- `[default.global.parameters]`: This indicates the parameters defined here will be applied globally to all environments within the samconfig.toml file. 
- `StackName = "my-application"`: Sets the "StackName" parameter to "my-application" for all deployments. [1, 2, 3]  

Important Considerations:

- Environment-Specific Overrides: If you need to use different values for a parameter in a specific environment, create a section for that environment and define the parameter there. [1, 2, 3]  

```toml
[dev.parameters]
StackName = "my-application-dev" 
```

• Accessing Parameters in your SAM Template: Within your SAM template, use the Ref intrinsic function to access parameters defined in the samconfig.toml file. [1, 2, 4]  

```json
    "MyFunction": {
        "Type": "AWS::Serverless::Function",
        "Properties": {
            "Environment": {
                "Variables": {
                    "STACK_NAME": {"Ref": "StackName"}
                }
            }
        }
    }
```

Generative AI is experimental.

[1] [How to use environment variables in AWS SAM (BlowStack)](https://blowstack.com/blog/how-to-use-environmental-variables-in-aws-sam)
[2] [Configuring the AWS SAM CLI (AWS Documentation)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/using-sam-cli-configure.html)
[3] [sam config - Improving the Configuration File in the AWS SAM CLI (GitHub)](https://github.com/aws/aws-sam-cli/discussions/4591)
[4] [Introduction to deploying with AWS SAM (AWS Documentation)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/using-sam-cli-deploy.html)


## Q's Incorrect Responses

> in a samconfig toml file what is the purpose of default.global.parameters

In a samconfig.toml file, the default.global.parameters section defines configuration parameters that will be applied globally across all AWS SAM CLI commands for the "default" environment. These parameters serve as default values that will be used unless overridden by more specific configurations. [1]

Looking at your open samconfig file, you're using default.global.parameters to set:

```toml
[default.global.parameters]
template_file = "./templates/template-service-role.yml"
s3_bucket = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
region = "us-east-2"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true
```

These settings mean:

1. The SAM template to use ( template_file)
2. The S3 bucket where deployment artifacts will be stored ( s3_bucket)
3. The AWS region to deploy to ( region)
4. Required IAM capabilities ( capabilities)
5. Whether to confirm changesets before deployment ( confirm_changeset)

These parameters will be used for all SAM CLI commands (like sam build, sam deploy, etc.) when using the default configuration environment. However, command-specific parameters (like those under default.deploy.parameters in your file) will override these global settings when they conflict.

This is particularly useful when you want to set common configuration values that should apply across different SAM CLI operations without having to repeat them for each command type.

> how do i use global parameters across all environments in a samconfig toml file

To use global parameters across all environments in a samconfig.toml file, you can create a section with the environment name all. This will apply those parameters across every environment (like dev, prod, staging, etc.). [1]

Here's an example structure:

```toml
[all.global.parameters]
region = "us-east-2"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true

[dev.deploy.parameters]
stack_name = "dev-stack"
parameter_overrides = "Environment=dev"

[prod.deploy.parameters]
stack_name = "prod-stack"
parameter_overrides = "Environment=prod"
```

In this case, the region, capabilities, and confirm_changeset parameters will apply to both dev and prod environments, while each environment can still have its own specific configurations.

Looking at your current file, you could refactor it like this:

```toml
[all.global.parameters]
template_file = "./templates/template-service-role.yml"
s3_bucket = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
region = "us-east-2"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true

[default.deploy.parameters]
stack_name = "lab-service-role"
s3_prefix = "lab-service-role"
parameter_overrides = "\"Prefix\"=\"lab\" \"PrefixUpper\"=\"LAB\" ..."
tags = "\"Atlantis\"=\"service-role-infrastructure\" ..."

[asdf.deploy.parameters]
stack_name = "lab-service-role"
s3_prefix = "lab-service-role"
parameter_overrides = "\"Prefix\"=\"lab\" \"PrefixUpper\"=\"LAB\" ..."
tags = "\"Atlantis\"=\"service-role-infrastructure\" ..."
```

This approach:

1. Reduces duplication
2. Makes global settings easier to maintain
3. Ensures consistency across environments
4. Still allows environment-specific overrides when needed

The parameters in [all.global.parameters] will be used unless specifically overridden in an environment-specific configuration.

> Are you sure? When I change it to all, then neither environment works

I apologize for my previous incorrect response. You are right to question this.

Looking at your file again and based on AWS SAM's configuration behavior, the correct approach is to keep using [default.global.parameters] rather than [all.global.parameters]. The all prefix is not actually supported by SAM CLI for global parameters.

The correct structure would be:

```toml
[default.global.parameters]
template_file = "./templates/template-service-role.yml"
s3_bucket = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
region = "us-east-2"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true

[default.deploy.parameters]
stack_name = "lab-service-role"
s3_prefix = "lab-service-role"
parameter_overrides = "..."
tags = "..."

[asdf.deploy.parameters]
stack_name = "lab-service-role"
s3_prefix = "lab-service-role"
parameter_overrides = "..."
tags = "..."
```

If you need to share parameters across environments, you would need to repeat them in each environment's configuration. I apologize for any confusion my previous response may have caused.