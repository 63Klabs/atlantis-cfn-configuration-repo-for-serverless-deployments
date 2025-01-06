> i want a python script that can be given the name of an existing CloudFormation stack in my account and then generate a sam config file (toml format) for future use

I'll help you create a Python script that can generate a SAM config file (samconfig.toml) based on an existing CloudFormation stack. This script will use boto3 to get the stack information and create the TOML configuration. [1]

Here's the script:

```python
import boto3
import tomlkit
import argparse
from datetime import datetime

def get_stack_info(stack_name, region):
    """Retrieve stack information from CloudFormation"""
    cfn = boto3.client('cloudformation', region_name=region)
    
    try:
        # Get stack details
        stack = cfn.describe_stacks(StackName=stack_name)['Stacks'][0]
        
        # Get stack parameters
        parameters = {param['ParameterKey']: param['ParameterValue'] 
                     for param in stack.get('Parameters', [])}
        
        # Get stack tags
        tags = {tag['Key']: tag['Value'] 
                for tag in stack.get('Tags', [])}
        
        return {
            'parameters': parameters,
            'tags': tags,
            'capabilities': stack.get('Capabilities', []),
            'region': stack['StackId'].split(':')[3],  # Extract region from stack ID
        }
    
    except Exception as e:
        print(f"Error getting stack information: {str(e)}")
        raise

def create_sam_config(stack_name, stack_info):
    """Create SAM config file in TOML format"""
    config = tomlkit.document()
    
    # Create version
    config["version"] = 0.1
    
    # Create default config
    default = tomlkit.table()
    
    # Deploy configuration
    deploy = tomlkit.table()
    deploy["parameters"] = tomlkit.table()
    
    # Add stack parameters
    parameter_overrides = []
    for key, value in stack_info['parameters'].items():
        parameter_overrides.append(f"{key}={value}")
    
    deploy["parameters"]["stack_name"] = stack_name
    deploy["parameters"]["region"] = stack_info['region']
    deploy["parameters"]["confirm_changeset"] = True
    deploy["parameters"]["capabilities"] = stack_info['capabilities']
    
    if parameter_overrides:
        deploy["parameters"]["parameter_overrides"] = " ".join(parameter_overrides)
    
    # Add tags if they exist
    if stack_info['tags']:
        tags = []
        for key, value in stack_info['tags'].items():
            tags.append(f"{key}={value}")
        deploy["parameters"]["tags"] = " ".join(tags)
    
    default["deploy"] = deploy
    config["default"] = default
    
    # Write to samconfig.toml
    with open("samconfig.toml", "w") as f:
        tomlkit.dump(config, f)

def main():
    parser = argparse.ArgumentParser(description='Generate SAM config from existing CloudFormation stack')
    parser.add_argument('--stack-name', required=True, help='Name of the existing CloudFormation stack')
    parser.add_argument('--region', required=False, default='us-east-1', help='AWS region (default: us-east-1)')
    
    args = parser.parse_args()
    
    try:
        print(f"Fetching information for stack: {args.stack_name}")
        stack_info = get_stack_info(args.stack_name, args.region)
        
        print("Generating samconfig.toml file...")
        create_sam_config(args.stack_name, stack_info)
        
        print("Successfully created samconfig.toml")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
```

To use this script, you'll need to:

Install the required dependencies:

```bash
pip install boto3 tomlkit
```

Make sure you have AWS credentials configured (either through AWS CLI or environment variables)

Run the script with a stack name:

```bash
python script.py --stack-name your-stack-name --region your-region
```

The script will:

- Fetch the existing stack's information using boto3
- Extract parameters, tags, capabilities, and region
- Generate a samconfig.toml file with the deploy configuration
- Include all parameter overrides and tags from the original stack

The generated samconfig.toml will contain:

- Stack name
- Region
- Capabilities (if any)
- Parameter overrides (if any)
- Tags (if any)
- Confirm changeset setting

This configuration file can then be used with SAM CLI commands like sam deploy.

Note that you'll need appropriate AWS permissions to describe the CloudFormation stack in your account for this script to work.

Sources

[1] sam list stack-outputs - AWS Serverless Application Model
https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-list-stack-outputs.html

> I need to be able to add a --profile argument to this script, and pass it along to the command

I'll modify the script to include AWS profile support. Here's the updated version:

