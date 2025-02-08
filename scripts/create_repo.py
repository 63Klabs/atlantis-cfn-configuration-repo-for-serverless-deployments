#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-28"
# Created by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

# Usage Information:
# create_repo.py -h

# Full Documentation:
# https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/

import tempfile
import zipfile
import base64
import os
import argparse
import sys
import click
from pathlib import Path
from typing import Optional, List, Union
from urllib.parse import urlparse

from lib.loader import ConfigLoader
from lib.aws_session import AWSSessionManager, TokenRetrievalError
from lib.logger import ScriptLogger, Log, ConsoleAndLog
from lib.tools import Colorize
from typing import Dict

if sys.version_info[0] < 3:
    sys.stderr.write("Error: Python 3 is required\n")
    sys.exit(1)

# Initialize logger for this script
ScriptLogger.setup('create_repo')

SETTINGS_DIR = "defaults"

class RepositoryCreator:

    def __init__(self, repo_name: str, s3_uri: Optional[str] = None, region:  Optional[str] = None, profile: Optional[str] = None, prefix: Optional[str] = None) -> None:
        self.repo_name = repo_name
        self.s3_uri = s3_uri
        self.region = region
        self.profile = profile
        self.prefix = prefix
        self.tags = {}
        
        self.aws_session = AWSSessionManager(self.profile, self.region)
        self.s3_client = self.aws_session.get_client('s3', self.region)
        self.codecommit_client = self.aws_session.get_client('codecommit', self.region)

        config_loader = ConfigLoader(
            settings_dir=self.get_settings_dir(),
            prefix=self.prefix,
            project_id=None,
            infra_type=None
        )

        self.settings = config_loader.load_settings()
        self.defaults = config_loader.load_defaults()

    # -------------------------------------------------------------------------
    # - Utility
    # -------------------------------------------------------------------------

    def parse_s3_url(self, s3_uri: str) -> List[str]:
        """Parse an S3 URL into bucket and key."""
        try:
            parsed = urlparse(s3_uri)
            if parsed.scheme != 's3':
                raise ValueError("URL must be an S3 URL starting with 's3://'")
            return parsed.netloc, parsed.path.lstrip('/')
        except ValueError as e:
            click.echo(Colorize.error(f"Error parsing S3 URL: {str(e)}"))
            Log.error(f"Error: {str(e)}")
            sys.exit(1)

    # -------------------------------------------------------------------------
    # - Create and Seed Repository
    # -------------------------------------------------------------------------

    def create_and_seed_repository(self):

        # Parse S3 URL
        s3_bucket, s3_key = self.parse_s3_url(self.s3_uri)

        # Create the repository
        try:
            click.echo(Colorize.output_with_value("Creating repository:", self.repo_name))
            Log.info(f"Creating repository: {self.repo_name}")
            response = self.codecommit_client.create_repository(
                repositoryName=self.repo_name,
                repositoryDescription=f'Repository seeded from {self.s3_uri}',
                tags=self.tags
            )
            click.echo(Colorize.output_with_value("Repository created:", response['repositoryMetadata']['cloneUrlHttp']))
            Log.info(f"Repository created: {response['repositoryMetadata']['cloneUrlHttp']}")
        except self.codecommit_client.exceptions.RepositoryNameExistsException:
            click.echo(Colorize.error(f"Repository {self.repo_name} already exists"))
            Log.error(f"Error: Repository {self.repo_name} already exists")
            sys.exit(1)
        except Exception as e:
            click.echo(Colorize.error(f"Error creating repository: {str(e)}"))
            Log.error(f"Error creating repository: {str(e)}")
            sys.exit(1)
        
        # Download and process the zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'source.zip')
            
            try:
                click.echo(Colorize.output_with_value("Downloading zip from S3:", self.s3_uri))
                Log.info(f"Downloading zip from S3: {self.s3_uri}")
                self.s3_client.download_file(s3_bucket, s3_key, zip_path)
            except Exception as e:
                click.echo(Colorize.error(f"Error downloading zip file. Check logs for more information."))
                Log.error(f"Error downloading zip file: {str(e)}")
                self.codecommit_client.delete_repository(repositoryName=self.repo_name)
                sys.exit(1)
            
            # Extract files
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                os.remove(zip_path)  # Remove the zip file to not include it
            except Exception as e:
                click.echo(Colorize.error(f"Error extracting zip file. Check logs for more information."))
                Log.error(f"Error extracting zip file: {str(e)}")
                self.codecommit_client.delete_repository(repositoryName=self.repo_name)
                sys.exit(1)

            # Prepare files for commit
            put_files = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, temp_dir)
                    
                    try:
                        with open(full_path, 'rb') as f:
                            content = f.read()
                            put_files.append({
                                'filePath': relative_path,
                                'fileContent': base64.b64encode(content).decode('utf-8')
                            })
                    except Exception as e:
                        click.echo(Colorize.error(f"Error processing file {relative_path}"))
                        Log.error(f"Error processing file {relative_path}: {str(e)}")
                        self.codecommit_client.delete_repository(repositoryName=self.repo_name)
                        sys.exit(1)

            # Create initial commit
            try:
                click.echo(Colorize.output("Seeding repository with initial commit"))
                Log.info("Creating initial commit")
                self.codecommit_client.create_commit(
                    repositoryName=self.repo_name,
                    branchName='main',
                    putFiles=put_files,
                    commitMessage=f'Initial commit: Seeded from {self.s3_uri}'
                )
                Log.info(f"\nRepository {self.repo_name} seeded successfully!")
                Log.info(f"Clone URL (HTTPS): {response['repositoryMetadata']['cloneUrlHttp']}")
                Log.info(f"Clone URL (SSH): {response['repositoryMetadata']['cloneUrlSsh']}")
                click.echo(Colorize.success(f"\nRepository {self.repo_name} seeded successfully!"))
                click.echo(Colorize.output_with_value("Clone URL (HTTPS):", response['repositoryMetadata']['cloneUrlHttp']))
                click.echo(Colorize.output_with_value("Clone URL (SSH):", response['repositoryMetadata']['cloneUrlSsh']))
            except Exception as e:
                click.echo(Colorize.error(f"Error creating initial commit. Check logs for more information."))
                Log.error(f"Error creating initial commit: {str(e)}")
                self.codecommit_client.delete_repository(repositoryName=self.repo_name)
                sys.exit(1)

    # -------------------------------------------------------------------------
    # - Interactive Prompts
    # -------------------------------------------------------------------------

    def select_from_app_starters(self, app_starters: List[str]) -> str:
        """List available application starters and prompt the user to choose one to seed the repository.
        
        Args:
            app_starters (List[str]): List of application starters from s3
            
        Returns:
            str: Selected application starter
        """

        if not app_starters:
            Log.error("No application starters found")
            click.echo(Colorize.error("No application starters found"))
            sys.exit(1)
        
        # Sort app_starters for consistent ordering
        app_starters.sort()
        
        # Display numbered list
        click.echo(Colorize.question("Available application starters:"))
        for idx, app_starter in enumerate(app_starters, 1):
            click.echo(Colorize.option(f"{idx}. {app_starter}"))
        
        print()

        while True:
            try:
                default = ''

                choice = Colorize.prompt("Enter app number", default, str)
                # Check if input is a number
                app_idx = int(choice) - 1
                
                # Validate the index is within range
                if 0 <= app_idx < len(app_starters):
                    selected = app_starters[app_idx]
                            
                    return selected
                else:
                    click.echo(Colorize.error(f"Please enter a number between 1 and {len(app_starters)}"))
            except ValueError:
                click.echo(Colorize.error("Please enter a valid number"))
            except KeyboardInterrupt:
                click.echo(Colorize.info("Application starter selection cancelled"))
                sys.exit(1)


    def discover_s3_app_starters(self) -> List[str]:
        """Discover available app starters in the app starter directory"""
        app_starters = []
        # loop through self.settings.get('app_starters', []), access the bucket, and append to app_starters
        for s3_app_starters_location in self.settings.get('app_starters', []):
            try:
                bucket = s3_app_starters_location['bucket']
                prefix = s3_app_starters_location['prefix'].strip('/')
                Log.info(f"Discovering app starters from s3://{bucket}/{prefix}")
                response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}")
                for obj in response.get('Contents', []):
                    if obj['Key'].endswith('.zip'):
                        #Log.info(f"Found app starter: {obj}")
                        s3_uri = f"s3://{bucket}/{obj['Key']}"
                        app_starters.append(s3_uri)
            except Exception as e:
                Log.error(f"Error discovering application starters from S3: {e}")
                click.echo(Colorize.error("Error discovering application starters from S3. Check logs for more info."))
                raise

        return app_starters

    def prompt_for_tags(self, tags: Dict) -> Dict:
        """Prompt the user to enter tags for the repository

        Args:
            tags (Dict): Default tags for the repository

        Returns:
            Dict: Tags for the repository
        """

        # First, iterate through the default tags and prompt the user to enter values
        # Some may already have default values. Allow the user to just hit enter to accept default
        for key, value in tags.items():
            if value is None:
                value = ''
            tags[key] = Colorize.prompt(f"Enter value for tag '{key}'", value, str)

        # Now, ask the user to add any additional tags using key=value. 
        # After the user enters a key=value pair, place it in the tags Dict and prompt again
        # If the user enters an empty string, stop prompting and return the tags
        while True:
            tag_input = Colorize.prompt("Enter tag in key=value format", "", str)
            if tag_input == "":
                break
            try:
                key, value = tag_input.split('=')
                tags[key.strip()] = value.strip()
            except ValueError:
                click.echo(Colorize.error("Invalid tag format. Please use key=value format."))
                continue

        return tags
    
    def get_default_tags(self) -> Dict:
        """Get the default tags for the repository

        Returns:
            Dict: Default tags for the repository
        """
        tags = {}

        # Get the default tag keys from self.settings.tag_keys
        tag_keys = self.settings.get('tag_keys', [])
        # place each key as an entry in tags where it's value is None
        for key in tag_keys:
            tags[key] = None

        # Get the default tags from self.defaults.tags and merge with tags. Overwrite existing keys in tags with the value from default. Add in any new tags.
        default_tags = self.defaults.get('tags', {})
        for key, value in default_tags.items():
            tags[key] = value

        return tags

    # -------------------------------------------------------------------------
    # - Naming and File Locations
    # -------------------------------------------------------------------------

    def get_settings_dir(self) -> Path:
        """Get the settings directory path"""
        # Get the script's directory in a cross-platform way
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent / SETTINGS_DIR
    
    # -------------------------------------------------------------------------
    # - Setters
    # -------------------------------------------------------------------------

    def set_s3_uri(self, s3_uri: str) -> None:
        """Set the S3 URI for the repository"""
        self.s3_uri = s3_uri

    def set_tags(self, tags: Union[Dict, List]) -> None:
        """Set the tags for the repository
        
        Args:
            tags: Either a dictionary of tags {"key": "value"} or 
                a list of tag dictionaries [{"Key": "key", "Value": "value"}]
        """
        if isinstance(tags, list):
            # Convert AWS-style tag list to dictionary
            self.tags = {
                item["Key"]: item["Value"] 
                for item in tags 
                if "Key" in item and "Value" in item
            }
        elif isinstance(tags, dict):
            self.tags = tags
        else:
            raise TypeError("Tags must be either a dictionary or a list of key-value pairs")


    
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

    # Create repository and load code from zip
    create_repo.py <repo-name> --s3-uri <s3://bucket/path/to/file.zip>

    # Create repository and load code from zip using profile
    create_repo.py <repo-name> --s3-uri <s3://bucket/path/to/file.zip> --profile <profile>
