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
import subprocess
import traceback
from typing import Dict, Optional

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
DEFAULT_GITHUB_REPO = "chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments"
DEFAULT_S3_BUCKET = "63klabs"
DEFAULT_S3_PATH = "/atlantis/utilities/v2/"

TARGET_DIRS = ['docs', 'scripts']
DEFAULT_SRC = f"https://github.com/{DEFAULT_GITHUB_REPO}"
DEFAULT_SRC_VER = "release:latest"
SETTINGS_DIR = "defaults"

class UpdateManager:

    def __init__(self, profile: Optional[str] = None):

        self.profile = profile

        config_loader = ConfigLoader(
            settings_dir=self.get_settings_dir()
        )

        self.settings = config_loader.load_settings()

        # Assemble the source info
        update_settings = self.settings.get('updates', {})
        self.target_dirs = update_settings.get('target_dirs', TARGET_DIRS)
        self.source = update_settings.get('source', DEFAULT_SRC)
        ver = DEFAULT_SRC_VER if self.source == DEFAULT_SRC else ""
        self.src_type = self.get_type(self.source)
        self.src_ver = self.get_version(self.source, self.src_type, update_settings.get('ver', ver))
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
        if not self.source.lower().startswith(('https://github.com/', 's3://', '/')):
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

    def update_from_zip(self, zip_location: str ) -> bool:
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

                                # Check if we care about the file
                                if not self.is_allowed_file(file_info.filename):
                                    ConsoleAndLog.info(f"Skipping file based on extension: {file_info.filename}")
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
    
    def is_allowed_file(self, filename: str) -> bool:
        # Define allowed files
        allowed_extensions = {'.py', '.sh', '.md', '.txt', '.json', '.toml'}
        allowed_filenames = {'.gitignore'}
        
        # Check if it's a special filename first
        if filename in allowed_filenames:
            return True
            
        # Check extensions
        file_extension = os.path.splitext(filename)[1].lower()
        return file_extension in allowed_extensions
    
# =============================================================================
# ----- GitOperations Class ---------------------------------------------------
# =============================================================================

class GitOperationsManager:
    def __init__(self):
        self.original_branch = None
        self.target_branch = None

    def confirm_update(self) -> bool:
        """Prompt user to confirm the update"""
        ConsoleAndLog.info("\nWARNING: This will update files in your repository.")
        ConsoleAndLog.info("Type 'UPDATE' to continue:")
        response = input().strip()
        return response == "UPDATE"

    def get_current_branch(self) -> str:
        """Get the name of the current branch"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            ConsoleAndLog.error(f"Failed to get current branch: {str(e)}")
            Log.error(f"Error occurred at:\n{traceback.format_exc()}")
            raise

    def confirm_branch(self) -> bool:
        """Confirm branch selection and handle branch switching"""
        try:
            self.original_branch = self.get_current_branch()
            ConsoleAndLog.info(f"\nCurrently on branch: {self.original_branch}")
            ConsoleAndLog.info("Continue with current branch? (Y/N):")
            
            if input().strip().lower() != 'y':
                ConsoleAndLog.info("Enter branch name to checkout:")
                new_branch = input().strip()
                
                # Verify branch exists
                result = subprocess.run(
                    ["git", "branch", "--list", new_branch],
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                if not result.stdout.strip():
                    ConsoleAndLog.info(f"Branch '{new_branch}' does not exist. Create it? (Y/N):")
                    if input().strip().lower() == 'y':
                        subprocess.run(
                            ["git", "checkout", "-b", new_branch],
                            check=True
                        )
                        ConsoleAndLog.info(f"Created and checked out new branch: {new_branch}")
                    else:
                        return False
                else:
                    subprocess.run(
                        ["git", "checkout", new_branch],
                        check=True
                    )
                    ConsoleAndLog.info(f"Checked out existing branch: {new_branch}")
                
                self.target_branch = new_branch
            else:
                self.target_branch = self.original_branch
            
            return True
            
        except subprocess.CalledProcessError as e:
            ConsoleAndLog.error(f"Git operation failed: {str(e)}")
            Log.error(f"Error occurred at:\n{traceback.format_exc()}")
            return False

    def pull_changes(self) -> bool:
        """Pull latest changes from remote"""
        try:
            ConsoleAndLog.info("\nWould you like to pull latest changes? (Y/N):")
            if input().strip().lower() == 'y':
                ConsoleAndLog.info("Pulling latest changes...")
                subprocess.run(
                    ["git", "pull"],
                    check=True
                )
                return True
            return False
        except subprocess.CalledProcessError as e:
            ConsoleAndLog.error(f"Failed to pull changes: {str(e)}")
            Log.error(f"Error occurred at:\n{traceback.format_exc()}")
            return False

    def cleanup(self) -> None:
        """Cleanup and restore original branch if needed"""
        if (self.original_branch and 
            self.target_branch and 
            self.original_branch != self.target_branch):
            try:
                ConsoleAndLog.info(f"\nSwitching back to original branch: {self.original_branch}")
                subprocess.run(
                    ["git", "checkout", self.original_branch],
                    check=True
                )
            except subprocess.CalledProcessError as e:
                ConsoleAndLog.error(f"Failed to restore original branch: {str(e)}")
                Log.error(f"Error occurred at:\n{traceback.format_exc()}")

# =============================================================================
# ----- Main function ---------------------------------------------------------
# =============================================================================

EPILOG = """
Supports both AWS SSO and IAM credentials.
For SSO users, credentials will be refreshed automatically.
For IAM users, please ensure your credentials are valid using 'aws configure'.