```python
import boto3
import tomlkit
import argparse
from datetime import datetime

def get_stack_info(stack_name, region, profile=None):
    """Retrieve stack information from CloudFormation"""
    # Create session with profile if specified
    if profile:
        session = boto3.Session(profile_name=profile)
        cfn = session.client('cloudformation', region_name=region)
    else:
        cfn = boto3.client('cloudformation', region_name=region)
    
    try:
        # Get stack details
        stack = cfn.describe_stacks(StackName=stack_name)['Stacks'][0]
        
        # Get stack parameters
        parameters = {param['ParameterKey']: param['ParameterValue'] 
                     for param in stack.get('Parameters', [])}
        
        # Get stack tags
        tags = {tag['Key']: tag['Value'] 
                for tag in stack.get('Tags', [])}
        
        return {
            'parameters': parameters,
            'tags': tags,
            'capabilities': stack.get('Capabilities', []),
            'region': stack['StackId'].split(':')[3],  # Extract region from stack ID
            'profile': profile  # Include profile in stack info
        }
    
    except Exception as e:
        print(f"Error getting stack information: {str(e)}")
        raise

def create_sam_config(stack_name, stack_info):
    """Create SAM config file in TOML format"""
    config = tomlkit.document()
    
    # Create version
    config["version"] = 0.1
    
    # Create default config
    default = tomlkit.table()
    
    # Deploy configuration
    deploy = tomlkit.table()
    deploy["parameters"] = tomlkit.table()
    
    # Add stack parameters
    parameter_overrides = []
    for key, value in stack_info['parameters'].items():
        parameter_overrides.append(f"{key}={value}")
    
    deploy["parameters"]["stack_name"] = stack_name
    deploy["parameters"]["region"] = stack_info['region']
    deploy["parameters"]["confirm_changeset"] = True
    deploy["parameters"]["capabilities"] = stack_info['capabilities']
    
    # Add profile if specified
    if stack_info['profile']:
        deploy["parameters"]["profile"] = stack_info['profile']
    
    if parameter_overrides:
        deploy["parameters"]["parameter_overrides"] = " ".join(parameter_overrides)
    
    # Add tags if they exist
    if stack_info['tags']:
        tags = []
        for key, value in stack_info['tags'].items():
            tags.append(f"{key}={value}")
        deploy["parameters"]["tags"] = " ".join(tags)
    
    default["deploy"] = deploy
    config["default"] = default
    
    # Write to samconfig.toml
    with open("samconfig.toml", "w") as f:
        tomlkit.dump(config, f)

def main():
    parser = argparse.ArgumentParser(description='Generate SAM config from existing CloudFormation stack')
    parser.add_argument('--stack-name', required=True, help='Name of the existing CloudFormation stack')
    parser.add_argument('--region', required=False, default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--profile', required=False, help='AWS profile name')
    
    args = parser.parse_args()
    
    try:
        print(f"Fetching information for stack: {args.stack_name}")
        stack_info = get_stack_info(args.stack_name, args.region, args.profile)
        
        print("Generating samconfig.toml file...")
        create_sam_config(args.stack_name, stack_info)
        
        print("Successfully created samconfig.toml")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
```

Key changes made:

1. Added a `--profile` argument to the script
2. Modified `get_stack_info()` to accept a profile parameter
3. Created a boto3 Session with the specified profile when provided
4. Included the profile in the stack_info dictionary
5. Added the profile to the samconfig.toml output when specified

You can now run the script with a profile:

```bash
python script.py --stack-name your-stack-name --region your-region --profile your-profile-name
```

The generated samconfig.toml will now include the profile in its configuration when specified, which SAM CLI will use during deployments.

> I need the parameter_overrides to be in \"key\"=\"value\" format. Same with tags

I'll modify the script to format the parameter_overrides and tags with quoted keys and values. Here's the updated version:

