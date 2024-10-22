# Storage

> This is still beta and in flux. The directory structure will change over and over again as we work on organization.

A few things to note:

- SAM config files should be stored in the main `storage-infrastructure` directory.
- The templates should be stored in templates directory (save off a copy if you really need to modify, but for the most part they do not need to be modified) Check with the lead SAM developer to go over options and if you really need to start with a new template. There is probably a better way.
- We utilize the same template over and over so that we can quickly apply updates such as features, environment upgrades, fixes, and security enhancements across all our applications.

There is only one environment for storage as it will be used across all instances of an application. Therefore an environment flag does not need to be sent with the command.

`sam deploy --profile default --config-file ./samconfig-acme-sample-storage.toml`

Please contact clkluck@stthomas.edu with any questions.
