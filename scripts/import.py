#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-28"
# Created by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

# Usage Information:
# import.py -h

# Full Documentation:
# https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/

import tomlkit
import argparse
import os
import sys
from typing import Optional, Dict
from pathlib import Path

from lib.aws_session import AWSSessionManager
from lib.logger import ScriptLogger, ConsoleAndLog, Log
from lib.tools import Strings

if sys.version_info[0] < 3:
    sys.stderr.write("Error: Python 3 is required\n")
    sys.exit(1)

# Initialize logger for this script
ScriptLogger.setup('import')

def format_key_value_pair(key, value):
    """Format key-value pairs with escaped quotes"""
    return f'"{key}"="{value}"'

IMPORT_DIR = "local-imports"

class ConfigImporter:
    def __init__(self, stack_name: str, region: Optional[str] = None, profile: Optional[str] = None) -> None:
        self.stack_name = stack_name
        self.region = region
        self.profile = profile
        self.aws_session = AWSSessionManager(self.profile, self.region)
        self.cfn_client = self.aws_session.get_client('cloudformation', self.region)

    def get_stack_info(self) -> Dict:
        """Retrieve stack information from CloudFormation"""
        
        try:
            # Get stack details
            stack = self.cfn_client.describe_stacks(StackName=self.stack_name)['Stacks'][0]
            
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
                'region': stack['StackId'].split(':')[3]  # Extract region from stack ID
            }
        
        except Exception as e:
            ConsoleAndLog.error(f"Error getting stack information: {str(e)}")
            raise

    def create_sam_config(self, stack_info: Dict) -> bool:
        """Create SAM config file in TOML format
        
        Args:
            stack_info (Dict): Dictionary containing stack information
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If required stack information is missing
            OSError: If there are file system related errors
            Exception: For other unexpected errors
        """
        try:
            # Validate required stack information
            required_fields = ['region', 'capabilities']
            missing_fields = [field for field in required_fields if not stack_info.get(field)]
            if missing_fields:
                raise ValueError(f"Missing required stack information: {', '.join(missing_fields)}")

            config = tomlkit.document()
            
            # Create version
            config["version"] = 0.1
            
            # Create default config
            default = tomlkit.table()
            
            # Deploy configuration
            deploy = tomlkit.table()
            deploy["parameters"] = tomlkit.table()
                
            try:
                deploy["parameters"]["stack_name"] = self.stack_name
                deploy["parameters"]["region"] = stack_info['region']
                deploy["parameters"]["confirm_changeset"] = True
                deploy["parameters"]["capabilities"] = stack_info['capabilities']
            except KeyError as e:
                raise ValueError(f"Failed to set required parameter: {str(e)}")
                    
            # Add stack parameters
            try:
                parameter_overrides = []
                for key, value in stack_info.get('parameters', {}).items():
                    if value is None:
                        ConsoleAndLog.warning(f"Parameter '{key}' has None value, skipping")
                        continue
                    parameter_overrides.append(format_key_value_pair(key, value))

                if parameter_overrides:
                    deploy["parameters"]["parameter_overrides"] = " ".join(parameter_overrides)
            except Exception as e:
                ConsoleAndLog.warning(f"Error processing parameters: {str(e)}")
            
            # Add tags if they exist
            try:
                if stack_info.get('tags'):
                    tags = []
                    for key, value in stack_info['tags'].items():
                        if value is None:
                            ConsoleAndLog.warning(f"Tag '{key}' has None value, skipping")
                            continue
                        tags.append(format_key_value_pair(key, value))
                    if tags:
                        deploy["parameters"]["tags"] = " ".join(tags)
            except Exception as e:
                ConsoleAndLog.warning(f"Error processing tags: {str(e)}")
            
            default["deploy"] = deploy
            config["default"] = default
            
            # Create import directory if it doesn't exist
            import_dir = self.get_import_dir()
            try:
                if not os.path.exists(import_dir):
                    os.makedirs(import_dir)
            except OSError as e:
                raise OSError(f"Failed to create import directory {import_dir}: {str(e)}")
                
            # Write to samconfig.toml
            file_path = self.get_import_file_path(stack_info)
            try:
                with open(file_path, "w") as f:
                    tomlkit.dump(config, f)
            except OSError as e:
                raise OSError(f"Failed to write config file {file_path}: {str(e)}")
            except Exception as e:
                raise Exception(f"Failed to dump TOML configuration: {str(e)}")
                
            ConsoleAndLog.info(f"Successfully created SAM config file at: {file_path}")
            return True
        
        except ValueError as e:
            ConsoleAndLog.error(f"Validation error: {str(e)}")
            raise
        except OSError as e:
            ConsoleAndLog.error(f"File system error: {str(e)}")
            raise
        except Exception as e:
            ConsoleAndLog.error(f"Unexpected error creating SAM config: {str(e)}")
            raise

    def get_import_dir(self) -> Path:
        """Get the import directory path"""
        # Get the script's directory in a cross-platform way
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent / IMPORT_DIR
    
    def get_import_file_name(self, stack_info: Optional[Dict] = {}) -> str:
        """Get the import file name"""
        region = stack_info.get('region', "")
        if region:
            region += "_"
        return f"samconfig-{self.stack_name}_{region}{Strings.get_date_stamp()}.toml"
    
    def get_import_file_path(self, stack_info: Optional[Dict] = {}) -> Path:
        """Get the import file path"""
        return self.get_import_dir() / self.get_import_file_name(stack_info)

# =============================================================================
# ----- Main function ---------------------------------------------------------
# =============================================================================

EPILOG = """
Supports both AWS SSO and IAM credentials.
For SSO users, credentials will be refreshed automatically.
For IAM users, please ensure your credentials are valid using 'aws configure'.

Examples:

    # Import stack acme-blue-test-pipeline
    import.py acme-blue-test-pipeline

    # Import stack acme-blue-test-pipeline from a specific region
    import.py acme-blue-test-pipeline --region us-west-1

    # With different AWS profile
    import.py acme-blue-test-pipeline --region us-west-1 --profile myprofile
"""

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description='Generate SAM config from existing CloudFormation stack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(EPILOG)
    )
    parser.add_argument('stack-name',
                        required=True,
                        help='Name of the existing CloudFormation stack')
    parser.add_argument('--profile',
                        required=False,
                        help='AWS profile name')
    parser.add_argument('--region',
                        required=False,
                        default=None,
                        help='AWS region (default: us-east-1)')
    
    args = parser.parse_args()
        
    return args

def main():
    args = parse_args()
    Log.info(f"{sys.argv}")
    Log.info(f"Version: {VERSION}")

    importer = ConfigImporter(args.stack_name, args.region, args.profile)
    
    try:
        ConsoleAndLog.info(f"Fetching information for stack: {args.stack_name}")
        stack_info = importer.get_stack_info()

        ConsoleAndLog.info(f"Generating SAM config file...")
        success = importer.create_sam_config(stack_info)

        if success:
            ConsoleAndLog.info(f"Import completed successfully")
        else:
            ConsoleAndLog.error("Import could not complete")
            sys.exit(1)

    except ValueError as e:
        ConsoleAndLog.error(f"Configuration error: {str(e)}")
        sys.exit(1)
    except OSError as e:
        ConsoleAndLog.error(f"File system error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        ConsoleAndLog.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
