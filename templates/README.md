# Sample Templates

It is recommend you utilize a separate repository and S3 bucket to store your templates. The `s3://63klabs` templates are available and free to use until you establish your own template repository and S3 template bucket.

It is best practice to keep your templates and configuration files separate, and to limit the number of users who have access to change the templates.

> The [Atlantis Repository for AWS SAM Templates](https://github.com/chadkluck/atlantis-repo-aws-sam-templates) provides scripts and templates for managing an S3 template bucket with versioning.

By default, all templates in this directory are git ignored! Comment out the appropriate lines in .gitignore to include them.

If you do not wish to maintain a separate template directory at this time, you can download templates from 63klabs using a command similar to the one below. Be sure to change the template S3 key, the destination directory, and the profile used. You must be authenticated to AWS in order to access. (Object read access is granted to anyone with an AWS account.)

```bash
aws s3 cp s3://63klabs/atlantis/templates/v2/service-role/template-service-role.yml ./templates/service-role/ --profile yourprofile
```

Templates must be stored in their infrastructure type directory in order to be located and used by the `config.py` script.

For a list of templates and versions:

```bash
aws s3 cp s3://63klabs/atlantis/inventory.json ./templates/ --profile yourprofile
```
