#!/usr/bin/env python3

VERSION = "v0.1.0/2025-03-25"
# Created by Chad Kluck with AI assistance from Amazon Q Developer

import os
import sys
import requests
import tempfile
import zipfile
import click
import argparse
import traceback
from typing import Dict, Optional, List

from pathlib import Path

from lib.aws_session import AWSSessionManager, TokenRetrievalError
from lib.logger import ScriptLogger, Log, ConsoleAndLog
from lib.tools import Colorize
from lib.atlantis import ConfigLoader

if sys.version_info[0] < 3:
    sys.stderr.write("Error: Python 3 is required\n")
    sys.exit(1)

# Initialize logger for this script
ScriptLogger.setup('update')

# Directories to update
TARGET_DIRS = ['docs', 'scripts']
DEFAULT_SRC = "https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments"
SETTINGS_DIR = "defaults"
DEFAULT_S3_PATH = "/atlantis/utilities/v2/"

class UpdateManager:

    def __init__(self, profile: Optional[str] = None):

        self.profile = profile

        config_loader = ConfigLoader(
            settings_dir=self.get_settings_dir()
        )

        self.settings = config_loader.load_settings()

        # Validate and assemble the source info
        update_settings = self.settings.get('updates', {})
        self.target_dirs = update_settings.get('target_dirs', TARGET_DIRS)
        self.source = update_settings.get('source', DEFAULT_SRC)
        self.src_type = self.get_type(self.source)
        self.src_ver = self.get_version(self.source, self.src_type, update_settings.get('ver', ""))
        self.source = self.update_source(self.source, self.src_type, self.src_ver)


        # Check the arguments before moving on
        self._validate_args()

        # Set up AWS session and clients
        self.aws_session = AWSSessionManager(profile)
        self.s3_client = self.aws_session.get_client('s3')

    def _validate_args(self) -> None:
        """Validate arguments"""
        
        # validate target dirs
        # Target directories must be a list and can only include strings defined in TARGET_DIRS
        if not isinstance(self.target_dirs, list):
            raise click.UsageError(f"target_dirs must be a list")
        if not all(isinstance(item, str) for item in self.target_dirs):
            raise click.UsageError(f"target_dirs must be a list of strings")
        if not all(item in TARGET_DIRS for item in self.target_dirs):
            raise click.UsageError(f"target_dirs must be a subset of {TARGET_DIRS}")
        
        # validate source
        # Source must be a string and must be either a GitHub URL, S3 location, or local file path
        if not isinstance(self.source, str):
            raise click.UsageError(f"source must be a string")
        if not self.source.startswith(('https://github.com/', 's3://', '/')):
            raise click.UsageError(f"source must be a valid URL, S3 location, or local file path")
        
        # validate profile
        if self.profile and not isinstance(self.profile, str):
            raise click.UsageError(f"profile must be a string")

    def get_settings_dir(self) -> Path:
        """Get the settings directory path"""
        # Get the script's directory in a cross-platform way
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent / SETTINGS_DIR
    
    def get_type(self, source: str) -> str:
        """Determine the type of the source
        From the source string, determine if we are going to use a local zip file,
        download a zip from S3, the GitHub repository main branch, or the GitHub repository release
        """
        # Source may be
        # - a local zip file
        # - a S3 location
        # - a GitHub repository main branch
        # - a GitHub repository release (either latest or a specific release)
        
        # if source is http/https and ends with .zip, then we can just use it
        if source.startswith("https://github.com/"):
            return "github"

        # If source is an S3 location, then we can just use it
        if source.startswith("s3://"):
            return "s3"

        # If source is a local zip file, then we can just use it
        if source.endswith(".zip"):
            return "local"

    def get_version(self, source: str, src_type: str, ver: str) -> str:
        """Get the version of the source
        For GitHub, this is either "latest", "commit:latest", "release:latest", or "release:<tag>"
        For S3, this is "latest" or the version_id
        For local, this is always "latest"
        """

        if src_type == "":
            src_type = self.get_type(source)

        if src_type == "github":
            if '/archive/refs/heads/' in source:
                return "commit:latest"
            elif source.endswith('.zip') and '/archive/refs/tags/' in source:
                # get release tag from source
                tag = source.split('/')[-1].split('-')[-1].split('.')[0]
                return f"release:{tag}"
            elif '/archive/refs/tags/' in source:
                return "release:latest"
            elif ver.startswith("release:"):
                return ver
            elif ver == "release:latest":
                return "release:latest"
            elif ver == "commit:latest":
                return "commit:latest"
            elif ver == "":
                return "release:latest"
            else:
                raise click.UsageError(f"Invalid GitHub source/ver combo: {ver} from {source}")
        elif src_type == "s3":
            # valid source is:
            # s3://bucket/path/to/file.zip
            # s3://bucket/path/to/file.zip?versionId=version_id
            # s3://bucket
            if '?versionId=' in source:
                return source.split('?versionId=')[-1]
            elif ver != "latest" and ver != "":
                return ver
            else:
                return "latest"
        elif src_type == "local":
            return "latest"
        else:
            raise click.UsageError(f"Invalid source/ver combo: {ver} from {source}")
    
    def update_source(self, source: str, src_type: str, ver: str) -> str:
        """Using the source, src_type, and ver, generate the full urls needed"""

        # https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/archive/refs/heads/main.zip
        # https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/archive/refs/tags/v1.1.4.zip
        # s3://63klabs/atlantis/utilities/v2/config_scripts.zip

        if src_type == "github":
            # Get owner and repo from source
            result = self.get_github_repo_info(self.source)
            owner = result['owner']
            repo = result['repo']

            if ver == "commit:latest":
                return f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
            elif ver.startswith("release:"):
                if ver == "release:latest":
                    try:
                        tag = self.get_latest_github_release(owner, repo)
                        ConsoleAndLog.info(f"Latest release tag: {tag}")
                    except Exception as e:
                        ConsoleAndLog.error(f"Error getting latest release tag: {e}")
                        Log.error(f"Error occurred at:\n{traceback.format_exc()}")
                        return ""
                else:
                    tag = ver.split(':')[1]

                return f"https://github.com/{owner}/{repo}/archive/refs/tags/{tag}.zip"

        elif src_type == "s3":
            if '?versionId=' in source:
                t_split = source.split('?versionId=')
                source = t_split[0]
                ver = source.split('?versionId=')[-1]

            # Get bucket and path from source
            bucket = source.split('/')[2]
            path = '/'.join(source.split('/')[3:])

            # if path is blank or / then use default
            if path == "" or path == "/":
                path = f"{DEFAULT_S3_PATH}config_scripts.zip"

            if ver == "latest":
                return f"s3://{bucket}{path}"
            else:
                return f"s3://{bucket}{path}?versionId={ver}"

        elif src_type == "local":
            # if local path exists and ends with zip then return source
            if os.path.exists(source) and source.endswith('.zip'):
                return source
            else:
                raise click.UsageError(f"Invalid local path: {source}")
        else:
            raise click.UsageError(f"Invalid source/ver combo: {ver} from {source}")

    def get_github_repo_info(self, source: str) -> Dict:
        """
        Get the owner and repo from a GitHub repository URL

        Args:
            source (str): GitHub repository URL

        Returns:
            Dict: Dictionary containing owner and repo
        """
        try:
            # Split the URL into parts
            parts = source.split('/')

            # Get the owner and repo from the URL
            owner = parts[3]
            repo = parts[4]
            tag = ""

            # if source ends with .zip then it is a release
            if source.endswith('.zip'):
                tag = source.split('/')[-1].split('-')[-1].split('.')[0]

            return {
                'owner': owner,
                'repo': repo,
                'tag': tag
            }

        except IndexError:
            ConsoleAndLog.error(f"Invalid GitHub repository URL {source}")
            raise Exception("Invalid GitHub repository URL")
        
    def get_latest_github_release(owner: str, repo: str) -> str:
        """
        Get the latest release tag from a GitHub repository
        
        Args:
            owner (str): GitHub repository owner
            repo (str): GitHub repository name
        
        Returns:
            str: Latest release tag (e.g. 'v1.0.0')
        """
        try:
            # Query the GitHub API for latest release
            response = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
                headers={
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            response.raise_for_status()
            
            # Extract the tag name from the response
            return response.json()['tag_name']
            
        except requests.exceptions.RequestException as e:
            ConsoleAndLog.error(f"Failed to get latest release {str(e)}");
            raise Exception(f"Failed to get latest release: {str(e)}")
        
    def download_zip(self) -> None:
        # Create a temporary file with .zip extension
        ConsoleAndLog.info(f"Downloading zip file from {self.source}")
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            if self.src_type == "github":
                try:
                    response = requests.get(self.source)
                    response.raise_for_status()
                    temp_zip.write(response.content)
                    return temp_zip.name
                except Exception as e:
                    ConsoleAndLog.error(f"Error downloading zip file: {str(e)}")
                    Log.error(f"Error occurred at:\n{traceback.format_exc()}")
                    return False
                    
            elif self.src_type == "s3":
                try:
                    # Get bucket and path from source
                    t_source = self.source.split('?versionId=')
                    ver = t_source[-1]
                    bucket = t_source[0].split('/')[2]
                    path = '/'.join(t_source[0].split('/')[3:])

                    # Get the object from S3
                    params = {
                        'Bucket': bucket,
                        'Key': path
                    }
                    if ver:
                        params['VersionId'] = ver
                        
                    response = self.s3_client.get_object(**params)
                    temp_zip.write(response['Body'].read())
                    return temp_zip.name
                except Exception as e:
                    ConsoleAndLog.error(f"Error downloading zip file: {str(e)}")
                    Log.error(f"Error occurred at:\n{traceback.format_exc()}")
                    return False
            elif self.src_type == "local":
                # if local path exists and ends with zip then return source
                if os.path.exists(self.source) and self.source.endswith('.zip'):
                    return self.source
                else:
                    raise click.UsageError(f"Invalid local path: {self.source}")
            else:
                raise click.UsageError(f"Invalid source/ver combo: {self.src_ver} from {self.source}")

    def update_from_zip(self, zip_location):
        """Update specified directories from zip file that was downloaded to temp"""
        ConsoleAndLog.info(f"Updating from zip file: {zip_location}")
        try:

            # If the zip file is from github, then the extracted base path will be repo-tag
            zipped_dir = ""
            if self.src_type == "github":
                result = self.get_github_repo_info(self.source)
                repo = result['repo']
                tag = result['tag']

                if tag == "":
                    tag = "main"
                zipped_dir = f"{repo}-{tag}/"

            with zipfile.ZipFile(zip_location, 'r') as zip_ref:
                # Extract only the directories we want
                for file_info in zip_ref.filelist:
                    for target_dir in self.target_dirs:
                        src_dir = zipped_dir + target_dir + '/'
                        if file_info.filename.startswith(src_dir):
                            try:
                                # Get the relative path by removing the source directory prefix
                                relative_path = file_info.filename[len(src_dir):]
                                
                                # Create the full destination path
                                dest_path = os.path.join(target_dir, relative_path)

                                # Ensure the destination path is safe
                                dest = os.path.abspath(dest_path)
                                if not dest.startswith(os.path.abspath(target_dir)):
                                    raise ValueError("Attempted path traversal in zip file")
                                
                                # Create parent directories if they don't exist
                                os.makedirs(os.path.dirname(dest), exist_ok=True)
                                
                                ConsoleAndLog.info(f"Extracting {file_info.filename} to {dest}")

                                # Add your existing extension validation
                                allowed_extensions = {'.py', '.sh', '.md', '.txt', '.json', '.toml', '.gitignore'}
                                if not os.path.splitext(file_info.filename)[1].lower() in allowed_extensions:
                                    ConsoleAndLog.warning(f"Skipping file with unauthorized extension: {file_info.filename}")
                                    continue

                                # Extract the file content and write it to the correct location
                                with zip_ref.open(file_info) as source, open(dest, 'wb') as target:
                                    target.write(source.read())

                            except Exception as e:
                                ConsoleAndLog.error(f"Failed to extract {file_info.filename}: {str(e)}")
                                Log.error(f"Error occurred at:\n{traceback.format_exc()}")

                                # # Extract the file to the target directory
                                # dest = os.path.join(target_dir, os.path.basename(file_info.filename))
                                # ConsoleAndLog.info(f"Extracting {file_info.filename} to {dest}")
                                # zip_ref.extract(file_info, dest)
                            
        except Exception as e:
            ConsoleAndLog.error(f"Error updating from zip: {str(e)}")
            Log.error(f"Error occurred at:\n{traceback.format_exc()}")
            return False
        
        return True
    
# =============================================================================
# ----- Main function ---------------------------------------------------------
# =============================================================================

EPILOG = """
Supports both AWS SSO and IAM credentials.
For SSO users, credentials will be refreshed automatically.
For IAM users, please ensure your credentials are valid using 'aws configure'.

Update from a zip (S3, local or https), github repo release, or git repository (git)

For settings, update settings.json in the defaults directory.

Examples:

    # Basic
    update.py 
    
    # Use specific AWS profile
    update.py --profile <yourprofile>

Settings (defaults/settings.json):

-- Update using latest commit from GitHub: --

{
	"updates": {
		"src": "https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments",
		"ver": "commit:latest",
		"target_dirs": [ "docs", "scripts" ]
	}
}

-- Update using a latest release from GitHub --

{
	"updates": {
		"src": "https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments",
		"ver": "release:latest",
		"target_dirs": [ "docs", "scripts" ]
	}
}

-- Update using a zip from local, S3, or https (version_id is only available for S3) --

{
	"updates": {
		"src": "S3://63klabs/atlantis/utils/config-scripts.zip",
        "ver": "latest",
		"target_dirs": [ "docs", "scripts" ]
	}
}

Version:

GitHub Commit (archive/refs/head): if using latest commit as source, "commit:latest" 
GitHub Release (archive/refs/tags): "release:latest" or "release:<version>"
S3: "latest" or S3 Object Version ID

If a GitHub repo url is used and "ver" is not provided, "release:latest" is default.
If a S3 location is used and "ver" is not provided, "latest" is default.

ONLY USE TRUSTED SOURCES

Target Directories:

"docs" and "scripts" are the only valid target_dirs. You can include one, both, or leave target_dirs as [] (never update even when script is run)

    - docs : overwrites docs/*
    - scripts : overwrites scripts/*

It is recommended you store custom docs and scripts outside the provided directories. 
"""

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description='Update Scripts and Documentation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(EPILOG)
    )

    parser.add_argument('--profile',
                        required=False,
                        default=None,
                        help='AWS credential profile name')
    
    args = parser.parse_args()
        
    return args


