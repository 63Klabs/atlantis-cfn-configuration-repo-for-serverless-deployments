VERSION = "v0.1.0/2025-01-12"
# Written by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

# =============================================================================
# Usage:
#
# `python config.py <infra_type> <prefix> [<project_id>] [<stage_id>] [--check-stack true] [--profile default]`
#
# Create/Update a service-role with prefix acme
# `python config.py service-role acme`
#
# Create/Update a pipeline with prefix acme, project_id widget-ws, and stage_id test
# `python config.py pipeline acme widget-ws test`
#
# Import/Check existing stack using local AWS credential profile devuser
# `python config.py network acme widget-ws test --check-stack true --profile devuser`
#
# -----------------------------------------------------------------------------
# Install:
#
# `sudo pip install boto3 toml click`
# ---------- OR ----------
# `sudo apt install python3-boto3 python3-toml python3-click`
#
# -----------------------------------------------------------------------------
# Full Documentation:
#
# Check local READMEs or GitHub repository:
# https://github.com/chadkluck/atlantis-for-aws-sam-deployments/
#
# =============================================================================

# TODO: Test validation of prompts along with ? - ^
# TODO: Test deploy
# TODO: Test read existing stack

# TODO: Validate Tag reads

# Q's suggestions
# TODO: Better error handling
# TODO: More detailed logging
# TODO: Template validation before deployment

import boto3
import toml
import json
import logging
import yaml
import re
import sys
import os
import shlex
import click
import hashlib
from pathlib import Path
from typing import Dict, Optional, List
from botocore.exceptions import ClientError

# if logs directory does not exist, create it
if not os.path.exists('logs'):
    os.makedirs('logs')
    
