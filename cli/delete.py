#!/usr/bin/env python3

VERSION = "v0.0.3/2025-08-26"
# Created by Chad Kluck with AI assistance from Amazon Q Developer

# Usage Information:
# delete.py -h

# Full Documentation:
# https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/

import toml
import sys
import argparse
import click
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lib.aws_session import AWSSessionManager
from lib.logger import ScriptLogger, Log
from lib.tools import Colorize
from lib.atlantis import DefaultsLoader
from lib.gitops import Git

if sys.version_info[0] < 3:
    sys.stderr.write("Error: Python 3 is required\n")
    sys.exit(1)

# Initialize logger for this script
ScriptLogger.setup('destroy')

SAMCONFIG_DIR = "samconfigs"
SETTINGS_DIR = "defaults"
VALID_INFRA_TYPES = ['pipeline', 'storage', 'network', 'iam']

class StackDestroyer:
    """
    Manages destruction of AWS CloudFormation/SAM stacks.
    """
    
    def __init__(self, infra_type: str, prefix: str, project_id: str, stage_id: str, 
                    profile: Optional[str] = None, region: Optional[str] = None, 
                    no_browser: Optional[bool] = False):
        self.infra_type = infra_type
        self.prefix = prefix
        self.project_id = project_id
        self.stage_id = stage_id
        self.profile = profile
        self.region = region
        
        self._validate_args()
        
        # Set up AWS session and clients
        self.aws_session = AWSSessionManager(profile, region, no_browser)
        self.cfn_client = self.aws_session.get_client('cloudformation', region)
        self.ssm_client = self.aws_session.get_client('ssm', region)
        
        config_loader = DefaultsLoader(
            settings_dir=self.get_settings_dir(),
            prefix=self.prefix,
            project_id=self.project_id,
            infra_type=self.infra_type
        )
        
        self.settings = config_loader.load_settings()

    def _validate_args(self) -> None:
        """Validate arguments"""
        if self.infra_type not in VALID_INFRA_TYPES:
            raise click.UsageError(f"Invalid infra_type. Must be one of {VALID_INFRA_TYPES}")

    def get_settings_dir(self) -> Path:
        """Get the settings directory path"""
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent / SETTINGS_DIR

    def get_samconfig_dir(self) -> Path:
        """Get the samconfig directory path"""
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent / SAMCONFIG_DIR / self.prefix / self.project_id

    def get_samconfig_file_name(self) -> str:
        """Get the samconfig file name"""
        return f"samconfig-{self.prefix}-{self.project_id}-{self.infra_type}.toml"

    def get_samconfig_file_path(self) -> Path:
        """Get the samconfig file path"""
        return self.get_samconfig_dir() / self.get_samconfig_file_name()

    def get_pipeline_stack_name(self) -> str:
        """Get the pipeline stack name"""
        return f"{self.prefix}-{self.project_id}-{self.stage_id}-pipeline"

    def get_application_stack_name(self) -> str:
        """Get the application stack name"""
        return f"{self.prefix}-{self.project_id}-{self.stage_id}-application"

    def validate_stack_arn(self, stack_name: str, expected_name: str) -> bool:
        """Validate that the provided ARN matches the expected stack name"""
        arn = Colorize.prompt(f"Enter the ARN of the {stack_name} stack", "", str)
        if not arn:
            click.echo(Colorize.error("ARN cannot be empty"))
            return False
        
        # Extract stack name from ARN
        try:
            # ARN format: arn:aws:cloudformation:region:account:stack/stack-name/stack-id
            arn_parts = arn.split('/')
            if len(arn_parts) >= 2:
                actual_stack_name = arn_parts[1]
                if actual_stack_name == expected_name:
                    return True
                else:
                    click.echo(Colorize.error(f"Stack name mismatch. Expected: {expected_name}, Got: {actual_stack_name}"))
                    return False
            else:
                click.echo(Colorize.error("Invalid ARN format"))
                return False
        except Exception as e:
            click.echo(Colorize.error(f"Error parsing ARN: {str(e)}"))
            return False

    def check_delete_tag(self, stack_name: str) -> bool:
        """Check if stack has DeleteOnOrAfter tag with valid date"""
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            tags = {tag['Key']: tag['Value'] for tag in stack.get('Tags', [])}
            
            delete_date_str = tags.get('DeleteOnOrAfter')
            if not delete_date_str:
                click.echo(Colorize.error(f"Stack {stack_name} does not have DeleteOnOrAfter tag"))
                return False
            
            # Parse date
            try:
                if delete_date_str.endswith('Z'):
                    delete_date = datetime.fromisoformat(delete_date_str[:-1]).replace(tzinfo=timezone.utc)
                    current_date = datetime.now(timezone.utc)
                else:
                    delete_date = datetime.fromisoformat(delete_date_str).date()
                    current_date = datetime.now().date()
                
                if current_date >= delete_date:
                    click.echo(Colorize.success(f"DeleteOnOrAfter tag validation passed: {delete_date_str}"))
                    return True
                else:
                    click.echo(Colorize.error(f"Current date ({current_date}) is before DeleteOnOrAfter date ({delete_date})"))
                    return False
            except ValueError as e:
                click.echo(Colorize.error(f"Invalid date format in DeleteOnOrAfter tag: {delete_date_str}"))
                return False
                
        except Exception as e:
            click.echo(Colorize.error(f"Error checking DeleteOnOrAfter tag: {str(e)}"))
            return False

    def check_stack_termination_protection(self, stack_name: str) -> bool:
        """Check if stack termination protection is disabled"""
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            termination_protection = stack.get('EnableTerminationProtection', False)
            
            if not termination_protection:
                click.echo(Colorize.success(f"Stack termination protection validation passed: disabled"))
                return True
            else:
                click.echo(Colorize.error(f"Stack {stack_name} has termination protection enabled"))
                return False
                
        except Exception as e:
            click.echo(Colorize.error(f"Error checking stack termination protection: {str(e)}"))
            return False

    def final_confirmation(self) -> bool:
        """Final confirmation by entering prefix, project_id, and stage_id"""
        click.echo(Colorize.warning("For final confirmation, please enter the Prefix, ProjectId, and StageId of the pipeline and application to delete."))
        
        entered_prefix = Colorize.prompt("Prefix", "", str)
        entered_project_id = Colorize.prompt("ProjectId", "", str)
        entered_stage_id = Colorize.prompt("StageId", "", str)
        
        if (entered_prefix == self.prefix and 
            entered_project_id == self.project_id and 
            entered_stage_id == self.stage_id):
            return True
        else:
            click.echo(Colorize.error("Confirmation failed. Values do not match."))
            return False

    def delete_stack(self, stack_name: str) -> bool:
        """Delete a CloudFormation stack"""
        import time
        
        try:
            click.echo(Colorize.output(f"Deleting stack: {stack_name}"))
            Log.info(f"Deleting stack: {stack_name}")
            
            self.cfn_client.delete_stack(StackName=stack_name)
            
            # Custom polling loop with progress updates
            max_attempts = 180  # 30 minutes max
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    response = self.cfn_client.describe_stacks(StackName=stack_name)
                    stack_status = response['Stacks'][0]['StackStatus']
                    
                    if stack_status == 'DELETE_COMPLETE':
                        click.echo(Colorize.success(f"Stack {stack_name} deleted successfully"))
                        Log.info(f"Stack {stack_name} deleted successfully")
                        return True
                    elif stack_status in ['DELETE_FAILED', 'ROLLBACK_COMPLETE']:
                        click.echo(Colorize.error(f"Stack deletion failed with status: {stack_status}"))
                        Log.error(f"Stack deletion failed with status: {stack_status}")
                        return False
                    else:
                        click.echo(Colorize.output(f"Stack deletion in progress... Status: {stack_status}"))
                        Log.info(f"Stack deletion in progress... Status: {stack_status}")
                        
                except self.cfn_client.exceptions.ClientError as e:
                    if 'does not exist' in str(e):
                        click.echo(Colorize.success(f"Stack {stack_name} deleted successfully"))
                        Log.info(f"Stack {stack_name} deleted successfully")
                        return True
                    else:
                        raise
                
                time.sleep(10)
                attempt += 1
            
            click.echo(Colorize.error(f"Stack deletion timed out after 30 minutes"))
            Log.error(f"Stack deletion timed out after 30 minutes")
            return False
            
        except Exception as e:
            click.echo(Colorize.error(f"Error deleting stack {stack_name}: {str(e)}"))
            Log.error(f"Error deleting stack {stack_name}: {str(e)}")
            return False

    def delete_ssm_parameters(self) -> None:
        """Delete SSM parameters associated with the application"""
        try:
            # Check for ParameterStoreHierarchy in application stack
            application_stack_name = self.get_application_stack_name()
            parameter_store_hierarchy = ""
            
            try:
                response = self.cfn_client.describe_stacks(StackName=application_stack_name)
                stack = response['Stacks'][0]
                parameters = {param['ParameterKey']: param['ParameterValue'] for param in stack.get('Parameters', [])}
                parameter_store_hierarchy = parameters.get('ParameterStoreHierarchy', '')
            except Exception as e:
                Log.warning(f"Could not get ParameterStoreHierarchy from stack {application_stack_name}: {str(e)}")
            
            application_suffix = f"/{self.prefix}-{self.project_id}-{self.stage_id}/"

            # if parameter_store_hierarchy and ends with application_suffix
            if parameter_store_hierarchy and parameter_store_hierarchy.endswith(application_suffix):
                parameter_prefix = parameter_store_hierarchy
            else:
                parameter_prefix = application_suffix
            
            # List parameters with the prefix
            paginator = self.ssm_client.get_paginator('describe_parameters')
            parameters_to_delete = []
            
            for page in paginator.paginate():
                for param in page['Parameters']:
                    if param['Name'].startswith(parameter_prefix):
                        parameters_to_delete.append(param['Name'])
            
            if parameters_to_delete:
                click.echo(Colorize.output(f"Found {len(parameters_to_delete)} SSM parameters to delete"))
                Log.info(f"Found {len(parameters_to_delete)} SSM parameters to delete: {parameters_to_delete}")
                
                # List the parameters
                for param in parameters_to_delete:
                    click.echo(Colorize.output(f" - {param}"))

                # confirm deletion of parameters
                if not click.confirm(Colorize.question("Proceed with deletion of these SSM parameters?")):
                    click.echo(Colorize.error("SSM parameter deletion cancelled by user"))
                    Log.info("SSM parameter deletion cancelled by user")
                    return
                
                # Delete parameters in batches of 10 (AWS limit)
                for i in range(0, len(parameters_to_delete), 10):
                    batch = parameters_to_delete[i:i+10]
                    self.ssm_client.delete_parameters(Names=batch)
                    
                click.echo(Colorize.success(f"Deleted {len(parameters_to_delete)} SSM parameters"))
                Log.info(f"Deleted {len(parameters_to_delete)} SSM parameters")
            else:
                click.echo(Colorize.output("No SSM parameters found to delete"))
                Log.info("No SSM parameters found to delete")
                
        except Exception as e:
            click.echo(Colorize.error(f"Error deleting SSM parameters: {str(e)}"))
            Log.error(f"Error deleting SSM parameters: {str(e)}")

    def update_samconfig(self) -> None:
        """Update or delete samconfig file"""
        samconfig_path = self.get_samconfig_file_path()
        
        if not samconfig_path.exists():
            click.echo(Colorize.warning("Samconfig file not found"))
            return
        
        if click.confirm(Colorize.question("Delete samconfig entry for this deployment?")):
            try:
                # Load current config
                with open(samconfig_path, 'r') as f:
                    config = toml.load(f)
                
                # Remove the environment section (e.g., test.deploy.parameters)
                if self.stage_id in config:
                    del config[self.stage_id]
                    click.echo(Colorize.success(f"Removed {self.stage_id} environment from samconfig"))
                    Log.info(f"Removed {self.stage_id} environment from samconfig")
                
                # Count remaining environments (exclude 'atlantis' and 'version')
                remaining_envs = [key for key in config.keys() if key not in ['atlantis', 'version']]
                
                # If no environments left, delete the file
                if not remaining_envs:
                    samconfig_path.unlink()
                    click.echo(Colorize.success("Deleted samconfig file (no environments remaining)"))
                    Log.info("Deleted samconfig file (no environments remaining)")
                    
                    # Delete parent directory if empty
                    parent_dir = samconfig_path.parent
                    try:
                        parent_dir.rmdir()  # Only removes if empty
                        click.echo(Colorize.success(f"Deleted empty directory: {parent_dir}"))
                        Log.info(f"Deleted empty directory: {parent_dir}")
                    except OSError:
                        # Directory not empty or other error, ignore
                        pass
                else:
                    # Save updated config
                    with open(samconfig_path, 'w') as f:
                        toml.dump(config, f)
                    click.echo(Colorize.success("Updated samconfig file"))
                    Log.info("Updated samconfig file")
                    
            except Exception as e:
                click.echo(Colorize.error(f"Error updating samconfig: {str(e)}"))
                Log.error(f"Error updating samconfig: {str(e)}")

    def destroy_pipeline(self) -> None:
        """Destroy pipeline infrastructure"""
        click.echo(Colorize.output_bold(f"Starting destruction of pipeline: {self.prefix}-{self.project_id}-{self.stage_id}"))
        
        # 1. Git pull prompt
        Git.prompt_git_pull()
        
        # 2. Validate pipeline stack ARN
        pipeline_stack_name = self.get_pipeline_stack_name()
        click.echo(Colorize.output_bold("Step 1: Validate Pipeline Stack"))
        if not self.validate_stack_arn("pipeline", pipeline_stack_name):
            click.echo(Colorize.error("Pipeline stack validation failed"))
            sys.exit(1)
        
        # 3. Validate application stack ARN
        application_stack_name = self.get_application_stack_name()
        click.echo(Colorize.output_bold("Step 2: Validate Application Stack"))
        if not self.validate_stack_arn("application", application_stack_name):
            click.echo(Colorize.error("Application stack validation failed"))
            sys.exit(1)
        
        # 4. Check DeleteOnOrAfter tag
        click.echo(Colorize.output_bold("Step 3a: Validate DeleteOnOrAfter Tag"))
        if not self.check_delete_tag(pipeline_stack_name):
            click.echo(Colorize.error("DeleteOnOrAfter tag validation failed"))
            sys.exit(1)

        # 5. Check Stack Termination Protection tag for Pipeline
        click.echo(Colorize.output_bold("Step 3b: Validate Stack Termination Protection is Disabled for Pipeline"))
        if not self.check_stack_termination_protection(pipeline_stack_name):
            click.echo(Colorize.error("Stack Termination Protection validation failed"))
            sys.exit(1)

        # 6. Check Stack Termination Protection tag for Application
        click.echo(Colorize.output_bold("Step 3c: Validate Stack Termination Protection is Disabled for Application"))
        if not self.check_stack_termination_protection(application_stack_name):
            click.echo(Colorize.error("Stack Termination Protection validation failed"))
            sys.exit(1)
        
        # 7. Final confirmation
        click.echo(Colorize.output_bold("Step 4: Final Confirmation"))
        if not self.final_confirmation():
            click.echo(Colorize.error("Final confirmation failed"))
            sys.exit(1)
        
        # 8. Begin deletion
        click.echo(Colorize.output_bold("Step 5: Beginning Deletion Process"))
        
        # Delete application stack first
        if not self.delete_stack(application_stack_name):
            click.echo(Colorize.error("Failed to delete application stack"))
            sys.exit(1)
        
        # Delete pipeline stack
        if not self.delete_stack(pipeline_stack_name):
            click.echo(Colorize.error("Failed to delete pipeline stack"))
            sys.exit(1)
        
        # Delete SSM parameters
        self.delete_ssm_parameters()
        
        # Update samconfig
        self.update_samconfig()
        
        # 7. Git commit and push
        commit_message = f"Destroyed {self.infra_type} {self.prefix}-{self.project_id}"
        if self.stage_id:
            commit_message += f"-{self.stage_id}"
        print()
        Git.git_commit_and_push(commit_message)
        
        click.echo(Colorize.success("Pipeline destruction completed successfully!"))

    def destroy(self) -> None:
        """Main destroy method"""
        if self.infra_type == 'pipeline':
            self.destroy_pipeline()
        else:
            click.echo(Colorize.error(f"Destruction for {self.infra_type} is not implemented yet"))
            click.echo(Colorize.info("For storage, network, and iam: cleanup can be done by deleting the stack manually"))
            click.echo(Colorize.info("(Ensure S3 buckets are empty first)"))
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Destroy AWS infrastructure stacks',
        epilog="""
Examples:
    delete.py pipeline acme mywebapp test --profile ACME_DEV
    delete.py storage acme static-assets --profile ACME_DEV --region us-west-2
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('infra_type', choices=VALID_INFRA_TYPES,
                        help='Type of infrastructure to destroy')
    parser.add_argument('prefix', help='Prefix for stack names')
    parser.add_argument('project_id', help='Project identifier')
    parser.add_argument('stage_id', help='Stage identifier')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument('--no-browser', action='store_true',
                        help='Disable browser-based authentication')
    
    args = parser.parse_args()
    
    try:
        destroyer = StackDestroyer(
            infra_type=args.infra_type,
            prefix=args.prefix,
            project_id=args.project_id,
            stage_id=args.stage_id,
            profile=args.profile,
            region=args.region,
            no_browser=args.no_browser
        )
        
        destroyer.destroy()
        
    except KeyboardInterrupt:
        click.echo(Colorize.error("\nOperation cancelled by user"))
        sys.exit(1)
    except Exception as e:
        click.echo(Colorize.error(f"Unexpected error: {str(e)}"))
        Log.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()