Update from a zip stored locally or downloaded from s3 or GitHub (commit or release)

For settings, update settings.json in the defaults directory (see below for samples).

Examples:

    # Basic
    update.py 
    
    # Use specific AWS profile
    update.py --profile <yourprofile>

-----------------
Settings (defaults/settings.json):

The latest release from the GitHub repository will be used by default if no "updates" property is specified in settings.json 

Otherwise, you can customize where updates are downloaded from:

-- Update using a latest release from GitHub --

{
	"updates": {
		"source": "https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments",
		"ver": "release:latest",
		"target_dirs": [ "docs", "scripts" ]
}


}-- Update using latest commit from GitHub: --

{
	"updates": {
		"source": "https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments",
		"ver": "commit:latest",
		"target_dirs": [ "docs", "scripts" ]
	}
}

-- Update using a zip from local or S3 (version_id is only available for S3) --

{
	"updates": {
		"source": "s3://63klabs/atlantis/utilities/v2/config_scripts.zip",
        "ver": "latest",
		"target_dirs": [ "docs", "scripts" ]
	}
}

{
	"updates": {
		"source": "s3://63klabs/atlantis/utilities/v2/config_scripts.zip",
        "ver": "74ssh_some-version-12345",
		"target_dirs": [ "docs", "scripts" ]
	}
}

{
	"updates": {
		"source": "~/downloaded.zip",
		"target_dirs": [ "docs", "scripts" ]
	}
}

https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments
https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/archive/refs/heads/main.zip
https://github.com/chadkluck/atlantis-cfn-configuration-repo-for-serverless-deployments/archive/refs/tags/v0.0.1.zip
s3://63klabs/atlantis/utilities/v2/config_scripts.zip
s3://63klabs # since this is known, the script will fill in the path itself

------------------
Version:

GitHub Commit (archive/refs/head): if using latest commit as source, "commit:latest" 
GitHub Release (archive/refs/tags): "release:latest" or "release:<version>"
S3: "latest" or S3 Object Version ID

If a GitHub repo url is used and "ver" is not provided, "release:latest" is default.
If a S3 location is used and "ver" is not provided, "latest" is default.

ONLY USE TRUSTED SOURCES - You can host your own s3 bucket or GitHub repository or use the ones offered by 63klabs and chadkluck 

-----------------
Target Directories:

"docs" and "scripts" are the only valid target_dirs. You can include one, both, or leave target_dirs as [] (never update even when script is run)

    - docs : overwrites docs/*
    - scripts : overwrites scripts/*

It is recommended you store custom docs and scripts OUTSIDE the provided directories. While update.py does not currently delete files, it will replace any with conflicting names.

-----------------
Self-Hosted ZIPs

The update script will automatically extract files from the "<repository-name>-main" directory within the ZIP when GitHub is the source.

ALL OTHER ZIPS (s3 and locally downloaded) MUST have all files in the base directory of the zip file.

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
    git_manager = GitOperationsManager()

    try:
        args = parse_args()
        Log.info(f"{sys.argv}")
        Log.info(f"Version: {VERSION}")
        
        print()
        click.echo(Colorize.divider("="))
        click.echo(Colorize.output_bold(f"Update Manager ({VERSION})"))
        click.echo(Colorize.divider("="))
        print()

        # Get confirmation to proceed
        if not git_manager.confirm_update():
            ConsoleAndLog.info("Update cancelled by user.")
            return False

        # Handle branch selection and switching
        if not git_manager.confirm_branch():
            ConsoleAndLog.info("Branch operation cancelled by user.")
            return False

        # Pull changes if requested
        git_manager.pull_changes()

        # Perform Update
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
        # Always try to restore original branch
        git_manager.cleanup()
        return success

if __name__ == '__main__':
    main()
