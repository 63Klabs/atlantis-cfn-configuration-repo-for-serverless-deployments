# pip install boto3 toml click

# v0.1 - 2025-01-06
# Designed, Prompt Engineered, and Reviewed by Chad Leigh Kluck
# Written by Amazon Q

# TODO: Read in tags 
# TODO: Add tags to config
# TODO: Write toml file to correct location with correct name
# TODO: Read in toml file and set defaults
# TODO: For pipeline, network allow multiple stages instead of just default

# TODO: Test deploy
# TODO: Test read existing stack

import boto3
import toml
import json
import logging
import yaml
import re
import sys
import os
from pathlib import Path
from typing import Dict, Optional, List
import click
from botocore.exceptions import ClientError

class ConfigManager:
    def __init__(self, prefix: str, infra_type: str, project_id: str, stage_id: Optional[str] = None):
        self.prefix = prefix
        self.infra_type = infra_type
        self.project_id = project_id
        self.stage_id = stage_id or 'default'
        self.cfn_client = boto3.client('cloudformation')
        self.templates_dir = Path('..') / f"{infra_type}-infrastructure/templates"
        self.settings_dir = Path("settings")

        # Validate inputs
        if infra_type != 'service-role' and project_id is None:
            raise ValueError("project_id is required for non-service-role infrastructure types")

    def generate_stack_name(prefix: str, project_id: str, stage_id: str, infra_type: str) -> str:
        """Generate the stack name based on the prefix, project, stage, and infra type"""
        stack_name = f"{prefix}-"

        if project_id:
            stack_name += f"{project_id}-"
        
        if stage_id != 'default' and stage_id:
            stack_name += f"{stage_id}-"

        stack_name += f"{infra_type}"

        return stack_name
    
    def read_samconfig(self) -> Optional[Dict]:
        """Read existing samconfig.toml if it exists
		
		Naming convention: samconfig-Prefix-ProjectId-InfraType.toml
		For service-role: samconfig-Prefix-service-role.toml
		"""
        if self.infra_type == 'service-role':
			# For service-role, we don't include project_id in the filename
            samconfig_path = Path(f"samconfig-{self.prefix}-service-role.toml")
        else:
			# For all other infrastructure types, include project_id
            samconfig_path = Path(f"samconfig-{self.prefix}-{self.project_id}-{self.infra_type}.toml")
		
        if samconfig_path.exists():
            return toml.load(samconfig_path)
        return None

    def get_stack_config(self, stack_name: str) -> Optional[Dict]:
        """Get configuration from existing CloudFormation stack"""
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            # Get template file from tags
            template_file = None
            for tag in stack.get('Tags', []):
                if tag['Key'] == 'atlantis:TemplateFile':
                    template_file = tag['Value']
                    
            return {
                'parameters': {p['ParameterKey']: p['ParameterValue'] 
                             for p in stack.get('Parameters', [])},
                'template_file': template_file
            }
        except ClientError:
            return None

    def compare_configurations(self, local_config: Dict, stack_config: Dict) -> Dict:
        """Compare local and deployed configurations"""
        differences = {}
        
        for key, local_value in local_config.items():
            stack_value = stack_config.get(key)
            if stack_value != local_value:
                differences[key] = {
                    'local': local_value,
                    'deployed': stack_value
                }
        return differences

    def get_template_parameters(self, template_path: str) -> Dict:
        """Get parameters from CloudFormation template"""
        if template_path.startswith('s3://'):
            # Handle S3 template
            pass
        else:
            # Handle local template
            template_path = self.templates_dir / template_path
            
            try:
                # Read the file content
                with open(template_path) as f:
                    # Look for the Parameters section
                    parameters_section = ""
                    in_parameters = False
                    
                    for line in f:
                        if line.startswith('Parameters:'):
                            in_parameters = True
                            parameters_section = line
                        elif in_parameters:
                            # Check if we've moved to a new top-level section
                            if line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                                break
                            parameters_section += line
                    
                    # Parse just the Parameters section
                    if parameters_section:
                        # Add a dummy root to ensure valid YAML
                        yaml_content = yaml.safe_load(parameters_section)
                        return yaml_content.get('Parameters', {})
                    return {}
                    
            except Exception as e:
                logging.error(f"Error parsing template file {template_path}: {e}")
                return {}


    def discover_templates(self) -> List[str]:
        """Discover available templates in the infrastructure type directory"""
        return [f.name for f in self.templates_dir.glob('*.yml')]

    def load_defaults(self) -> Dict:
        """Load default values from settings files in a specific order, with later files
        overwriting properties from earlier files.
        
        Order:
        1. defaults.json
        2. {prefix}-defaults.json
        3. {prefix}-{project_id}-defaults.json
        4. infra_type/{prefix}-defaults.json
        5. infra_type/{prefix}-{project_id}-defaults.json
        6. infra_type/{prefix}-{project_id}-{stage_id}-defaults.json
        """
        defaults = {}
        
        # Define the sequence of potential config files
        config_files = [
            self.settings_dir / "defaults.json",
            self.settings_dir / f"{self.prefix}-defaults.json"
        ]
        
        # Add project_id specific files only if project_id exists
        if self.project_id:
            config_files.extend([
                self.settings_dir / f"{self.prefix}-{self.project_id}-defaults.json",
            ])
        
        # Add infra_type specific files
        config_files.append(self.settings_dir / f"{self.infra_type}" / f"{self.prefix}-defaults.json")
        
        # Add project_id specific files in infra_type directory
        if self.project_id:
            config_files.append(
                self.settings_dir / f"{self.infra_type}" / f"{self.prefix}-{self.project_id}-defaults.json"
            )
            
            # Add stage_id specific file only if both project_id and stage_id exist
            if self.stage_id and self.stage_id != 'default':
                config_files.append(
                    self.settings_dir / f"{self.infra_type}" / 
                    f"{self.prefix}-{self.project_id}-{self.stage_id}-defaults.json"
                )
        
        # Load each config file in sequence if it exists
        for config_file in config_files:
            try:
                if config_file.exists():
                    with open(config_file) as f:
                        # Update defaults with new values, overwriting any existing ones
                        defaults.update(json.load(f))
            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON from {config_file}: {e}")
            except Exception as e:
                logging.error(f"Error loading config file {config_file}: {e}")
                
        return defaults

    def prompt_for_parameters(self, parameters: Dict, defaults: Dict) -> Dict:
        """Prompt user for parameter values"""
        values = {}
        
        # Add prefix, project_id and stage_id to defaults if they exist
        if self.prefix and 'Prefix' in parameters:
            defaults['Prefix'] = self.prefix

        if self.prefix and 'PrefixUpper' in parameters:
            defaults['PrefixUpper'] = self.prefix.upper()

        if self.project_id and 'ProjectId' in parameters:
            defaults['ProjectId'] = self.project_id
        
        if self.stage_id and 'StageId' in parameters:
            defaults['StageId'] = self.stage_id
        
        for param_name, param_def in parameters.items():
            default_value = defaults.get(param_name, param_def.get('Default', ''))
            
            while True:
                value = click.prompt(
                    f"{param_name} [{default_value}]",
                    default=default_value,
                    show_default=False
                )
                
                if value == '?':
                    click.echo(param_def.get('Description', 'No description available'))
                    continue
                elif value == '^':
                    raise click.Abort()
                elif value == '-':
                    value = ''
                
                # Validate parameter
                if self.validate_parameter(value, param_def):
                    values[param_name] = value
                    break
                else:
                    click.echo(f"Invalid value for {param_name}")
                    
        return values

    def select_template(self, templates: List[str]) -> str:
        """Display numbered list of templates and let user select by number"""
        if not templates:
            logging.error("No templates found")
            sys.exit(1)
        
        # Sort templates for consistent ordering
        templates.sort()
        
        # Display numbered list
        print("\nAvailable templates:")
        for idx, template in enumerate(templates, 1):
            print(f"{idx}. {template}")
        
        while True:
            try:
                choice = input("\nEnter template number: ")
                # Check if input is a number
                template_idx = int(choice) - 1
                
                # Validate the index is within range
                if 0 <= template_idx < len(templates):
                    return templates[template_idx]
                else:
                    print(f"Please enter a number between 1 and {len(templates)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\nTemplate selection cancelled")
                sys.exit(1)

    def gather_global_parameters(self, infra_type: str) -> Dict:
        """Gather global deployment parameters"""
        global_params = {}
        
        # Get S3 bucket for deployments
        global_params['s3_bucket'] = click.prompt(
            "S3 bucket for deployments",
            type=str,
            default=os.getenv('SAM_DEPLOY_BUCKET', '')
        )
        
        # Get AWS region
        global_params['region'] = click.prompt(
            "AWS region",
            type=str,
            default=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Confirm changeset prompt
        global_params['confirm_changeset'] = click.prompt(
            "Confirm changeset before deploy",
            type=bool,
            default=True
        )
        
        # Get role ARN if this is a pipeline deployment
        if infra_type == 'pipeline':
            global_params['role_arn'] = click.prompt(
                "IAM role ARN for deployments",
                type=str,
                default=os.getenv('SAM_DEPLOY_ROLE', '')
            )
        
        return global_params

    def build_config(self, template_file: str, parameter_values: Dict, infra_type: str) -> Dict:
        """Build the complete config dictionary"""
        # Get global parameters
        global_params = self.gather_global_parameters(infra_type)

        stack_name = self.generate_stack_name(self.prefix, self.project_id, self.stage_id, infra_type)
        
        # Build the config structure
        config = {
            'globals': {
                'deploy': {
                    'parameters': {
                        'template_file': template_file,
                        's3_bucket': global_params['s3_bucket'],
                        'region': global_params['region'],
                        'capabilities': 'CAPABILITY_NAMED_IAM',
                        'confirm_changeset': global_params['confirm_changeset']
                    }
                }
            },
            'default': {
                'deploy': {
                    'parameters': {
                        'stack_name': stack_name,
                        's3_prefix': stack_name,
                        'parameter_overrides': parameter_values
                    }
                }
            }
        }
        
        # Add role_arn if this is a pipeline deployment
        if infra_type == 'pipeline':
            config['globals']['deploy']['parameters']['role_arn'] = global_params['role_arn']
        
        return config

    def validate_parameter(self, value: str, param_def: Dict) -> bool:
        """Validate parameter value against CloudFormation parameter definition
        
        Validates against:
        - AllowedPattern (regex pattern)
        - AllowedValues (list of allowed values)
        - MinLength/MaxLength (for string types)
        - MinValue/MaxValue (for numeric types)
        """
        if not value and param_def.get('Default'):
            # Empty value with default defined is valid
            return True
            
        param_type = param_def.get('Type', 'String')
        
        # Check AllowedValues if defined
        allowed_values = param_def.get('AllowedValues', [])
        if allowed_values and value not in allowed_values:
            logging.error(f"Value must be one of: {', '.join(allowed_values)}")
            return False
        
        # Check AllowedPattern if defined
        allowed_pattern = param_def.get('AllowedPattern')
        if allowed_pattern and not re.match(allowed_pattern, value):
            logging.error(f"Value must match pattern: {allowed_pattern}")
            return False
        
        # Type-specific validations
        if param_type in ['String', 'AWS::SSM::Parameter::Value<String>']:
            min_length = int(param_def.get('MinLength', 0))
            # Handle MaxLength differently - if not specified, use None instead of infinity
            max_length = param_def.get('MaxLength')
            if max_length is not None:
                max_length = int(max_length)
            
            if len(value) < min_length:
                logging.error(f"String length must be at least {min_length}")
                return False
            if max_length is not None and len(value) > max_length:
                logging.error(f"String length must be no more than {max_length}")
                return False
                
        elif param_type in ['Number', 'AWS::SSM::Parameter::Value<Number>']:
            try:
                num_value = float(value)
                min_value = float(param_def.get('MinValue', float('-inf')))
                max_value = float(param_def.get('MaxValue', float('inf')))
                
                if num_value < min_value:
                    logging.error(f"Number must be at least {min_value}")
                    return False
                if num_value > max_value:
                    logging.error(f"Number must be no more than {max_value}")
                    return False
                    
            except ValueError:
                logging.error("Value must be a number")
                return False
                
        elif param_type == 'CommaDelimitedList':
            # Validate each item in the comma-delimited list
            items = [item.strip() for item in value.split(',')]
            if not all(items):
                logging.error("CommaDelimitedList cannot contain empty items")
                return False
                
        elif param_type == 'List<Number>':
            try:
                items = [item.strip() for item in value.split(',')]
                # Verify each item is a valid number
                [float(item) for item in items]
            except ValueError:
                logging.error("All items must be valid numbers")
                return False
                
        elif param_type == 'AWS::EC2::KeyPair::KeyName':
            if not value:
                logging.error("KeyPair name cannot be empty")
                return False
                
        elif param_type == 'AWS::EC2::VPC::Id':
            if not value.startswith('vpc-'):
                logging.error("VPC ID must start with 'vpc-'")
                return False
                
        elif param_type == 'AWS::EC2::Subnet::Id':
            if not value.startswith('subnet-'):
                logging.error("Subnet ID must start with 'subnet-'")
                return False
                
        elif param_type == 'AWS::EC2::SecurityGroup::Id':
            if not value.startswith('sg-'):
                logging.error("Security Group ID must start with 'sg-'")
                return False
        
        return True

    def save_config(self, config: Dict) -> None:
        """Save configuration to samconfig.toml file"""
        try:
            # Get the parameter values from the config
            parameter_values = config.get('default', {}).get('deploy', {}).get('parameters', {}).get('parameter_overrides', {})
            
            # Convert parameter_values dict to parameter_overrides string
            if isinstance(parameter_values, dict):
                parameter_overrides = " ".join([
                    f'{key}="{value}"' for key, value in parameter_values.items()
                ])
                
                # Update the config with the string version
                config['default']['deploy']['parameters']['parameter_overrides'] = parameter_overrides
            
            # Create the header with version and comments
            header = (
                'version = 0.1\n\n'
                '# !!! DO NOT EDIT THIS FILE !!!\n\n'
                '# Make changes and re-generate this file by running the python script:\n\n'
                f'# python {sys.argv[0]} {" ".join(sys.argv[1:])}\n\n'
                '# Using the script provides consistent parameter overrides and tags '
                'and ensures your changes are not overwritten!\n\n'
            )
            
            # Write the config to samconfig.toml
            with open('samconfig.toml', 'w') as f:
                f.write(header)
                toml.dump(config, f)
                
            logging.info("Configuration saved to samconfig.toml")
            
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            sys.exit(1)


@click.command()
@click.option('--check-stack', is_flag=True, help='Check existing stack configuration')
@click.option('--profile', help='AWS profile name')
@click.argument('infra_type')
@click.argument('prefix')
@click.argument('project_id', required=False)
@click.argument('stage_id', required=False)
def main(check_stack: bool, profile: str, infra_type: str, prefix: str, 
        project_id: Optional[str], stage_id: Optional[str]):
    if profile:
        boto3.setup_default_session(profile_name=profile)
    
    # Validate project_id requirement
    if infra_type != 'service-role' and not project_id:
        raise click.UsageError("project_id is required for non-service-role infrastructure types")
        
    config_manager = ConfigManager(prefix, infra_type, project_id, stage_id)
    
    # Read existing configuration
    local_config = config_manager.read_samconfig()
    
    if check_stack:
        stack_name = f"{project_id}-{stage_id}"
        stack_config = config_manager.get_stack_config(stack_name)
        
        if stack_config and local_config:
            differences = config_manager.compare_configurations(local_config, stack_config)
            if differences:
                click.echo("Differences found between local and deployed configuration:")
                click.echo(json.dumps(differences, indent=2))
                
                choice = click.prompt(
                    "Choose configuration to use (local/deployed/cancel)",
                    type=click.Choice(['local', 'deployed', 'cancel'])
                )
                
                if choice == 'cancel':
                    raise click.Abort()
                elif choice == 'deployed':
                    local_config = stack_config

    # Handle template selection and parameter configuration
    # Handle template selection and parameter configuration
    if not local_config:
        templates = config_manager.discover_templates()
        template_file = config_manager.select_template(templates)
    else:
        template_file = local_config['template_file']

    parameters = config_manager.get_template_parameters(template_file)
    defaults = config_manager.load_defaults()
    
    # Prompt for parameters
    parameter_values = config_manager.prompt_for_parameters(parameters, defaults)
    
    # Build the complete config
    config = config_manager.build_config(template_file, parameter_values, infra_type)
    
    # Save the config
    config_manager.save_config(config)

if __name__ == '__main__':
    main()
