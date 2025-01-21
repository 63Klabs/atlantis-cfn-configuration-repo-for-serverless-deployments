"""
AWS Infrastructure Configuration Management Tool

This module provides a command-line interface for managing AWS CloudFormation/SAM 
deployments across different infrastructure types (pipeline, network, service-role).
It handles configuration management, stack naming conventions, and deployment parameters.

Usage Examples:
    Create/Update a pipeline:
        python config.py pipeline acme widget-ws test

    Import/Check existing stack:
        python config.py network acme widget-ws test --check-stack true --profile devuser

Dependencies:
    - boto3: AWS SDK for Python
    - toml: TOML file parser
    - click: Command-line interface creation kit
    
Environment Setup:
    Install required packages:
        pip install boto3 toml click
        or
        apt install python3-boto3 python3-toml python3-click

Version: 1.0.0
"""

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
from typing import Dict, Optional, List, Any, Union
from botocore.exceptions import ClientError

# Add lib directory to Python path for custom modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts/lib'))

import tools

# Initialize logging configuration
if not os.path.exists('scripts/logs'):
    os.makedirs('scripts/logs')
    
logging.basicConfig(
    level=logging.INFO,
    filename='scripts/logs/script-config.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ConfigManager:
    """
    Manages AWS CloudFormation/SAM deployment configurations.

    This class handles the creation and management of AWS infrastructure deployments,
    including stack naming conventions, configuration file management, and parameter 
    processing. It supports multiple infrastructure types and deployment stages.

    Attributes:
        prefix (str): The prefix to use for stack names and resources
        infra_type (str): Type of infrastructure (e.g., 'service-role', 'pipeline', 'network')
        project_id (str): Identifier for the project
        stage_id (str): Deployment stage identifier (default: 'default')
        profile (str): AWS credential profile name
        templates_dir (Path): Directory containing CloudFormation/SAM templates
        samconfig_dir (Path): Directory containing SAM configuration files
        settings_dir (Path): Directory containing additional settings
        template_version (str): Version of the template being used
        template_hash (str): Hash of the template content
        template_hash_id (str): Identifier based on template hash
        template_file (str): Name of the template file being used
        cfn_client: Boto3 CloudFormation client
    """

    def __init__(self, infra_type: str, prefix: str, project_id: str, 
                 stage_id: Optional[str] = None, *, profile: Optional[str] = None) -> None:
        """
        Initialize a new ConfigManager instance.

        Args:
            infra_type: Type of infrastructure to deploy
            prefix: Prefix for stack names and resources
            project_id: Project identifier
            stage_id: Stage identifier (default: None)
            profile: AWS credential profile (default: None)

        Raises:
            ValueError: If project_id is None for non-service-role infrastructure types
        """
        # Initialize basic attributes
        self.prefix = prefix
        self.infra_type = infra_type
        self.project_id = project_id
        self.stage_id = 'default' if stage_id is None else stage_id
        self.profile = 'default' if profile is None else profile

        # Set up AWS client and paths
        self.cfn_client = boto3.client('cloudformation')
        self.templates_dir = Path('infrastructure') / f"{infra_type}/templates"
        self.samconfig_dir = Path('infrastructure') / f"{infra_type}"
        self.settings_dir = Path("scripts") / "settings"

        # Initialize template-related attributes
        self.template_version = 'No version found'
        self.template_hash: Optional[str] = None
        self.template_hash_id: Optional[str] = None
        self.template_file: Optional[str] = None

        # Validate inputs
        if infra_type != 'service-role' and project_id is None:
            raise ValueError("project_id is required for non-service-role infrastructure types")
        
        # Set up AWS session with specified profile
        boto3.setup_default_session(profile_name=self.profile)

    def generate_stack_name(self, prefix: str = "", 
                          project_id: str = "", 
                          stage_id: str = "") -> str:
        """
        Generate a standardized CloudFormation stack name.

        Creates a stack name following the pattern:
        {prefix}-{project_id}-{stage_id}-{infra_type}

        Args:
            prefix: Resource prefix (default: instance prefix)
            project_id: Project identifier (default: instance project_id)
            stage_id: Stage identifier (default: instance stage_id)

        Returns:
            Formatted stack name string
        """
        # Use instance values if no parameters provided
        prefix = prefix or self.prefix
        project_id = project_id or self.project_id
        stage_id = stage_id or self.stage_id

        # Build stack name
        stack_name_parts = [prefix]
        if project_id:
            stack_name_parts.append(project_id)
        if stage_id and stage_id != 'default':
            stack_name_parts.append(stage_id)
        stack_name_parts.append(self.infra_type)

        return "-".join(stack_name_parts)
    
    def generate_samconfig_path(self, prefix: str, project_id: str) -> Path:
        """
        Generate the path for the SAM configuration file.

        Args:
            prefix: Resource prefix
            project_id: Project identifier

        Returns:
            Path object pointing to the SAM configuration file
        """
        # Handle service-role differently (no project_id in filename)
        if self.infra_type == 'service-role':
            filename = f"samconfig-{prefix}-service-role.toml"
        else:
            filename = f"samconfig-{prefix}-{project_id}-{self.infra_type}.toml"
        
        return self.samconfig_dir / filename
    
    def read_samconfig(self) -> Optional[Dict[str, Any]]:
        """
        Read and parse a SAM configuration file.

        Returns:
            Dictionary containing parsed configuration data or None if file doesn't exist
            Structure:
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
        """
        samconfig_path = self.generate_samconfig_path(self.prefix, self.project_id)
        
        if samconfig_path.exists():
            try:
                # Display configuration file being used
                print()
                click.echo(tools.formatted_output_with_value(
                    "Using samconfig file:", samconfig_path))
                print()

                # Initialize configuration structure
                samconfig_data = {'atlantis': {}, 'deployments': {}}
                samconfig = toml.load(samconfig_path)
                
                # Process atlantis section
                if 'atlantis' in samconfig and isinstance(samconfig['atlantis'], dict):
                    samconfig_data['atlantis'] = samconfig['atlantis']

                # Process deployment sections
                for key, value in samconfig.items():
                    if key != 'atlantis' and isinstance(value, dict):
                        try:
                            deploy_params = value.get('deploy', {}).get('parameters', {})
                            if isinstance(deploy_params, dict):
                                # Process parameter overrides
                                parameter_overrides = deploy_params.get(
                                    'parameter_overrides', '')
                                if parameter_overrides and isinstance(
                                    parameter_overrides, str):
                                    value['deploy']['parameters'][
                                        'parameter_overrides'] = self.parse_parameter_overrides(
                                            parameter_overrides)
                                
                                # Process tags
                                tags = deploy_params.get('tags', '')
                                if tags and isinstance(tags, str):
                                    value['deploy']['parameters']['tags'] = self.parse_tags(
                                        tags)

                                samconfig_data['deployments'][key] = value
                        except Exception as e:
                            logging.error(f"Error processing deployment section {key}: {str(e)}")
                
                return samconfig_data
            except Exception as e:
                logging.error(f"Error reading samconfig file {samconfig_path}: {str(e)}")
                return None
        else:
            logging.warning(f"Samconfig file not found: {samconfig_path}")
            return None

    def parse_parameter_overrides(self, parameter_string: str) -> Dict[str, str]:
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
                    logging.warning(f"Skipping invalid parameter format: {part}")
                    
        except Exception as e:
            logging.error(f"Error parsing parameter overrides: {str(e)}")
            
        return parameters

    def parse_tags(self, tags_string: str) -> Dict[str, str]:
        """
        Parse tags from a string into a dictionary.

        Converts a space-separated string of key=value pairs into a dictionary of tags.
        Handles quoted values and escaping properly.

        Args:
            tags_string: Space-separated string of key=value pairs

        Returns:
            Dictionary of tag names and values

        Example:
            Input: 'TagKey1=value1 TagKey2="value 2"'
            Output: {'TagKey1': 'value1', 'TagKey2': 'value 2'}
        """
        tags: Dict[str, str] = {}
        
        if not tags_string:
            return tags

        try:
            # Split the string while preserving quoted values
            parts = shlex.split(tags_string)
            
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    tags[key.strip()] = value.strip()
                else:
                    logging.warning(f"Skipping invalid tag format: {part}")
                    
        except Exception as e:
            logging.error(f"Error parsing tags: {str(e)}")
            
        return tags

    def get_template_file(self) -> Optional[str]:
        """
        Locate and validate the CloudFormation/SAM template file.

        Searches for template files in the templates directory with supported extensions
        (.yaml, .yml, .json). Updates template-related attributes if found.

        Returns:
            str: Path to the template file if found, None otherwise

        Side Effects:
            Updates self.template_file, self.template_hash, and self.template_hash_id
        """
        template_extensions = ['.yaml', '.yml', '.json']
        
        try:
            for ext in template_extensions:
                template_path = self.templates_dir / f"template{ext}"
                if template_path.exists():
                    # Calculate template hash for versioning
                    with open(template_path, 'rb') as f:
                        content = f.read()
                        self.template_hash = hashlib.sha256(content).hexdigest()
                        self.template_hash_id = self.template_hash[:8]
                    
                    self.template_file = str(template_path)
                    return self.template_file
                    
            logging.error(f"No template file found in {self.templates_dir}")
            return None
            
        except Exception as e:
            logging.error(f"Error accessing template file: {str(e)}")
            return None

    def get_stack_outputs(self, stack_name: str) -> Dict[str, str]:
        """
        Retrieve outputs from an existing CloudFormation stack.

        Args:
            stack_name: Name of the CloudFormation stack

        Returns:
            Dictionary of stack outputs (output_key: output_value)

        Raises:
            ClientError: If stack doesn't exist or other AWS API errors occur
        """
        outputs: Dict[str, str] = {}
        
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            
            if 'Stacks' in response and len(response['Stacks']) > 0:
                stack_outputs = response['Stacks'][0].get('Outputs', [])
                
                for output in stack_outputs:
                    key = output.get('OutputKey', '')
                    value = output.get('OutputValue', '')
                    if key and value:
                        outputs[key] = value
                        
        except ClientError as e:
            if 'does not exist' in str(e):
                logging.warning(f"Stack {stack_name} does not exist")
            else:
                logging.error(f"Error getting stack outputs: {str(e)}")
                
        return outputs

    def get_stack_parameters(self, stack_name: str) -> Dict[str, str]:
        """
        Retrieve parameters from an existing CloudFormation stack.

        Args:
            stack_name: Name of the CloudFormation stack

        Returns:
            Dictionary of stack parameters (parameter_key: parameter_value)

        Raises:
            ClientError: If stack doesn't exist or other AWS API errors occur
        """
        parameters: Dict[str, str] = {}
        
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            
            if 'Stacks' in response and len(response['Stacks']) > 0:
                stack_parameters = response['Stacks'][0].get('Parameters', [])
                
                for param in stack_parameters:
                    key = param.get('ParameterKey', '')
                    value = param.get('ParameterValue', '')
                    if key and value:
                        parameters[key] = value
                        
        except ClientError as e:
            if 'does not exist' in str(e):
                logging.warning(f"Stack {stack_name} does not exist")
            else:
                logging.error(f"Error getting stack parameters: {str(e)}")
                
        return parameters

    def get_stack_tags(self, stack_name: str) -> Dict[str, str]:
        """
        Retrieve tags from an existing CloudFormation stack.

        Args:
            stack_name: Name of the CloudFormation stack

        Returns:
            Dictionary of stack tags (tag_key: tag_value)

        Raises:
            ClientError: If stack doesn't exist or other AWS API errors occur
        """
        tags: Dict[str, str] = {}
        
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            
            if 'Stacks' in response and len(response['Stacks']) > 0:
                stack_tags = response['Stacks'][0].get('Tags', [])
                
                for tag in stack_tags:
                    key = tag.get('Key', '')
                    value = tag.get('Value', '')
                    if key and value:
                        tags[key] = value
                        
        except ClientError as e:
            if 'does not exist' in str(e):
                logging.warning(f"Stack {stack_name} does not exist")
            else:
                logging.error(f"Error getting stack tags: {str(e)}")
                
        return tags

    def check_stack_exists(self, stack_name: str) -> bool:
        """
        Check if a CloudFormation stack exists.

        Args:
            stack_name: Name of the CloudFormation stack to check

        Returns:
            bool: True if stack exists, False otherwise
        """
        try:
            self.cfn_client.describe_stacks(StackName=stack_name)
            return True
        except ClientError as e:
            if 'does not exist' in str(e):
                return False
            logging.error(f"Error checking stack existence: {str(e)}")
            raise

    def get_stack_status(self, stack_name: str) -> Optional[str]:
        """
        Get the current status of a CloudFormation stack.

        Args:
            stack_name: Name of the CloudFormation stack

        Returns:
            str: Current stack status (e.g., 'CREATE_COMPLETE', 'UPDATE_IN_PROGRESS')
            None: If stack doesn't exist or there's an error
        """
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            if 'Stacks' in response and len(response['Stacks']) > 0:
                return response['Stacks'][0]['StackStatus']
            return None
        except ClientError as e:
            logging.error(f"Error getting stack status: {str(e)}")
            return None

# CLI Commands and Options
@click.group()
def cli() -> None:
    """
    Command line interface for AWS infrastructure deployment management.
    
    Provides commands for managing different types of infrastructure deployments
    including service roles, pipelines, and networks.
    """
    pass

@cli.command()
@click.argument('prefix', required=True)
@click.argument('project_id', required=False)
@click.argument('stage_id', required=False)
@click.option('--check-stack', is_flag=True, help="Check if stack exists")
@click.option('--profile', default=None, help="AWS credential profile")
def service_role(prefix: str, project_id: Optional[str], stage_id: Optional[str], 
                check_stack: bool, profile: Optional[str]) -> None:
    """
    Manage service role infrastructure.

    Args:
        prefix: Resource prefix for naming
        project_id: Optional project identifier
        stage_id: Optional stage identifier
        check_stack: Flag to check if stack exists
        profile: AWS credential profile to use
    """
    try:
        config = ConfigManager('service-role', prefix, project_id, stage_id, profile=profile)
        stack_name = config.generate_stack_name()
        
        if check_stack:
            exists = config.check_stack_exists(stack_name)
            click.echo(f"Stack {stack_name} exists: {exists}")
            if exists:
                status = config.get_stack_status(stack_name)
                click.echo(f"Stack status: {status}")
        #else:
            #click.echo(f"Stack name would be: {stack_name}")
            
    except Exception as e:
        logging.error(f"Error in service_role command: {str(e)}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument('prefix', required=True)
@click.argument('project_id', required=True)
@click.argument('stage_id', required=False)
@click.option('--check-stack', is_flag=True, help="Check if stack exists")
@click.option('--profile', default=None, help="AWS credential profile")
def pipeline(prefix: str, project_id: str, stage_id: Optional[str], 
            check_stack: bool, profile: Optional[str]) -> None:
    """
    Manage pipeline infrastructure.

    Args:
        prefix: Resource prefix for naming
        project_id: Project identifier
        stage_id: Optional stage identifier
        check_stack: Flag to check if stack exists
        profile: AWS credential profile to use
    """
    try:
        config = ConfigManager('pipeline', prefix, project_id, stage_id, profile=profile)
        stack_name = config.generate_stack_name()
        
        if check_stack:
            exists = config.check_stack_exists(stack_name)
            click.echo(f"Stack {stack_name} exists: {exists}")
            if exists:
                status = config.get_stack_status(stack_name)
                click.echo(f"Stack status: {status}")
                
                # Display stack outputs
                outputs = config.get_stack_outputs(stack_name)
                if outputs:
                    click.echo("\nStack Outputs:")
                    for key, value in outputs.items():
                        click.echo(f"{key}: {value}")
        else:
            click.echo(f"Stack name would be: {stack_name}")
            
    except Exception as e:
        logging.error(f"Error in pipeline command: {str(e)}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument('prefix', required=True)
@click.argument('project_id', required=True)
@click.argument('stage_id', required=False)
@click.option('--check-stack', is_flag=True, help="Check if stack exists")
@click.option('--profile', default=None, help="AWS credential profile")
def network(prefix: str, project_id: str, stage_id: Optional[str], 
           check_stack: bool, profile: Optional[str]) -> None:
    """
    Manage network infrastructure.

    Args:
        prefix: Resource prefix for naming
        project_id: Project identifier
        stage_id: Optional stage identifier
        check_stack: Flag to check if stack exists
        profile: AWS credential profile to use
    """
    try:
        config = ConfigManager('network', prefix, project_id, stage_id, profile=profile)
        stack_name = config.generate_stack_name()
        
        if check_stack:
            exists = config.check_stack_exists(stack_name)
            click.echo(f"Stack {stack_name} exists: {exists}")
            if exists:
                status = config.get_stack_status(stack_name)
                click.echo(f"Stack status: {status}")
                
                # Display stack outputs
                outputs = config.get_stack_outputs(stack_name)
                if outputs:
                    click.echo("\nStack Outputs:")
                    for key, value in outputs.items():
                        click.echo(f"{key}: {value}")
        else:
            click.echo(f"Stack name would be: {stack_name}")
            
    except Exception as e:
        logging.error(f"Error in network command: {str(e)}")
        raise click.ClickException(str(e))

if __name__ == '__main__':
    """
    Entry point for the CLI application.
    
    Executes the CLI command group and handles any uncaught exceptions.
    """
    try:
        cli()
    except Exception as e:
        logging.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)
