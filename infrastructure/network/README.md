# CloudFront Distribution with Route53 DNS Record

> Still under development, naming conventions may change

Parameters are explained in the template, but there are some values that correspond to the Atlantis templates (Prefix, ProjectId, Stage, etc)

## Deployments 

Deploy using the `sam deploy` command. All parameters, including tags should be specified in the TOML file so that deployments can be replicated. Each application/project should have it's own TOML file! Name it appropriately! In future we may separate these into their own directories, like what we did with the pipeline template.

> Note: There is a known issue ([which is not a bug because it is "working as designed"](https://github.com/aws/aws-sam-cli/issues/3753)) in which sam deploy will not use the bucket specified for the --s3-bucket param if `-g` (guided) is used.

### More information on `sam deploy` and config file

https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-deploy.html
https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-config.html

To view changes without deploying, add the `--no-execute-changeset` flag to the `deploy` command.

Note the use of the `--profile` flag. Change it to the aws profile you are currently using. Otherwise set the `AWS_PROFILE` bash variable.

```bash
export AWS_PROFILE=default
```

Replace `default` with your own profile name.

## Deploy Test

```bash
sam deploy --profile default --config-env test --config-file samconfig-acme-magic-ws-network.toml
```

## Deploy Production

```bash
sam deploy --profile default --config-env prod --config-file samconfig-acme-magic-ws-network.toml
```
