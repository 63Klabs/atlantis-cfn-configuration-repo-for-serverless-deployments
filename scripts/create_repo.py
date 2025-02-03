#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-22"
# Created by Chad Kluck with AI assistance from Amazon Q Developer

import tempfile
import zipfile
import base64
import os
import argparse
import sys
from typing import Optional, List
from urllib.parse import urlparse

from lib.aws_session import AWSSessionManager
from lib.logger import ScriptLogger, ConsoleAndLog, Log

if sys.version_info[0] < 3:
    sys.stderr.write("Error: Python 3 is required\n")
    sys.exit(1)

# Initialize logger for this script
ScriptLogger.setup('create_repo')

class RepositoryCreator:

    def __init__(self, repo_name: str, s3_uri: str, region:  Optional[str] = None, profile: Optional[str] = None) -> None:
        self.repo_name = repo_name
        self.s3_uri = s3_uri
        self.region = region
        self.profile = profile
        
        self.aws_session = AWSSessionManager(self.profile, self.region)
        self.s3_client = self.aws_session.get_client('s3', self.region)
        self.codecommit_client = self.aws_session.get_client('codecommit', self.region)

    def parse_s3_url(self, s3_uri: str) -> List[str]:
        """Parse an S3 URL into bucket and key."""
        try:
            parsed = urlparse(s3_uri)
            if parsed.scheme != 's3':
                raise ValueError("URL must be an S3 URL starting with 's3://'")
            return parsed.netloc, parsed.path.lstrip('/')
        except ValueError as e:
            ConsoleAndLog.error(f"Error: {str(e)}")
            sys.exit(1)

    def create_and_seed_repository(self):

        # Parse S3 URL
        s3_bucket, s3_key = self.parse_s3_url(self.s3_uri)

        # Create the repository
        try:
            ConsoleAndLog.info(f"Creating repository: {self.repo_name}")
            response = self.codecommit_client.create_repository(
                repositoryName=self.repo_name,
                repositoryDescription=f'Repository seeded from {self.s3_uri}'
            )
            ConsoleAndLog.info(f"Repository created: {response['repositoryMetadata']['cloneUrlHttp']}")
        except self.codecommit_client.exceptions.RepositoryNameExistsException:
            ConsoleAndLog.error(f"Error: Repository {self.repo_name} already exists")
            sys.exit(1)
        except Exception as e:
            ConsoleAndLog.error(f"Error creating repository: {str(e)}")
            sys.exit(1)
        
        # Download and process the zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'source.zip')
            
            try:
                ConsoleAndLog.info(f"Downloading zip from S3: {self.s3_uri}")
                self.s3_client.download_file(s3_bucket, s3_key, zip_path)
            except Exception as e:
                ConsoleAndLog.error(f"Error downloading zip file: {str(e)}")
                self.codecommit_client.delete_repository(repositoryName=self.repo_name)
                sys.exit(1)
            
            # Extract files
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                os.remove(zip_path)  # Remove the zip file to not include it
            except Exception as e:
                ConsoleAndLog.error(f"Error extracting zip file: {str(e)}")
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
                        ConsoleAndLog.error(f"Error processing file {relative_path}: {str(e)}")
                        self.codecommit_client.delete_repository(repositoryName=self.repo_name)
                        sys.exit(1)

            # Create initial commit
            try:
                ConsoleAndLog.info("Creating initial commit")
                self.codecommit_client.create_commit(
                    repositoryName=self.repo_name,
                    branchName='main',
                    putFiles=put_files,
                    commitMessage=f'Initial commit: Seeded from {self.s3_uri}'
                )
                ConsoleAndLog.info(f"\nRepository {self.repo_name} seeded successfully!")
                ConsoleAndLog.info(f"Clone URL (HTTPS): {response['repositoryMetadata']['cloneUrlHttp']}")
                ConsoleAndLog.info(f"Clone URL (SSH): {response['repositoryMetadata']['cloneUrlSsh']}")
            except Exception as e:
                ConsoleAndLog.error(f"Error creating initial commit: {str(e)}")
                self.codecommit_client.delete_repository(repositoryName=self.repo_name)
                sys.exit(1)

# =============================================================================
# ----- Main function ---------------------------------------------------------
# =============================================================================

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description='Create and seed a CodeCommit repository from an S3 zip file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Supports both AWS SSO and IAM credentials."
            "For SSO users, credentials will be refreshed automatically."
            "For IAM users, please ensure your credentials are valid using 'aws configure'."
            ""
            "Examples:"
            ""
            "    # Create repository and load code from zip"
            "    create_repo.py <repo-name> --s3-uri <s3://bucket/path/to/file.zip>"
            ""
            "    # Create repository and load code from zip using profile"
            "    create_repo.py <repo-name> --s3-uri <s3://bucket/path/to/file.zip> --profile <profile>"
        )
    )
    parser.add_argument('repository_name',
                        required=True,
                        help='Name of the CodeCommit repository to create')
    parser.add_argument('--s3-uri',
                        required=True,
                        help='S3 URL of the zip file (e.g., s3://bucket-name/path/to/file.zip)')
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

    repo_creator = RepositoryCreator(args.repository_name, args.s3_uri, args.region, args.profile)
    repo_creator.create_and_seed_repository()

if __name__ == "__main__":
    main()