```python
import boto3
import tomlkit
import argparse
from datetime import datetime

def get_stack_info(stack_name, region, profile=None):
    """Retrieve stack information from CloudFormation"""
    # Create session with profile if specified
    if profile:
        session = boto3.Session(profile_name=profile)
        cfn = session.client('cloudformation', region_name=region)
    else:
        cfn = boto3.client('cloudformation', region_name=region)
    
    try:
        # Get stack details
        stack = cfn.describe_stacks(StackName=stack_name)['Stacks'][0]
        
        # Get stack parameters
        parameters = {param['ParameterKey']: param['ParameterValue'] 
                     for param in stack.get('Parameters', [])}
        
        # Get stack tags
        tags = {tag['Key']: tag['Value'] 
                for tag in stack.get('Tags', [])}
        
        return {
            'parameters': parameters,
            'tags': tags,
            'capabilities': stack.get('Capabilities', []),
            'region': stack['StackId'].split(':')[3],  # Extract region from stack ID
            'profile': profile  # Include profile in stack info
        }
    
    except Exception as e:
        print(f"Error getting stack information: {str(e)}")
        raise

def format_key_value_pair(key, value):
    """Format key-value pairs with escaped quotes"""
    return f'\\"{key}\\"=\\"{value}\\"'

def create_sam_config(stack_name, stack_info):
    """Create SAM config file in TOML format"""
    config = tomlkit.document()
    
    # Create version
    config["version"] = 0.1
    
    # Create default config
    default = tomlkit.table()
    
    # Deploy configuration
    deploy = tomlkit.table()
    deploy["parameters"] = tomlkit.table()
    
    # Add stack parameters
    parameter_overrides = []
    for key, value in stack_info['parameters'].items():
        parameter_overrides.append(format_key_value_pair(key, value))
    
    deploy["parameters"]["stack_name"] = stack_name
    deploy["parameters"]["region"] = stack_info['region']
    deploy["parameters"]["confirm_changeset"] = True
    deploy["parameters"]["capabilities"] = stack_info['capabilities']
    
    # Add profile if specified
    if stack_info['profile']:
        deploy["parameters"]["profile"] = stack_info['profile']
    
    if parameter_overrides:
        deploy["parameters"]["parameter_overrides"] = " ".join(parameter_overrides)
    
    # Add tags if they exist
    if stack_info['tags']:
        tags = []
        for key, value in stack_info['tags'].items():
            tags.append(format_key_value_pair(key, value))
        deploy["parameters"]["tags"] = " ".join(tags)
    
    default["deploy"] = deploy
    config["default"] = default
    
    # Write to samconfig.toml
    with open("samconfig.toml", "w") as f:
        tomlkit.dump(config, f)

def main():
    parser = argparse.ArgumentParser(description='Generate SAM config from existing CloudFormation stack')
    parser.add_argument('--stack-name', required=True, help='Name of the existing CloudFormation stack')
    parser.add_argument('--region', required=False, default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--profile', required=False, help='AWS profile name')
    
    args = parser.parse_args()
    
    try:
        print(f"Fetching information for stack: {args.stack_name}")
        stack_info = get_stack_info(args.stack_name, args.region, args.profile)
        
        print("Generating samconfig.toml file...")
        create_sam_config(args.stack_name, stack_info)
        
        print("Successfully created samconfig.toml")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
```

Key changes made:

1. Added a new `format_key_value_pair()` function to handle the quoted format
2. Modified the parameter_overrides formatting to use `\"key\"=\"value\"` format
3. Applied the same formatting to tags

Now when you run the script, the generated samconfig.toml will contain parameter overrides and tags in the correct format. For example:

```toml
[default.deploy.parameters]
parameter_overrides = "\"ParameterKey1\"=\"value1\" \"ParameterKey2\"=\"value2\""
tags = "\"TagKey1\"=\"value1\" \"TagKey2\"=\"value2\""
```

This format ensures compatibility with SAM CLI's expected format for parameter overrides and tags.

> There are too many backslashes in the generated samconfig-ws-sam-api-chadkluck-prod-deploy.toml file for tags and parameter overrides. Why are extra backslashes being added from the toml-from-stack.py script?

The extra backslashes are appearing because the `format_key_value_pair()` function is adding escape characters (`\`) for the quotes, and then the TOML serialization is also escaping them. Let's modify the function to use single quotes around the f-string to avoid double escaping:

```python
def format_key_value_pair(key, value):
    """Format key-value pairs with escaped quotes"""
    return f'""{key}""=""{value}""'
```

Or alternatively:

```python
def format_key_value_pair(key, value):
    """Format key-value pairs with escaped quotes"""
    return f'"{key}"="{value}"'
```

This should generate the correct format in the TOML file without extra escaping. The resulting TOML file should have entries that look like: [1]

```toml
parameter_overrides = '"ParameterKey1"="value1" "ParameterKey2"="value2"'
tags = '"TagKey1"="value1" "TagKey2"="value2"'
```

Instead of the current output with extra backslashes. The rest of your script can remain the same. This change will ensure the proper escaping level in the generated TOML file.

Sources

[1] [Python and TOML: New Best Friends – Real Python](https://realpython.com/python-toml/)