"""

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description='Create and seed a CodeCommit repository from an S3 zip file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(EPILOG)
    )
    parser.add_argument('repository_name',
                        type=str,
                        help='Name of the CodeCommit repository to create')
    parser.add_argument('--s3-uri',
                        type=str,
                        required=False,
                        help='S3 URL of the zip file (e.g., s3://bucket-name/path/to/file.zip)')
    parser.add_argument('--profile',
                        type=str,
                        required=False,
                        default=None,
                        help='AWS profile name (default: default profile)')
    parser.add_argument('--region',
                        type=str,
                        required=False,
                        default=None,
                        help='AWS region (default: default region from profile)')
    parser.add_argument('--prefix',
                        type=str,
                        required=False,
                        default=None,
                        help='Prefix to use for default tags. The repository name DOES NOT need the prefix.')
    
    args = parser.parse_args()
        
    return args

def main():
    
    args = parse_args()
    Log.info(f"{sys.argv}")
    Log.info(f"Version: {VERSION}")

    print()
    click.echo(Colorize.divider("="))
    click.echo(Colorize.output_bold(f"Repository Creator ({VERSION})"))
    click.echo(Colorize.divider("="))
    print()

    try:
        repo_creator = RepositoryCreator(
            args.repository_name, 
            args.s3_uri, 
            args.region, 
            args.profile, 
            args.prefix
        )
    except TokenRetrievalError as e:
        ConsoleAndLog.error(f"AWS authentication error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        ConsoleAndLog.error(f"Error initializing repository creator: {str(e)}")
        sys.exit(1)
    
    # prompt for starter app if no args.s3_uri
    try:
        if args.s3_uri is None:
            repo_creator.set_s3_uri(repo_creator.select_from_app_starters(repo_creator.discover_s3_app_starters()))
    except KeyboardInterrupt:
        ConsoleAndLog.info("Repository creation cancelled")
        sys.exit(1)
    except Exception as e:
        ConsoleAndLog.error(f"Error selecting application starter: {str(e)}")
        sys.exit(1)

    # prompt for tags
    try:
        repo_creator.set_tags(repo_creator.prompt_for_tags(repo_creator.get_default_tags()))
    except KeyboardInterrupt:
        ConsoleAndLog.info("Repository creation cancelled")
        sys.exit(1)
    except Exception as e:
        ConsoleAndLog.error(f"Error setting tags: {str(e)}")
        sys.exit(1)

    # create repo and seed with code
    try:
        repo_creator.create_and_seed_repository()
    except Exception as e:
        ConsoleAndLog.error(f"Error creating and seeding repository: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
