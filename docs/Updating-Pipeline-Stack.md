
# Create, Edit, or Replace Existing CloudFormation -pipeline Stacks

> NOTE: This **template-pipeline.yml** template is for a **Deploy Pipeline (-pipeline)** stack! **NOT** your application **Infrastructure (-infrastructure)** stack!

If you are replacing the entire contents of the template file then you can do this one of four ways:

1. Upload `template-pipeline.yml` from your local machine
2. Point to a template in an S3 bucket.
3. Edit Template "In Place" in the Template Designer
4. Create or Update the stack using AWS CLI (Command Line Interface)

## Option 1: Upload from Local Machine

1. Go to your `-pipeline` stack in the CloudFormation AWS Web Console and choose Update
2. Choose "Replace current template"
3. Choose "Upload a template file"
4. Upload your file
5. Update any Parameters and Tags on the next page
6. Choose the deployment role (Typically something like `ACME-CloudFormationServiceRole`) If unsure look at the Stack Info/Overview/IAM Role assigned to similar Deploy stacks.
7. Check the box for acknowledging AWS may create resources.
8. Watch the stack update progress. Hopefully it is successful!

## Option 2: Point to the S3 Bucket

1. Go to your `-pipeline` stack and choose Update
2. Choose "Replace current template"
3. Choose "Amazon S3 URL" and enter in the S3 location of a template using the `https` protocol. (Even if it is not a publicly accessible bucket, `https://` not `s3://` is used). For example: `https://63klabs.s3.amazonaws.com/atlantis/v2/template-pipeline.yml`
4. Update any Parameters and Tags on the next page
5. Choose the deployment role (Typically something like `ACME-CloudFormationServiceRole`) If unsure look at the Stack Info/Overview/IAM Role assigned to similar Deploy stacks.
6. Check the box for acknowledging AWS may create resources.
7. Watch the stack update progress. Hopefully it is successful!

## Option 3: Edit Template "In Place" in the Template Designer

1. Go to your `-pipeline` stack and choose Update
2. Choose "Edit template in designer" and then the button "View in Designer"
3. You will see a code section at the bottom of the diagram.
4. You can do one of two things:
    1. Copy the entire contents of the new template file and paste it into the designer
    2. Perform edits within the designer
5. When finished, choose "Validate"
6. Once validated, choose "Upload" (Cloud icon with up arrow)
7. Update any Parameters and Tags on the next page
5. Choose the deployment role (Typically something like `ACME-CloudFormationServiceRole`) If unsure look at the Stack Info/Overview/IAM Role assigned to similar Deploy stacks.
6. Check the box for acknowledging AWS may create resources.
7. Watch the stack update progress. Hopefully it is successful!

## Option 4: Update using the AWS CLI

This option is outlined in [README: Use AWS CLI](../scripts/README-CLI.md).

It may be beneficial to use this option as you can maintain input files that define your stack using parameters and tags. This is helpful as it avoids manual entry, is re-producible, self-documents, and maintains the concept of infrastructure as code.

Other similar options that avoid the Web Console and still follow Infrastructure as Code are using Terraform and AWS CDK for the process of creating and updating the deploy pipeline stack. (Exploring and implementing those options are far beyond the scope of this template and its tutorials.)
