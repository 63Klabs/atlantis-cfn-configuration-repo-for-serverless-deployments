#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-28"
# Created by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

# Usage Information:
# config.py -h

# Full Documentation:
# https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/

import toml
import json
import yaml
import re
import sys
import os
import shlex
import click
import hashlib
import argparse
import traceback
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from botocore.exceptions import ClientError

from lib.aws_session import AWSSessionManager, TokenRetrievalError
from lib.logger import ScriptLogger, Log, ConsoleAndLog
from lib.tools import Colorize
from lib.atlantis import FileNameListUtils, DefaultsLoader, TagUtils, Utils

if sys.version_info[0] < 3:
    sys.stderr.write("Error: Python 3 is required\n")
    sys.exit(1)

# Initialize logger for this script
ScriptLogger.setup('config')

TEMPLATES_DIR = "local-templates"
SAMCONFIG_DIR = "samconfigs"
SETTINGS_DIR = "defaults"
VALID_INFRA_TYPES = ['service-role', 'pipeline', 'storage', 'network']

class ConfigManager:
    """
    Manages AWS CloudFormation/SAM deployment configurations.

    This class handles the creation and management of AWS infrastructure deployments,
    including stack naming conventions, configuration file management, and parameter processing.

    Attributes:
        infra_type (str): Type of infrastructure (e.g., 'service-role', 'pipeline', 'network')
        prefix (str): The prefix to use for stack names and resources
        project_id (str): Identifier for the project
        stage_id (str): Deployment stage identifier (default: 'default')
        profile (str): AWS credential profile name
        check_stack (bool): Check saved config against deployed stack
        aws_session (AWSSessionManager): AWS Session Manager
        s3_client: AWS S3 Boto Client
        cfn_client: AWS CloudFormation Boto Client
        template_version (str): Version of the template being used
        template_hash (str): Hash of the template content
        template_hash_id (str): Identifier based on template hash
        template_file (str): Name of the template file being used
    """
    def __init__(self, infra_type: str, prefix: str, project_id: str, stage_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None, check_stack: Optional[bool] = False, no_browser: Optional[bool] = False):
        """
        Initialize a new ConfigManager instance.

        Args:
            infra_type (str): Type of infrastructure to deploy
            prefix (str): Prefix for stack names and resources
            project_id (str): Project identifier
            stage_id (Optional[str]): Stage identifier (default: None)
            profile (Optional[str]): AWS credential profile (default: None)
            region (Optional[str]): AWS region
            check_stack (Optional[bool]): Check saved config against deployed stack (default: False)

        Raises:
            UsageError: If required arguments are missing or invalid
        """

        # Initialize basic attributes
        self.infra_type = infra_type
        self.prefix = prefix
        self.project_id = project_id
        self.stage_id = 'default' if (stage_id is None) else stage_id
        self.profile = profile
        self.region = region
        self.check_stack = check_stack

        # Check the arguments before moving on
        self._validate_args()

        # Set up AWS session and clients
        self.aws_session = AWSSessionManager(profile, region, no_browser)
        self.s3_client = self.aws_session.get_client('s3', region)
        self.cfn_client = self.aws_session.get_client('cloudformation', region)

        # Initialize template-related attributes
        self.template_version = 'No version found'
        self.template_hash: Optional[str] = None
        self.template_hash_id: Optional[str] = None
        self.template_file: Optional[str] = None

        config_loader = DefaultsLoader(
            settings_dir=self.get_settings_dir(),
            prefix=self.prefix,
            project_id=self.project_id,
            infra_type=self.infra_type
        )

        self.settings = config_loader.load_settings()
        self.defaults = config_loader.load_defaults()

    def _validate_args(self) -> None:
        """Validate arguments"""

        # Validate infra_type
        if self.infra_type not in VALID_INFRA_TYPES:
            raise click.UsageError(f"Invalid infra_type. Must be one of {VALID_INFRA_TYPES}")
        
        # infra_type service-role requires a project id equal to one of VALID_INFRA_TYPES (except 'service-role')
        # create temp variable to store VALID_INFRA_TYPES without 'service-role'
        temp_valid_infra_types = VALID_INFRA_TYPES.copy()
        temp_valid_infra_types.remove('service-role')
        if self.infra_type == 'service-role' and self.project_id not in temp_valid_infra_types:
            raise click.UsageError(f"project_id must be one of {temp_valid_infra_types}")


    def prompt_for_parameters(self, parameter_groups: List, parameters: Dict, defaults: Dict) -> Dict:
        """
        Prompt user for parameter values.

        Args:
            parameter_groups (List): List of parameter groups defining the organization
                of parameters in the template
            parameters (Dict): Dictionary of parameters and their properties from
                the CloudFormation template
            defaults (Dict): Dictionary of default values for parameters

        Returns:
            Dict: Dictionary containing parameter names as keys and their user-provided
                or default values
        
        Example:
            >>> parameter_groups = [{'Label': {'default': 'Network'}, 'Parameters': ['VpcId', 'Subnets']}]
            >>> parameters = {'VpcId': {'Type': 'AWS::EC2::VPC::Id'}, 'Subnets': {'Type': 'List<AWS::EC2::Subnet::Id>'}}
            >>> defaults = {'VpcId': 'vpc-123456'}
            >>> result = prompt_for_parameters(parameter_groups, parameters, defaults)
        """

        print()
        click.echo(Colorize.divider())
        click.echo(Colorize.output_bold("Template Parameter Overrides:"))
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

        # If there are no parameter groups, then create a parameter_list that is just a list of all the parameter_name values
        if not parameter_groups:
            # loop through parameters and create a list of all the parameter_name values
            params = []
            for param in parameters.items():
                # add to params list
                params.append(param[0])
            parameter_groups = [{'Parameters': params}]

        useLineBreakBeforeLabel = False

        # Loop through each group in parameter_groups
        for group in parameter_groups:
            label = group.get('Label', {}).get('default', None)
            if label:
                if useLineBreakBeforeLabel:
                    print()
                useLineBreakBeforeLabel = True
                click.echo(Colorize.output_bold(f"{label}\n"))

            # for each parameter_name in group.Parameters, find the corresponding parameter_name and param_def in parameters
            for param_name in group['Parameters']:
                # find the corresponding parameter_name and param_def in parameters
                param_def = parameters.get(param_name, None)

            #for param_name, param_def in parameters.items():

                # Skip PrefixUpper as it will be handled automatically
                if param_name == 'PrefixUpper':
                    continue

                default_value = defaults.get(param_name, param_def.get('Default', ''))

                while True:

                    value = Colorize.prompt(
                        param_name,
                        default_value,
                        str
                    )
                    
                    if value == '?':
                        help = []

                        help.append({"header": "Description", "text": param_def.get('Description', 'No description available')})

                        allowed_pattern = param_def.get('AllowedPattern', None)
                        if allowed_pattern:
                            help.append({"header": "Allowed Pattern", "text": allowed_pattern})

                        allowed_values = param_def.get('AllowedValues', None)
                        if allowed_values:
                            help.append({"header": "Allowed Values", "text": ", ".join(allowed_values)})

                        constraint_description = param_def.get('ConstraintDescription', None)
                        if constraint_description:
                            help.append({"header": "Constraint Description", "text": constraint_description})

                        # Assemble help text from MinLength, MaxLength, MinValue, MaxValue in one line like "MinLength: x, MaxLength: x, "
                        help_text = ""
                        if 'Type' in param_def:
                            help_text += f"Type: {param_def['Type']}, "
                        if 'MinLength' in param_def:
                            help_text += f"MinLength: {param_def['MinLength']}, "
                        if 'MaxLength' in param_def:
                            help_text += f"MaxLength: {param_def['MaxLength']}, "
                        if 'MinValue' in param_def:
                            help_text += f"MinValue: {param_def['MinValue']}, "
                        if 'MaxValue' in param_def:
                            help_text += f"MaxValue: {param_def['MaxValue']}, "
                        if help_text:
                            help.append({"header": None, "text": help_text[:-2]})

                        print()
                        Colorize.box_info(help)
                        print()

                        continue
                    elif value == '^':
                        raise click.Abort()
                    elif value == '-':
                        value = ''
                    
                    # Validate and store parameter
                    validation_result = self.validate_parameter(value, param_def)
                    if validation_result.get("valid", False):
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

                            # if StageId was changed from default, then recalculate defaults for DeployEnvironment, Repository Branch
                            if self.stage_id != defaults['StageId']:
                                stage_defaults = self.calculate_stage_defaults(self.stage_id)
                                if 'DeployEnvironment' in parameters:
                                    defaults['DeployEnvironment'] = stage_defaults['DeployEnvironment']

                                if 'RepositoryBranch' in parameters:
                                    defaults['RepositoryBranch'] = stage_defaults['RepositoryBranch']

                                if 'CodeCommitBranch' in parameters:
                                    defaults['CodeCommitBranch'] = stage_defaults['CodeCommitBranch']

                        break
                    else:
                        print()
                        click.echo(Colorize.error(f"Invalid value for {param_name}"))
                        click.echo(Colorize.error(validation_result.get("reason")))
                        click.echo(Colorize.info("Enter ? for help, ^ to exit"))
                        print()

        return values
    
    def calculate_stage_defaults(self, stage_id: str = None) -> Dict:
        """Calculate defaults for DeployEnvironment and Branch based on stage_id"""
            
        defaults = {}

        # stage_id impacts the defaults of the 
        # DeployEnvironment, RepositoryBranch/CodeCommitBranch

        if stage_id is not None:

            envValue = 'PROD'
            if stage_id.startswith('t'):
                envValue = 'TEST'
            elif stage_id.startswith('d'):
                envValue = 'DEV'
            
            defaults['DeployEnvironment'] = envValue

            # if value is prod, then set RepositoryBranch
            # to 'main' otherwise set to value
            branch = stage_id
            if stage_id == 'prod':
                branch = 'main'

            defaults['CodeCommitBranch'] = branch
            defaults['RepositoryBranch'] = branch

        return defaults                  

    def gather_atlantis_deploy_parameters(self, infra_type: str, atlantis_deploy_parameter_defaults: Dict) -> Dict:
        """Gather atlantis deployment parameters with validation"""
        print()
        click.echo(Colorize.divider())
        click.echo(Colorize.output_bold("Deployment Parameters:"))
        print()

        atlantis_deploy_params = {}
        
        def display_help(param_name: str) -> None:
            """Display help text for parameters"""
            help_text = {
                's3_bucket': "S3 bucket name for storing deployment artifacts.\n"
                            "Must be 3-63 characters, lowercase, and contain only letters, numbers, or hyphens.",
                'region': "AWS region where resources will be deployed.\n"
                        "Example: us-east-1, us-west-2, eu-west-1",
                'confirm_changeset': "Whether to confirm CloudFormation changesets before deployment.\n"
                                    "Enter 'true' or 'false'",
                'role_arn': "IAM role ARN used for deployments.\n"
                        "Format: arn:aws:iam::account-id:role/role-name"
            }
            text = help_text.get(param_name, "No help available")
            # split text by \n, then add element at 0 to first List Dict with header as param_name and text[0] as text, then rest with header as None
            help = [{"header": param_name, "text": text.split('\n')[0]}]
            for line in text.split('\n')[1:]:
                help.append({"header": None, "text": line})

            print()
            Colorize.box_info(help)
            print()

        def get_validated_input(prompt, default, validator_func, error_message, param_name, required=False):
            while True:
                value = Colorize.prompt(prompt, default, str)
                
                # Handle special commands
                if value == '?':
                    display_help(param_name)
                    continue
                elif value == '-':
                    if required:
                        click.echo(Colorize.error("This field is required and cannot be cleared"))
                        click.echo(Colorize.info("Enter ? for help, ^ to exit"))
                        continue
                    return ''
                elif value == '^':
                    click.echo(Colorize.info("\nExiting script..."))
                    sys.exit(0)
                
                # Handle empty input when default exists
                if value == '' and default:
                    value = default

                # Validate input
                if validator_func(value):
                    return value
                
                print()
                click.echo(Colorize.error(f"Invalid value for {param_name}"))
                click.echo(Colorize.error(error_message))
                click.echo(Colorize.info("Enter ? for help, - to clear, ^ to exit"))
                print()

        # Validation functions
        def validate_s3_bucket(bucket):
            if not bucket:
                return False
            if not 3 <= len(bucket) <= 63:
                return False
            if not bucket.islower():
                return False
            if not all(c.isalnum() or c == '-' for c in bucket):
                return False
            if bucket.startswith('-') or bucket.endswith('-'):
                return False
            return True

        def validate_region(region):
            valid_regions = self.settings.get('regions', ['us-east-1'])
            return region in valid_regions

        def validate_role_arn(arn):
            if not arn:
                return False
            return (arn.startswith('arn:aws:iam::') and 
                    ':role/' in arn and 
                    len(arn.split(':')) == 6)

        def validate_boolean(value):
            return value.lower() in ('true', 'false')

        try:
            # Get S3 bucket with validation (required)
            atlantis_deploy_params['s3_bucket'] = get_validated_input(
                "S3 bucket for deployments",
                atlantis_deploy_parameter_defaults.get('s3_bucket', os.getenv('SAM_DEPLOY_BUCKET', '')),
                validate_s3_bucket,
                "Invalid S3 bucket name. Must be 3-63 characters, lowercase, and contain only letters, numbers, or hyphens",
                's3_bucket',
                required=True
            )

            # Get AWS region with validation (required)
            atlantis_deploy_params['region'] = get_validated_input(
                "AWS region",
                atlantis_deploy_parameter_defaults.get('region', os.getenv('AWS_REGION', 'us-east-1')),
                validate_region,
                "Invalid AWS region. Please enter a valid AWS region (e.g., us-east-1)",
                'region',
                required=True
            )

            # Confirm changeset prompt with validation
            atlantis_deploy_params['confirm_changeset'] = get_validated_input(
                "Confirm changeset before deploy",
                'true' if atlantis_deploy_parameter_defaults.get('confirm_changeset', True) else 'false',
                validate_boolean,
                "Please enter 'true' or 'false'",
                'confirm_changeset',
                required=True
            )

            # Get role ARN if this is a pipeline deployment
            if infra_type == 'pipeline':
                atlantis_deploy_params['role_arn'] = get_validated_input(
                    "IAM role ARN for deployments",
                    atlantis_deploy_parameter_defaults.get('role_arn', os.getenv('SAM_DEPLOY_ROLE', '')),
                    validate_role_arn,
                    "Invalid role ARN. Must be in format: arn:aws:iam::account-id:role/role-name",
                    'role_arn',
                    required=True
                )
            
            return atlantis_deploy_params

        except KeyboardInterrupt:
            click.echo(Colorize.info("\nOperation cancelled by user"))
            sys.exit(1)

    def validate_parameter(self, value: str, param_def: Dict) -> bool:
        """Validate parameter value against CloudFormation parameter definition
        
        Validates against:
        - AllowedPattern (regex pattern)
        - AllowedValues (list of allowed values)
        - MinLength/MaxLength (for string types)
        - MinValue/MaxValue (for numeric types)
        """

        if not value and "Default" in param_def:
            # Empty value with default defined is valid
            return {"reason": "Valid", "valid": True}
            
        param_type = param_def.get('Type', 'String')
        
        # Check AllowedValues if defined
        allowed_values = param_def.get('AllowedValues', [])
        if allowed_values and value not in allowed_values:
            return {"reason": f"Value must be one of: {', '.join(allowed_values)}", "valid": False}
        
        # Check AllowedPattern if defined
        allowed_pattern = param_def.get('AllowedPattern')
        if allowed_pattern and not re.match(allowed_pattern, value):
            return {"reason": f"Value must match pattern: {allowed_pattern}", "valid": False}
        
        # Type-specific validations
        if param_type in ['String', 'AWS::SSM::Parameter::Value<String>']:
            min_length = int(param_def.get('MinLength', 0))
            # Handle MaxLength differently - if not specified, use None instead of infinity
            max_length = param_def.get('MaxLength')
            if max_length is not None:
                max_length = int(max_length)
            
            if len(value) < min_length:
                return {"reason": f"String length must be at least {min_length}", "valid": False}
            if max_length is not None and len(value) > max_length:
                return {"reason": f"String length must be no more than {max_length}", "valid": False}
                
        elif param_type in ['Number', 'AWS::SSM::Parameter::Value<Number>']:
            try:
                num_value = float(value)
                min_value = float(param_def.get('MinValue', float('-inf')))
                max_value = float(param_def.get('MaxValue', float('inf')))
                
                if num_value < min_value:
                    return {"reason": f"Number must be at least {min_value}", "valid": False}
                if num_value > max_value:
                    return {"reason": f"Number must be no more than {max_value}", "valid": False}
                    
            except ValueError:
                return {"reason": "Value must be a number", "valid": False}
                
        elif param_type == 'CommaDelimitedList':
            # Validate each item in the comma-delimited list
            items = [item.strip() for item in value.split(',')]
            if not all(items):
                return {"reason": "CommaDelimitedList cannot contain empty items", "valid": False}
                
        elif param_type == 'List<Number>':
            try:
                items = [item.strip() for item in value.split(',')]
                # Verify each item is a valid number
                [float(item) for item in items]
            except ValueError:
                return {"reason": "All items must be valid numbers", "valid": False}
                
        elif param_type == 'AWS::EC2::KeyPair::KeyName':
            if not value:
                return {"reason": "KeyPair name cannot be empty", "valid": False}
                
        elif param_type == 'AWS::EC2::VPC::Id':
            if not value.startswith('vpc-'):
                return {"reason": "VPC ID must start with 'vpc-'", "valid": False}
                
        elif param_type == 'AWS::EC2::Subnet::Id':
            if not value.startswith('subnet-'):
                return {"reason": "Subnet ID must start with 'subnet-'", "valid": False}
                
        elif param_type == 'AWS::EC2::SecurityGroup::Id':
            if not value.startswith('sg-'):
                return {"reason": "Security Group ID must start with 'sg-'", "valid": False}
        
        return {"reason": "Valid", "valid": True}

    # -------------------------------------------------------------------------
    # - Deployed Stack Utilities
    # -------------------------------------------------------------------------

    def compare_against_stack(self, local_config: Dict) -> Dict:

        stack_name = self.get_stack_name()
        stack_config = self.get_stack_config(stack_name)
        
        if stack_config and local_config:
            differences = self.compare_configurations(local_config, stack_config)
            if differences:
                click.echo(Colorize.warning(f"Differences found between local and deployed stack configuration for {stack_name}"))
                
                choice = Colorize.prompt("Choose configuration to use", "", click.Choice(['Local', 'Deployed', 'Cancel'], False))
                
                if choice.lower() == 'cancel':
                    print()
                    click.echo(Colorize.warning("Operation cancelled by user"))
                    print()
                    sys.exit(1)
                elif choice.lower() == 'deployed':
                    local_config = stack_config
            else:
                click.echo(Colorize.output("No differences found between local and deployed configuration:"))
        elif stack_config and not local_config:
            click.echo(Colorize.warning(f"No local configuration found for {stack_name}"))
            click.echo(Colorize.warning("However, a deployed stack was found."))
            choice = Colorize.prompt("Import deployed stack?", "", click.Choice(['Yes', 'No', 'Cancel'], False))

            if choice.lower() == 'cancel':
                print()
                click.echo(Colorize.warning("Operation cancelled by user"))
                print()
                sys.exit(1)
            elif choice.lower() == 'yes':
                local_config = stack_config

        return local_config

    def compare_configurations(self, local_config: Dict, stack_config: Dict) -> bool:
        """Compare local and stack configurations in a list format with color coding"""
        
        differences = False

        def format_value(value):
            """Convert value to string, handling None/empty values"""
            return str(value) if value is not None else 'None'
        
        def print_comparison(name: str, local_val: str, stack_val: str) -> None:
            """Print a three-line comparison with color coding"""
            local_str = format_value(local_val)
            stack_str = format_value(stack_val)
            
            # Determine color based on whether values match
            color = Colorize.SUCCESS if local_str == stack_str else Colorize.ERROR
            
            click.echo(Colorize.output_bold(name))
            click.echo(click.style(f"  Local: {local_str}", fg=color))
            click.echo(click.style(f"  Stack: {stack_str}", fg=color))
            click.echo("")  # Empty line for spacing

        # Extract configurations
        local_params = local_config.get('deployments', {}).get(self.stage_id, {}).get('deploy', {}).get('parameters', {})
        local_parameter_overrides = local_params.get('parameter_overrides', {})
        local_atlantis_params = local_config.get('atlantis', {}).get('deploy', {}).get('parameters', {})
        local_tags = local_params.get('tags', [])

        stack_params = stack_config.get('deployments', {}).get(self.stage_id, {}).get('deploy', {}).get('parameters', {})
        stack_parameter_overrides = stack_params.get('parameter_overrides', {})
        stack_atlantis_params = stack_config.get('atlantis', {}).get('deploy', {}).get('parameters', {})
        stack_tags = stack_params.get('tags', [])

        # copy non-essentials over so they aren't listed as not matching
        if 'confirm_changeset' in local_atlantis_params:
            stack_atlantis_params['confirm_changeset'] = local_atlantis_params['confirm_changeset']
        if 's3_bucket' in local_atlantis_params:
            stack_atlantis_params['s3_bucket'] = local_atlantis_params['s3_bucket']

        # Convert tags to dictionaries for easier comparison
        local_tags_dict = {tag['Key']: tag['Value'] for tag in local_tags}
        stack_tags_dict = {tag['Key']: tag['Value'] for tag in stack_tags}


        # Print Parameter Overrides
        click.echo(Colorize.divider())
        click.echo(Colorize.output_bold("Parameter Overrides"))
        click.echo(Colorize.divider())
        
        all_param_keys = sorted(set(local_parameter_overrides.keys()) | set(stack_parameter_overrides.keys()))
        for key in all_param_keys:
            local_value = local_parameter_overrides.get(key)
            stack_value = stack_parameter_overrides.get(key)
            if local_value != stack_value:
                differences = True
            print_comparison(
                key,
                local_value,
                stack_value
            )

        # Print Atlantis Deploy Parameters
        click.echo(Colorize.divider())
        click.echo(Colorize.output_bold("Deploy Parameters"))
        click.echo(Colorize.divider())
        
        all_atlantis_keys = sorted(set(local_atlantis_params.keys()) | set(stack_atlantis_params.keys()))
        for key in all_atlantis_keys:
            local_value = local_atlantis_params.get(key)
            stack_value = stack_atlantis_params.get(key)
            if local_value != stack_value:
                differences = True
            print_comparison(
                key,
                local_value,
                stack_value
            )

        # Print Tags
        click.echo(Colorize.divider())
        click.echo(Colorize.output_bold("Tags"))
        click.echo(Colorize.divider())
        
        all_tag_keys = sorted(set(local_tags_dict.keys()) | set(stack_tags_dict.keys()))
        for key in all_tag_keys:
            local_value = local_tags_dict.get(key)
            stack_value = stack_tags_dict.get(key)
            if local_value != stack_value:
                differences = True
            print_comparison(
                key,
                local_value,
                stack_value
            )

        return differences

    def get_stack_config(self, stack_name: str) -> Optional[Dict]:
        """Get configuration from existing CloudFormation stack"""
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]

            parameter_overrides = {}
            tags = stack.get('Tags', [])
            atlantis_parameters = {}

            for param in stack.get('Parameters', []):
                parameter_overrides[param['ParameterKey']] = param['ParameterValue']

            print(stack['StackId'])

            atlantis_parameters['capabilities'] = ' '.join(stack.get('Capabilities', []))
            atlantis_parameters['region'] = stack['StackId'].split(':')[3]  # Extract region from stack ID

            # Get template file from tags
            for tag in stack.get('Tags', []):
                if tag['Key'] == 'atlantis:TemplateFile':
                    template_file = tag['Value']
                    # if template_file does not start with s3:// then prepend ./templates/
                    if not template_file.startswith('s3://'):
                        template_file = f"./templates/{template_file}"
                    atlantis_parameters['template_file'] = template_file

            # place into same format as local_config
            stack_info = {
                'deployments': {
                    self.stage_id: {
                        'deploy': {
                            'parameters': {
                                'parameter_overrides': parameter_overrides,
                                'tags': tags,
                            }
                        }
                    }
                },
                'atlantis': { "deploy": { "parameters": atlantis_parameters }}                
            }
                    
            return stack_info
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            Log.error(f"Error getting configuration for stack {stack_name}: {error_code} - {error_message}")
            
            if error_code == 'UnauthorizedException':
                click.echo(Colorize.error("Authentication Error"))
                click.echo(Colorize.error("Your session token is invalid or has expired"))
                click.echo(Colorize.warning("Please authenticate again with AWS and ensure you have the correct permissions"))
                click.echo(Colorize.info("You may need to run 'aws sso login' if using AWS SSO"))
            elif error_code == 'ValidationError':
                click.echo(Colorize.error(f"Stack '{stack_name}' does not exist"))
            else:
                click.echo(Colorize.error(f"Error getting configuration for stack {stack_name}"))
                click.echo(Colorize.error(f"Error: {error_code} - {error_message}"))
                click.echo(Colorize.warning(f"Ensure you are currently logged in and using the correct profile ({self.profile})"))
            
            print()
            sys.exit(1)
        except Exception as e:
            Log.error(f"Unexpected error getting configuration for stack {stack_name}: {e}")
            click.echo(Colorize.error(f"Unexpected error getting configuration for stack {stack_name}"))
            click.echo(Colorize.error(f"Error: {str(e)}"))
            click.echo(Colorize.warning("Please check your AWS configuration and try again"))
            print()
            sys.exit(1)

    # -------------------------------------------------------------------------
    # - Read in Settings and Defaults
    # -------------------------------------------------------------------------

    def check_for_default_json(self, atlantis: Dict, parameter_overrides: Dict) -> None:
        """Check if settings/defaults.json and/or <prefix>-defaults.json exists.
        If not, offer to save region to defaults.json
        If user chooses no to region, save a blank file as a sample.
        If prefix-defaults.json doesn't exist, offer to save s3_bucket (and region if not saved to defaults)"""

        defaults_path = self.get_settings_dir() / "defaults.json"
        prefix_defaults_path = self.get_settings_dir() / f"{self.prefix}-defaults.json"

        defaults_data = {}
        prefix_defaults_data = {}

        skip = {}
        
        # Create settings directory if it doesn't exist
        os.makedirs(self.get_settings_dir(), exist_ok=True)

        current_params = {
            "atlantis": atlantis.get('deploy', {}).get('parameters', {}),
            "parameter_overrides": parameter_overrides
        }

        click.echo(Colorize.divider())
        click.echo(Colorize.output_bold("Atlantis Configuration Defaults:"))
        print()

        # Read, Prompt User, and Write defaults.json
        default_file_data = self.read_defaults_file(defaults_path)
        defaults_data, skip = self.set_future_defaults(current_params, default_file_data, skip, 'ALL')
        if self.write_defaults_file(defaults_path, defaults_data):
            click.echo(Colorize.success(f"Saved default configuration to {defaults_path}"))
        else:
            click.echo(Colorize.error(f"Failed to save default configuration to {defaults_path}"))

        print()
        click.echo(Colorize.divider())
        click.echo(Colorize.output_bold(f"Prefix Defaults ({self.prefix}):"))
        print()
            
        # Read, Prompt User, and Write defaults.json
        prefix_default_file_data = self.read_defaults_file(prefix_defaults_path)
        prefix_defaults_data, skip = self.set_future_defaults(current_params, prefix_default_file_data, skip, self.prefix)
        if self.write_defaults_file(prefix_defaults_path, prefix_defaults_data):
            click.echo(Colorize.success(f"Saved prefix default configuration to {defaults_path}"))
        else:
            click.echo(Colorize.error(f"Failed to save prefix default configuration to {defaults_path}"))

        # # add in the role arn
        # role_arn = atlantis.get('deploy', {}).get('parameters', {}).get('role_arn')
        # # Prompt for role_arn if not saved in prefix-defaults.json
        # if role_arn:
        #     click.echo(Colorize.output_with_value(f"Current {self.infra_type.capitalize()} Service Role ARN:", role_arn))
        #     save_role_arn_prefix = click.confirm(
        #         Colorize.question(f"Would you like to save this {self.infra_type.capitalize()} Service Role ARN as the default for this prefix?"),
        #         default=True
        #     )
            
        #     if save_role_arn_prefix:
        #         prefix_defaults_data["atlantis"]["role_arn"] = { self.infra_type: role_arn}

    def set_future_defaults(self, current_params: Dict, default_file_data: Dict, skip: Dict, scope: Optional[str] = 'ALL') -> tuple[Dict, Dict]:
        """Set the default parameters for configurations

        Args:
            current_params (Dict): The deploy configuration
            default_file_data: (Dict): Existing data from the defaults file
            skip (Dict): A dictionary { "atlantis": [], "parameter_overrides": []}
            scope (str, optional): The scope of the configuration. Defaults to None.
        """

        if scope != 'ALL' and scope != self.prefix:
            scope = 'ALL'

        possible_defaults = [ 
            {'name': 'atlantis', 'params': ['region', 's3_bucket'] },
            {'name': 'parameter_overrides', 'params': ['RolePath', 'ServiceRolePath', 'PermissionsBoundaryArn', 'S3BucketNameOrgPrefix', 'ParameterStoreHierarchy'] }
        ]

        for section in possible_defaults:

            section_name = section['name']
            section_params = section['params']
            curr_deploy_params_for_section = current_params.get(section_name, {})

            for param in section_params:

                if section_name in skip and param in skip[section_name]:
                    continue
                param_is_not_set = True if "" == default_file_data.get(section_name, {}).get(param, "") else False

                if param in curr_deploy_params_for_section and param_is_not_set:
                    if curr_deploy_params_for_section[param]:
                        print()
                        click.echo(Colorize.output_with_value(f"Current {param}:", curr_deploy_params_for_section[param]))
                        save_param = click.confirm(
                            Colorize.question(f"Would you like to save this '{param}' value as the default choice for '{scope}' configurations?"),
                            default=True
                        )

                        if save_param:
                            if section_name not in skip:
                                skip[section_name] = []
                            skip[section_name].append(param)
                            default_file_data[section_name][param] = curr_deploy_params_for_section[param]

        return (default_file_data, skip)
        
    def read_defaults_file(self, file_path: str) -> Dict:
        """Read in a single defaults file"""
        if os.path.exists(file_path):

            # read in defaults.json
            try:
                Log.info(f"Reading {file_path}")
                with open(file_path, 'r') as f:
                    defaults_data = json.load(f)
                return defaults_data
            except Exception as e:
                click.echo(Colorize.error(f"Error reading {file_path} {str(e)}"))
                Log.error(f"Error reading {file_path}: {str(e)}")
                Log.error(f"Error occurred at:\n{traceback.format_exc()}")
                return
        else:
            Log.info(f"Defaults file does not yet exist: {file_path}")

            return {
                "atlantis": {},
                "parameter_overrides": {},
                "tags": []
            }
    
    def write_defaults_file(self, file_path: str, defaults_data: Dict) -> bool:
        """Write to a defaults file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(defaults_data, f, indent=2)
            click.echo(Colorize.output(f"Created {file_path}"))
            Log.info(f"Created {file_path}")
            return True
        except Exception as e:
            click.echo(Colorize.error(f"Error creating {file_path} {str(e)}"))
            Log.error(f"Error creating {file_path}: {str(e)}")
            Log.error(f"Error occurred at:\n{traceback.format_exc()}")
            return False
        
    # -------------------------------------------------------------------------
    # - Prompts: Tags
    # -------------------------------------------------------------------------
    
    def get_default_tags(self) -> Dict:
        """Get the default tags for the repository

        Returns:
            Dict: Default tags for the repository
        """
        try:
            default_tags = TagUtils.get_default_tags(self.settings, self.defaults)
            return default_tags
        except Exception as e:
            Log.error(f"Error getting default tags: {str(e)}")
            raise

    # -------------------------------------------------------------------------
    # - Parse, Stringify, and Process Parameter Overrides and Tags
    # -------------------------------------------------------------------------

    def generate_automated_tags(self, parameters: Dict) -> List[Dict]:
        """Generate automated tags for the deployment"""

        # If self.template_file has a version (?version=) then place the version information in template_file_version
        template_file_version = None
        if '?' in self.template_file:
            template_file_version = self.template_file.split('?')[-1]
            template_file = self.template_file.split('?')[0]
        else:
            template_file = self.template_file


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
                "Value": template_file
            },
            {
                "Key": "atlantis:TemplateFileVersion",
                "Value": template_file_version
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
            if key in tag_dict and not (TagUtils.is_atlantis_reserved_tag(key)):
                tag_dict[key] = new_tag['Value']
            elif key not in tag_dict:  # Add new custom tags
                tag_dict[key] = new_tag['Value']
        
        # Convert back to list of dictionaries
        return [{'Key': k, 'Value': v} for k, v in tag_dict.items()]
    
    def stringify_tags(self, tags: List[Dict]) -> str:
        """Convert tags to a string"""
        return ' '.join([f'"{tag['Key']}"="{tag['Value']}"' for tag in tags])
    
    def parse_parameter_overrides(self, parameter_string: str) -> Dict:
        """
        Parse parameter overrides from a string into a dictionary.

        Converts a space-separated string of key=value pairs into a dictionary.
        Handles quoted values and escaping properly.

        Args:
            parameter_string: Space-separated string of key=value pairs

        Returns:
            Dictionary of parameter names and values

        Example:
            Input: 'ParameterKey1=value1 ParameterKey2="value 2"'
            Output: {'ParameterKey1': 'value1', 'ParameterKey2': 'value 2'}
        """
 
        parameters: Dict[str, str] = {}
        
        if not parameter_string:
            return parameters

        try:
            # Split the string while preserving quoted values
            parts = shlex.split(parameter_string)
            
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    parameters[key.strip()] = value.strip()
                else:
                    Log.warning(f"Skipping invalid parameter format: {part}")
                    
        except Exception as e:
            Log.error(f"Error parsing parameter overrides: {str(e)}")
            
        return parameters

    def parse_tags(self, tag_string: str) -> List[Dict[str, str]]:
        """Convert a string of key-value tag pairs into AWS tag format.
        
        Uses shlex to properly handle quoted strings, spaces, and special characters
        in both keys and values. Supports both single and double quotes.
        
        Args:
            tag_string: A string containing space-separated key=value pairs.
                    Examples:
                    - 'atlantis="pipeline" Stage="test"'
                    - 'Name="My App Server" Environment="Prod 2.0"'
                    - 'Owner="John Doe" Cost Center="123 456"'
        
        Returns:
            List[Dict[str, str]]: List of AWS format tags.
            Example: [{'Key': 'atlantis', 'Value': 'pipeline'},
                    {'Key': 'Stage', 'Value': 'test'}]
        
        Raises:
            ValueError: If tag_string format is invalid, missing required parts,
                    or contains malformed quotes
        """
        if not tag_string:
            return []
        
        tags = []
        lexer = shlex.shlex(tag_string, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ''
        lexer.wordchars += '=.-/@'  # Allow these chars in unquoted strings
        
        try:
            # Convert iterator to list to handle pairs
            tokens = list(lexer)
            
            # Process tokens in pairs
            for i in range(0, len(tokens), 1):
                if not tokens[i]:
                    continue
                    
                # Split on first = only
                try:
                    key, value = tokens[i].split('=', 1)
                except ValueError:
                    raise ValueError(
                        f"Invalid tag format. Each tag must be in 'key=value' format: {tokens[i]}"
                    )
                
                # Remove any remaining quotes
                key = key.strip().strip('"\'')
                value = value.strip().strip('"\'')
                
                if not key or not value:
                    raise ValueError(
                        f"Empty key or value not allowed: {tokens[i]}"
                    )
                
                tags.append({
                    'Key': key,
                    'Value': value
                })
                
        except ValueError as e:
            raise ValueError(f"Error parsing tags: {str(e)}")
        except shlex.Error as e:
            raise ValueError(f"Error parsing quoted strings: {str(e)}")
            
        return tags

    def stringify_parameter_overrides(self, parameter_overrides_as_dict: Dict) -> str:
        """Convert parameter overrides from dictionary to string"""

        parameter_overrides_as_string = " ".join([
            f'"{key}"="{value}"' for key, value in parameter_overrides_as_dict.items()
        ])
        
        return parameter_overrides_as_string

    # -------------------------------------------------------------------------
    # - Read and Process Templates
    # -------------------------------------------------------------------------

    def read_template_file(self, template_path: str) -> tuple[bytes, str]:
        """
        Read template file content from either S3 or local filesystem.
        
        Args:
            template_path (str): Path to template (s3:// or local path)
            
        Returns:
            tuple: (file_content as bytes, template_source_path as string)
        
        Raises:
            Exception: If template cannot be read
        """
        try:
            if template_path.startswith('s3://'):
                # Parse S3 URL
                bucket_name = template_path.split('/')[2]
                
                # Split the key and potential version ID
                remaining_path = '/'.join(template_path.split('/')[3:])
                if '?' in remaining_path:
                    key, query_string = remaining_path.split('?', 1)
                    if query_string.startswith('versionId='):
                        version_id = query_string.replace('versionId=', '')
                        # Get object with specific version
                        response = self.s3_client.get_object(
                            Bucket=bucket_name,
                            Key=key,
                            VersionId=version_id
                        )
                else:
                    key = remaining_path
                    # Get latest version of object
                    response = self.s3_client.get_object(
                        Bucket=bucket_name,
                        Key=key
                    )
                
                content = response['Body'].read()
                return content, template_path

            else:
                # Handle local template
                template_path = self.get_templates_dir() / template_path
                with open(template_path, "rb") as f:
                    content = f.read()
                return content, str(template_path)
                
        except (Exception) as e:
            click.echo(Colorize.error(f"Error reading template file {template_path}"))
            Log.error(f"Error reading template file {template_path}: {str(e)}")
            raise
            
    def process_template_content(self, content: bytes, template_path: str) -> None:
        """
        Process template content to extract version and calculate hash.
        
        Args:
            content (bytes): Template file content
            template_path (str): Original template path for logging
        """

        try:
            # Calculate template hash
            sha256_hash = hashlib.sha256()
            sha256_hash.update(content)
            full_hash = sha256_hash.hexdigest()
            self.template_hash = full_hash
            self.template_hash_id = full_hash[-6:]
            
            # Extract version from content
            content_str = content.decode('utf-8')
            for line in content_str.splitlines():
                if line.startswith('# Version:'):
                    self.template_version = line.split(':', 1)[1].strip()
                    break
            else:
                self.template_version = 'No version found'
            
            # Log template info
            print()
            click.echo(Colorize.output_with_value("Using template file:", template_path))
            click.echo(Colorize.output_with_value("Template version:", self.template_version))
            click.echo(Colorize.output_with_value("Template hash:", full_hash))
            click.echo(Colorize.output_with_value("Template hash ID:", self.template_hash_id))
            print()
        except(Exception) as e:
            Log.error(f"Error processing template content: {str(e)}")
            click.echo(Colorize.error("Error processing template content. Check logs for more info."))
            raise

    def extract_parameter_groups(self, content: bytes) -> List:
        """
        Extract metadata section from template content and return parameter groups.

        Args:
            content (bytes): Template file content

        Returns:
            Dict: Parameter Groups from metadata section from template
        """
        try:
            content_str = content.decode('utf-8')
            metadata_section = ""
            in_metadata = False

            for line in content_str.splitlines():
                if line.startswith('Metadata:'):
                    in_metadata = True
                    metadata_section = line
                elif in_metadata:
                    # Check if we've moved to a new top-level section
                    if line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                        break
                    metadata_section += '\n' + line

            # Parse just the Metadata section
            if metadata_section:
                yaml_content = yaml.safe_load(metadata_section)
                metadata_section = yaml_content.get('Metadata', {})
                parameter_groups = metadata_section.get('AWS::CloudFormation::Interface', {}).get('ParameterGroups', [])
                return parameter_groups
            return []

        except Exception as e:
            Log.error(f"Error parsing metadata section: {str(e)}")
            click.echo(Colorize.error("Error parsing metadata section. Check logs for more info."))
            return []

    def extract_parameters(self, content: bytes) -> Dict:
        """
        Extract parameters section from template content.
        
        Args:
            content (bytes): Template file content
            
        Returns:
            Dict: Parameters section from template
        """
        try:
            content_str = content.decode('utf-8')
            parameters_section = ""
            in_parameters = False
            
            for line in content_str.splitlines():
                if line.startswith('Parameters:'):
                    in_parameters = True
                    parameters_section = line
                elif in_parameters:
                    # Check if we've moved to a new top-level section
                    if line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                        break
                    parameters_section += '\n' + line
            
            # Parse just the Parameters section
            if parameters_section:
                yaml_content = yaml.safe_load(parameters_section)
                return yaml_content.get('Parameters', {})
            return {}
            
        except Exception as e:
            Log.error(f"Error parsing parameters section: {str(e)}")
            click.echo(Colorize.error("Error parsing parameters section. Check logs for more info."))
            return {}

    def get_template_parameters(self, template_path: str) -> Tuple[List, Dict]:
        """
        Get parameters from CloudFormation template.
        
        Args:
            template_path (str): Path to template (s3:// or local path)
                
        Returns:
            Tuple[List, Dict]: A tuple containing:
                - List: Parameter Groups
                - Dict: Template parameters
        """

        self.template_file = str(template_path)
        Log.info(f"Using template file: '{self.template_file}'")

        try:
            # Read template content
            content, actual_path = self.read_template_file(template_path)
            
            # Process template metadata (version, hash etc)
            self.process_template_content(content, actual_path)

            # Extract metadata if present
            parameter_groups = self.extract_parameter_groups(content)
            
            # Extract and return parameters
            parameters = self.extract_parameters(content)
            
            return (parameter_groups, parameters)
            
        except Exception as e:
            Log.error(f"Error processing template file {template_path}: {str(e)}")
            click.echo(Colorize.error("Error processing template file. Check logs for more info."))
            return ([],{})


    # -------------------------------------------------------------------------
    # - Read and Process samconfig
    # -------------------------------------------------------------------------

    def read_samconfig(self) -> Optional[Dict]:
        """
        Read and parse a SAM configuration file.

        Loads the appropriate samconfig.toml file based on the current configuration
        and parses its contents into a structured dictionary. Handles both atlantis
        configuration and deployment parameters.

        Returns:
            Optional[Dict]: Dictionary containing parsed configuration data with structure:
                          {
                              'atlantis': {configuration settings},
                              'deployments': {
                                  'stage_name': {
                                      'deploy': {
                                          'parameters': {
                                              'parameter_overrides': {...},
                                              'tags': {...}
                                          }
                                      }
                                  }
                              }
                          }
                          Returns None if file doesn't exist or on error

        Raises:
            Logs errors but doesn't raise exceptions
        """
        samconfig_path = self.get_samconfig_file_path()
        
        if samconfig_path.exists():
            try:
                print()
                # samconfig_path relative to script
                samconfig_path_relative = samconfig_path.relative_to(os.getcwd())
                click.echo(Colorize.output_with_value("Using samconfig file:", samconfig_path_relative))
                Log.info(f"Using samconfig file: {samconfig_path}")
                print()

                samconfig_data = {'atlantis': {}, 'deployments': {}}
                samconfig = toml.load(samconfig_path)
                
                # Handle atlantis deploy parameters section
                if 'atlantis' in samconfig and isinstance(samconfig['atlantis'], dict):
                    samconfig_data['atlantis'] = samconfig['atlantis']

                # Handle deployment sections
                for key, value in samconfig.items():
                    if key != 'atlantis' and isinstance(value, dict):
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
                            Log.warning(f"Skipping invalid deployment section '{key}': {str(e)}")
                            continue

                return samconfig_data
            except Exception as e:
                Log.error(f"Error reading samconfig file {samconfig_path}: {str(e)}")
                click.echo(Colorize.error("Error reading samconfig file. Check logs for more info."))
                return None
        return None

    def build_config(self, infra_type: str, template_file: str, atlantis_deploy_parameter_defaults: Dict, parameter_values: Dict, tag_defaults: List, local_config: Dict) -> Dict:
        """Build the complete config dictionary"""
        # Get atlantis deploy parameters used for all deployments of this application
        atlantis_deploy_params = self.gather_atlantis_deploy_parameters(infra_type, atlantis_deploy_parameter_defaults)

        prefix = parameter_values.get('Prefix', '')
        project_id = parameter_values.get('ProjectId', '')
        if parameter_values.get('StageId', '') != '':
            stage_id = parameter_values.get('StageId', '')
        else:
            stage_id = self.stage_id

        # if self.prefix or self.project_id is not equal to sys arg 2 and 3 
        # then deployments = {} else set to local_config deployments
        # Because that means we made a copy and are creating a fresh copy 
        # with only atlantis and current deploy environment
        if not isinstance(local_config, dict) or prefix != sys.argv[2] or (project_id and project_id != sys.argv[3]):
            deployments = {}
        else:
            deployments = local_config.get('deployments', {})

        # if template_file is not s3 it is local and use the local path
        if not template_file.startswith('s3://'):
            # Make template_file_path relative to samconfig_file
            file_path = f'{self.get_templates_dir()}/{template_file}'
            template_file = os.path.relpath(file_path, self.get_samconfig_dir())

        # Generate stack name
        stack_name = self.get_stack_name()

        # Generate automated tags
        tags = self.generate_tags(parameter_values, tag_defaults)

        atlantis_default_deploy_parameters = {
            'template_file': template_file,
            's3_bucket': atlantis_deploy_params['s3_bucket'],
            'region': atlantis_deploy_params['region'],
            'capabilities': 'CAPABILITY_NAMED_IAM',
            'confirm_changeset': (atlantis_deploy_params['confirm_changeset'].lower() == 'true')
        }

        # If deployments has more than one key then inform the user that multiple deployments were detected, 
        # would they like to update the atlantis deployment parameters across all?
        if len(deployments) > 1:
            print()
            # Multiple deploy environments detected. Do you want to apply the atlantis deploy parameters to ALL deployments? This will NOT update parameter_overrides or tags for those deployments.
            click.echo(Colorize.output_with_value("Multiple deploy environments detected for ", f"{prefix}-{project_id}"))
            click.echo(Colorize.question(f"Do you want to apply the Deploy Parameters to ALL deployments?"))
            click.echo(Colorize.info(f"(This will NOT update Template Parameter Overrides or Tags for those deployments.)"))
            click.echo(Colorize.option("Yes or No"))
            print()
            choice = ""
            # prompt until choice is either y or n
            while choice.upper() not in ['Y', 'N', 'YES', 'NO']:
                choice = Colorize.prompt("Apply Deploy Parameters to All?", "Yes", str)
                if choice.upper() not in ['Y', 'N', 'YES', 'NO']:
                    click.echo(Colorize.error("Please enter 'Yes' or 'No'"))
            print()
            if choice.upper() in ['Y', 'YES']:
                click.echo(Colorize.output_bold(f"Updating Deploy Parameters across all deployments of {prefix}-{project_id}..."))
                for deployment in deployments:
                    deployments[deployment]['deploy']['parameters'].update(atlantis_default_deploy_parameters)
            else:
                click.echo(Colorize.output_bold(f"Updating Deploy Parameters only for {stage_id}..."))
                # We do this below so we'll skip doing it here

        # We will now apply the deploy parameters to the deployment
        # We already applied the atlantis_default_deploy_parameters above but now
        # we focus on just the current stage
        deployment_parameters = atlantis_default_deploy_parameters.copy()
        deployment_parameters.update({
            'stack_name': stack_name,
            's3_prefix': stack_name,
            'parameter_overrides': parameter_values,
            'tags': tags
        })

        deployments[stage_id] = {
            'deploy': {
                'parameters': deployment_parameters
            }
        }

        # Build the config structure
        config = {
            'atlantis': {
                'deploy': {
                    'parameters': atlantis_default_deploy_parameters
                }
            },
            'deployments': deployments
        }
        
        # Add role_arn if this is a pipeline deployment
        if infra_type == 'pipeline':
            config['atlantis']['deploy']['parameters']['role_arn'] = atlantis_deploy_params['role_arn']
        
        return config

    def get_sam_deploy_command(self, stage_id: str) -> str:
        ### Get sam deploy command ###
        return f"sam deploy --config-env {stage_id} --config-file {self.get_samconfig_file_name()} --profile {self.profile}"
    
    def get_script_deploy_command(self, stage_id: str) -> str:
        ### Get the script deploy command ###
        return f"./scripts/deploy.py {self.infra_type} {self.prefix} {self.project_id} {stage_id} --profile {self.profile}"


    def save_config(self, config: Dict) -> None:
        """Save configuration to samconfig.toml file"""

        try:
            # Get the parameter values from the config
            parameter_values = config.get('deployments', {}).get(self.stage_id, {}).get('deploy', {}).get('parameters', {}).get('parameter_overrides', {})
            
            prefix = parameter_values.get('Prefix', self.prefix)
            project_id = parameter_values.get('ProjectId', self.project_id)

            pystr = f"{sys.argv[0]} {self.infra_type} {prefix} {project_id}"

            header_pystr = f"{pystr}"
            if self.stage_id != 'default':
                header_pystr += " <StageId>"
            if self.profile != 'default' and self.profile != None:
                header_pystr += f" --profile {self.profile}"
            # Create the header with version and comments
            header = (
                'version = 0.1\n\n'
                '# !!! DO NOT EDIT THIS FILE !!!\n\n'
                '# Make changes and re-generate this file by running the python script:\n\n'
                f'# python3 {header_pystr}\n\n'
                '# Using the script provides consistent parameter overrides and tags '
                'and ensures your changes are not overwritten!\n\n'
            )

            atlantis_deploy_section = {
                'atlantis': config.get('atlantis', {})
            }

            non_atlantis_deploy_sections = {}
            # Reorder the deployments to place default first, then those starting with t, b, s, and finally p
            for stage_id in sorted(config.get('deployments', {}), key=lambda x: (x[0] != 'd', x[0] != 't', x[0] != 'b', x[0] != 's', x[0] != 'p')):
                non_atlantis_deploy_sections[stage_id] = config['deployments'][stage_id]
                        
            # Write the config to samconfig.toml
            samconfig_path = self.get_samconfig_file_path()

            # Create the samconfig directory if it doesn't exist
            os.makedirs(os.path.dirname(samconfig_path), exist_ok=True)
            
            with open(samconfig_path, 'w') as f:
                f.write(header)
                toml.dump(atlantis_deploy_section, f)
                    
                for section, section_config in non_atlantis_deploy_sections.items():

                    section_pystr = f"{pystr}"
                    if section != 'default':
                        section_pystr += f" {section}"

                    section_deploy_command = ""
                    if self.template_file.startswith('s3://'):
                        section_deploy_command += "# Since template is in S3 you MUST use the python deploy script:\n"
                        section_deploy_command += f"# {self.get_script_deploy_command(section)}"
                    else:
                        section_deploy_command += f"# {self.get_sam_deploy_command(section)}\n# -- OR --\n"
                        section_deploy_command += f"# {self.get_script_deploy_command(section)}\n"
                    
                    deploy_section_header = (
                        '# =====================================================\n'
                        f'# {section} Deployment Configuration\n\n'
                        '# Deploy command:\n'
                        f'{section_deploy_command}\n\n'
                        '# Do not update this file!\n'
                        '# To update parameter_overrides or tags for this deployment, use the generate script:\n'
                        f'# python3 {section_pystr}\n'
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
                
            Log.info(f"Configuration saved to '{samconfig_path}'")

            # samconfig_path relative to script
            samconfig_path_relative = samconfig_path.relative_to(os.getcwd())
            # get only the directory path from samconfig_path
            saved_dir = os.path.dirname(samconfig_path_relative)
            
            print()
            click.echo(Colorize.output_with_value("Configuration saved to", samconfig_path_relative))
            click.echo(Colorize.output_bold("Deploy commands are saved in the samconfig file for later reference."))

            # If self.template_file is s3 then display ./scripts/deploy.py message
            if self.template_file.startswith('s3://'):
                click.echo(Colorize.output_bold("Since the template is in S3, 'sam deploy' will NOT work."))
                click.echo(Colorize.output_bold("Use ./scripts/deploy.py instead"))
            else:
                click.echo(Colorize.output_bold(f"You must be in the {saved_dir} directory to run the 'sam deploy' command:"))
                click.echo(Colorize.output(f"cd {saved_dir}"))
                click.echo(Colorize.output(self.get_sam_deploy_command(self.stage_id)))
                click.echo(Colorize.output_bold("Otherwise, you can run the ./scripts/deploy.py script from here:"))
            
            click.echo(Colorize.output(self.get_script_deploy_command(self.stage_id)))
            print()

            # Check if default.json and prefix.json exists
            self.check_for_default_json(atlantis_deploy_section.get('atlantis', {}), parameter_values)
            
        except Exception as e:
            Log.error(f"Error saving configuration: {str(e)}")
            Log.error(f"Error occurred at:\n{traceback.format_exc()}")
            click.echo(Colorize.error(f"Error saving configuration. Check logs for more info."))
            sys.exit(1)

    # -------------------------------------------------------------------------
    # - Prompt for stage_id
    # -------------------------------------------------------------------------

    def prompt_for_stage_id(self, local_config: Dict) -> str:
        """
        Prompts user to select an existing stage or create a new one.

        Args:
            local_config (Dict): Configuration dictionary containing deployment stages.
                Expected structure: {'deployments': {'stage1': {...}, 'stage2': {...}}}

        Returns:
            str: Selected or newly created stage ID. Examples: 'test', 'beta', 'prod'

        Notes:
            - If stages exist, presents numbered list for selection
            - If no selection made, prompts for new stage name
            - Suggests logical next stage based on existing stages:
                * If 'test' exists, suggests 'beta'
                * If 'beta' exists, suggests 'prod'
            - Empty stage names are not allowed

        Example:
            >>> config = {'deployments': {'test': {}, 'beta': {}}}
            >>> stage = prompt_for_stage_id(config)
            Select a stage to edit or copy
            0. New
            1. test
            2. beta
            Enter stage number: 0
            Enter a name for the new stage [prod]: production
            >>> print(stage)
            'production'
        """
        stage_id = None

        # if deployments exists in local_config, then get the key of its children
        if local_config:
            deployments = local_config.get('deployments', {})
            # get the keys
            stages = list(deployments.keys())

            # Prompt the user to choose a stage from stages. If the user chooses 0 they should be prompted to enter a name for the stage. The user cannot proceed until a stage is selected

            heading_text = "Select a stage to edit or copy"
            prompt_text = "Enter stage number"
            allow_none = True
            options = stages

            stage_id = Utils.make_selection_from_list(options, allow_none, heading_text=heading_text, prompt_text=prompt_text)

            if stage_id is None:
                next_logical_stage = ''
                # determine the next logical stage
                if 'test' in stages:
                    next_logical_stage = 'beta'
                    if 'beta' in stages:
                        next_logical_stage = 'prod'
                # Prompt the user to enter a name for the stage and it cannot be empty
                while True:
                    stage_id = Colorize.prompt("Enter a name for the new stage", next_logical_stage, str)
                    if stage_id:
                        break
                    else:
                        click.echo(Colorize.error("Stage name cannot be empty"))
        self.stage_id = stage_id
        return stage_id
 
    # -------------------------------------------------------------------------
    # - Template Selection
    # -------------------------------------------------------------------------

    def discover_templates(self) -> List[str]:
        """Discover available templates from local and s3"""
        templates = self.discover_local_templates()
        templates.extend(self.discover_s3_templates())
        return templates
        
    def discover_local_templates(self) -> List[str]:
        """Discover available templates in the infrastructure type directory"""
        Log.info(f"Discovering templates from local directory: {self.get_templates_dir()}")
        return [f.name for f in self.get_templates_dir().glob('*.yml')]

    def discover_s3_templates(self) -> List[str]:
        """Discover available templates in the infrastructure type directory"""
        templates = []
        # loop through self.settings.get('templates', []), access the bucket, and append to templates
        for s3_template_location in self.settings.get('templates', []):
            try:
                bucket = s3_template_location['bucket']
                prefix = s3_template_location['prefix'].strip('/')
                Log.info(f"Discovering templates from s3://{bucket}/{prefix}/{self.infra_type}")
                response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}/{self.infra_type}")
                for obj in response.get('Contents', []):
                    if obj['Key'].endswith('.yml') or obj['Key'].endswith('.yaml'):
                        Log.info(f"Found template: {obj}")
                        s3_uri = f"s3://{bucket}/{obj['Key']}"
                        templates.append(s3_uri)
            except Exception as e:
                Log.error(f"Error discovering templates from S3: {str(e)}")
                click.echo(Colorize.error("Error discovering templates from S3. Check logs for more info."))
                raise

        return templates

    def _parse_s3_uri(self, s3_uri: str) -> tuple[str, str, str]:
        """Parse an S3 URI into bucket, key, and version ID components
        
        Args:
            s3_uri (str): S3 URI in format s3://bucket/key or s3://bucket/key?versionId=xyz
            
        Returns:
            tuple: (bucket, key, version_id)
            
        Example:
            >>> _parse_s3_uri("s3://my-bucket/path/to/file.txt?versionId=abc123")
            ('my-bucket', 'path/to/file.txt', 'abc123')
            >>> _parse_s3_uri("s3://my-bucket/path/to/file.txt")
            ('my-bucket', 'path/to/file.txt', '')
        """
        # Remove s3:// prefix
        if not s3_uri.startswith('s3://'):
            raise ValueError(f"Invalid S3 URI format: {s3_uri}")
        
        # Split into path and query parts
        path_part = s3_uri[5:]  # Remove 's3://'
        if '?' in path_part:
            path_part, query_part = path_part.split('?', 1)
        else:
            query_part = ''
        
        # Get bucket and key
        parts = path_part.split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URI format: {s3_uri}")
        
        bucket = parts[0]
        key = parts[1]
        
        # Extract version ID if present
        version_id = ''
        if query_part.startswith('versionId='):
            version_id = query_part[10:]  # Remove 'versionId='
            
        return bucket, key, version_id

    def get_latest_version_id(self, s3_uri: str) -> str:
        """Get the latest version ID for an S3 object and return full URI with version
        
        Args:
            s3_uri (str): S3 URI of the object
                
        Returns:
            str: S3 URI with latest version ID appended if versioning enabled
        """
        try:
            bucket, key, _ = self._parse_s3_uri(s3_uri)
            
            # Get the latest version ID
            version_id = self.s3_client.head_object(Bucket=bucket, Key=key).get('VersionId', '')
            
            if version_id:
                return f"{s3_uri}?versionId={version_id}"
            
            return s3_uri
            
        except Exception as e:
            Log.warning(f"Failed to get version ID for {s3_uri}: {str(e)}")
            return s3_uri

    def check_for_template_update(self, s3_uri: str) -> str:
        """Check if the template has been updated in S3 and prompt for update

        Args:
            s3_uri (str): S3 URI of the template

        Returns:
            str: Updated S3 URI if updated, otherwise original S3 URI
        """
        try:
            bucket, key, current_version_id = self._parse_s3_uri(s3_uri)
            
            Log.info(f"Checking for template update: s3://{bucket}/{key}")

            try:
                # Get the latest version ID
                latest_version_id = self.s3_client.head_object(Bucket=bucket, Key=key).get('VersionId', '')
            except self.s3_client.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    Log.warning(f"Template not found at s3://{bucket}/{key}")
                    return s3_uri
                raise

            Log.info(f"Latest version ID: {latest_version_id}")

            # Check if the template has been updated
            if latest_version_id and latest_version_id != current_version_id:
                Log.info("Newer version of template available")
                # Prompt for update
                if click.confirm(Colorize.warning("A newer version of the template is available. Update?")):
                    return f"s3://{bucket}/{key}?versionId={latest_version_id}"
                
            return s3_uri
            
        except Exception as e:
            Log.warning(f"Failed to check for template update: {str(e)}")
            return s3_uri

    # -------------------------------------------------------------------------
    # - Naming and File Locations
    # -------------------------------------------------------------------------

    def get_stack_name(self) -> str:
        """
        Generate a standardized CloudFormation stack name.

        Combines prefix, project_id, stage_id, and infra_type to create a consistent
        stack naming convention. If no parameters are provided, uses instance values.

        Returns:
            str: Generated stack name following the pattern:
                 {prefix}-{project_id}-{stage_id}-{infra_type}
                 Note: stage_id is optional in the pattern
        """

        # We capitalize the prefix of service-roles as they are special and can be used to provide permissions
        prefix = self.prefix.upper() if self.infra_type == 'service-role' else self.prefix

        stack_name = f"{prefix}-"

        if self.project_id:
            stack_name += f"{self.project_id}-"
        
        if  self.stage_id and self.stage_id != 'default':
            stack_name += f"{self.stage_id}-"

        stack_name += f"{self.infra_type}"

        return stack_name
    
    def get_samconfig_dir(self) -> Path:
        """Get the samconfig directory path"""
        # Get the script's directory in a cross-platform way
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent / SAMCONFIG_DIR / self.prefix / self.project_id 
    
    def get_samconfig_file_name(self) -> str:
        """Get the samconfig file name"""
        return f"samconfig-{self.prefix}-{self.project_id}-{self.infra_type}.toml"
    
    def get_samconfig_file_path(self) -> Path:
        """Get the samconfig file path"""
        return self.get_samconfig_dir() / self.get_samconfig_file_name()

    def get_settings_dir(self) -> Path:
        """Get the settings directory path"""
        # Get the script's directory in a cross-platform way
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent / SETTINGS_DIR
        
    def get_templates_dir(self) -> Path:
        """Get the settings directory path"""
        # Get the script's directory in a cross-platform way
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent / TEMPLATES_DIR / self.infra_type

    # -------------------------------------------------------------------------
    # - Internal Utilities
    # -------------------------------------------------------------------------

    # none
        
# =============================================================================
# ----- Main function ---------------------------------------------------------
# =============================================================================

EPILOG = """
Supports both AWS SSO and IAM credentials.
For SSO users, credentials will be refreshed automatically.
For IAM users, please ensure your credentials are valid using 'aws configure'.

For default parameter and tag values, add default.json files to the defaults directory.
For settings, update settings.json in the defaults directory.

Examples:

    # Basic
    config.py <infra_type> <prefix> <project_id> [<stage_id>] 
    
    # Use specific AWS profile
    config.py <infra_type> <prefix> <project_id> [<stage_id>] --profile <yourprofile>
        
    # Check saved configuration against deployed stack
    config.py <infra_type> <prefix> <project_id> [<stage_id>] --profile <yourprofile> --check-stack    

    # Optional flags:
    --check-stack
        Compare a deployed stack against current sam configuration file 
    --no-browser
        For an AWS SSO login session, whether or not to set the --no-browser flag.        
"""

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description='Create, Update, and Manage AWS samconfig for stack deployments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(EPILOG)
    )

    # Positional arguments
    parser.add_argument('infra_type',
                        type=str,
                        choices=VALID_INFRA_TYPES,
                        help="Type of infrastructure (e.g., 'storage', 'pipeline', 'network')")
    parser.add_argument('prefix',
                        type=str,
                        help='The prefix to use for stack names and resources')
    parser.add_argument('project_id',
                        type=str,
                        help='Identifier for the project')
    parser.add_argument('stage_id',
                        type=str,
                        nargs='?',  # Makes it optional
                        default=None,
                        help="Deployment stage identifier (e.g. 'test', 'beta', 'stage', 'prod')")
    
    # Optional Named Arguments
    parser.add_argument('--profile',
                        required=False,
                        default=None,
                        help='AWS credential profile name')
    parser.add_argument('--region',
                        required=False,
                        default=None,
                        help='AWS region (e.g. us-east-1)')
    
    # Optional Flags
    parser.add_argument('--check-stack',
                        action='store_true',  # This makes it a flag
                        default=False,        # Default value when flag is not used
                        help='Compare saved configuration against deployed stack.')
    parser.add_argument('--no-browser',
                        action='store_true',  # This makes it a flag
                        default=False,        # Default value when flag is not used
                        help='For an AWS SSO login session, whether or not to set the --no-browser flag.')
    
    args = parser.parse_args()
        
    return args

def main():
    
    try:
        args = parse_args()
        Log.info(f"{sys.argv}")
        Log.info(f"Version: {VERSION}")
        
        print()
        click.echo(Colorize.divider("="))
        click.echo(Colorize.output_bold(f"Configuration Manager ({VERSION})"))
        click.echo(Colorize.output_with_value("Infra Type:", args.infra_type))
        click.echo(Colorize.divider("="))
        print()
            
    
        try:
            config_manager = ConfigManager(
                args.infra_type, args.prefix, 
                args.project_id, args.stage_id, 
                args.profile, args.region, 
                args.check_stack, args.no_browser
            )

        except TokenRetrievalError as e:
            ConsoleAndLog.error(f"AWS authentication error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            ConsoleAndLog.error(f"Error initializing configuration manager: {str(e)}")
            sys.exit(1)

        # Read existing configuration
        local_config = config_manager.read_samconfig()

        # if no stage_id is provided for a pipeline or network, prompt for one
        if not args.stage_id and args.infra_type in ['pipeline', 'network']:
            args.stage_id = config_manager.prompt_for_stage_id(local_config)
        
        # Compare against deployed stack
        if args.check_stack:
            local_config = config_manager.compare_against_stack(local_config)

        # Handle template selection and parameter configuration
        if not local_config:
            # get local templates and then add in the s3 templates before passing to the select UI
            templates = config_manager.discover_templates()
            template_file = FileNameListUtils.select_from_file_list(templates, heading_text="Available templates", prompt_text="Enter a template number")
            if template_file.startswith('s3://'):
                template_file = config_manager.get_latest_version_id(template_file)
        else:
            template_file_from_config = local_config.get('atlantis', {}).get('deploy', {}).get('parameters', {}).get('template_file', '')
            # if template file starts with s3://, use it as is, else parse
            if template_file_from_config and template_file_from_config.startswith('s3://'):
                template_file = config_manager.check_for_template_update(template_file_from_config)
            else:
                # Split by / and get the last part
                template_file = template_file_from_config.split('/')[-1]

        parameter_groups, parameters = config_manager.get_template_parameters(template_file)
        defaults = config_manager.defaults

        print()

        click.echo(Colorize.divider("-", fg=Colorize.INFO))
        click.echo(Colorize.info("Enter to accept default, ? for help, - to clear, ^ to exit "))

        atlantis_deploy_parameter_defaults = defaults.get('atlantis', {})
        if local_config:
            atlantis_deploy_parameter_defaults.update(local_config.get('atlantis', {}).get('deploy', {}).get('parameters', {}))

        parameter_defaults = config_manager.calculate_stage_defaults(config_manager.stage_id)
        parameter_defaults.update(defaults.get('parameter_overrides', {}))
        if local_config:
            parameter_defaults.update(local_config.get('deployments', {}).get(config_manager.stage_id, {}).get('deploy', {}).get('parameters', {}).get('parameter_overrides', {}))

        tag_defaults = defaults.get('tags', [])
        if local_config:
            tag_defaults = config_manager.merge_tags(tag_defaults, local_config.get('deployments', {}).get(config_manager.stage_id, {}).get('deploy', {}).get('parameters', {}).get('tags', []))

        # Prompt for parameters
        parameter_values = config_manager.prompt_for_parameters(parameter_groups, parameters, parameter_defaults)
        
        # prompt for tags
        try:
            tag_defaults = config_manager.merge_tags(TagUtils.tags_as_list(config_manager.get_default_tags()), tag_defaults)
            tag_defaults = TagUtils.tags_as_list(TagUtils.prompt_for_tags(TagUtils.tags_as_dict(tag_defaults)))
        except KeyboardInterrupt:
            ConsoleAndLog.info("Config creation cancelled")
            sys.exit(1)
        except Exception as e:
            ConsoleAndLog.error(f"Error setting tags: {str(e)}")
            sys.exit(1)

        # Build the complete config
        config = config_manager.build_config(args.infra_type, template_file, atlantis_deploy_parameter_defaults, parameter_values, tag_defaults, local_config)
        
        print()
        click.echo(Colorize.divider())

        # Save the config
        config_manager.save_config(config)

        click.echo(Colorize.divider("="))
        print()

    except Exception as e:
        ConsoleAndLog.error(f"Unexpected error: {str(e)}")
        ConsoleAndLog.error(f"Error occurred at:\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main()
