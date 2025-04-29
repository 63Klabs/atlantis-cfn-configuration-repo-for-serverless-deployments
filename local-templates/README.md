# Sample Templates

It is recommend you utilize a separate repository and S3 bucket to store your templates. The `s3://63klabs` templates are available and free to use until you establish your own template repository and S3 template bucket.

It is best practice to keep your templates and configuration files separate, version them, and to limit the number of users who have access to change the templates.

> The [Atlantis Template Repository for Serverless Deployments using AWS SAM](https://github.com/chadkluck/atlantis-template-repo-for-serverless-deployments) provides cli and AWS CloudFormation templates for managing an S3 template bucket with versioning.

By default, all templates in this directory are git ignored! Comment out the appropriate lines in .gitignore to include them.

You can utilize the templates from `s3://63klabs` by setting the `atlantis.s3_template_host` in `defaults/defaults.json` or entering a template S3 URL when configuring a deployment. Version IDs are also accepted.

If if you wish to keep a local copy of a template from `s3://63klabs` or other public template bucket, you can use a command similar to the one below. You must be authenticated to AWS in order to access. (Object read access is granted to anyone with an AWS account.)

```bash
aws s3 cp s3://63klabs/atlantis/templates/v2/service-role/template-service-role.yml ./templates/service-role/ --profile yourprofile
```

Templates stored locally must be in their infrastructure type directory in order to be located and used by the `config.py` cli.

For a list of templates and versions:

```bash
aws s3 cp s3://63klabs/atlantis/templates/inventory.json ./local-templates/ --profile yourprofile
```
