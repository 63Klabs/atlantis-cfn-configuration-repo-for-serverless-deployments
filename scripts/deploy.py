#!/usr/bin/env python3

# TODO: Add local file deploy
# TODO: Add additional error logging
# TODO: Update user messages

import sys

if sys.version_info[0] < 3:
    sys.stderr.write("Error: Python 3 is required\n")
    sys.exit(1)

import os
import tempfile
import boto3
import subprocess
import logging
import argparse
import tomli  # Make sure to pip install tomli
from pathlib import Path
from typing import Tuple, Optional
from botocore.exceptions import ClientError, TokenRetrievalError

class TemplateDeployer:
    def __init__(self, config_dir: str, profile: Optional[str] = None) -> None:
        self.profile = profile
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(__name__)
        
        # Initialize AWS session and client
        self.refresh_credentials()

    def refresh_credentials(self) -> None:
        """Initialize or refresh AWS credentials"""
        if self.profile:
            self.logger.info(f"Using AWS profile: {self.profile}")
            
            try:
                # First attempt to create session
                self.session = boto3.Session(profile_name=self.profile)
                credentials = self.session.get_credentials()
                
                # Verify credentials are valid
                if not credentials:
                    self.logger.info("No credentials found. Attempting to refresh SSO login...")
                    self._refresh_sso_login()
                    self.session = boto3.Session(profile_name=self.profile)
                
                self.s3_client = self.session.client('s3')
                
            except (TokenRetrievalError, ClientError) as e:
                self.logger.error(f"Error with credentials: {str(e)}")
                self.logger.info("Attempting to refresh SSO login...")
                self._refresh_sso_login()
                self.session = boto3.Session(profile_name=self.profile)
                self.s3_client = self.session.client('s3')
        else:
            self.session = boto3.Session()
            self.s3_client = self.session.client('s3')

    def _refresh_sso_login(self) -> None:
        """Execute AWS SSO login command"""
        try:
            # Use shell=True on Windows to find aws.exe in PATH
            self.logger.info(f"Running: aws sso login --profile {self.profile}")
            result = subprocess.run(
                f"aws sso login --profile {self.profile}",
                check=True,
                capture_output=True,
                text=True,
                shell=True if os.name == 'nt' else False  # Use shell on Windows
            )
            if result.stdout:
                self.logger.info(result.stdout)
            if result.stderr:
                self.logger.error(result.stderr)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to refresh SSO login: {str(e)}")
            raise

    def get_template_from_config(self, config_file: str, stage_id: str) -> str:
        """
        Read template URL from samconfig.toml file.
        
        Args:
            config_file: Path to samconfig.toml
            stage_id: Stage ID to look up parameters
            
        Returns:
            str: Template URL from config file
            
        Raises:
            ValueError: If template parameter is not found in config
        """
        config_path = self.config_dir / config_file
        try:
            with open(config_path, 'rb') as f:
                config = tomli.load(f)
            
            # Look for template parameter in stage-specific section
            template_param = config.get('default', {}).get('deploy', {}).get('parameters', {}).get('template_file')
            stage_template = config.get(stage_id, {}).get('deploy', {}).get('parameters', {}).get('template_file')
            
            # Use stage-specific template if available, otherwise fall back to default
            template_url = stage_template or template_param
            
            if not template_url:
                raise ValueError(f"Template parameter not found in config file for stage '{stage_id}'")
                
            return template_url
            
        except FileNotFoundError:
            raise ValueError(f"Config file not found: {config_path}")
        except tomli.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML format in config file: {str(e)}")

    def parse_s3_url(self, s3_url: str) -> tuple[str, str, Optional[str]]:
        """
        Parse S3 URL into bucket, key, and optional version ID.
        
        Args:
            s3_url: The S3 URL to parse (e.g., s3://bucket/key or s3://bucket/key?versionId=abc123)
            
        Returns:
            Tuple containing (bucket_name, object_key, version_id)
            
        Raises:
            ValueError: If the S3 URL format is invalid
        """
        if not s3_url.startswith('s3://'):
            raise ValueError(f"Invalid S3 URL format: {s3_url}")
        
        # Split URL and query parameters
        url_parts = s3_url.replace('s3://', '').split('?')
        path_parts = url_parts[0].split('/')
        
        if len(path_parts) < 2:
            raise ValueError(f"Invalid S3 URL format: {s3_url}")
        
        bucket = path_parts[0]
        key = '/'.join(path_parts[1:])
        version_id = None
        
        # Parse query parameters for versionId
        if len(url_parts) > 1:
            query_params = dict(param.split('=') for param in url_parts[1].split('&'))
            version_id = query_params.get('versionId')
            
        return bucket, key, version_id

    def verify_s3_object_exists(self, bucket: str, key: str, version_id: Optional[str] = None) -> bool:
        """
        Verify S3 object exists and is accessible.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            version_id: Optional version ID
            
        Returns:
            bool: True if object exists and is accessible, False otherwise
        """
        try:
            params = {'Bucket': bucket, 'Key': key}
            if version_id:
                params['VersionId'] = version_id
            
            self.s3_client.head_object(**params)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                self.logger.error(f"Template file not found: s3://{bucket}/{key}" + 
                                (f"?versionId={version_id}" if version_id else ""))
            else:
                self.logger.error(f"Error accessing S3: {str(e)}")
            return False

    def deploy_with_temp_template(self, template_path: str, config_file: str) -> int:
        """
        Deploy template from either S3 or local file.
        
        Args:
            template_path: Either S3 URL (s3://) or local file path
            config_file: Path to samconfig.toml
            
        Returns:
            int: Return code from sam deploy
        """
        try:
            # Ensure config file exists
            config_path = self.config_dir / config_file
            if not config_path.exists():
                self.logger.error(f"Config file not found: {config_path}")
                return 1

            if template_path.startswith('s3://'):
                # Handle S3 template
                bucket, key, version_id = self.parse_s3_url(template_path)
                
                # Verify template exists
                if not self.verify_s3_object_exists(bucket, key, version_id):
                    return 1

                # Create temp directory for S3 download
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir) / "template.yml"
                    
                    self.logger.info(f"Downloading template from s3://{bucket}/{key}" +
                                (f"?versionId={version_id}" if version_id else ""))
                    
                    try:
                        get_args = {
                            'Bucket': bucket,
                            'Key': key
                        }
                        if version_id:
                            get_args['VersionId'] = version_id

                        response = self.s3_client.get_object(**get_args)
                        with open(temp_path, 'wb') as f:
                            f.write(response['Body'].read())

                    except ClientError as e:
                        if 'ExpiredToken' in str(e):
                            self.logger.info("Token expired, refreshing credentials...")
                            self.refresh_credentials()
                            response = self.s3_client.get_object(**get_args)
                            with open(temp_path, 'wb') as f:
                                f.write(response['Body'].read())
                        else:
                            self.logger.error(f"Failed to download template: {str(e)}")
                            return 1

                    return self._run_sam_deploy(temp_path, config_path)
            else:
                # Handle local template
                local_template_path = self.config_dir / template_path
                if not local_template_path.exists():
                    self.logger.error(f"Local template file not found: {local_template_path}")
                    return 1
                    
                self.logger.info(f"Using local template: {local_template_path}")
                return self._run_sam_deploy(local_template_path, config_path)

        except Exception as e:
            self.logger.error(f"Deployment failed: {str(e)}")
            raise

    def _run_sam_deploy(self, template_path: Path, config_path: Path) -> int:
        """
        Execute the SAM deploy command.
        
        Args:
            template_path: Path to the template file
            config_path: Path to the config file
            
        Returns:
            int: Return code from sam deploy
        """
        sam_cmd = [
            "sam.cmd" if os.name == 'nt' else "sam",
            "deploy",
            "--template-file", str(template_path),
            "--config-file", str(config_path),
            "--no-fail-on-empty-changeset"
        ]
        
        if self.profile:
            sam_cmd.extend(["--profile", self.profile])
        
        self.logger.info(f"Executing: {' '.join(sam_cmd)}")
        
        result = subprocess.run(
            sam_cmd,
            cwd=self.config_dir,
            check=False,
            stdout=None,
            stderr=None,
            shell=True if os.name == 'nt' else False,
            env={
                **os.environ,
                'FORCE_COLOR': '1',
                'TERM': 'xterm-256color' if os.name != 'nt' else os.environ.get('TERM', '')
            }
        )
        
        return result.returncode

