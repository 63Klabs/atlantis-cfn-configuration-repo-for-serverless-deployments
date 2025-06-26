# In-Depth Guide to Serverless Deployments using 63K Atlantis

I bet you hate arriving to an In-Depth guide that is empty.

My apologies, but while the scripts are stable, they are still under development.

Beyond the tutorials, you can use the `-h` for any of the scripts to receive guidance on their use, arguments, options, and flags.

> NOTE: Since the SAM Configuration repository is the SOURCE of CONFIGURATION TRUTH, be sure to `pull` and `push` changes before updating or deploying, and after updating or deploying. Ensure your changes are properly recorded and saved! (Eventually the scripts will aide in this to prevent mishaps from forgetfulness--happens to the best of us!)

Let's start off with an overview of the scripts.

## create_repo.py

Create a GitHub or CodeCommit repository and seed it from an application starter, GitHub repo, or a ZIP stored S3 using the create_repo.py script

For usage info:

```bash
./cli/create_repo.py -h
```

## config.py

Create and maintain a CloudFormation stack utilizing stack options stored in a samconfig file and a central template repository managed by your organization (or 63Klabs for training and getting started).

The config script will walk you through selecting a template and filling out stack parameters, options, and tags.

For usage info:

```bash
./cli/config.py -h
```

## deploy.py

After configuring a stack, you must deploy it. Although the scripts maintain a samconfig file, it utilizes a template repository hosted in S3, which, oddly, samconfig does not support even though CloudFormation templates can easily import Lambda code and nested stacks from S3.

The deploy script runs the `sam deploy` command after obtaining the template from S3 and providing it to the command as a temporary, local file.

For usage info:

```bash
./cli/deploy.py -h
```

## import.py

You probably have some stacks that were deployed prior to using the CLI scripts to manage them.

Import current stack configurations to a samconfig file.

You can also import the template that was used (if you need a copy).

From there you can tweak the samconfig file, upload the template to a central location (or apply a different one) and after formatting and saving to the proper location for the scripts to use, utilize the CLI scrips.

For usage info:

```bash
./cli/import.py -h
```

## update.py

While stable, the scripts are still under development. Various enhancements and fixes will be released.

The update script is essential in making sure you have the most current scripts.

> Note: Refer to, or create, your organization's policy reguarding WHO should be performing the updates and WHEN the updates should be performed.

The script is very friendly as it will kindly remind, and perform a pull of the configuration repository before proceeding. It will then push all changes back after completion. This ensures that the push/pull step is not forgotten and all subsequent pulls by developers have the new files!

For usage info:

```bash
./cli/update.py -h
```

> NOTE: While the update script has pull/push built in, the other scripts do not yet have this implemented. It is on the list of future enhancements!
