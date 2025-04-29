# Creating Repo in CodeCommit

Use the script `create_repo.py` to create the repository and seed it with a starter application.

It will access the app starter S3 bucket which is set up in `defaults/settings.json`:

```json
"app_starters": [
		{
			"bucket": "63klabs",
			"prefix": "atlantis/app-starters/v2"
		},
		{
			"bucket": "63klabz",
			"prefix": "atlantis/app-starters/v2"
		}
	],
```

The `63klabs` (released) and `63klabz` (beta) buckets are default and publicly available. Your organization is able to establish their own buckets. Note that you can reference multiple buckets and each will be inventoried and presented to the user as a list to choose from when the script is executed.

```bash
# You may need to add --profile yourprofile if not using the default AWS CLI profile
# Python cli will automatically check for current credentials an initiate a login if necessary.

# See options
./cli/create_repo.py -h

# Create a CodeCommit repository and seed it with an application starter from a list of choices
./cli/create_repo.py your-repo-name --profile yourprofile

# Create a CodeCommit repository and seed it with an application starter from a zip in S3
./cli/create_repo.py your-repo-name --s3-uri s3://bucket/path/to/file.zip --profile yourprofile
```

Choose the application starter and fill in the prompts.

Once the repository is created, you will be given a clone URL to use to clone it to your local machine.

It is recommended you make changes to the application only after you have achieved a successful deployment via the test pipeline.

To create the test pipeline, follow the instructions for creating a pipeline in [Creating Infrastructure Stacks](./12-Creating-Infrastructure-Stacks.md)