def main():

    success = False
    zip_loc = None

    try:
        args = parse_args()
        Log.info(f"{sys.argv}")
        Log.info(f"Version: {VERSION}")
        
        print()
        click.echo(Colorize.divider("="))
        click.echo(Colorize.output_bold(f"Update Manager ({VERSION})"))
        click.echo(Colorize.divider("="))
        print()

        try:
            update_manager = UpdateManager(args.profile)
            zip_loc = update_manager.download_zip()
            success = update_manager.update_from_zip(zip_loc)
        except TokenRetrievalError as e:
            ConsoleAndLog.error(f"AWS authentication error: {str(e)}")
            Log.error(f"Error occurred at:\n{traceback.format_exc()}")
            sys.exit(1)
        except Exception as e:
            ConsoleAndLog.error(f"Error initializing update manager: {str(e)}")
            Log.error(f"Error occurred at:\n{traceback.format_exc()}")
            sys.exit(1)
        finally:
            if zip_loc and os.path.exists(zip_loc):
                os.remove(zip_loc)
                ConsoleAndLog.info(f"Temporary zip file {zip_loc} removed")

        if success:
            ConsoleAndLog.info("Update completed successfully!")
        else:
            ConsoleAndLog.error("Update failed!")

    except Exception as e:
        ConsoleAndLog.error(f"Unexpected error: {str(e)}")
        Log.error(f"Error occurred at:\n{traceback.format_exc()}")
        sys.exit(1)
    finally:
        return success

if __name__ == '__main__':
    main()
