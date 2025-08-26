# TODO - Features

## Config

- [ ] If deploy bucket is in param use s3 deploy and vice versa
- [ ] Check Repository and pull in tags
- [ ] Add Pull and Commit
- [ ] Add ability to run deploy script
- [ ] Documentation

## Deploy

- [ ] Add Pull and Commit
- [ ] Save service role after service role deploy and make sure it is loaded in
- [ ] Documentation

## Import

- [ ] Documentation

## Create Repository

- [ ] Documentation

## Update

- [ ] Skip _custom. files
- [ ] Documentation

## Lib

- [ ] Make sure logs are being stored in the right spot when current working dir is not repo root

### AWS Sessions

- None

### GitHub Utils

- None

### Destroy

To avoid ongoing charges to your AWS account, delete the resources created in this tutorial.

For pipelines:
1. Prompt user if a git pull should be performed (similar to how update.py does it)
2. Confirm deletion by requesting ARN of stack
3. Next confirm the prefix, project id, and stage Id
4. Delete the application stack first
5. Delete the pipeline stack next
6. Delete any SSM parameters associated with the application
7. Prompt user if samconfig entry for deployment should be deleted
8. If last deployment deleted in samconfg, then delete samconfig
9. Perform a git commit and push

For storage, network and iam: Not implemented as cleanup can be done by deleting the stack. (User should ensure S3 buckets are empty first)

```bash
# Perform this command in the SAM Config Repo
./cli/destroy.py pipeline acme py8ball-adv test --profile ACME_DEV
```
