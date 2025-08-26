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
1. Delete the application stack first
2. Delete the pipeline stack next
3. Delete any SSM parameters associated with the application

For storage, network and iam: Not implemented as cleanup can be done by deleting the stack. (Ensure S3 buckets are empty first)

```bash
# Perform this command in the SAM Config Repo
./cli/destroy.py pipeline acme py8ball-adv test --profile ACME_DEV
```
