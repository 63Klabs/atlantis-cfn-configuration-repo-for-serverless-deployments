import boto3
import tomlkit
import argparse
from datetime import datetime
import os

def format_key_value_pair(key, value):
    """Format key-value pairs with escaped quotes"""
    return f'"{key}"="{value}"'

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
            'profile': profile
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
    
        
    deploy["parameters"]["stack_name"] = stack_name
    deploy["parameters"]["region"] = stack_info['region']
    deploy["parameters"]["confirm_changeset"] = True
    deploy["parameters"]["capabilities"] = stack_info['capabilities']
    
    # Add profile if specified
    if stack_info['profile']:
        deploy["parameters"]["profile"] = stack_info['profile']
    
    # Add stack parameters
    parameter_overrides = []
    for key, value in stack_info['parameters'].items():
        parameter_overrides.append(format_key_value_pair(key, value))

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
    
	# if imports folder does not exist, create it
    if not os.path.exists("../imports"):
        os.makedirs("../imports")

    samconfig_path = f"../imports/samconfig-{stack_name}.toml"
        
    # Write to samconfig.toml
    with open(samconfig_path, "w") as f:
        tomlkit.dump(config, f)
        
    return samconfig_path

def main():
    parser = argparse.ArgumentParser(description='Generate SAM config from existing CloudFormation stack')
    parser.add_argument('--stack-name', required=True, help='Name of the existing CloudFormation stack')
    parser.add_argument('--region', required=False, default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--profile', required=False, help='AWS profile name')
    
    args = parser.parse_args()
    
    try:
        print(f"Fetching information for stack: {args.stack_name}")
        stack_info = get_stack_info(args.stack_name, args.region, args.profile)

        print(f"Generating samconfig-{args.stack_name}.toml file...")
        saved_file = create_sam_config(args.stack_name, stack_info)
        
        print(f"Successfully created {saved_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()


# ws-sam-api-chadkluck-prod-deploy
# python script.py --stack-name your-stack-name --region your-region --profile your-profile-name
# python3 toml-from-stack.py --stack-name ws-sam-api-chadkluck-prod-deploy --region us-east-2 --profile chadkluck