# def parse_args() -> argparse.Namespace:
#     # Get the script's directory
#     script_dir = Path(__file__).resolve().parent
#     samconfigs_dir = script_dir.parent / "samconfigs"

def parse_args() -> argparse.Namespace:
    # Get the script's directory in a cross-platform way
    script_dir = Path(__file__).resolve().parent
    samconfigs_dir = script_dir.parent / "samconfigs"

    parser = argparse.ArgumentParser(
        description='Deploy CloudFormation template from S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
            # Deploy service-role for acme prefix and project
            deploy.py service-role acme project123

            # Deploy pipeline for specific project and stage
            deploy.py pipeline acme project123 dev

            # With different AWS profile
            deploy.py service-role acme project123 --profile myprofile
                """
    )
    
    # Positional arguments
    parser.add_argument('infra_type',
                       help='Type of infrastructure to deploy (e.g., pipeline)')
    parser.add_argument('prefix',
                       help='Prefix/org unit (e.g., acme)')
    parser.add_argument('project_id',
                       help='Project ID')
    parser.add_argument('stage_id',
                       nargs='?',  # Makes it optional
                       default='default',
                       help='Stage ID (optional, defaults to "default")')
    
    # Optional arguments
    parser.add_argument('--profile', 
                       help='AWS profile name to use',
                       default="release")
    
    args = parser.parse_args()
    
    # Construct config directory and file paths using relative path
    args.config_dir = str(samconfigs_dir / args.prefix / args.project_id)
    args.config_file = f"samconfig-{args.prefix}-{args.project_id}-{args.infra_type}.toml"
    
    return args

def main() -> int:
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Parse command line arguments
    args = parse_args()
    
    # Log the constructed paths
    logging.info(f"Config directory: {args.config_dir}")
    logging.info(f"Config file: {args.config_file}")
    
    # Verify config directory exists
    if not Path(args.config_dir).exists():
        logging.error(f"Config directory not found: {args.config_dir}")
        return 1
    
    # Initialize deployer with profile if specified
    deployer = TemplateDeployer(args.config_dir, args.profile)
    
    # Run deployment
    try:
        # Get template URL from config file
        template_url = deployer.get_template_from_config(args.config_file, args.stage_id)
        logging.info(f"Template URL from config: {template_url}")
        
        exit_code = deployer.deploy_with_temp_template(template_url, args.config_file)
        if exit_code == 0:
            logging.info("Deployment completed successfully")
        else:
            logging.error(f"Deployment failed with exit code {exit_code}")
        return exit_code
    except ValueError as e:
        logging.error(str(e))
        return 1
    except Exception as e:
        logging.error(f"Deployment failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())