logging.basicConfig(
    level=logging.INFO,
    filename='logs/script-config.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class ConfigManager:
    def __init__(self, infra_type: str, prefix: str, project_id: str, stage_id: Optional[str] = 'default'):
        self.prefix = prefix
        self.infra_type = infra_type
        self.project_id = project_id
        self.stage_id = stage_id
        self.cfn_client = boto3.client('cloudformation')
        self.templates_dir = Path('..') / f"{infra_type}-infrastructure/templates"
        self.samconfig_dir = Path('..') / f"{infra_type}-infrastructure"
        self.settings_dir = Path("settings")
        self.template_version = 'No version found'
        self.template_hash = None
        self.template_hash_id = None
        self.template_file = None

        # Validate inputs
        if infra_type != 'service-role' and project_id is None:
            raise ValueError("project_id is required for non-service-role infrastructure types")

    def generate_stack_name(self, prefix: str, project_id: str, stage_id: str) -> str:
        """Generate the stack name based on the prefix, project, stage, and infra type"""
        stack_name = f"{prefix}-"

        if project_id:
            stack_name += f"{project_id}-"
        
        if  stage_id and stage_id != 'default':
            stack_name += f"{stage_id}-"

        stack_name += f"{self.infra_type}"

        return stack_name
    
    def generate_samconfig_path(self, prefix: str, project_id: str) -> Path:
        """Generate the samconfig path based on the prefix, project, stage, and infra type
        		
		Naming convention: samconfig-Prefix-ProjectId-InfraType.toml
		For service-role: samconfig-Prefix-service-role.toml
        """
        if self.infra_type == 'service-role':
            # For service-role, we don't include project_id in the filename
            samconfig_path = self.samconfig_dir / f"samconfig-{prefix}-service-role.toml"
        else:
            # For all other infrastructure types, include project_id
            samconfig_path = self.samconfig_dir / f"samconfig-{prefix}-{project_id}-{self.infra_type}.toml"

        return samconfig_path
    
    def read_samconfig(self) -> Optional[Dict]:
        """Read existing samconfig.toml if it exists"""
        samconfig_path = self.generate_samconfig_path(self.prefix, self.project_id)
        
        if samconfig_path.exists():
            try:
                print()
                click.echo(formatted_output_with_value("Using samconfig file:", samconfig_path))
                print()

                samconfig_data = {'global': {}, 'deployments': {}}
                samconfig = toml.load(samconfig_path)
                
                # Handle global section
                if 'global' in samconfig and isinstance(samconfig['global'], dict):
                    samconfig_data['global'] = samconfig['global']

                # Handle deployment sections
                for key, value in samconfig.items():
                    if key != 'global' and isinstance(value, dict):
                        try:
                            deploy_params = value.get('deploy', {}).get('parameters', {})
                            if isinstance(deploy_params, dict):
                                parameter_overrides = deploy_params.get('parameter_overrides', '')
                                if parameter_overrides and isinstance(parameter_overrides, str):
                                    value['deploy']['parameters']['parameter_overrides'] = self.parse_parameter_overrides(parameter_overrides)
                                tags = deploy_params.get('tags', '')
                                if tags and isinstance(tags, str):
                                    value['deploy']['parameters']['tags'] = self.parse_tags(tags)
                                samconfig_data['deployments'][key] = value
                        except (AttributeError, TypeError) as e:
                            logging.warning(f"Skipping invalid deployment section '{key}': {e}")
                            continue

                return samconfig_data
            except Exception as e:
                logging.error(f"Error reading samconfig file {samconfig_path}: {e}")
                return None
        return None

    def parse_parameter_overrides(self, parameter_overrides_as_string: str) -> Dict:
        """Parse parameter overrides string into a dictionary"""
        if not parameter_overrides_as_string:
            return {}
        
        parameters = {}
        current_key = None
        current_value = []
        
        # Split the string while preserving quoted strings
        tokens = shlex.split(parameter_overrides_as_string)
        
        for token in tokens:
            if '=' in token:
                # If we have a previous key-value pair, add it to parameters
                if current_key is not None:
                    parameters[current_key] = ' '.join(current_value)
                    current_value = []
                
                # Start new key-value pair
                key, value = token.split('=', 1)
                current_key = key.strip('"')
                current_value = [value.strip('"')]
            else:
                # Continuation of previous value
                if current_key is not None:
                    current_value.append(token.strip('"'))
        
        # Add the last key-value pair
        if current_key is not None:
            parameters[current_key] = ' '.join(current_value)
        
        return parameters

    def parse_tags(self, tags_as_string: str) -> List[Dict[str, str]]:
        """Parse tags string into a list of Key-Value dictionaries
        
        Example input: '"atlantis"="pipeline" "Stage"="test"'
        Returns: [{'Key': 'atlantis', 'Value': 'pipeline'}, {'Key': 'Stage', 'Value': 'test'}]
        """
        if not tags_as_string:
            return []
        
        tags_list = []
        current_key = None
        current_value = []
        
        # Split the string while preserving quoted strings
        tokens = shlex.split(tags_as_string)
        
        for token in tokens:
            if '=' in token:
                # If we have a previous key-value pair, add it to tags_list
                if current_key is not None:
                    tags_list.append({
                        'Key': current_key,
                        'Value': ' '.join(current_value)
                    })
                    current_value = []
                
                # Start new key-value pair
                key, value = token.split('=', 1)
                current_key = key.strip('"')
                current_value = [value.strip('"')]
            else:
                # Continuation of previous value
                if current_key is not None:
                    current_value.append(token.strip('"'))
        
        # Add the last key-value pair
        if current_key is not None:
            tags_list.append({
                'Key': current_key,
                'Value': ' '.join(current_value)
            })
        
        return tags_list


    def stringify_parameter_overrides(self, parameter_overrides_as_dict: Dict) -> str:
        """Convert parameter overrides from dictionary to string"""

        parameter_overrides_as_string = " ".join([
            f'"{key}"="{value}"' for key, value in parameter_overrides_as_dict.items()
        ])
        
        return parameter_overrides_as_string

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

        self.template_file = str(template_path)
        logging.info(f"Using template file: '{self.template_file}'")

        if template_path.startswith('s3://'):
            # Handle S3 template
            pass
        else:
            # Handle local template
            template_path = self.templates_dir / template_path
            
            try:

                # Read the file content
                with open(template_path, "rb") as f:

                    # get SHA256 hash of template file
                    sha256_hash = hashlib.sha256()
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                    full_hash = sha256_hash.hexdigest()
                    self.template_hash = full_hash
                    self.template_hash_id = full_hash[-6:]

                    # get version from template file
                    f.seek(0)
                    for line in f:
                        line = line.decode('utf-8')  # Decode each line to process as text
                        if line.startswith('# Version:'):
                            self.template_version = line.split(':', 1)[1].strip()
                            break

                    # let user know what template is being used
                    print()
                    click.echo(formatted_output_with_value("Using template file:", template_path))
                    click.echo(formatted_output_with_value("Template version:", self.template_version))
                    click.echo(formatted_output_with_value("Template hash:", full_hash))
                    click.echo(formatted_output_with_value("Template hash ID:", self.template_hash_id))
                    print()

                    # Go back to start of file to process contents
                    f.seek(0)

                    # Look for the Parameters section
                    parameters_section = ""
                    in_parameters = False
                    
                    for line in f:
                        line = line.decode('utf-8')  # Decode each line to process as text
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

    def deep_update(self, original: Dict, update: Dict) -> Dict:
        """
        Recursively update a dictionary with another dictionary's values.
        Lists are replaced entirely rather than merged.
        """
        for key, value in update.items():
            if key in original and isinstance(original[key], dict) and isinstance(value, dict):
                self.deep_update(original[key], value)
            elif key in original and isinstance(original[key], list) and isinstance(value, list):
                original[key] = self.merge_tags(original[key], value)
            else:
                original[key] = value

        return original

    def load_defaults(self) -> Dict:
        """Load and merge configuration files in sequence
        
        Order:
        1. defaults.json
        2. {prefix}-defaults.json
        3. {prefix}-{project_id}-defaults.json
        4. {infra_type}/defaults.json
        5. {infra_type}/{prefix}-defaults.json
        6. {infra_type}/{prefix}-{project_id}-defaults.json
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
        config_files.append(self.settings_dir / f"{self.infra_type}" / "defaults.json")
        config_files.append(self.settings_dir / f"{self.infra_type}" / f"{self.prefix}-defaults.json")
        
        # Add project_id specific files in infra_type directory
        if self.project_id:
            config_files.append(
                self.settings_dir / f"{self.infra_type}" / f"{self.prefix}-{self.project_id}-defaults.json"
            )
        
        # Load each config file in sequence if it exists
        for config_file in config_files:
            try:
                if config_file.exists():
                    with open(config_file) as f:
                        # Deep update defaults with new values
                        new_config = json.load(f)
                        self.deep_update(defaults, new_config)
                        logging.info(f"Loaded config from '{config_file}'")
            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON from {config_file}: {e}")
            except Exception as e:
                logging.error(f"Error loading config file {config_file}: {e}")
        return defaults

    def prompt_for_parameters(self, parameters: Dict, defaults: Dict) -> Dict:
        """Prompt user for parameter values"""

        print()
        click.echo(formatted_divider())
        click.echo(formatted_output_bold("Template Parameter Overrides:"))
        print()
        
        values = {}
        
        # Add prefix, project_id and stage_id to defaults if they exist
        if self.prefix:
            if 'Prefix' in parameters:
                defaults['Prefix'] = self.prefix
            if 'PrefixUpper' in parameters:
                defaults['PrefixUpper'] = self.prefix.upper()

        if self.project_id and 'ProjectId' in parameters:
            defaults['ProjectId'] = self.project_id
        
        if self.stage_id and self.stage_id != 'default' and 'StageId' in parameters:
            defaults['StageId'] = self.stage_id

        for param_name, param_def in parameters.items():

            # Skip PrefixUpper as it will be handled automatically
            if param_name == 'PrefixUpper':
                continue

            default_value = defaults.get(param_name, param_def.get('Default', ''))

            while True:

                value = formatted_prompt(
                    param_name,
                    default_value,
                    str
                )
                
                if value == '?':
                    click.echo(formatted_info(f"{param_def.get('Description', 'No description available')}"))
                    continue
                elif value == '^':
                    raise click.Abort()
                elif value == '-':
                    value = ''
                
                # Validate and store parameter
                if self.validate_parameter(value, param_def):
                    values[param_name] = value

                    # If we just got a Prefix value, automatically set PrefixUpper and update self.prefix
                    if param_name == 'Prefix':
                        self.prefix = value
                        if 'PrefixUpper' in parameters:
                            values['PrefixUpper'] = value.upper()
                    
                    # Update project_id and stage_id if they were just set
                    if param_name == 'ProjectId':
                        self.project_id = value

                    if param_name == 'StageId':
                        self.stage_id = value

                        # stage_id impacts the defaults of the 
                        # DeployEnvironment, RepositoryBranch/CodeCommitBranch
                        if 'DeployEnvironment' in parameters:
                            # if value starts with t then 'TEST', d then 'DEV', otherwise 'PROD'
                            envValue = 'PROD'
                            if value.startswith('t'):
                                envValue = 'TEST'
                            elif value.startswith('d'):
                                envValue = 'DEV'
                            
                            parameters['DeployEnvironment']['Default'] = envValue

                        if 'RepositoryBranch' in parameters:
                            # if value is prod, then set RepositoryBranch
                            # to 'main' otherwise set to value
                            if value == 'prod':
                                parameters['RepositoryBranch']['Default'] = 'main'
                            else:
                                parameters['RepositoryBranch']['Default'] = value  

                        # CodeCommitBranch will be replaced by RepositoryBranch
                        if 'CodeCommitBranch' in parameters:
                            # if value is prod, then set CodeCommitBranch 
                            # to 'main' otherwise set to value
                            if value == 'prod':
                                parameters['CodeCommitBranch']['Default'] = 'main'
                            else:
                                parameters['CodeCommitBranch']['Default'] = value                      

                    break
                else:
                    click.echo(formatted_error(f"Invalid value for {param_name}"))

                    
        return values

    def select_template(self, templates: List[str]) -> str:
        """Display numbered list of templates and let user select by number"""
        if not templates:
            logging.error("No templates found")
            sys.exit(1)
        
        # Sort templates for consistent ordering
        templates.sort()
        
        # Display numbered list
        click.echo(formatted_question("Available templates:"))
        for idx, template in enumerate(templates, 1):
            click.echo(formatted_option(f"{idx}. {template}"))
        
        print()

        while True:
            try:
                default = ''
                # if only one template, make it the default
                if len(templates) == 1:
                    default = 1

                choice = formatted_prompt("Enter template number", default, str)
                # Check if input is a number
                template_idx = int(choice) - 1
                
                # Validate the index is within range
                if 0 <= template_idx < len(templates):
                    return templates[template_idx]
                else:
                    click.echo(formatted_error(f"Please enter a number between 1 and {len(templates)}"))
            except ValueError:
                click.echo(formatted_error("Please enter a valid number"))
            except KeyboardInterrupt:
                click.echo(formatted_info("Template selection cancelled"))
                sys.exit(1)

    def gather_global_parameters(self, infra_type: str, global_defaults: Dict) -> Dict:
        """Gather global deployment parameters"""

        print()
        click.echo(formatted_divider())
        click.echo(formatted_output_bold("Global Deployment Parameters:"))
        print()

        global_params = {}
        
        # Get S3 bucket for deployments
        global_params['s3_bucket'] = formatted_prompt(
            "S3 bucket for deployments",
            global_defaults.get('s3_bucket', os.getenv('SAM_DEPLOY_BUCKET', '')),
            str
        )

        # Get AWS region
        global_params['region'] = formatted_prompt(
            "AWS region",
            global_defaults.get('region', os.getenv('AWS_REGION', 'us-east-1')),
            str
        )

        # Confirm changeset prompt
        global_params['confirm_changeset'] = formatted_prompt(
            "Confirm changeset before deploy",
            'true' if global_defaults.get('confirm_changeset', True) else 'false',
            str
        )

        # Get role ARN if this is a pipeline deployment
        if infra_type == 'pipeline':
            global_params['role_arn'] = formatted_prompt(
                "IAM role ARN for deployments",
                global_defaults.get('role_arn', os.getenv('SAM_DEPLOY_ROLE', '')),
                str
            )
        
        return global_params

    def build_config(self, infra_type: str, template_file: str, global_defaults: Dict, parameter_values: Dict, tag_defaults: List, local_config: Dict) -> Dict:
        """Build the complete config dictionary"""
        # Get global parameters
        global_params = self.gather_global_parameters(infra_type, global_defaults)

        prefix = parameter_values.get('Prefix', '')
        project_id = parameter_values.get('ProjectId', '')
        if parameter_values.get('StageId', '') != '':
            stage_id = parameter_values.get('StageId', '')
        else:
            stage_id = self.stage_id

        # Generate stack name
        stack_name = self.generate_stack_name(prefix, project_id, stage_id)

        # Generate automated tags
        tags = self.generate_tags(parameter_values, tag_defaults)

        deployment_parameters = {
            'stack_name': stack_name,
            's3_prefix': stack_name,
            'parameter_overrides': parameter_values,
            'tags': tags
        }

        # if self.prefix or self.project_id is not equal to sys arg 2 and 3 
        # then deployments = {} else set to local_config deployments
        # Because that means we made a copy and are creating a fresh copy 
        # with only global and current stage
        if not isinstance(local_config, dict) or prefix != sys.argv[2] or (project_id and project_id != sys.argv[3]):
            deployments = {}
        else:
            deployments = local_config.get('deployments', {})

        deployments[stage_id] = {
            'deploy': {
                'parameters': deployment_parameters
            }
        }

        # if template_file is not s3 it is local and use the local path
        if not template_file.startswith('s3://'):
            template_file = f'./templates/{template_file}'

        # Build the config structure
        config = {
            'global': {
                'deploy': {
                    'parameters': {
                        'template_file': template_file,
                        's3_bucket': global_params['s3_bucket'],
                        'region': global_params['region'],
                        'capabilities': 'CAPABILITY_NAMED_IAM',
                        'confirm_changeset': (global_params['confirm_changeset'].lower() == 'true')
                    }
                }
            },
            'deployments': deployments
        }
        
        # Add role_arn if this is a pipeline deployment
        if infra_type == 'pipeline':
            config['global']['deploy']['parameters']['role_arn'] = global_params['role_arn']
        
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

    def generate_automated_tags(self, parameters: Dict) -> List[Dict]:
        """Generate automated tags for the deployment"""
        tags = [
            {
                "Key": "Atlantis",
                "Value": f"{self.infra_type}-infrastructure"
            },
            {
                "Key": "atlantis:Prefix",
                "Value": parameters.get('Prefix')
            },
            {
                "Key": "Provisioner",
                "Value": "CloudFormation"
            },
            {
                "Key": "DeployedUsing",
                "Value": "AWS SAM CLI"
            },
            {
                "Key": "atlantis:TemplateVersion",
                "Value": f"{self.template_version} {self.template_hash_id}"              
            },
            {
                "Key": "atlantis:TemplateFile",
                "Value": self.template_file
            }
        ]

        # Add ProjectId if defined
        if parameters.get('ProjectId'):
            tags.append({
                "Key": "atlantis:Application",
                "Value": f"{parameters['Prefix']}-{parameters['ProjectId']}"
            })
            tags.append({
                "Key": "Name",
                "Value": f"{parameters['Prefix']}-{parameters['ProjectId']}"
            })

        # Add StageId if defined
        if parameters.get('StageId'):
            tags.append({
                "Key": "atlantis:ApplicationDeploymentId",
                "Value": f"{parameters['Prefix']}-{parameters['ProjectId']}-{parameters['StageId']}"
            })
            tags.append({
                "Key": "Stage",
                "Value": parameters['StageId']
            })

        # Add Environment if defined
        if parameters.get('DeployEnvironment'):
            tags.append({
                "Key": "Environment",
                "Value": parameters['DeployEnvironment']
            })

        # Add AlarmNotificationEmail if defined
        if parameters.get('AlarmNotificationEmail'):
            tags.append({
                "Key": "AlarmNotificationEmail",
                "Value": parameters['AlarmNotificationEmail']
            })

        # Add CodeCommitRepository if defined
        if parameters.get('Repository'):
            tags.append({
                "Key": "CodeCommitRepository",
                "Value": parameters['CodeCommitRepository']
            })

        # Add CodeCommitBranch if defined
        if parameters.get('RepositoryBranch'):
            tags.append({
                "Key": "CodeCommitBranch",
                "Value": parameters['CodeCommitBranch']
            })

        return tags

    def generate_tags(self, parameters: Dict, custom_tags: List[Dict]) -> List[Dict]:
        """Generate tags for the deployment"""
        # Generate automated tags
        automated_tags = self.generate_automated_tags(parameters)

        return self.merge_tags(automated_tags, custom_tags)
    
    def merge_tags(self, original_tags: List[Dict], new_tags: List[Dict]) -> List[Dict]:
        """
        Merge automated and custom tags with custom tags taking precedence unless the tag
        key starts with 'atlantis:' or 'Atlantis'
        """
        # Convert automated tags to a dictionary for easier lookup
        tag_dict = {
            tag['Key']: tag['Value'] 
            for tag in original_tags
        }
        
        # Process custom tags
        for new_tag in new_tags:
            key = new_tag['Key']
            # Only allow new tags to override if they don't start with atlantis: or Atlantis
            if key in tag_dict and not (key.startswith('atlantis:') or key.startswith('Atlantis')):
                tag_dict[key] = new_tag['Value']
            elif key not in tag_dict:  # Add new custom tags
                tag_dict[key] = new_tag['Value']
        
        # Convert back to list of dictionaries
        return [{'Key': k, 'Value': v} for k, v in tag_dict.items()]
    
    def stringify_tags(self, tags: List[Dict]) -> str:
        """Convert tags to a string"""
        return ' '.join([f'"{tag['Key']}"="{tag['Value']}"' for tag in tags])
    
    def save_config(self, config: Dict) -> None:
        """Save configuration to samconfig.toml file"""

        try:
            # Get the parameter values from the config
            parameter_values = config.get('deployments', {}).get(self.stage_id, {}).get('deploy', {}).get('parameters', {}).get('parameter_overrides', {})
            
            prefix = parameter_values.get('Prefix', '')
            project_id = parameter_values.get('ProjectId', '')

            pystr = f"{sys.argv[0]} {self.infra_type} {prefix}"
            if project_id:
                pystr += f" {project_id}"


            header_pystr = f"{pystr}"
            if self.stage_id != 'default':
                header_pystr += f" {self.stage_id}"
            # Create the header with version and comments
            header = (
                'version = 0.1\n\n'
                '# !!! DO NOT EDIT THIS FILE !!!\n\n'
                '# Make changes and re-generate this file by running the python script:\n\n'
                f'# python {header_pystr}\n\n'
                '# Using the script provides consistent parameter overrides and tags '
                'and ensures your changes are not overwritten!\n\n'
            )

            global_section = {
                'global': config.get('global', {})
            }

            non_global_sections = {}
            # Reorder the deployments to place default first, then those starting with t, b, s, and finally p
            for stage_id in sorted(config.get('deployments', {}), key=lambda x: (x[0] != 'd', x[0] != 't', x[0] != 'b', x[0] != 's', x[0] != 'p')):
                non_global_sections[stage_id] = config['deployments'][stage_id]
                        
            # Write the config to samconfig.toml
            samconfig_path = self.generate_samconfig_path(prefix, project_id)
            
            with open(samconfig_path, 'w') as f:
                f.write(header)
                toml.dump(global_section, f)

                fnstr = prefix
                if project_id:
                    fnstr += f"-{project_id}"
                    
                for section, section_config in non_global_sections.items():

                    section_pystr = f"{pystr}"
                    if section != 'default':
                        section_pystr += f" {section}"

                    deploy_section_header = (
                        '# =====================================================\n'
                        f'# {section} Deployment Configuration\n\n'
                        '# Deploy command:\n'
                        f'# sam deploy --config-env {section} --config-file samconfig-{fnstr}-{self.infra_type}.toml --profile default\n\n'
                        '# Do not update this file!\n'
                        '# To update parameter_overrides or tags for this deployment, use the generate script:\n'
                        f'# python {section_pystr}\n'
                    )

                    # Convert parameter_values dict to parameter_overrides string
                    p_overrides = section_config.get('deploy', {}).get('parameters', {}).get('parameter_overrides', '')
                    if isinstance(p_overrides, dict):
                        parameter_overrides = self.stringify_parameter_overrides(p_overrides)
                        
                        # Update the config with the string version
                        section_config['deploy']['parameters']['parameter_overrides'] = parameter_overrides

                    tags = section_config.get('deploy', {}).get('parameters', {}).get('tags', '')
                    if isinstance(tags, list):
                        # Update the config with the string version
                        section_config['deploy']['parameters']['tags'] = self.stringify_tags(tags)
                    
                    f.write(f'\n{deploy_section_header}\n')
                    toml.dump({section: section_config}, f)
                
            logging.info(f"Configuration saved to '{samconfig_path}'")
            
            print()
            click.echo(formatted_output_with_value("Configuration saved to", samconfig_path))
            click.echo(formatted_output_bold("Open file for 'sam deploy' commands"))
            click.echo(formatted_output_bold(f"You must be in the {self.infra_type}-infrastructure directory to run the command"))
            click.echo(formatted_output(f"cd ../{self.infra_type}-infrastructure"))
            print()
            
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            sys.exit(1)

# =============================================================================
# ----- Helper functions ------------------------------------------------------
# =============================================================================

# Prompt colors may be changable at a later date
COLOR_PROMPT = 'cyan'
COLOR_OPTION = 'magenta'
COLOR_OUTPUT = 'green'
COLOR_OUTPUT_VALUE = 'yellow'
COLOR_ERROR = 'red'
COLOR_WARNING = 'yellow'
COLOR_INFO = 'blue'

# This function was written by GitHub Copilot :)
# GitHub Copilot also assisted in all coloring of output and prompts
def formatted_prompt(prompt_text: str, default_value: str, value_type: type = str, show_default: bool = False):
    """Format prompts so that they are consistent"""
    formatted_text = ''
    
    if default_value != '':
        formatted_text = click.style(f"{prompt_text} [", fg=COLOR_PROMPT, bold=True) + \
                         click.style(f"{default_value}", fg=COLOR_OPTION) + \
                         click.style("]", fg=COLOR_PROMPT, bold=True)
    else:
        formatted_text = click.style(f"{prompt_text}", fg=COLOR_PROMPT, bold=True)

    return click.prompt(formatted_text, type=value_type, default=default_value, show_default=show_default)

def formatted_question(question_text: str):
    """Format questions so that they are consistent"""
    return click.style(f"{question_text} ", fg=COLOR_PROMPT, bold=True)

def formatted_option(option_text: str):
    """Format options so that they are consistent"""
    return click.style(f"{option_text} ", fg=COLOR_OPTION)

def formatted_output_with_value(response_text: str, response_value: str):
    """Format responses so that they are consistent"""
    return click.style(f"{response_text.strip()} ", fg=COLOR_OUTPUT, bold=True) + \
           click.style(f"{response_value}", fg=COLOR_OUTPUT_VALUE)

def formatted_output_bold(response_text: str):
    """Format responses so that they are consistent"""
    return click.style(f"{response_text} ", fg=COLOR_OUTPUT, bold=True)

def formatted_output(response_text: str):
    """Format responses so that they are consistent"""
    return click.style(f"{response_text} ", fg=COLOR_OUTPUT)

def formatted_error(response_text: str):
    """Format responses so that they are consistent"""
    return click.style(f"{response_text} ", fg=COLOR_ERROR, bold=True)

def formatted_warning(response_text: str):
    """Format responses so that they are consistent"""
    return click.style(f"{response_text} ", fg=COLOR_WARNING, bold=True)

def formatted_info(response_text: str):
    """Format responses so that they are consistent"""
    return click.style(f"{response_text} ", fg=COLOR_INFO)

def formatted_divider(char: str = '-'):
    """Format dividers so that they are consistent"""
    return click.style(f"{char * 80}", fg=COLOR_OUTPUT, bold=True)

# =============================================================================
# ----- Main function ---------------------------------------------------------
# =============================================================================

VALID_INFRA_TYPES = ['service-role', 'pipeline', 'storage', 'network']

@click.command()
@click.option('--check-stack', is_flag=True, help='Check existing stack configuration')
@click.option('--profile', help='AWS profile name')
@click.argument('infra_type')
@click.argument('prefix')
@click.argument('project_id', required=False)
@click.argument('stage_id', required=False)
def main(check_stack: bool, profile: str, infra_type: str, prefix: str, 
        project_id: Optional[str], stage_id: Optional[str]):
    
    # log script arguments
    logging.info(f"{sys.argv}")

    if profile:
        boto3.setup_default_session(profile_name=profile)
    
    # Validate infra_type
    if infra_type not in VALID_INFRA_TYPES:
        raise click.UsageError(f"Invalid infra_type. Must be one of {VALID_INFRA_TYPES}")

    # Validate project_id requirement
    if infra_type != 'service-role' and not project_id:
        raise click.UsageError("project_id is required for non-service-role infrastructure types")
    
    # Validate stage_id requirement
    if infra_type != 'service-role' and infra_type != 'storage' and not stage_id:
        raise click.UsageError(f"stage_id is required for infrastructure type: {infra_type}")
    
    stage_id = stage_id if stage_id else 'default'

    print()
    click.echo(formatted_divider("="))
    click.echo(formatted_output_bold(f"Configuration Generator ({VERSION})"))
    click.echo(formatted_output_with_value("Infra Type:", infra_type))
    click.echo(formatted_divider("="))
    print()
        
    config_manager = ConfigManager(infra_type, prefix, project_id, stage_id)
    
    # Read existing configuration
    local_config = config_manager.read_samconfig()
    
    if check_stack:

        stack_name = config_manager.generate_stack_name(config_manager.prefix, config_manager.project_id, config_manager.stage_id)
        stack_config = config_manager.get_stack_config(stack_name)
        
        if stack_config and local_config:
            differences = config_manager.compare_configurations(local_config, stack_config)
            if differences:
                click.echo(formatted_warning("Differences found between local and deployed configuration:"))
                click.echo(formatted_warning(json.dumps(differences, indent=2)))
                
                choice = formatted_prompt("Choose configuration to use (local/deployed/cancel)", "", click.Choice(['local', 'deployed', 'cancel']))
                
                if choice == 'cancel':
                    raise click.Abort()
                elif choice == 'deployed':
                    local_config = stack_config

    # Handle template selection and parameter configuration
    if not local_config:
        templates = config_manager.discover_templates()
        template_file = config_manager.select_template(templates)
    else:
        template_file_from_config = local_config.get('global', {}).get('deploy', {}).get('parameters', {}).get('template_file', '')
        # if template file starts with s3://, use it as is, else parse
        if template_file_from_config and template_file_from_config.startswith('s3://'):
            template_file = template_file_from_config
        else:
            # Split by / and get the last part
            template_file = template_file_from_config.split('/')[-1]

    parameters = config_manager.get_template_parameters(template_file)
    defaults = config_manager.load_defaults()

    print()
    click.echo(formatted_divider("-"))
    click.echo(formatted_output_bold("[Enter] to accept default"))
    click.echo(formatted_output_bold("[-] to ignore default and leave blank"))
    click.echo(formatted_output_bold("[?] to see description"))
    click.echo(formatted_output_bold("[^] to cancel and exit"))

    global_defaults = defaults.get('global', {})
    if local_config:
        global_defaults.update(local_config.get('global', {}).get('deploy', {}).get('parameters', {}))

    parameter_defaults = defaults.get('parameter_overrides', {})
    if local_config:
        parameter_defaults.update(local_config.get('deployments', {}).get(config_manager.stage_id, {}).get('deploy', {}).get('parameters', {}).get('parameter_overrides', {}))

    tag_defaults = defaults.get('tags', [])
    if local_config:
        tag_defaults = config_manager.merge_tags(tag_defaults, local_config.get('deployments', {}).get(config_manager.stage_id, {}).get('deploy', {}).get('parameters', {}).get('tags', []))

    # Prompt for parameters
    parameter_values = config_manager.prompt_for_parameters(parameters, parameter_defaults)
    
    # Build the complete config
    config = config_manager.build_config(infra_type, template_file, global_defaults, parameter_values, tag_defaults, local_config)
    
    print()
    click.echo(formatted_divider())

    # Save the config
    config_manager.save_config(config)

    click.echo(formatted_divider("="))
    print()


if __name__ == '__main__':
    main()
